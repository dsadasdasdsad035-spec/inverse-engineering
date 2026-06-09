#!/usr/bin/env python3
"""run-pipeline 数据采集脚本：执行第 5-6 步（inventory + 逐文件精确路径查询 + 数量对账）。"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def exec_json(args, timeout=120):
    """执行命令并返回 (json_data, exit_code, duration_ms, stderr)"""
    start = time.time()
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        duration_ms = int((time.time() - start) * 1000)
        if proc.returncode != 0:
            return None, proc.returncode, duration_ms, proc.stderr
        out = proc.stdout.strip()
        if not out:
            return [], proc.returncode, duration_ms, ""
        try:
            return json.loads(out), proc.returncode, duration_ms, ""
        except json.JSONDecodeError:
            # 检查是否为 "无匹配文件" 类的信息
            if "no matching files" in out.lower() or "no files" in out.lower():
                return [], proc.returncode, duration_ms, ""
            return None, proc.returncode, duration_ms, f"非法 JSON: {out[:200]}"
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start) * 1000)
        return None, -1, duration_ms, "命令超时"
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        return None, -1, duration_ms, f"异常: {e}"


def query_file(source, file_path, index_total_nodes):
    """对单个文件执行精确路径查询，返回 (节点列表, 错误信息)"""
    args = [
        "codegraph", "query", "-p", source, "-l", str(index_total_nodes),
        "-j", f"path:{file_path}"
    ]
    data, code, duration, err = exec_json(args, timeout=60)
    if data is None:
        return None, {
            "file": file_path,
            "exit_code": code,
            "duration_ms": duration,
            "error": err,
            "args": args,
        }
    # 精确过滤：node.filePath == 当前文件
    filtered = [r for r in data if r.get("node", {}).get("filePath") == file_path]
    # 按 node.id 去重
    seen = set()
    unique = []
    for r in filtered:
        nid = r.get("node", {}).get("id")
        if nid and nid not in seen:
            seen.add(nid)
            unique.append(r)
    truncated = len(data) >= index_total_nodes
    return {
        "file": file_path,
        "results": unique,
        "raw_count": len(data),
        "filtered_count": len(filtered),
        "unique_count": len(unique),
        "duration_ms": duration,
        "truncated": truncated,
    }, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--entry-id", required=True)
    ap.add_argument("--entry-path", required=True)
    ap.add_argument("--include-patterns", nargs="+", default=["**/*"])
    ap.add_argument("--exclude-patterns", nargs="+", default=[])
    ap.add_argument("--output-root", required=True)
    ap.add_argument("--index-total-nodes", type=int, required=True)
    ap.add_argument("--parallel", type=int, default=4)
    args = ap.parse_args()

    evidence_dir = Path(args.output_root) / ".codebook" / "evidence" / args.entry_id
    evidence_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{args.entry_id}] 开始枚举文件 ...", flush=True)

    # 第 5 步：枚举文件
    all_files = []
    for pattern in args.include_patterns:
        files_args = [
            "codegraph", "files", "-p", args.source,
            "--filter", args.entry_path,
            "--pattern", pattern,
            "--format", "flat", "-j"
        ]
        data, code, duration, err = exec_json(files_args, timeout=120)
        if data is None:
            print(f"[{args.entry_id}] files 命令失败 pattern={pattern}: {err}", file=sys.stderr)
            sys.exit(1)
        all_files.extend(data)

    # 排除规则
    def excluded(p):
        for ex in args.exclude_patterns:
            # 简单匹配：包含子串
            tag = ex.replace("**/", "").replace("**", "").replace("*", "")
            if tag and tag.strip("/") in p:
                return True
        return False

    seen_paths = set()
    inventory = []
    for f in all_files:
        p = f.get("path")
        if not p or p in seen_paths:
            continue
        if excluded(p):
            continue
        seen_paths.add(p)
        inventory.append(f)

    inventory_path = evidence_dir / "inventory.json"
    inventory_path.write_text(json.dumps({
        "entry_id": args.entry_id,
        "entry_path": args.entry_path,
        "files": inventory,
        "total_files": len(inventory),
        "expected_symbols": sum(f.get("nodeCount", 0) for f in inventory),
    }, ensure_ascii=False, indent=2))
    print(f"[{args.entry_id}] inventory: {len(inventory)} 文件, "
          f"{sum(f.get('nodeCount', 0) for f in inventory)} 预期节点", flush=True)

    if not inventory:
        print(f"[{args.entry_id}] 无源码文件，标记 skipped", flush=True)
        return

    # 第 6 步：逐文件精确路径查询
    print(f"[{args.entry_id}] 开始逐文件查询，limit={args.index_total_nodes}, parallel={args.parallel}", flush=True)

    nodes_by_file = {}
    query_failures = []
    reconciliation_failures = []
    truncation_warnings = []

    completed = 0
    total = len(inventory)
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        future_to_file = {
            ex.submit(query_file, args.source, f["path"], args.index_total_nodes): f
            for f in inventory
        }
        for future in as_completed(future_to_file):
            f = future_to_file[future]
            result, error = future.result()
            completed += 1
            if completed % 25 == 0 or completed == total:
                print(f"[{args.entry_id}] 进度 {completed}/{total}", flush=True)
            if error is not None:
                query_failures.append(error)
                continue
            expected = f.get("nodeCount", 0)
            actual = result["unique_count"]
            nodes_by_file[f["path"]] = result["results"]
            if result["truncated"]:
                truncation_warnings.append({
                    "file": f["path"],
                    "raw_count": result["raw_count"],
                    "limit": args.index_total_nodes,
                    "warning": f"达到 limit {args.index_total_nodes}",
                })
            if actual != expected:
                reconciliation_failures.append({
                    "file": f["path"],
                    "expected": expected,
                    "actual": actual,
                    "raw_count": result["raw_count"],
                    "filtered_count": result["filtered_count"],
                    "error": f"原生符号数量对账失败：{f['path']}，预期 {expected}，实际 {actual}",
                })

    # 聚合所有节点 → nodes.json（按 node.id 全局去重）
    seen_ids = set()
    aggregated = []
    for path, results in nodes_by_file.items():
        for r in results:
            nid = r.get("node", {}).get("id")
            if nid and nid not in seen_ids:
                seen_ids.add(nid)
                aggregated.append(r)

    incomplete_files = [r["file"] for r in reconciliation_failures] + [r["file"] for r in query_failures]

    nodes_payload = {
        "entry_id": args.entry_id,
        "entry_path": args.entry_path,
        "nodes": aggregated,
        "nodes_by_file": nodes_by_file,
        "total_nodes": len(aggregated),
        "query_failures": query_failures,
        "reconciliation_failures": reconciliation_failures,
        "truncation_warnings": truncation_warnings,
        "incomplete_files": sorted(set(incomplete_files)),
        "symbol_enumeration_complete": (
            not query_failures and not reconciliation_failures
        ),
        "inventory_files": len(inventory),
        "enumerated_files": len(nodes_by_file),
        "expected_symbols": sum(f.get("nodeCount", 0) for f in inventory),
        "enumerated_symbols": sum(len(v) for v in nodes_by_file.values()),
    }
    (evidence_dir / "nodes.json").write_text(
        json.dumps(nodes_payload, ensure_ascii=False, indent=2)
    )

    print(f"[{args.entry_id}] 完成: 节点={len(aggregated)} "
          f"对账失败={len(reconciliation_failures)} "
          f"查询失败={len(query_failures)} "
          f"截断警告={len(truncation_warnings)} "
          f"完整={nodes_payload['symbol_enumeration_complete']}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
按 inventory.json 逐文件执行 codegraph query 收集节点，写入 nodes.json 与对账报告。
- 路径过滤: result.node.filePath == 当前文件
- 去重键: node.id
- 对账: enumerated_symbols (去重后) == file.nodeCount
"""
import json, os, sys, subprocess, time, argparse, hashlib

def run_query(source, file_path, limit):
    """执行 codegraph query，返回 JSON 结果。"""
    args = [
        "codegraph", "query",
        "-p", source,
        "-l", str(limit),
        "-j", f"path:{file_path}"
    ]
    start = time.time()
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=60)
        dur = (time.time() - start) * 1000
        if proc.returncode != 0:
            return None, proc.returncode, dur, proc.stderr.strip()
        # 解析 JSON
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            return None, -1, dur, f"JSON 解析失败: {e}"
        return data, proc.returncode, dur, ""
    except subprocess.TimeoutExpired:
        return None, -124, (time.time() - start) * 1000, "timeout"
    except FileNotFoundError as e:
        return None, -127, 0, str(e)


def collect_for_entry(source, inventory_path, out_nodes_path, out_reconcile_path, log_path, limit):
    with open(inventory_path) as f:
        inv = json.load(f)
    files = inv['files']
    print(f"[{inv['entry_id']}] 开始逐文件查询，共 {len(files)} 个文件")

    all_nodes = []
    incomplete = []
    reconciliation_failures = []
    query_failures = []
    executed = []
    enumerated_files = 0
    expected_total = 0
    enumerated_total = 0
    truncation_warnings = []

    for idx, fobj in enumerate(files):
        fpath = fobj['path']
        expected = fobj['nodeCount']
        expected_total += expected
        result, exit_code, dur, err = run_query(source, fpath, limit)
        cmd_args = ["codegraph","query","-p",source,"-l",str(limit),"-j",f"path:{fpath}"]
        executed.append({"args": cmd_args, "exit_code": exit_code, "duration_ms": round(dur,1)})

        if result is None:
            incomplete.append(fpath)
            query_failures.append({
                "file": fpath,
                "command": " ".join(cmd_args),
                "exit_code": exit_code,
                "error": err
            })
            if (idx+1) % 50 == 0:
                print(f"  进度 {idx+1}/{len(files)}，失败 {len(incomplete)}")
            continue

        # 提取 nodes 列表 - 多种可能结构
        nodes_raw = []
        if isinstance(result, dict):
            for key in ('nodes','results','data'):
                if key in result and isinstance(result[key], list):
                    nodes_raw = result[key]
                    break
            if not nodes_raw and 'node' in result:
                nodes_raw = [result]
        elif isinstance(result, list):
            nodes_raw = result

        # 严格过滤: node.filePath == 当前文件
        filtered = []
        for n in nodes_raw:
            node = n.get('node', n)
            fp = node.get('filePath', node.get('file_path',''))
            if fp == fpath:
                filtered.append(node)

        # 按 node.id 去重
        seen_ids = set()
        deduped = []
        for n in filtered:
            nid = n.get('id')
            if nid is None:
                # 兜底：构造 id
                nid = f"{n.get('name','')}_{n.get('filePath','')}_{n.get('startLine','')}_{n.get('endLine','')}"
            if nid in seen_ids:
                continue
            seen_ids.add(nid)
            deduped.append(n)

        actual = len(deduped)
        enumerated_total += actual

        if actual == expected:
            enumerated_files += 1
            all_nodes.extend(deduped)
        elif actual == 0 and expected == 0:
            # 空文件 - 视为完成
            enumerated_files += 1
        else:
            incomplete.append(fpath)
            reconciliation_failures.append({
                "file": fpath,
                "expected": expected,
                "actual": actual
            })

        if (idx+1) % 100 == 0 or idx == len(files)-1:
            print(f"  进度 {idx+1}/{len(files)}，已对账 {enumerated_files}，失败 {len(incomplete)}")

    # 写入 nodes.json（精简节点：id, name, filePath, startLine, endLine, kind, signature）
    nodes_compact = []
    for n in all_nodes:
        nodes_compact.append({
            "id": n.get("id"),
            "name": n.get("name"),
            "kind": n.get("kind") or n.get("native_kind"),
            "filePath": n.get("filePath"),
            "startLine": n.get("startLine"),
            "endLine": n.get("endLine"),
            "signature": n.get("signature") or n.get("raw","")[:200],
        })
    with open(out_nodes_path, 'w') as f:
        json.dump({
            "entry_id": inv['entry_id'],
            "source_path": source,
            "node_count": len(nodes_compact),
            "files_queried": len(files),
            "files_enumerated": enumerated_files,
            "expected_symbols": expected_total,
            "enumerated_symbols": enumerated_total,
            "incomplete_files": incomplete,
            "nodes": nodes_compact
        }, f, indent=2, ensure_ascii=False)

    # 对账报告
    symbol_enumeration_complete = (
        len(incomplete) == 0
        and enumerated_files == len(files)
        and enumerated_total == expected_total
    )
    reconcile = {
        "entry_id": inv['entry_id'],
        "inventory_files": len(files),
        "enumerated_files": enumerated_files,
        "expected_symbols": expected_total,
        "enumerated_symbols": enumerated_total,
        "incomplete_files": incomplete,
        "reconciliation_failures": reconciliation_failures,
        "query_failures": query_failures,
        "symbol_enumeration_complete": symbol_enumeration_complete,
        "executed_command_count": len(executed),
        "sample_executed": executed[:3] + (executed[-3:] if len(executed) > 6 else []),
    }
    with open(out_reconcile_path, 'w') as f:
        json.dump(reconcile, f, indent=2, ensure_ascii=False)
    print(f"[{inv['entry_id']}] 完成：对账 {enumerated_files}/{len(files)}，符号 {enumerated_total}/{expected_total}，完整={symbol_enumeration_complete}")
    return reconcile


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--entry", required=True)
    ap.add_argument("--limit", type=int, default=23996)
    ap.add_argument("--codebook-root", required=True)
    args = ap.parse_args()
    inv_path = f"{args.codebook_root}/evidence/{args.entry}/inventory.json"
    nodes_path = f"{args.codebook_root}/evidence/{args.entry}/nodes.json"
    reconcile_path = f"{args.codebook_root}/evidence/{args.entry}/reconciliation.json"
    collect_for_entry(args.source, inv_path, nodes_path, reconcile_path, None, args.limit)

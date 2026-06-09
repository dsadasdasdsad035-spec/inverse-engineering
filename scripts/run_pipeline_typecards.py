#!/usr/bin/env python3
"""第 7 步：对可分析节点批量采集 callers/callees 并生成 TypeCard。

策略：基于 codegraph 节点元数据 + 源码区间 + 调用图，按 output_schema 结构化生成 TypeCard。
attributes/behaviors/constraints/events 由机械化派生：
- attributes: 字段、签名片段、属性
- behaviors: callees + 节点 kind 推断的动作（如 component 的渲染、function 的副作用关键字）
- constraints: 异常 throws、注解（@RequiresPermissions/@Validated），守卫 if 关键字
- events: $emit、emit()、@xxxEvent、CommonEvent 监听
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ANALYZABLE_KINDS = {"class", "interface", "type", "method", "function", "route", "component", "variable"}


def exec_json(args, timeout=60):
    start = time.time()
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        duration_ms = int((time.time() - start) * 1000)
        if proc.returncode != 0:
            return None, proc.returncode, duration_ms, proc.stderr[:200]
        out = proc.stdout.strip()
        if not out:
            return [], proc.returncode, duration_ms, ""
        try:
            return json.loads(out), proc.returncode, duration_ms, ""
        except json.JSONDecodeError:
            return None, proc.returncode, duration_ms, f"非法 JSON: {out[:200]}"
    except subprocess.TimeoutExpired:
        return None, -1, int((time.time() - start) * 1000), "超时"
    except Exception as e:
        return None, -1, int((time.time() - start) * 1000), f"异常: {e}"


def get_callers(source, symbol, limit=20):
    args = ["codegraph", "callers", "-p", source, "-l", str(limit), "-j", symbol]
    data, code, _, err = exec_json(args)
    if data is None:
        return [], err
    # 实际输出: {symbol, callers: [...]}
    if isinstance(data, dict):
        return data.get("callers", []), None
    if isinstance(data, list):
        return data, None
    return [], None


def get_callees(source, symbol, limit=20):
    args = ["codegraph", "callees", "-p", source, "-l", str(limit), "-j", symbol]
    data, code, _, err = exec_json(args)
    if data is None:
        return [], err
    # 实际输出: {symbol, callees: [...]}
    if isinstance(data, dict):
        return data.get("callees", []), None
    if isinstance(data, list):
        return data, None
    return [], None


def read_source(source_root, file_path, start_line, end_line, max_lines=200):
    try:
        full = Path(source_root) / file_path
        if not full.exists() or not str(full.resolve()).startswith(str(Path(source_root).resolve())):
            return ""
        lines = full.read_text(errors="ignore").splitlines()
        s = max(1, start_line)
        e = min(len(lines), end_line if end_line > 0 else start_line)
        snippet = "\n".join(lines[s-1:e])
        if (e - s + 1) > max_lines:
            snippet = "\n".join(lines[s-1:s-1+max_lines]) + "\n# ...截断..."
        return snippet
    except Exception:
        return ""


def map_semantic_kind(node, semantic_rules):
    path = node.get("filePath", "")
    name = node.get("name", "")
    kind = node.get("kind", "")
    for rule in semantic_rules.get("rules", []):
        if rule["native_kind"] != kind:
            continue
        if re.search(rule["path_regex"], path) and re.search(rule["name_regex"], name):
            return rule["semantic_kind"]
    return semantic_rules.get("fallback_semantic_kind", "function")


def extract_attributes(node, source_code):
    attrs = []
    sig = node.get("signature") or ""
    if sig:
        attrs.append({"type": "signature", "value": sig[:400]})
    doc = node.get("docstring")
    if doc:
        attrs.append({"type": "doc", "value": doc[:300]})
    # 提取注解（Java/TS）
    annotations = re.findall(r"@(\w+)(?:\([^)]*\))?", source_code[:1000])
    if annotations:
        uniq = list(dict.fromkeys(annotations))[:10]
        attrs.append({"type": "annotations", "value": uniq})
    # 提取 Vue props / defineProps
    if node.get("kind") == "component":
        props = re.findall(r"defineProps[<(]([^)>]+)", source_code)
        if props:
            attrs.append({"type": "props", "value": props[0][:200]})
    return attrs


def extract_behaviors(node, source_code, callees):
    behs = []
    # 调用关系（callees 项是 {name, kind, filePath, startLine}）
    callee_names = []
    for c in callees:
        if not isinstance(c, dict):
            continue
        n = c.get("name") or (c.get("node") or {}).get("name") if isinstance(c.get("node"), dict) else c.get("name")
        if n:
            callee_names.append(n)
    callee_names = list(dict.fromkeys(callee_names))[:15]
    if callee_names:
        behs.append({"type": "calls", "value": callee_names})
    # HTTP 路由方法
    http = re.findall(r"@(Get|Post|Put|Delete|Patch|Request)Mapping(?:\(([^)]*)\))?", source_code)
    if http:
        behs.append({"type": "http", "value": [{"method": h[0], "path": h[1]} for h in http[:5]]})
    # Vue 生命周期
    lifecycle = re.findall(r"\b(onMounted|onUnmounted|onBeforeMount|watch|computed)\b", source_code)
    if lifecycle:
        behs.append({"type": "lifecycle", "value": list(dict.fromkeys(lifecycle))[:8]})
    # async / await
    if re.search(r"\basync\b|\bawait\b", source_code):
        behs.append({"type": "async", "value": True})
    return behs


def extract_constraints(node, source_code):
    cons = []
    # 异常 throws
    throws = re.findall(r"throws\s+([\w, ]+)", source_code)
    if throws:
        cons.append({"type": "throws", "value": throws[:5]})
    # @Validated / @NotNull / @NotBlank
    validators = re.findall(r"@(Validated|NotNull|NotBlank|Valid|Min|Max|Pattern|Email|RequiresPermissions|PreAuthorize)\b", source_code)
    if validators:
        cons.append({"type": "validators", "value": list(dict.fromkeys(validators))[:8]})
    # if/guards
    guards = re.findall(r"if\s*\(([^)]{0,80})\)", source_code)
    if guards:
        cons.append({"type": "guards_count", "value": len(guards)})
    return cons


def extract_events(node, source_code):
    evs = []
    # Vue $emit / emit
    emits = re.findall(r"emit\(['\"]([\w-]+)['\"]", source_code)
    if emits:
        evs.append({"type": "emit", "value": list(dict.fromkeys(emits))[:8]})
    # Spring @EventListener / ApplicationEventPublisher
    if re.search(r"@EventListener|ApplicationEventPublisher", source_code):
        evs.append({"type": "spring_event", "value": True})
    # message publish
    pubs = re.findall(r"\.publish[A-Z]\w*\(", source_code)
    if pubs:
        evs.append({"type": "publish", "value": list(dict.fromkeys(pubs))[:5]})
    return evs


def typecard_for_node(source, source_root, node, semantic_rules, fetch_call_graph=True):
    name = node.get("name", "")
    file_path = node.get("filePath", "")
    kind = node.get("kind", "")
    start = node.get("startLine", 0) or 0
    end = node.get("endLine", 0) or 0

    source_code = read_source(source_root, file_path, start, end)

    callers, callees = [], []
    callers_err, callees_err = None, None
    if fetch_call_graph and name:
        callers, callers_err = get_callers(source, name)
        callees, callees_err = get_callees(source, name)

    semantic = map_semantic_kind(node, semantic_rules)
    attributes = extract_attributes(node, source_code)
    behaviors = extract_behaviors(node, source_code, callees)
    constraints = extract_constraints(node, source_code)
    events = extract_events(node, source_code)

    return {
        "name": name,
        "file": file_path,
        "native_kind": kind,
        "semantic_kind": semantic,
        "attributes": attributes,
        "behaviors": behaviors,
        "constraints": constraints,
        "events": events,
        "source_nodes": [node.get("id")],
        "callers": [
            {"name": c.get("name"),
             "file": c.get("filePath") or c.get("file"),
             "kind": c.get("kind"),
             "line": c.get("startLine")}
            for c in callers[:10] if isinstance(c, dict)
        ],
        "callees": [
            {"name": c.get("name"),
             "file": c.get("filePath") or c.get("file"),
             "kind": c.get("kind"),
             "line": c.get("startLine")}
            for c in callees[:10] if isinstance(c, dict)
        ],
        "start_line": start,
        "end_line": end,
        "source_snippet": source_code[:1500],
        "_errors": {"callers": callers_err, "callees": callees_err} if (callers_err or callees_err) else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--entry-id", required=True)
    ap.add_argument("--output-root", required=True)
    ap.add_argument("--semantic-kinds", required=True)
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--skip-call-graph", action="store_true",
                    help="跳过 callers/callees CLI 调用（用于快速试运行）")
    args = ap.parse_args()

    semantic_rules = json.load(open(args.semantic_kinds))
    nodes_payload = json.load(open(
        Path(args.output_root) / ".codebook" / "evidence" / args.entry_id / "nodes.json"
    ))
    all_nodes = [r["node"] for r in nodes_payload["nodes"]]
    analyzable = [n for n in all_nodes if n.get("kind") in ANALYZABLE_KINDS]
    print(f"[{args.entry_id}] 可分析节点 {len(analyzable)} / 总节点 {len(all_nodes)}", flush=True)

    typecards = []
    errors = []
    completed = 0
    total = len(analyzable)
    fetch_cg = not args.skip_call_graph

    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        future_map = {
            ex.submit(typecard_for_node, args.source, args.source, n, semantic_rules, fetch_cg): n
            for n in analyzable
        }
        for future in as_completed(future_map):
            n = future_map[future]
            try:
                tc = future.result()
                typecards.append(tc)
                if tc.get("_errors"):
                    errors.append({"node_id": n.get("id"), "errors": tc["_errors"]})
            except Exception as e:
                errors.append({"node_id": n.get("id"), "errors": str(e)})
            completed += 1
            if completed % 50 == 0 or completed == total:
                print(f"[{args.entry_id}] TypeCard 进度 {completed}/{total}", flush=True)

    # 写入 typecards.json
    out_path = Path(args.output_root) / ".codebook" / "evidence" / args.entry_id / "typecards.json"
    out_path.write_text(json.dumps({
        "entry_id": args.entry_id,
        "typecards": typecards,
        "total": len(typecards),
        "errors": errors,
        "kind_distribution": {
            k: sum(1 for tc in typecards if tc["native_kind"] == k)
            for k in ANALYZABLE_KINDS
        },
        "semantic_distribution": {},
    }, ensure_ascii=False, indent=2))

    print(f"[{args.entry_id}] 完成 TypeCard {len(typecards)}, 错误 {len(errors)}", flush=True)


if __name__ == "__main__":
    main()

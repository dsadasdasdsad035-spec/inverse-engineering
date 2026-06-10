#!/usr/bin/env python3
"""
节点深挖与 TypeCard 生成：
- 对每个顶层类型（class/interface/enum）做 callers/callees 抽样
- 解析源码提取字段、方法签名、注解
- 按 class 聚类生成 TypeCard
- 写入 evidence/<entry>/nodes_dive.json 和 typecards.json
"""
import json, os, re, subprocess, time, argparse
from collections import defaultdict


def run_cmd(args, timeout=30):
    start = time.time()
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        dur = (time.time() - start) * 1000
        return proc.returncode, proc.stdout, proc.stderr, dur
    except subprocess.TimeoutExpired:
        return -124, "", "timeout", (time.time() - start) * 1000
    except FileNotFoundError as e:
        return -127, "", str(e), 0


def call_callers(source, name, limit=20):
    args = ["codegraph","callers","-p",source,"-l",str(limit),"-j",name]
    rc, out, err, dur = run_cmd(args)
    if rc != 0 or not out.strip():
        return {"error": err or f"rc={rc}", "duration_ms": round(dur,1), "callers": []}
    try:
        data = json.loads(out)
        callers = data.get('callers', data) if isinstance(data, dict) else data
        # 标准化
        if isinstance(callers, dict):
            callers = callers.get('callers') or callers.get('results') or []
        return {"callers": callers, "duration_ms": round(dur,1)}
    except json.JSONDecodeError:
        return {"error": "json", "raw": out[:500], "duration_ms": round(dur,1)}


def call_callees(source, name, limit=20):
    args = ["codegraph","callees","-p",source,"-l",str(limit),"-j",name]
    rc, out, err, dur = run_cmd(args)
    if rc != 0 or not out.strip():
        return {"error": err or f"rc={rc}", "duration_ms": round(dur,1), "callees": []}
    try:
        data = json.loads(out)
        callees = data.get('callees', data) if isinstance(data, dict) else data
        if isinstance(callees, dict):
            callees = callees.get('callees') or callees.get('results') or []
        return {"callees": callees, "duration_ms": round(dur,1)}
    except json.JSONDecodeError:
        return {"error": "json", "raw": out[:500], "duration_ms": round(dur,1)}


def read_source_range(source, file_path, start_line, end_line):
    abs_path = os.path.join(source, file_path)
    if not abs_path.startswith(os.path.abspath(source)):
        return None, "路径越界"
    try:
        with open(abs_path, encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        if start_line < 1: start_line = 1
        if end_line > len(lines): end_line = len(lines)
        return ''.join(lines[start_line-1:end_line]), None
    except (OSError, IOError) as e:
        return None, str(e)


# 简单的 Java 解析（基于正则）
ANNOTATION_RE = re.compile(r'@([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)(?:\([^)]*\))?')
MODIFIER_RE = re.compile(r'\b(public|private|protected|static|final|abstract|synchronized|volatile|transient|native)\b')
CLASS_HEADER_RE = re.compile(r'\b(class|interface|enum)\s+([A-Z][A-Za-z0-9_]*)\s*(?:<[^>]*>)?\s*(?:extends\s+([A-Za-z0-9_<>.,\s]+))?\s*(?:implements\s+([A-Za-z0-9_<>.,\s]+))?')
METHOD_SIG_RE = re.compile(r'((?:@[A-Za-z_][A-Za-z0-9_.]*(?:\([^)]*\))?\s*)*)((?:public|private|protected|static|final|abstract|synchronized)\s+)*([A-Za-z_<>?\[\],\s]+?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?:throws\s+[A-Za-z0-9_,\s]+)?\s*[;{]')
FIELD_RE = re.compile(r'((?:@[A-Za-z_][A-Za-z0-9_.]*(?:\([^)]*\))?\s*)*)((?:public|private|protected|static|final|volatile|transient)\s+)*([A-Za-z_<>?\[\],\s]+?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*[^;]+)?\s*;')


def parse_java_body(source_code):
    """解析 Java 源码片段，提取注解/类头/字段/方法。"""
    if not source_code:
        return {"annotations": [], "extends": None, "implements": [], "attributes": [], "behaviors": []}
    annotations = [m.group(0).strip() for m in ANNOTATION_RE.finditer(source_code)]
    header_match = CLASS_HEADER_RE.search(source_code)
    extends = None
    implements = []
    if header_match:
        extends = header_match.group(3)
        if extends: extends = extends.strip()
        impl = header_match.group(4)
        if impl:
            implements = [x.strip() for x in impl.split(',')]

    # 简单地去掉字符串字面量与注释以减少误匹配
    clean = re.sub(r'"(?:\\.|[^"\\])*"', '""', source_code)
    clean = re.sub(r'//.*', '', clean)
    clean = re.sub(r'/\*.*?\*/', '', clean, flags=re.DOTALL)

    attributes = []
    for m in FIELD_RE.finditer(clean):
        ann = m.group(1).strip()
        mods = m.group(2).strip() if m.group(2) else ""
        ftype = m.group(3).strip()
        fname = m.group(4)
        if fname in ('class','interface','enum','return','if','else','for','while','switch','case','default','new','throw','try','catch','finally','do','synchronized'):
            continue
        attributes.append({
            "name": fname,
            "type": ftype,
            "modifiers": mods,
            "annotations": ann if ann else ""
        })

    behaviors = []
    for m in METHOD_SIG_RE.finditer(clean):
        ann = m.group(1).strip()
        mods = m.group(2).strip() if m.group(2) else ""
        ret = m.group(3).strip()
        name = m.group(4)
        params = m.group(5).strip()
        if name in ('if','for','while','switch','catch','return','class','interface','enum','new','throw','try','finally','synchronized','case','default','do'):
            continue
        # 排除控制流误识别
        if not ret or ret.startswith('"') or '(' in ret:
            continue
        # 排除看起来不像方法的（含有 = 等）
        sig = f"{mods} {ret} {name}({params})".strip()
        behaviors.append({
            "name": name,
            "return_type": ret,
            "parameters": params,
            "modifiers": mods,
            "annotations": ann if ann else "",
            "signature": sig.replace("  ", " ")
        })

    return {
        "annotations": annotations,
        "extends": extends,
        "implements": implements,
        "attributes": attributes,
        "behaviors": behaviors
    }


def semantic_kind_for(node, semantic_rules):
    """根据 semantic-kinds.json 推断语义 kind。"""
    kind = node.get('kind','')
    fpath = node.get('filePath','')
    name = node.get('name','')
    for rule in semantic_rules:
        if rule.get('native_kind') != kind:
            continue
        path_re = rule.get('path_regex')
        name_re = rule.get('name_regex')
        if path_re and not re.search(path_re, fpath):
            continue
        if name_re and not re.search(name_re, name):
            continue
        return rule.get('semantic_kind')
    return "type"


def process_entry(source, codebook_root, entry_id, semantic_rules, sample_callers=200):
    ev_dir = f"{codebook_root}/evidence/{entry_id}"
    with open(f"{ev_dir}/nodes.json") as f:
        nodes_data = json.load(f)
    nodes = nodes_data['nodes']

    # 顶层类型：class/interface/enum
    top_kinds = {'class','interface','enum'}
    top_nodes = [n for n in nodes if n.get('kind') in top_kinds]

    # 同 class 内的方法/字段按 filePath 归入 class
    file_to_class = {}
    for n in top_nodes:
        file_to_class.setdefault(n['filePath'], []).append(n)

    members_by_class = defaultdict(lambda: {"fields": [], "methods": [], "routes": [], "enums": []})
    for n in nodes:
        if n.get('kind') == 'field':
            members_by_class[n['filePath']]["fields"].append(n)
        elif n.get('kind') == 'method':
            members_by_class[n['filePath']]["methods"].append(n)
        elif n.get('kind') == 'route':
            members_by_class[n['filePath']]["routes"].append(n)
        elif n.get('kind') == 'enum_member':
            members_by_class[n['filePath']]["enums"].append(n)

    typecards = []
    dive_records = []
    print(f"[{entry_id}] 开始为 {len(top_nodes)} 个顶层类型生成 TypeCard")

    # 抽样做 callers/callees（限制总调用数）
    sample_step = max(1, len(top_nodes) // sample_callers)
    sample_indices = set(range(0, len(top_nodes), sample_step))

    for i, top in enumerate(top_nodes):
        file_path = top['filePath']
        start = top.get('startLine', 1)
        end = top.get('endLine', 1)
        source_code, err = read_source_range(source, file_path, start, end)
        if err:
            source_code = ""

        # 解析源码
        parsed = parse_java_body(source_code) if source_code else {
            "annotations": [], "extends": None, "implements": [], "attributes": [], "behaviors": []
        }

        # 收集同 class 内的方法节点
        methods_in_file = [m for m in members_by_class[file_path]["methods"] if m['startLine'] >= start and m['endLine'] <= end + 1]
        fields_in_file = [f for f in members_by_class[file_path]["fields"] if f['startLine'] >= start and f['endLine'] <= end + 1]
        enums_in_file = [e for e in members_by_class[file_path]["enums"] if e['startLine'] >= start and e['endLine'] <= end + 1]
        routes_in_file = [r for r in members_by_class[file_path]["routes"] if r['startLine'] >= start and r['endLine'] <= end + 1]

        # 合并行为：从源码解析 + Codegraph 节点
        behaviors = parsed['behaviors']
        # 附加 codegraph 节点的方法签名
        sigs_seen = {b['name'] for b in behaviors}
        for m in methods_in_file:
            if m['name'] not in sigs_seen:
                behaviors.append({
                    "name": m['name'],
                    "return_type": "",
                    "parameters": "",
                    "modifiers": m.get('visibility',''),
                    "annotations": "",
                    "signature": m.get('signature', m['name'])
                })
                sigs_seen.add(m['name'])

        # 合并 attributes
        attributes = parsed['attributes']
        attr_names = {a['name'] for a in attributes}
        for fld in fields_in_file:
            if fld['name'] not in attr_names:
                attributes.append({
                    "name": fld['name'],
                    "type": "",
                    "modifiers": fld.get('visibility',''),
                    "annotations": ""
                })
                attr_names.add(fld['name'])

        # 顶层枚举值
        events = []
        for e in enums_in_file:
            events.append({
                "name": e['name'],
                "type": "enum_value"
            })

        # 路由
        if routes_in_file:
            events.append({
                "type": "routes",
                "items": [{"name": r['name'], "signature": r.get('signature','')} for r in routes_in_file]
            })

        # 深挖：抽样做 callers/callees
        callers_data = None
        callees_data = None
        dive_entry = None
        if i in sample_indices:
            qname = top.get('name','')
            if qname:
                callers_data = call_callers(source, qname, 20)
                callees_data = call_callees(source, qname, 20)
                dive_entry = {
                    "name": qname,
                    "kind": top.get('kind'),
                    "filePath": file_path,
                    "startLine": start,
                    "endLine": end,
                    "callers": callers_data.get('callers', []),
                    "callees": callees_data.get('callees', []),
                    "callers_count": len(callers_data.get('callers', [])),
                    "callees_count": len(callees_data.get('callees', [])),
                }
                dive_records.append(dive_entry)

        semantic_kind = semantic_kind_for(top, semantic_rules)
        # interface 是 interface，class 是 class，enum 是 enum
        if top.get('kind') == 'interface':
            semantic_kind = 'interface'
        elif top.get('kind') == 'enum':
            semantic_kind = 'enum'
        elif top.get('kind') == 'class':
            semantic_kind = 'class'

        # source_nodes: class 节点 + 内部 method/field/enum_member/route 节点 id
        source_node_ids = [top.get('id')]
        for m in methods_in_file: source_node_ids.append(m.get('id'))
        for fld in fields_in_file: source_node_ids.append(fld.get('id'))
        for e in enums_in_file: source_node_ids.append(e.get('id'))
        for r in routes_in_file: source_node_ids.append(r.get('id'))

        # 约束：注解 + extends + implements
        constraints = []
        for a in parsed['annotations']:
            constraints.append(f"annotation:{a}")
        if parsed['extends']:
            constraints.append(f"extends:{parsed['extends']}")
        for impl in parsed['implements']:
            constraints.append(f"implements:{impl}")

        tc = {
            "name": top.get('name'),
            "file": file_path,
            "startLine": start,
            "endLine": end,
            "native_kind": top.get('kind'),
            "semantic_kind": semantic_kind,
            "attributes": attributes,
            "behaviors": behaviors,
            "constraints": constraints,
            "events": events,
            "source_nodes": [x for x in source_node_ids if x]
        }
        typecards.append(tc)
        if (i+1) % 100 == 0 or i == len(top_nodes)-1:
            print(f"  进度 {i+1}/{len(top_nodes)}，已写 {len(typecards)} TypeCard，深挖 {len(dive_records)}")

    # 写 typecards.json
    with open(f"{ev_dir}/typecards.json", 'w') as f:
        json.dump({
            "entry_id": entry_id,
            "source_path": source,
            "typecard_count": len(typecards),
            "dive_count": len(dive_records),
            "typecards": typecards
        }, f, indent=2, ensure_ascii=False)

    # 写 nodes_dive.json（深挖记录）
    with open(f"{ev_dir}/nodes_dive.json", 'w') as f:
        json.dump({
            "entry_id": entry_id,
            "dive_count": len(dive_records),
            "dive_records": dive_records
        }, f, indent=2, ensure_ascii=False)
    print(f"[{entry_id}] 完成: {len(typecards)} TypeCard, {len(dive_records)} 深挖")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--codebook-root", required=True)
    ap.add_argument("--entry", required=True)
    ap.add_argument("--semantic-kinds", required=True)
    ap.add_argument("--sample-callers", type=int, default=200)
    args = ap.parse_args()
    with open(args.semantic_kinds) as f:
        sk = json.load(f)
    process_entry(args.source, args.codebook_root, args.entry, sk.get('rules', []), args.sample_callers)

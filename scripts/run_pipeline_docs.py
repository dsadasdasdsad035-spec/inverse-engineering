#!/usr/bin/env python3
"""第 8 步：基于 typecards.json 生成入口级文档（骨架 + 自动填充）。

生成 8 份入口文档：
- ui-layout.md (仅前端入口，识别页面/组件树)
- architecture.md
- business-flows.md
- data-model.md
- state-machines.md
- error-handling.md
- database.md
- DOCUMENTATION.md
"""
import argparse
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path


def load_typecards(output_root, entry_id):
    p = Path(output_root) / ".codebook" / "evidence" / entry_id / "typecards.json"
    return json.load(open(p))


def load_nodes(output_root, entry_id):
    p = Path(output_root) / ".codebook" / "evidence" / entry_id / "nodes.json"
    return json.load(open(p))


def write_doc(output_root, entry_id, name, content):
    path = Path(output_root) / "entries" / entry_id / name
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
    return path


def file_sections_by_dir(typecards):
    """按文件路径所在子目录分组 typecards"""
    by_dir = defaultdict(list)
    for tc in typecards:
        f = tc.get("file", "")
        parts = f.split("/")
        if len(parts) >= 4:
            section = "/".join(parts[2:4])  # 取第 3-4 段，如 product/brand
        elif len(parts) >= 2:
            section = "/".join(parts[:-1])
        else:
            section = "其他"
        by_dir[section].append(tc)
    return dict(sorted(by_dir.items()))


# ==================== UI 布局 ====================
def gen_ui_layout(entry_id, typecards, frontend=True):
    if not frontend:
        return None
    lines = [f"# UI 布局：{entry_id}", "", "本入口前端界面层结构和组件树。所有内容来自 codegraph 索引中识别到的 Vue 组件 / TS 模块证据。", ""]
    pages = [tc for tc in typecards if tc.get("semantic_kind") == "page" or
             (tc.get("native_kind") == "component" and "/views/" in tc.get("file", ""))]
    components = [tc for tc in typecards if tc.get("native_kind") == "component" and tc not in pages]
    by_dir = file_sections_by_dir(pages)
    lines.append(f"## 页面清单（共 {len(pages)} 个组件）")
    lines.append("")
    for section, tcs in by_dir.items():
        lines.append(f"### {section}")
        lines.append("")
        for tc in tcs:
            f = tc.get("file", "")
            lines.append(f"#### {tc['name']}")
            lines.append("")
            lines.append(f"> 来源文件：`{f}` (lines {tc.get('start_line')}-{tc.get('end_line')})")
            lines.append("")
            # 提取 props/emits/lifecycle 作为 UI 描述
            props = [a["value"] for a in tc["attributes"] if a["type"] == "props"]
            if props:
                lines.append(f"- 属性: `{props[0][:120]}`")
            emits_list = [e["value"] for e in tc["events"] if e["type"] == "emit"]
            if emits_list:
                lines.append(f"- 抛出事件: {', '.join(emits_list[0])}")
            life = [b["value"] for b in tc["behaviors"] if b["type"] == "lifecycle"]
            if life:
                lines.append(f"- 生命周期: {', '.join(life[0])}")
            calls = [b["value"] for b in tc["behaviors"] if b["type"] == "calls"]
            if calls:
                lines.append(f"- 调用: {', '.join(calls[0][:8])}")
            lines.append("")
            lines.append(f"<!-- source_nodes: {tc.get('source_nodes')} -->")
            lines.append("")
        # Mermaid 子树
        if len(tcs) <= 20:
            lines.append("```mermaid")
            lines.append("graph TD")
            for tc in tcs:
                safe = re.sub(r"\W", "_", tc["name"])
                lines.append(f"  {safe}[{tc['name']}]")
                for cl in tc.get("callees", [])[:3]:
                    if cl["name"]:
                        csafe = re.sub(r"\W", "_", cl["name"])
                        lines.append(f"  {safe} --> {csafe}[{cl['name']}]")
            lines.append("```")
            lines.append("")
    lines.append("## 组件库")
    lines.append("")
    lines.append(f"共复用组件 {len(components)} 个：")
    lines.append("")
    for c in components[:40]:
        lines.append(f"- `{c['name']}` — `{c['file']}` <!-- source_nodes: {c['source_nodes']} -->")
    if len(components) > 40:
        lines.append(f"- ……（共 {len(components)} 个，余略）")
    lines.append("")
    return "\n".join(lines)


# ==================== Architecture ====================
def gen_architecture(entry_id, typecards, nodes_payload):
    lines = [f"# 架构概览：{entry_id}", ""]
    lines.append(f"入口范围：`{nodes_payload['entry_path']}`，inventory 文件 {nodes_payload['inventory_files']}，节点 {nodes_payload['total_nodes']}。")
    lines.append("")

    # 按 native_kind 统计
    kind_count = Counter(tc["native_kind"] for tc in typecards)
    sem_count = Counter(tc["semantic_kind"] for tc in typecards)
    lines.append("## 原生 kind 分布")
    lines.append("")
    lines.append("| 原生 kind | 数量 |")
    lines.append("|---|---|")
    for k, c in kind_count.most_common():
        lines.append(f"| {k} | {c} |")
    lines.append("")
    lines.append("## 语义 kind 分布")
    lines.append("")
    lines.append("| 语义 kind | 数量 |")
    lines.append("|---|---|")
    for k, c in sem_count.most_common():
        lines.append(f"| {k} | {c} |")
    lines.append("")

    # 按目录分层
    layer = defaultdict(int)
    for tc in typecards:
        f = tc.get("file", "")
        parts = f.split("/")
        if "controller" in f:
            layer["controller 控制器层"] += 1
        elif "service" in f:
            layer["service 业务服务层"] += 1
        elif "dal/mysql" in f or "/dao/" in f or "Mapper.java" in f:
            layer["dal 数据访问层"] += 1
        elif "/dal/dataobject" in f or "/entity/" in f or "/po/" in f:
            layer["domain 领域对象"] += 1
        elif "/convert/" in f or "Convert.java" in f:
            layer["convert 对象转换"] += 1
        elif "/vo/" in f or "/dto/" in f:
            layer["vo/dto 视图传输对象"] += 1
        elif "/api/" in f:
            layer["api 模块对外契约"] += 1
        elif "/views/" in f or ".vue" in f:
            layer["views 前端视图层"] += 1
        elif "/components/" in f:
            layer["components 前端组件层"] += 1
        else:
            layer["其他"] += 1
    lines.append("## 分层架构")
    lines.append("")
    lines.append("| 层 | 节点数 |")
    lines.append("|---|---|")
    for l, c in sorted(layer.items(), key=lambda x: -x[1]):
        lines.append(f"| {l} | {c} |")
    lines.append("")

    # 调用关系图（top hotspots）
    callee_counter = Counter()
    for tc in typecards:
        for c in tc.get("callees", []):
            if c.get("name"):
                callee_counter[c["name"]] += 1
    lines.append("## 调用热点（被引用最多的符号）")
    lines.append("")
    lines.append("| 符号 | 被调次数 |")
    lines.append("|---|---|")
    for name, c in callee_counter.most_common(20):
        lines.append(f"| `{name}` | {c} |")
    lines.append("")
    lines.append(f"<!-- source_nodes_sample: {[tc['source_nodes'][0] for tc in typecards[:10]]} -->")
    return "\n".join(lines)


# ==================== Business Flows ====================
def gen_business_flows(entry_id, typecards):
    lines = [f"# 业务流程：{entry_id}", ""]
    # 按子目录划分业务模块
    by_dir = file_sections_by_dir(typecards)
    lines.append(f"识别出 {len(by_dir)} 个业务模块（按目录分组）。")
    lines.append("")
    for section, tcs in by_dir.items():
        controllers = [t for t in tcs if "controller" in t["file"].lower() or t["semantic_kind"] == "route"]
        services = [t for t in tcs if "service" in t["file"].lower()]
        pages = [t for t in tcs if t["semantic_kind"] == "page"]
        if not (controllers or services or pages):
            continue
        lines.append(f"## {section}")
        lines.append("")
        if pages:
            lines.append("### 入口页面")
            for p in pages[:8]:
                lines.append(f"- `{p['name']}` — `{p['file']}`")
            lines.append("")
        if controllers:
            lines.append("### 控制器接口")
            for c in controllers[:15]:
                http = [b["value"] for b in c["behaviors"] if b["type"] == "http"]
                http_str = ""
                if http:
                    http_str = " " + " ".join(f"{h['method']}={h['path']}" for h in http[0])
                lines.append(f"- `{c['name']}`{http_str} — `{c['file']}`")
            lines.append("")
        if services:
            lines.append("### 业务服务")
            for s in services[:15]:
                calls = [b["value"] for b in s["behaviors"] if b["type"] == "calls"]
                calls_str = ""
                if calls:
                    calls_str = " → " + ", ".join(calls[0][:5])
                lines.append(f"- `{s['name']}`{calls_str}")
            lines.append("")
        # 拼接源节点追溯
        all_ids = [tc["source_nodes"][0] for tc in (controllers + services + pages)[:20]]
        lines.append(f"<!-- source_nodes: {all_ids} -->")
        lines.append("")
    return "\n".join(lines)


# ==================== Data Model ====================
def gen_data_model(entry_id, typecards):
    lines = [f"# 数据模型：{entry_id}", ""]
    # 候选实体：class 或 interface 且名称包含 DO/PO/VO/DTO 或在 entity/dataobject 目录
    entities = []
    for tc in typecards:
        f = tc["file"]
        name = tc["name"]
        if tc["native_kind"] in ("class", "interface"):
            if re.search(r"DO|PO|VO|DTO|Entity|Bean", name) or "/dal/dataobject" in f or "/entity/" in f or "/vo/" in f or "/dto/" in f or "/api/.*/dto/" in f:
                entities.append(tc)
    lines.append(f"识别出 {len(entities)} 个候选数据对象。")
    lines.append("")
    # 按目录分组
    grp = defaultdict(list)
    for e in entities:
        parts = e["file"].split("/")
        if "/vo/" in e["file"]:
            grp.setdefault("VO 视图对象", []).append(e)
        elif "/dto/" in e["file"]:
            grp.setdefault("DTO 数据传输对象", []).append(e)
        elif "/dal/dataobject" in e["file"] or "/entity/" in e["file"]:
            grp.setdefault("DO 持久化对象", []).append(e)
        elif "/po/" in e["file"]:
            grp.setdefault("PO 持久化对象", []).append(e)
        else:
            grp.setdefault("其他", []).append(e)
    for g, es in grp.items():
        lines.append(f"## {g}（{len(es)}）")
        lines.append("")
        for e in es[:60]:
            attrs = [a["value"] for a in e["attributes"] if a["type"] == "annotations"]
            ann = ", ".join(attrs[0]) if attrs else ""
            lines.append(f"- `{e['name']}` — `{e['file']}` <!-- ann: {ann} -->")
        if len(es) > 60:
            lines.append(f"- ……共 {len(es)} 个")
        lines.append("")
    # 源节点
    lines.append(f"<!-- source_nodes_sample: {[e['source_nodes'][0] for e in entities[:30]]} -->")
    return "\n".join(lines)


# ==================== State Machines ====================
def gen_state_machines(entry_id, typecards):
    lines = [f"# 状态机：{entry_id}", ""]
    # 查找名字带 Status/Stage/Phase/State 的常量、枚举或 typecard
    candidates = []
    for tc in typecards:
        n = tc["name"]
        if re.search(r"(Status|Stage|Phase|State|Step)$", n) or "status" in tc.get("file", "").lower():
            candidates.append(tc)
    if not candidates:
        lines.append("当前入口未识别出显式状态字段或枚举。")
        return "\n".join(lines)
    lines.append(f"识别出 {len(candidates)} 个状态相关符号。")
    lines.append("")
    for c in candidates[:30]:
        lines.append(f"## {c['name']}")
        lines.append(f"- 文件: `{c['file']}` (lines {c.get('start_line')}-{c.get('end_line')})")
        sig = [a["value"] for a in c["attributes"] if a["type"] == "signature"]
        if sig:
            lines.append(f"- 签名: `{sig[0][:200]}`")
        doc = [a["value"] for a in c["attributes"] if a["type"] == "doc"]
        if doc:
            lines.append(f"- 说明: {doc[0]}")
        lines.append(f"<!-- source_nodes: {c['source_nodes']} -->")
        lines.append("")
    return "\n".join(lines)


# ==================== Error Handling ====================
def gen_error_handling(entry_id, typecards):
    lines = [f"# 错误处理：{entry_id}", ""]
    with_throws = []
    with_validators = []
    for tc in typecards:
        thr = [c for c in tc["constraints"] if c["type"] == "throws"]
        val = [c for c in tc["constraints"] if c["type"] == "validators"]
        if thr:
            with_throws.append((tc, thr[0]["value"]))
        if val:
            with_validators.append((tc, val[0]["value"]))
    lines.append(f"## 显式异常声明（{len(with_throws)}）")
    lines.append("")
    for tc, throws in with_throws[:50]:
        lines.append(f"- `{tc['name']}` throws {', '.join(throws)} — `{tc['file']}`")
    if len(with_throws) > 50:
        lines.append(f"- ……共 {len(with_throws)} 个")
    lines.append("")
    lines.append(f"## 参数校验注解（{len(with_validators)}）")
    lines.append("")
    val_counter = Counter()
    for tc, vals in with_validators:
        for v in vals:
            val_counter[v] += 1
    lines.append("| 注解 | 使用次数 |")
    lines.append("|---|---|")
    for v, c in val_counter.most_common():
        lines.append(f"| @{v} | {c} |")
    lines.append("")
    lines.append("## 典型校验位点")
    lines.append("")
    for tc, vals in with_validators[:30]:
        lines.append(f"- `{tc['name']}` 使用 {', '.join('@' + v for v in vals)} — `{tc['file']}`")
    lines.append("")
    sample_ids = [tc[0]["source_nodes"][0] for tc in (with_throws + with_validators)[:20]]
    lines.append(f"<!-- source_nodes: {sample_ids} -->")
    return "\n".join(lines)


# ==================== Database ====================
def gen_database(entry_id, typecards):
    lines = [f"# 数据库：{entry_id}", ""]
    # 找出 mapper / dao
    mappers = [tc for tc in typecards if "Mapper" in tc["name"] or "/dal/mysql" in tc["file"] or "/mapper/" in tc["file"]]
    dos = [tc for tc in typecards if ("/dal/dataobject" in tc["file"] or re.search(r"DO$", tc["name"]))]
    lines.append(f"识别出 {len(mappers)} 个 Mapper / DAO，{len(dos)} 个 DO 数据对象。")
    lines.append("")
    lines.append("## DO 数据对象（候选数据表）")
    lines.append("")
    if dos:
        lines.append("```mermaid")
        lines.append("erDiagram")
        added_entities = []
        for d in dos[:18]:
            tbl = re.sub(r"DO$", "", d["name"])
            tbl_safe = re.sub(r"\W", "_", tbl)
            if tbl_safe not in added_entities:
                added_entities.append(tbl_safe)
                lines.append(f"  {tbl_safe} {{")
                # 字段（从 signature 中提取）
                sig = [a["value"] for a in d["attributes"] if a["type"] == "signature"]
                if sig:
                    fields = re.findall(r"(\w+)\s+(\w+);", sig[0])[:8]
                    for typ, fld in fields:
                        lines.append(f"    {typ} {fld}")
                else:
                    lines.append(f"    string id")
                lines.append(f"  }}")
        lines.append("```")
        lines.append("")
    lines.append("## DO 完整清单")
    lines.append("")
    for d in dos:
        lines.append(f"- `{d['name']}` — `{d['file']}`")
    lines.append("")
    lines.append("## Mapper 清单")
    lines.append("")
    for m in mappers[:80]:
        lines.append(f"- `{m['name']}` — `{m['file']}`")
    if len(mappers) > 80:
        lines.append(f"- ……共 {len(mappers)} 个")
    lines.append("")
    sample_ids = [tc["source_nodes"][0] for tc in (dos + mappers)[:30]]
    lines.append(f"<!-- source_nodes: {sample_ids} -->")
    return "\n".join(lines)


# ==================== DOCUMENTATION ====================
def gen_documentation_index(entry_id, typecards, docs):
    lines = [f"# 文档索引：{entry_id}", ""]
    lines.append(f"本入口共生成 {len(docs)} 份文档，证据来自 {len(typecards)} 个 TypeCard。")
    lines.append("")
    lines.append("| 文档 | 主题 |")
    lines.append("|---|---|")
    desc = {
        "ui-layout.md": "前端页面与组件树",
        "architecture.md": "分层架构与调用热点",
        "business-flows.md": "业务模块与控制器/服务流",
        "data-model.md": "数据对象（DO/VO/DTO）",
        "state-machines.md": "状态字段与枚举",
        "error-handling.md": "异常声明与校验注解",
        "database.md": "DO 数据表与 Mapper",
    }
    for d in docs:
        lines.append(f"| [{d}](./{d}) | {desc.get(d, '')} |")
    lines.append("")
    lines.append("## TypeCard 摘要")
    lines.append("")
    kind_count = Counter(tc["native_kind"] for tc in typecards)
    sem_count = Counter(tc["semantic_kind"] for tc in typecards)
    lines.append(f"- 原生 kind 分布: {dict(kind_count.most_common())}")
    lines.append(f"- 语义 kind 分布: {dict(sem_count.most_common())}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry-id", required=True)
    ap.add_argument("--output-root", required=True)
    ap.add_argument("--frontend", action="store_true")
    args = ap.parse_args()

    tc_payload = load_typecards(args.output_root, args.entry_id)
    typecards = tc_payload["typecards"]
    nodes_payload = load_nodes(args.output_root, args.entry_id)

    docs_generated = []

    if args.frontend:
        ui = gen_ui_layout(args.entry_id, typecards, frontend=True)
        if ui:
            write_doc(args.output_root, args.entry_id, "ui-layout.md", ui)
            docs_generated.append("ui-layout.md")

    arch = gen_architecture(args.entry_id, typecards, nodes_payload)
    write_doc(args.output_root, args.entry_id, "architecture.md", arch)
    docs_generated.append("architecture.md")

    flows = gen_business_flows(args.entry_id, typecards)
    write_doc(args.output_root, args.entry_id, "business-flows.md", flows)
    docs_generated.append("business-flows.md")

    data_m = gen_data_model(args.entry_id, typecards)
    write_doc(args.output_root, args.entry_id, "data-model.md", data_m)
    docs_generated.append("data-model.md")

    sm = gen_state_machines(args.entry_id, typecards)
    write_doc(args.output_root, args.entry_id, "state-machines.md", sm)
    docs_generated.append("state-machines.md")

    err = gen_error_handling(args.entry_id, typecards)
    write_doc(args.output_root, args.entry_id, "error-handling.md", err)
    docs_generated.append("error-handling.md")

    db = gen_database(args.entry_id, typecards)
    write_doc(args.output_root, args.entry_id, "database.md", db)
    docs_generated.append("database.md")

    idx = gen_documentation_index(args.entry_id, typecards, docs_generated)
    write_doc(args.output_root, args.entry_id, "DOCUMENTATION.md", idx)
    docs_generated.append("DOCUMENTATION.md")

    print(f"[{args.entry_id}] 已生成入口文档 {len(docs_generated)}: {docs_generated}")


if __name__ == "__main__":
    main()

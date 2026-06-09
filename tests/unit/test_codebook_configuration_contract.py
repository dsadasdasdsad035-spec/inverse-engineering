"""Codebook 配置化契约测试。"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = ROOT / "resources" / "codebook" / "defaults"
PROMPTS = DEFAULTS / "prompts"
SKILL_PATH = ROOT / ".claude" / "skills" / "run-pipeline" / "SKILL.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_default_codebook_assets_exist():
    """默认配置和提示词模板必须能初始化到本次输出目录。"""
    expected = [
        DEFAULTS / "manifest.json",
        DEFAULTS / "entries.json",
        DEFAULTS / "codegraph-tools.json",
        DEFAULTS / "semantic-kinds.json",
        PROMPTS / "temp_typecard.json",
        PROMPTS / "temp_architecture.json",
        PROMPTS / "temp_business_flows.json",
        PROMPTS / "temp_data_model.json",
        PROMPTS / "temp_srs.json",
        PROMPTS / "temp_ui.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in expected if not path.exists()]
    assert missing == []


def test_tool_policy_uses_codegraph_cli_json_commands():
    """Codegraph 采集必须使用可配置的 CLI JSON 命令，不能依赖 MCP。"""
    policy = load_json(DEFAULTS / "codegraph-tools.json")
    assert policy["version"] == "1.0"
    assert policy["transport"] == {
        "mode": "cli",
        "binary": "codegraph",
        "minimum_version": "0.9.9",
        "record_commands": True,
        "error_policy": "block_current_entry",
    }
    assert policy["pagination"]["on_limit_reached"] == "narrow_entry_or_file"
    assert policy["output_normalization"] == {
        "files_no_match": "empty_array",
        "all_other_invalid_json": "error",
    }

    commands = policy["commands"]
    assert commands["version"] == ["<binary>", "--version"]
    assert commands["status"][-1] == "<source>"
    assert commands["files"][-1] == "-j"
    assert commands["query"][-1] == "path:<exact-file-path>"
    assert commands["callers"][-1] == "<symbol>"
    assert commands["callees"][-1] == "<symbol>"
    for command in commands.values():
        assert isinstance(command, list)
        assert command[0] == "<binary>"
    assert all("-j" in command for name, command in commands.items() if name != "version")

    tools = policy["tools"]
    assert tools["codegraph_files"]["maxDepth"] > 0
    assert tools["source_read"]["includeCode"] is True

    native_kinds = set(tools["codegraph_query"]["kinds"])
    assert {"class", "interface", "type", "method", "function", "route", "component"}.issubset(native_kinds)
    assert {"store", "page", "hook"}.isdisjoint(native_kinds)

    for name in ["codegraph_query", "codegraph_callers", "codegraph_callees"]:
        assert isinstance(tools[name]["limit"], int)
        assert tools[name]["limit"] > 0


def test_tool_policy_requires_exhaustive_per_file_symbol_enumeration():
    """符号枚举必须逐文件全量执行，并通过节点数量对账证明未抽样。"""
    policy = load_json(DEFAULTS / "codegraph-tools.json")
    enumeration = policy["symbol_enumeration"]

    assert enumeration == {
        "query": "path:<exact-file-path>",
        "scope": "per_file",
        "sampling": "forbidden",
        "limit_source": "status.nodeCount",
        "reconcile_with": "files.nodeCount",
        "exact_filter": "node.filePath == current_file",
        "deduplicate_by": "node.id",
        "on_mismatch": "block_entry",
    }


def test_manifest_and_entries_define_output_local_initialization():
    """初始化配置必须以本次输出目录为作用域，并固定入口发现优先级。"""
    manifest = load_json(DEFAULTS / "manifest.json")
    entries = load_json(DEFAULTS / "entries.json")

    assert manifest["codebook_root"] == "<output>/.codebook"
    assert manifest["quality_report"] == "../quality.json"
    assert manifest["evidence_directory"] == "evidence"
    assert manifest["checkpoint_directory"] == "checkpoints"
    assert manifest["proposal_directory"] == "proposals"
    assert manifest["evolution_log"] == "skill-evolution.log"
    assert manifest["initialization"]["mode"] == "create_if_missing"
    assert manifest["initialization"]["refresh_entries_only"] is True

    assert entries["discovery"]["priority"] == [
        "explicit",
        "module",
        "backend_package",
        "frontend_root",
        "project_root",
    ]
    assert entries["discovery"]["backend_package"]["granularity"] == "common_root_plus_one"
    assert entries["entry_schema"]["required"] == [
        "id",
        "entry_type",
        "path",
        "languages",
        "include_patterns",
        "enabled",
    ]


def test_semantic_kinds_classify_frontend_without_native_kind_leak():
    """前端 store/page/hook 是语义分类，不能当作 Codegraph 原生 kind。"""
    semantic = load_json(DEFAULTS / "semantic-kinds.json")
    semantic_kinds = {rule["semantic_kind"] for rule in semantic["rules"]}
    assert {"page", "component", "store", "hook", "api", "route", "function"}.issubset(semantic_kinds)

    for rule in semantic["rules"]:
        assert rule["native_kind"] in {
            "class",
            "interface",
            "type",
            "method",
            "function",
            "route",
            "component",
            "variable",
            "file",
        }


def test_prompt_templates_share_contract_and_ui_schema():
    """所有 prompt 模板必须使用统一结构，UI 模板必须输出布局 JSON。"""
    required = {
        "temp_typecard",
        "temp_architecture",
        "temp_business_flows",
        "temp_data_model",
        "temp_srs",
        "temp_ui",
    }
    templates = {path.stem: load_json(path) for path in PROMPTS.glob("temp_*.json")}
    assert required.issubset(templates)

    for name, template in templates.items():
        assert template["name"] == name
        assert template["version"] == "1.0"
        assert isinstance(template["input_refs"], list)
        assert template["input_refs"]
        assert "prompt" in template and "{input}" in template["prompt"]
        assert template["output_schema"]["type"] == "object"

    ui_schema = templates["temp_ui"]["output_schema"]
    assert {"layout", "source_nodes", "confidence"}.issubset(ui_schema["required"])
    assert ui_schema["properties"]["layout"]["type"] == "object"


def test_run_pipeline_skill_references_configurable_codebook():
    """当前维护的 Claude Skill 必须显式引用配置化入口流程。"""
    skill = SKILL_PATH.read_text(encoding="utf-8")
    required_snippets = [
        "--package <包名>",
        "--init-only",
        "--refresh-entries",
        "output = --output 显式值，否则为 ./output/<source项目名>",
        "codebook_root = <output>/.codebook/",
        "项目根目录现有 `.codebook/` 仅作为旧数据保留",
        "<output>/.codebook/",
        "resources/codebook/defaults/",
        "entries.json",
        "codegraph-tools.json",
        "semantic-kinds.json",
        "temp_ui.json",
        "入口发现优先级",
        "公共根包 + 下一层包",
        "store/page/hook 不作为 Codegraph 原生 kind",
        'codegraph_transport = "cli"',
        "codegraph --version",
        "commands.version",
        "commands.status",
        "commands.files",
        "commands.query",
        "commands.callers",
        "commands.callees",
        "达到 limit 时",
        "entry_coverage",
        "`quality.json` 固定写入 `<output>/quality.json`",
    ]
    for snippet in required_snippets:
        assert snippet in skill
    assert "兼容读取" not in skill
    for forbidden in ["read .codebook/", "写入 .codebook/", "for each file in .codebook/"]:
        assert forbidden not in skill


def test_run_pipeline_requires_exhaustive_symbols_and_complete_entry_documents():
    """第 6、8、9 步必须禁止抽样、局部文档和不完整入口汇总。"""
    skill = SKILL_PATH.read_text(encoding="utf-8")
    required_snippets = [
        'query_args = render(tool_policy.commands.query',
        '"path:<精确文件路径>"',
        "limit=index_total_nodes",
        "Codegraph CLI `files -j` 返回的 nodeCount",
        "禁止使用文件名、符号名或关键字进行抽样枚举",
        "node.filePath == 当前文件",
        "node.id 去重",
        "startLine",
        "endLine",
        "不得调用 `codegraph_node`",
        "symbol_enumeration_complete = false",
        "禁止进入第 8 步",
        "使用该入口全部证据一次性生成",
        "禁止关键 TypeCard 抽样",
        "禁止局部片段输出",
        "临时文件",
        "原子重命名",
        "所有完整入口文档 + 全部 TypeCard",
        "存在任一非 skipped 入口不完整",
    ]
    for snippet in required_snippets:
        assert snippet in skill

    assert "所有入口文档片段 + 关键 TypeCard" not in skill


def test_quality_report_tracks_symbol_and_document_completeness():
    """质量报告必须能机器判断入口是否完成全量枚举和完整文档生成。"""
    skill = SKILL_PATH.read_text(encoding="utf-8")
    for field in [
        '"inventory_files"',
        '"enumerated_files"',
        '"expected_symbols"',
        '"enumerated_symbols"',
        '"symbol_enumeration_complete"',
        '"incomplete_files"',
        '"required_documents"',
        '"complete_documents"',
        '"document_generation_complete"',
        '"codegraph_transport"',
        '"codegraph_cli_version"',
        '"executed_commands"',
        '"query_failures"',
        '"reconciliation_failures"',
    ]:
        assert field in skill


def test_feature_003_spec_documents_contract():
    """003 规格必须单独记录本次配置化特性。"""
    spec_dir = ROOT / "specs" / "003-configurable-codebook-traversal"
    spec = (spec_dir / "spec.md").read_text(encoding="utf-8")
    assert "可配置的包/模组遍历" in spec
    assert "<output>/.codebook/" in spec
    assert "不自动迁移" in spec
    assert "temp_ui.json" in spec
    assert "Codegraph CLI" in spec
    assert "不依赖 Codegraph MCP" in spec

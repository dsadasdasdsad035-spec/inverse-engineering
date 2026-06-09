# Data Model: 可配置 Codebook 遍历

## CodebookRuntimeLayout

| 字段 | 类型 | 说明 |
|------|------|------|
| output | string | 本次运行文档产物目录，默认 `./output/<source项目名>` |
| codebook_root | string | 固定为 `<output>/.codebook/` |
| quality_report | string | 固定为 `<output>/quality.json` |
| evidence_directory | string | `<output>/.codebook/evidence/` |
| checkpoint_directory | string | `<output>/.codebook/checkpoints/` |
| proposal_directory | string | `<output>/.codebook/proposals/` |
| evolution_log | string | `<output>/.codebook/skill-evolution.log` |

项目根目录现有 `.codebook/` 属于旧数据，新运行不读取、不覆盖、不自动迁移或删除。

## EntryDefinition

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 顶级入口唯一标识 |
| entry_type | enum | explicit_module / explicit_package / module / backend_package / frontend_root / project_root |
| path | string | 相对源码根的入口路径 |
| package_prefix | string \| null | 后端包名前缀 |
| languages | string[] | 入口涉及语言 |
| include_patterns | string[] | 文件枚举 glob |
| exclude_patterns | string[] | 排除规则 |
| enabled | boolean | 是否参与本次运行 |

## ToolPolicy

| 字段 | 类型 | 说明 |
|------|------|------|
| transport.mode | string | 固定为 `cli` |
| transport.binary | string | Codegraph CLI 可执行文件名或路径 |
| transport.minimum_version | string | 最低兼容版本 |
| transport.record_commands | boolean | 是否将命令参数、退出码和耗时写入质量报告 |
| transport.error_policy | string | CLI 或 JSON 失败时固定阻断当前入口 |
| commands.version/status/files/query/callers/callees | string[][] | 不经 shell 拼接的 CLI 参数数组模板 |
| output_normalization.files_no_match | string | `files -j` 无匹配信息文本固定归一化为 `empty_array` |
| output_normalization.all_other_invalid_json | string | 其他非法 JSON 固定按错误处理 |
| codegraph_files.maxDepth | int | 树形枚举深度 |
| codegraph_query.limit | int | 非枚举查询的默认上限 |
| codegraph_query.kinds | string[] | Codegraph 原生 kind |
| source_read.includeCode | boolean | 是否按节点源码范围读取源码 |
| codegraph_callers.limit | int | 调用者上限 |
| codegraph_callees.limit | int | 被调用者上限 |
| symbol_enumeration.query | string | 固定为 `path:<exact-file-path>`，逐文件精确查询 |
| symbol_enumeration.scope | string | 固定为 `per_file` |
| symbol_enumeration.sampling | string | 固定为 `forbidden`，禁止抽样 |
| symbol_enumeration.limit_source | string | 固定为 `status.nodeCount` |
| symbol_enumeration.reconcile_with | string | 固定为 `files.nodeCount` |
| symbol_enumeration.exact_filter | string | 固定为 `node.filePath == current_file` |
| symbol_enumeration.deduplicate_by | string | 固定为 `node.id` |
| symbol_enumeration.on_mismatch | string | 固定为 `block_entry` |

## SemanticKindRule

| 字段 | 类型 | 说明 |
|------|------|------|
| semantic_kind | string | 文档语义 kind，如 page/store/hook |
| native_kind | string | codegraph 原生 kind |
| path_regex | string | 路径匹配规则 |
| name_regex | string | 符号名匹配规则 |

## PromptTemplate

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 模板名，如 temp_srs |
| version | string | 模板版本 |
| input_refs | string[] | 输入证据引用 |
| prompt | string | 提示词正文，必须包含 `{input}` |
| output_schema | object | 期望输出 JSON Schema |

## QualityReport 扩展

```json
{
  "codegraph_transport": "cli",
  "codegraph_cli_version": "0.9.9",
  "executed_commands": [],
  "query_failures": [],
  "reconciliation_failures": [],
  "entry_coverage": {
    "<entry-id>": {
      "inventory_files": 0,
      "enumerated_files": 0,
      "expected_symbols": 0,
      "enumerated_symbols": 0,
      "symbol_enumeration_complete": false,
      "incomplete_files": [],
      "required_documents": [],
      "complete_documents": [],
      "document_generation_complete": false,
      "document_errors": []
    }
  },
  "config_snapshot": {},
  "query_truncation_warnings": [],
  "ui_layout": {
    "status": "generated",
    "generated_entries": [],
    "skipped_entries": []
  }
}
```

入口完整性规则：

- `symbol_enumeration_complete` 仅在所有文件完成精确路径查询且节点数量全部对账时为 `true`。
- CLI 查询结果必须先按 `node.filePath` 精确过滤，再按 `node.id` 去重后参与对账。
- `document_generation_complete` 仅在所有应生成文档通过完整性校验并原子写入后为 `true`。
- 任一非跳过入口的上述字段不为 `true` 时，系统级文档、SRS 和 UML 汇总不得执行。

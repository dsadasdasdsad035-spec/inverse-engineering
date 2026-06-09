# Quickstart: 可配置 Codebook 遍历

## 确认 Codegraph CLI

```bash
codegraph --version
codegraph status -j tests/fixtures/java-vue-sample
```

预期：CLI 版本不低于 `0.9.9`，状态命令返回合法 JSON。流水线不依赖 Codegraph MCP 服务。

## 初始化配置

```bash
/run-pipeline --source tests/fixtures/java-vue-sample --output output-test --init-only
```

预期生成：

```text
output-test/.codebook/
├── manifest.json
├── entries.json
├── codegraph-tools.json
├── semantic-kinds.json
├── prompts/temp_ui.json
├── evidence/
├── checkpoints/
└── proposals/
```

## 刷新入口

```bash
/run-pipeline --source tests/fixtures/java-vue-sample --output output-test --refresh-entries
```

预期：只覆盖 `output-test/.codebook/entries.json`。

## 验证逐文件全量符号枚举

运行完整流水线后，检查：

```text
output-test/quality.json
```

每个非跳过入口必须满足：

```text
enumerated_files == inventory_files
enumerated_symbols == expected_symbols
symbol_enumeration_complete == true
document_generation_complete == true
```

任一文件节点数量无法与 `codegraph files -j` 返回的 `nodeCount` 对账时，预期该入口文档生成被阻断，系统级文档、SRS 和 UML 不生成。

手工验证单文件查询时，必须使用索引总节点数作为上限，并进行精确过滤与节点 ID 去重：

```bash
total_nodes="$(codegraph status -j /path/to/source | jq -r '.nodeCount')"
file='src/views/mall/home/components/ComparisonCard.vue'
codegraph query -p /path/to/source -l "$total_nodes" -j "path:$file" \
  | jq --arg file "$file" '[.[] | select(.node.filePath == $file)] | unique_by(.node.id)'
```

`quality.json` 必须记录 `codegraph_transport`、`codegraph_cli_version`、`executed_commands`、`query_failures` 和 `reconciliation_failures`。

当某个 include pattern 没有匹配文件时，例如模块内没有 TSX：

```bash
codegraph files -p /path/to/source --filter src/views/mall --pattern '**/*.tsx' --format flat -j
```

Codegraph CLI 可能输出“无匹配文件”的信息文本；流水线必须将该结果归一化为 `[]`，不得将入口误判为失败。

## 前端 UI 布局

含前端入口时，预期生成：

```text
output-test/.codebook/evidence/<entry-id>/ui-layout.json
```

本阶段只输出 JSON，不生成静态页面。

项目根目录现有 `.codebook/` 作为旧数据保留，新运行不会读取、覆盖、自动迁移或删除它。

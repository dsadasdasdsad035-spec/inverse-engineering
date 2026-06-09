# Quickstart: 流水线查询策略优化验证

## 基本验证

```bash
/run-pipeline --source tests/fixtures/java-vue-sample/
```

**预期产物**（`./output/java-vue-sample/`）：

```
architecture.md
business-flows.md
data-model.md
api-docs.md
state-machines.md
error-handling.md
uml/business/class-diagram.md
uml/business/state-diagram.md
uml/technical/component-diagram.md
flowcharts/flowchart.md
flowcharts/sequence-diagram.md
database.md
srs.md
quality.json
```

**quality.json 验证点**：
- `domain_coverage` 对象含 6 个领域条目
- 各条目有 `queried_files` / `total_files` / `coverage` 字段
- `doc_completeness_score` = 有实质内容文档数 / 非 skipped 领域数

## 循环查询验证（--max-batches）

```bash
/run-pipeline --source tests/fixtures/java-vue-sample/ --max-batches 2 --max-files-per-batch 3
```

验证 `quality.json` 中 `business_flows.queried_files <= 6`（2批 × 3文件），无报错。

## 覆盖率警告验证

对缺少某类文件的项目运行，验证：
- 无对应源码的领域在 `quality.json` 中 `skipped: "无源码证据"`
- 该领域不计入 `doc_completeness_denominator`
- 汇总报告中该领域显示 `⚠ 覆盖不足` 或跳过提示

## 质量门禁验证

```bash
/run-pipeline --source tests/fixtures/java-vue-sample/ --doc-quality-threshold 0.99
```

预期：若文档完整性分数 < 0.99，流水线在步骤 4 输出错误并终止，不生成 UML 和 SRS。

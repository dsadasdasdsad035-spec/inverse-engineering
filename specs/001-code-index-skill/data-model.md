# Data Model: 异构代码逆向工程 Skill 套件

**Date**: 2026-06-05 | **Feature**: 001-code-index-skill

---

## 核心实体

### Skill

流水线最小执行单元。

> **stage 枚举说明**：
> - `spec`：阶段 0（文档生成），通过 spec kit 生成系统技术文档
> - `ingest`：阶段 1（采集），通过 Codegraph CLI JSON 命令提取源码结构
> - `translate`：阶段 2（转译），将技术事实转换为技术无关 SRS 层
> - `generate`：阶段 3（生成），从 SRS 生成目标平台代码

| 字段 | 类型 | 约束 |
|------|------|------|
| name | string | 唯一，kebab-case |
| stage | enum | spec \| ingest \| translate \| generate |
| inputs | string[] | 上游产物路径列表 |
| outputs | string[] | 本 Skill 产物路径列表 |
| version | string | semver |

### SymbolNode（codegraph 符号节点）

来自 codegraph SQLite，只读映射。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | codegraph 内部唯一 ID |
| name | string | 符号名 |
| file_path | string | 所在文件路径 |
| type | enum | function \| class \| route \| variable |
| source_text | string | 原始代码片段 |

### FunctionalRequirement（FR）

SRS 层业务需求条目。

| 字段 | 类型 | 约束 |
|------|------|------|
| id | string | FR-NNN 格式，连续编号 |
| description | string | 技术无关业务语义 |
| source_symbol_ids | string[] | 追溯到的 codegraph 符号 ID 列表；空则为幽灵需求 |
| category | enum | functional \| nfr-reliability \| nfr-performance \| nfr-security \| nfr-availability \| nfr-maintainability |

### QualityReport

每次 Skill 运行产出，写入 `quality.json`。

| 字段 | 类型 | 说明 |
|------|------|------|
| skill_name | string | 产出该报告的 Skill |
| run_id | string | ISO 时间戳 |
| tech_agnostic_score | float | 0.0–1.0；阈值 = 1.0 |
| completeness_score | float | 0.0–1.0；阈值 ≥ 0.8 |
| uml_coverage_score | float | 0.0–1.0；阈值 ≥ 0.9 |
| parsed_files | int | 已解析文件数 |
| total_files | int | 总文件数 |
| symbol_count | int | 已提取符号节点数 |
| degraded_files | int | 降级为静态扫描的文件数 |
| skipped_uml_types | string[] | 无证据跳过的 UML 图类型 |
| refine_count | int | 本次运行 refine 次数（最大 3）|
| max_refine_reached | bool | 是否已达最大精化次数 |
| force_run | bool | 是否使用 --force 跳过覆盖率阻断 |

### SymbolSnapshot

一致性验证快照，存于 `.codebook/snapshots/<timestamp>.json`。

| 字段 | 类型 | 说明 |
|------|------|------|
| timestamp | string | ISO 时间戳 |
| symbols | SymbolNode[] | 本次索引的全量符号集合 |

### ProposalFile

Skill 自主进化提案，存于 `.codebook/proposals/<skill-name>-YYYY-MM-DD.md`。

| 字段（frontmatter）| 类型 | 说明 |
|-------------------|------|------|
| status | enum | pending \| approved \| rejected |
| skill_name | string | 提案针对的 Skill |
| created_at | string | ISO 日期 |
| trigger_type | string | 系统性缺陷类型描述 |

### CoverageMatrixRow

覆盖矩阵行，以符号节点为主键。

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol_id | string | codegraph 符号 ID |
| symbol_name | string | 函数/方法名 |
| file_path | string | 源码路径 |
| status | enum | COVERED \| MISSING \| PARTIAL |
| target_ref | string | 目标代码中的对应实现路径（MISSING 时为空）|

---

## 状态转换

### ProposalFile 状态机

```
pending → approved → [Skill 自动应用变更]
pending → rejected → [归档，不应用]
```

### QualityReport refine 流程

```
score < threshold
  → refine_count < 3 → refine() → re-eval
  → refine_count = 3 → max_refine_reached=true → 输出最佳版本
```

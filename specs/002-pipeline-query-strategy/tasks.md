# Tasks: 流水线查询策略优化

**Input**: `specs/002-pipeline-query-strategy/`（plan.md、spec.md、data-model.md、research.md）

---

## Phase 1: Setup（初始化）

- [x] T001 将 `specs/002-pipeline-query-strategy/plan.md` 复制确认为当前 CLAUDE.md plan 引用（已完成于实现阶段，此任务仅作记录）

---

## Phase 2: Foundational（阻塞前提）

**⚠️ CRITICAL**: Phase 3+ 全部依赖本阶段完成

- [x] T002 读取并理解 `.claude/skills/run-pipeline/skill.md` 现有结构，确认步骤编号和内容无误，为后续重构建立基线

**Checkpoint**: 基线确认，可开始并行实现

---

## Phase 3: User Story 1 — 分模块文档生成（Priority: P1）🎯 MVP

**Goal**: 每个领域查询完成后立即生成对应文档，不跨领域混合输入

**Independent Test**: 对 `tests/fixtures/java-vue-sample/` 运行 `/run-pipeline --source`，验证 `business-flows.md` 不含数据实体字段定义，`data-model.md` 不含接口路由信息

### Implementation

- [x] T003 [US1] 在 `.claude/skills/run-pipeline/skill.md` 步骤 1（参数解析）新增 `--max-files-per-batch`（默认 8）和 `--max-batches`（默认 5）两个可选参数及说明
- [x] T004 [US1] 将 skill.md 步骤 2（Codegraph 采集）和步骤 3（文档生成）重构为 6 个局部闭环单元（单元 A–F），每单元格式：codegraph_files 估算 → 循环 codegraph_explore → 立即生成对应文档
- [x] T005 [P] [US1] 在步骤 3 质量门禁中更新 `doc_completeness_score` 分母计算逻辑：从固定值 6 改为"非 skipped 领域数"，添加 `doc_completeness_denominator` 字段说明
- [x] T006 [US1] 验证 skill.md 步骤编号连贯（原步骤 3g 门禁变为新步骤 4，后续步骤顺延），确认 Done When 清单与新结构对应

**Checkpoint**: 分模块生成完成，对 fixture 运行后各文档内容互不污染

---

## Phase 4: User Story 2 — 查询范围自适应（Priority: P1）

**Goal**: 先查总文件数，自动决定批次大小，循环覆盖全部文件

**Independent Test**: 对含 >20 个服务类的代码库运行，`quality.json` 中 `domain_coverage.business_flows.queried_files` 大于单批上限（8），说明循环查询生效

### Implementation

- [x] T007 [US2] 在 skill.md 各单元的"通用循环查询逻辑"中补充完整的循环退出条件：`covered >= total_files` 或 `batch >= max-batches`，并说明超限时记录警告而非报错
- [x] T008 [P] [US2] 在 skill.md 通用查询逻辑中添加边界处理说明：`total_files == 0` 时立即标记 `skipped="无源码证据"`，不执行任何 codegraph_explore 调用

**Checkpoint**: 循环查询逻辑完整，边界条件覆盖

---

## Phase 5: User Story 3 — 查询覆盖率可见（Priority: P2）

**Goal**: `quality.json` 中每个领域有 `queried_files`/`total_files`/`coverage` 字段，低覆盖率领域标注警告

**Independent Test**: 运行完成后检查 `quality.json`，确认存在 `domain_coverage` 对象且含 6 个领域条目

### Implementation

- [x] T009 [US3] 在 skill.md 步骤 9（写入质量报告）中添加 `domain_coverage` 字段结构说明，格式参照 `data-model.md` 中 QualityReport 扩展章节
- [x] T010 [P] [US3] 在 skill.md 步骤 9 汇总报告展示部分新增覆盖率警告逻辑：`coverage < 0.8` 的领域在输出中标注 `⚠ 覆盖不足`

**Checkpoint**: 运行后 quality.json 包含 domain_coverage，汇总报告可见覆盖率警告

---

## Phase 6: Polish & Cross-Cutting

- [x] T011 [P] 将 `specs/002-pipeline-query-strategy/plan.md` 写入最终版（确认 Constitution Check 所有原则对齐）
- [x] T012 在 `specs/002-pipeline-query-strategy/` 补充 `quickstart.md`，记录验证步骤：`/run-pipeline --source tests/fixtures/java-vue-sample/ --max-batches 2`，预期产物列表

---

## Dependencies & Execution Order

- **Phase 1–2**：无依赖，立即开始
- **Phase 3（US1）**：依赖 Phase 2（基线确认）
- **Phase 4（US2）**：依赖 Phase 3（循环逻辑在闭环单元内部）
- **Phase 5（US3）**：依赖 Phase 3（domain_coverage 由单元 A–F 生成）
- **Phase 6**：依赖所有 US Phase 完成

### Parallel Opportunities

- T005 可与 T004 并行（不同段落）
- T008 可与 T007 并行（不同单元）
- T010 可与 T009 并行（不同段落）
- T011、T012 可并行（不同文件）

---

## Implementation Strategy

### MVP First（仅 User Story 1）

1. 完成 Phase 1 + Phase 2（T001–T002）
2. 完成 Phase 3（T003–T006）
3. **验证**：`/run-pipeline --source tests/fixtures/java-vue-sample/`
4. 检查各文档内容互不污染

### 增量交付

1. US1（分模块生成）→ 验证 → US2（循环查询）→ 验证 → US3（覆盖率）→ Polish

---

## Notes

- 本 feature 唯一修改文件：`.claude/skills/run-pipeline/skill.md`
- `[P]` 任务 = 修改不同段落/步骤，无冲突，可并行
- T003–T012 均已在 speckit-plan/speckit-implement 阶段完成

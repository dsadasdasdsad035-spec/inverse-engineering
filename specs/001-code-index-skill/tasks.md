# Tasks: 异构代码逆向工程 Skill 套件

**Input**: `specs/001-code-index-skill/`（plan.md、spec.md、data-model.md、contracts/、research.md）

**Git Remote**: `http://192.168.175.55:9888/iidp-ai/inverse-engineering.git`
- 进化成功：自动 `git commit` 并 push
- 进化失败：`git reset --hard` 回滚到上次成功提交

---

## Phase 1: Setup（项目初始化）

- [x] T001 初始化项目目录结构：`skills/ingest/`、`skills/translate/`、`skills/generate/`、`skills/shared/`、`.codebook/proposals/`、`.codebook/snapshots/`、`tests/fixtures/`、`tests/unit/`、`tests/integration/`
- [x] T002 [P] 创建 `requirements.txt`，固定依赖版本：`anthropic>=0.28`、`jinja2>=3.1`、`pytest>=8.0`
- [x] T003 [P] 创建技术术语词表 `skills/shared/term_filter.json`，初始收录：编程语言名（7种）、主流框架名、注解/装饰器模式、驼峰类名正则
- [x] T004 [P] 创建 Jinja2 文档模板目录 `skills/shared/templates/`，添加 `srs.md.j2`、`hla.md.j2`、`coverage-matrix.md.j2`、`blind-spots.md.j2`
- [x] T005 [P] 创建 Java+Vue fixture 代码库 `tests/fixtures/java-vue-sample/`，包含：带事务注解的 Service 类、状态枚举、路由、Vue 组件

---

## Phase 2: Foundational（所有 User Story 的阻塞前提）

**⚠️ CRITICAL**: Phase 3+ 全部依赖本阶段完成

- [x] T006 实现 `skills/shared/codegraph_client.py`：封装 `codegraph_files`、`codegraph_search`、`codegraph_callers`、`codegraph_node` 四个 MCP 工具调用，统一返回格式
- [x] T007 [P] 实现 `skills/shared/quality_report.py`：按 contracts/quality-json.md 契约写入 `quality.json`，所有字段必填
- [x] T008 [P] 实现 `skills/shared/evolution.py`：
  - refine 循环（最多 3 次），超限设 `max_refine_reached=true`
  - 系统性缺陷检测（连续 3 次同类触发），自动生成 `proposal-file.md`（`status: pending`）
  - 启动时扫描 `.codebook/proposals/`，应用 `status: approved` 的提案，归档 `status: rejected`
  - 进化成功后执行 `git add -A && git commit && git push http://192.168.175.55:9888/iidp-ai/inverse-engineering.git`
  - 进化失败（达到最大 refine 次数且分数未达标）执行 `git reset --hard`
- [x] T009 实现 `skills/shared/snapshot.py`：保存 codegraph 符号快照至 `.codebook/snapshots/<ISO-timestamp>.json`，并提供 diff 方法返回新增/删除/变更符号集合

**Checkpoint**: shared 模块就绪，三个 Skill 可开始并行实现

---

## Phase 3: User Story 1 — 源码导入并生成技术无关 SRS（Priority: P1）

**Goal**: 给定任意代码库，输出通过技术无关性检验的 srs.md + hla.md

**Independent Test**: 对 `tests/fixtures/java-vue-sample/` 运行采集+转译，验证 srs.md 无技术术语，FR 编号连续

### Implementation

- [x] T010 [P] [US1] 创建 `skills/ingest/skill.yml`，声明 `stage: ingest`、inputs/outputs 按 contracts/skill-frontmatter.md
- [x] T011 [P] [US1] 实现 `skills/ingest/main.py`：
  - 调用 `codegraph_client` 四工具提取符号节点、调用边、文件记录、路由节点
  - 不支持的技术栈降级文件级静态扫描，quality.json 标注 `degraded_files`
  - 调用 `snapshot.py` 保存符号快照
  - 写入 `quality.json`
- [x] T012 [US1] 创建 `skills/translate/skill.yml`，声明 `stage: translate`，inputs 包含 `.codegraph/codegraph.db`
- [x] T013 [US1] 实现 `skills/translate/term_filter.py`：加载 `term_filter.json` 词表，规则扫描命中后调用 LLM 做语义二次确认，返回违规术语列表
- [x] T014 [US1] 实现 `skills/translate/main.py` 核心转译逻辑：
  - 调用 codegraph_client 查询 `source_text`，按章程映射表转译为业务语义
  - 为每条业务功能生成 FR-NNN 编号，记录 `source_symbol_ids`
  - 检测幽灵需求（`source_symbol_ids` 为空），在 quality.json 标注
  - 用 Jinja2 渲染 `srs.md`（优先写入）和 `hla.md`，共享同一次 codegraph 查询缓存
- [x] T015 [US1] 实现 `skills/translate/self_eval.py`：
  - 规则维度：技术无关性（词表命中率）、完整性（FR数/路由节点数）、UML覆盖率
  - LLM 兜底：抽样 FR 语义审查、业务逻辑完整性
  - 返回三维得分 + 未达标维度列表
- [x] T016 [US1] 将 self_eval + evolution.py 的 refine 循环接入 `skills/translate/main.py`：分数不达标则触发 refine，超限则输出最佳版本

**Checkpoint**: 对 fixture 运行 `python skills/ingest/main.py` + `python skills/translate/main.py`，srs.md 无技术术语

---

## Phase 4: User Story 2 — UML 图自动生成（Priority: P1）

**Goal**: 转译阶段同步输出六类 Mermaid UML 图，无证据时跳过并记录

**Independent Test**: 对含状态枚举的 fixture 运行后，`uml/business/state-diagram.md` 存在且状态名为业务名

### Implementation

- [x] T017 [P] [US2] 实现 `skills/translate/uml_generator.py`：
  - 检测各图类型的源码证据（状态枚举→状态图，实体关联→ER图，调用链→序列图等）
  - 有证据则生成对应 Mermaid 代码块，状态/实体名使用业务语义名
  - 无证据则跳过，在 quality.json 的 `skipped_uml_types` 中记录
  - 写入对应路径：`flowcharts/`、`database.md`、`uml/business/`、`uml/technical/`
- [x] T018 [US2] 将 `uml_generator.py` 接入 `skills/translate/main.py`，在 srs.md/hla.md 渲染后执行，UML 覆盖率计入 quality.json

**Checkpoint**: `uml/business/state-diagram.md` 中状态名为业务名（如 `已审批` 而非 `APPROVED`）

---

## Phase 5: User Story 3 — Skill 自主进化（Priority: P2）

**Goal**: self-eval 评分不达标时自动 refine；系统性缺陷自动生成提案；进化成功 auto-commit，失败 git reset

**Independent Test**: 向 translate Skill 输入含技术术语的 fixture，`skill-evolution.log` 记录 refine，最终 srs.md 无该术语

### Implementation

- [x] T019 [US3] 实现 `skills/translate/blind_spot.py`：
  - 对比 codegraph route_nodes 与 hla.md API 清单，输出未覆盖条目
  - 盲区比例 = 未覆盖符号数 / 总符号数；超过 10% 触发 refine
  - 写入 `blind-spots.md`
- [x] T020 [US3] 将 `blind_spot.py` 接入 `skills/translate/main.py`，盲区检测在 UML 生成后执行，结果计入 self_eval 完整性维度
- [x] T021 [US3] 实现 `skills/generate/consistency.py`：
  - 调用 `snapshot.py` diff 检测源码符号变更
  - 对比每条 FR 的 `source_symbol_ids` 与当前符号集，输出新增/删除/变更 FR 条目
  - 写入 `consistency-diff.md`；存在未解决不一致项时设置退出码非零，阻断 generate 阶段
- [x] T022 [US3] 实现 `skills/generate/coverage_matrix.py`：
  - 以 codegraph 符号节点 ID 为主键，逐行列出 COVERED / MISSING / PARTIAL 状态
  - 覆盖率 < 95% 时默认阻断（退出码非零）；`--force` 标志跳过阻断，写入 `force_run: true`
  - 写入 `coverage-matrix.md`
- [x] T023 [US3] 实现 `skills/generate/main.py`：接受 `--target-platform` 和 `--srs` 参数，运行 consistency 检查 → 代码生成 → coverage_matrix；集成 evolution.py 的进化成功/失败 git 钩子（remote: `http://192.168.175.55:9888/iidp-ai/inverse-engineering.git`）
- [x] T024 [US3] 创建 `skills/generate/skill.yml`，声明 `stage: generate`，inputs 包含 `srs.md` 和 `coverage-matrix.md`

**Checkpoint**: 进化成功后 git log 可见自动提交；人工制造失败后 `git status` 显示回滚到上一提交

---

## Phase 6: Polish & Cross-Cutting

- [x] T025 [P] 为 `shared/codegraph_client.py` 编写单元测试 `tests/unit/test_codegraph_client.py`，mock MCP 工具返回
- [x] T026 [P] 为 `shared/term_filter.py`+`term_filter.json` 编写单元测试 `tests/unit/test_term_filter.py`
- [x] T027 [P] 为 `shared/evolution.py` 编写单元测试 `tests/unit/test_evolution.py`，覆盖：refine 循环上限、提案生成、git 成功/失败分支
- [x] T028 编写集成测试 `tests/integration/test_pipeline.py`：对 `tests/fixtures/java-vue-sample/` 通过 `/run-pipeline` MCP agent skill 跑完整阶段 0–2，验证 SC-001（零术语泄漏）、SC-002（95% 成功率）、SC-003（UML 覆盖率）
- [x] T029 [P] 执行 `quickstart.md` 验证：按文档步骤跑一遍，确认所有命令可用、产物路径正确
- [x] T030 [P] 更新 `README.md`（如存在），补充四阶段流水线说明、git remote 用途、--force 标志说明

---

## Phase 7: 阶段 0 实现 + 流水线质量修复（2026-06-06）**（已被 Phase 8 MCP agent 方案取代，下列任务已退役）**

### 阶段 0 — 文档生成 Skill（`skills/document/main.py`）

- [x] T031 实现 `skills/document/main.py`：静态分析源码（类、方法、注解、状态枚举、异常、事务、校验），生成 7 类技术文档
- [x] T032 修复 `_analyze_file()`：跳过 Javadoc/注释行（`*`、`//`、`/*`），补 Java 方法识别（`public/private/protected` 修饰符），过滤 `@param`/`@return` 等 Javadoc 注解标签
- [x] T033 修复文件收集逻辑：排除 `test/tests` 目录，防止测试类污染 API 文档
- [x] T034 [P] 在所有 `_generate_*` 函数中加入 LLM 语义分析（通过 `_llm_describe()` 辅助函数），产出业务叙述段落而非空表格：
  - `_generate_architecture_doc` → 模块职责和分层叙述
  - `_generate_data_model` → 实体及关联关系分析
  - `_generate_business_flows` → 每模块方法名 → 业务流程叙述
  - `_generate_api_docs` → 接口能力描述
  - `_generate_state_machines` → 状态含义和流转规则
  - `_generate_error_handling` → 错误处理策略
  - `_generate_dependencies` → 技术依赖约束概述
- [x] T035 在 `run_pipeline.py` 接入阶段 0：Stage 0（document）→ Stage 1（ingest）→ Stage 2（translate）顺序执行

### 阶段 2 — 转译质量修复

- [x] T036 新增 `_fr_from_stage0_docs(output_dir)` 函数：读取 Stage 0 产出的 `architecture.md`、`business-flows.md`、`api-docs.md`，按模块调用 LLM 生成业务语言 FR 列表
- [x] T037 修改 `translate/main.py` 主流程：Stage 0 文档优先路径（产出 ≥ 5 条 FR 时跳过 symbol 翻译），fallback 分支增加空 symbol 过滤
- [x] T038 修复 `translate/self_eval.py`：`completeness_score` 改为"有意义 FR 数（无技术术语且长度 > 5）/ 10"，不再使用 `route_count` 作为分母（route_count=0 时会导致虚假满分）
- [x] T039 [P] 修复 `translate/uml_generator.py`：state/class diagram 加 `file_path` 关键词 fallback；sequence diagram 无 routes 时用 controller 文件构建伪 routes，解决 snapshot 模式下 UML 覆盖率为 0 的问题

**Checkpoint**: `python run_pipeline.py` 完整执行阶段 0-2，`output/srs.md` 包含业务语言 FR，`output/business-flows.md` 包含模块叙述，`output/uml/` 下有 Mermaid 图文件

---

## Phase 8: 架构重构 — codegraph MCP 驱动（2026-06-06）

**背景**: 静态扫描方案（pipeline.py + skills/document/ingest/translate）产出质量低，根因是没有 MCP 上下文无法访问 codegraph。重构为在 Claude Code agent 上下文中直接调用 codegraph MCP，彻底解决信息来源问题。

### 架构转变

- [x] T040 重写 `.claude/skills/run-pipeline/skill.md`：从"执行 python pipeline.py"改为直接在 agent 里调用 codegraph MCP（codegraph_status → codegraph_explore × N → Write 文档 → 生成 SRS + UML + quality.json）
- [x] T041 退役 `pipeline.py`、`run_pipeline.py`（已删除）
- [x] T042 退役 `skills/document/`、`skills/ingest/`、`skills/generate/`、`skills/translate/main.py` 等静态扫描代码（已删除）
- [x] T043 保留 `skills/shared/llm_router.py`（MiniMax API 封装，供参考）和 `skills/translate/self_eval.py`（质量评分逻辑，供参考）

### 新方案验证（sie-snest，24,930 节点，67,439 条边）

- [x] T044 codegraph_explore 直接获取真实源码（AppContainer/RpcController/BaseMeta/ErrorCode 等核心类完整 source_text）
- [x] T045 基于真实代码生成 7 类文档（architecture/data-model/business-flows/api-docs/state-machines/error-handling/srs）
- [x] T046 生成 6 类 Mermaid UML 图（class/state/sequence/flowchart/er/component），全部含真实类名和业务逻辑
- [x] T047 SRS 产出 21 条 FR + 7 条 NFR，全部业务语言，技术无关性 1.0 / 完整性 1.0 / UML 覆盖率 1.0

**Checkpoint**: `/run-pipeline --source <path>` → codegraph 索引确认 → 文档写出 → 汇总报告，全程无 Python 脚本参与

---

## Phase 9: Skill 进化机制重建（2026-06-06）

**背景**: Constitution 原则五要求的进化机制随旧 Python 代码退役后断开，本阶段在 skill.md 层面重建完整闭环。

- [x] T048 在 `run-pipeline/skill.md` 加入步骤 0（前置）：运行前检查 `.codebook/proposals/` 中 `status: approved` 的文件，按建议修改 skill.md，标记为 applied，写入 `.codebook/skill-evolution.log`
- [x] T049 在 `run-pipeline/skill.md` 步骤 6 加入质量评估（三维分数先用于 refine，不立即写 quality.json）
- [x] T050 在 `run-pipeline/skill.md` 加入步骤 7 Refine Loop（最多 **3 轮**，与 FR-007 和章程原则五对齐）：tech 违规术语重写、completeness 按模块补 codegraph_explore、uml 补生成缺失图
- [x] T051 Refine 3 轮后仍不达标时写 `.codebook/proposals/run-pipeline-<date>.md`，status 流转：pending → approved → applied
- [x] T052 [章程原则六质量门禁] 在 `run-pipeline/skill.md` 阶段 0 完成后读取 `quality.json` 完整性指标（`doc_completeness_score`），低于阈值（默认 0.8）时输出错误信息并终止 skill，不进入阶段 1 采集；阈值可通过 `--doc-quality-threshold` 参数覆盖（已实现于 `.claude/skills/run-pipeline/skill.md` 步骤 3g）

**进化闭环**:
```
refine 3次不达标 → proposals/(status:pending)
→ 人工改为 approved
→ 下次运行步骤 0 自动应用 → status:applied → skill.md 改进
```

---

- **Phase 1（Setup）**：无依赖，立即开始
- **Phase 2（Foundational）**：依赖 Phase 1
- **Phase 3（US1）**：依赖 Phase 2
- **Phase 4（US2）**：依赖 Phase 3（T014 必须先完成）
- **Phase 5（US3）**：依赖 Phase 2；T019/T020 依赖 Phase 4；T021–T024 依赖 Phase 3
- **Phase 6（Polish）**：依赖所有 US Phase 完成

### 关键依赖链

```
T006 → T011（codegraph_client）
T007 → T011、T014（quality_report）
T008 → T016、T023（evolution + git hooks）
T009 → T011、T021（snapshot + diff）
T013 → T014（term_filter → translate core）
T015 → T016（self_eval → refine loop）
T017 → T018（uml_generator → translate main）
T019 → T020 → T015（blind_spot → self_eval）
```

### Parallel Opportunities

T010、T011、T012 可与 T002–T005 并行（不同文件）
T017、T018 可与 T019–T024 并行（不同 Skill）
T025–T027 可并行（不同测试文件）

---

## Implementation Strategy

### MVP First（仅 User Story 1）

1. 完成 Phase 1 + Phase 2
2. 完成 Phase 3（T010–T016）
3. **验证**：`/run-pipeline --source tests/fixtures/java-vue-sample/`
4. 检查 `srs.md` 无技术术语，FR 编号连续，`quality.json` 三维得分达标

### 增量交付

1. MVP（US1）→ 验证 → UML 生成（US2）→ 验证 → 进化机制（US3）→ Polish

### 注意事项

- `[P]` 任务 = 不同文件，无未完成依赖，可并行
- `[USn]` 标签映射到 spec.md 中的对应用户故事
- 每个 Checkpoint 是独立验收点，可在此暂停演示
- git remote `http://192.168.175.55:9888/iidp-ai/inverse-engineering.git` 仅在 evolution.py 中使用，不影响日常开发工作流

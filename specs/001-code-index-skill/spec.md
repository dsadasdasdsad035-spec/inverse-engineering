# Feature Specification: 异构代码逆向工程 Skill 套件

**Feature Branch**: `001-code-index-skill`

**Created**: 2026-06-05

**Status**: 架构重构完成（Codegraph CLI-first，阶段 3 待实现）

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 源码导入并生成技术无关 SRS（Priority: P1）

业务分析师或架构师将一个异构系统（Java / Python / Go / Node / C# / Vue / React 等任意组合）的代码库接入流水线，期望得到一份完全技术无关的需求文档（srs.md），无需自己阅读源码。

**Why this priority**: 这是整条流水线的核心价值——将代码翻译为业务语言，是后续所有工作的前提。

**Independent Test**: 给定一个包含至少两种技术栈的示例代码库，执行 Skill 后，srs.md 中不应出现任何语言名、框架名或类名；所有业务需求均以 FR-NNN 编号呈现。

**Acceptance Scenarios**:

1. **Given** 一个 Java Spring Boot + Vue 项目的代码库，**When** 执行 `/run-pipeline --source <path>`，**Then** 通过 Codegraph CLI JSON 命令提取符号节点、调用边、文件记录、路由节点四类数据，生成阶段 0 技术文档后进入采集阶段。
2. **Given** 已完成阶段 0 文档生成，**When** `/run-pipeline` 继续执行转译阶段，**Then** 输出 srs.md，其中 FR 编号连续（FR-001 起），且文档内容不含任何技术术语。
3. **Given** 源码中存在事务注解，**When** 转译阶段处理该方法，**Then** srs.md 对应需求描述为"操作具有原子性保证（NFR-可靠性）"。

---

### User Story 2 — UML 图自动生成（Priority: P1）

架构师在得到 srs.md 后，还需要配套的业务视角 UML 图（状态图、类图）以及技术参考图（组件图、序列图、ER 图），全部使用 Mermaid 语法，可直接嵌入文档或渲染工具。

**Why this priority**: 需求文档若缺乏可视化，沟通成本极高；UML 覆盖是章程强制要求。

**Independent Test**: 执行转译阶段 Skill 后，`uml/business/` 和 `flowcharts/` 目录中应分别存在至少一个 `.md` 文件，且每个文件包含合法的 Mermaid 代码块。

**Acceptance Scenarios**:

1. **Given** 源码中含有状态枚举字段，**When** Skill 处理完成，**Then** `uml/business/state-diagram.md` 存在，包含 `stateDiagram-v2` 语法，状态名为业务名称而非枚举值。
2. **Given** 源码中含有多个实体及其关联关系，**When** Skill 处理完成，**Then** `database.md` 包含 `erDiagram` 代码块。
3. **Given** 任意代码库，**When** Skill 处理完成，**Then** `flowcharts/` 下包含序列图和流程图各至少一个。

---

### User Story 3 — Skill 自主进化（Priority: P2）

平台运营人员希望每次运行结束后，Skill 能自动评分本次输出质量，并在分数低于阈值时自动精化，同时将改进建议写入提案文件供人工审查——无需人工干预即可持续提升输出质量。

**Why this priority**: 自主进化是本套件区别于普通代码分析工具的核心差异点；但不阻塞 P1 功能交付。

**Independent Test**: 在一次包含明显技术术语泄漏的测试运行后，日志 `.codebook/skill-evolution.log` 应记录"触发 refine：检测到技术术语 X"，最终 srs.md 不含该术语。

**Acceptance Scenarios**:

1. **Given** Skill 输出的 srs.md 包含技术术语，**When** `self-eval` 入口执行，**Then** 质量评分低于阈值，自动触发 `refine` 流程，输出精化后的 srs.md。
2. **Given** 连续三次运行均在同一类问题上触发 refine，**When** Skill 检测到系统性缺陷，**Then** 生成 `.codebook/proposals/<skill-name>-2026-06-05.md` 提案文件，内容包含问题描述和修改建议。
3. **Given** 所有输出均通过质量评分，**When** Skill 完成运行，**Then** `quality.json` 记录各维度得分，不触发 refine。

---

### Edge Cases

- 源码中存在混用多语言（如 Java 调用 Python 脚本）时，两种语言的技术术语均不得出现在 srs.md。
- 当 codegraph 无法解析某个文件时，Skill 应记录跳过原因并继续处理其余文件，不得中断整个流程。
- 当 codegraph 不支持某种技术栈（如 C# 支持有限）时，采集阶段降级为文件级静态扫描，仍输出有限 SRS；`quality.json` 中标注该技术栈的覆盖度不足，不阻断流程。
- 状态枚举中若枚举值本身即为业务语言（如 `APPROVED`、`REJECTED`），应直接使用，不需要额外映射。
- Qdrant 向量库不可用时，流水线前四阶段不受影响，仅 Phase E 降级跳过。
- 覆盖率低于 95% 时，生成阶段默认阻断；用户可通过 `--force` 标志强制跳过，产物顶部添加警告注释，quality.json 记录"强制运行，覆盖率未达标"。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统必须支持对以下技术栈的源码进行结构提取：Java、Python、Go、Node.js、C#/.NET、Vue、React。
- **FR-002**: 系统必须使用 Codegraph CLI JSON 命令（`status`、`files`、`query`、`callers`、`callees`）作为采集阶段的主要机制，项目地址：https://github.com/colbymchenry/codegraph。
- **FR-003**: 系统必须将技术事实按章程标准映射表转译为业务语义，输出 srs.md，且 srs.md 不得包含任何技术术语。
- **FR-004**: 系统必须在同一次转译阶段运行中同时产出分层输出：第一层 srs.md（技术无关，优先写入），第二层 hla.md + uml/technical/（技术参考，共享同一次 codegraph 查询缓存）。
- **FR-005**: 系统必须在存在对应源码证据时生成六类 UML 图（流程图、序列图、ER 图、业务状态图、业务类图、技术组件图）；无对应证据时跳过该图类型，并在 quality.json 中记录"无对应源码证据，已跳过"，不生成空图或占位文件。
- **FR-006**: 每个 Skill 必须暴露 `self-eval` 入口，按完整性、技术无关性、UML 覆盖率三个维度打分；评分采用规则优先 + LLM 兜底机制——结构性指标用规则计算，语义判断由 **MiniMax** 模型执行。
- **FR-015**: 转译阶段的语义翻译（词表未覆盖符号→业务语言）必须调用 **Claude Opus** 模型（base_url: `https://code.newcli.com/droid/ultra`）；评估/打分调用 **MiniMax** 模型。凭证通过项目根目录 `.env` 文件注入，不写入代码。
- **FR-016**: 系统必须以 `/run-pipeline` Claude Code skill 作为唯一执行入口，在 agent 上下文中执行 Codegraph CLI JSON 命令完成采集、文档生成、SRS 转译全流程；不依赖 MCP 服务或独立 Python 流水线脚本（pipeline.py 已退役）。
- **FR-007**: 质量分数低于阈值时，系统必须自动触发 `refine` 流程，精化输出后再次评分；单次运行中 refine 最多执行 3 次，超限后输出最佳版本并在 quality.json 中标注"已达最大精化次数"。
- **FR-008**: 系统必须将每次精化决策记录至 `.codebook/skill-evolution.log`。
- **FR-009**: 当系统检测到系统性缺陷（连续触发相同类型 refine）时，必须在 `.codebook/proposals/` 生成提案文件，文件头部包含 `status: pending`；Skill 在下次运行时检测 `status: approved` 后自动应用变更，`status: rejected` 则归档跳过。
- **FR-010**: 每个 Skill 必须在 YAML frontmatter 中声明 `stage`、`inputs`、`outputs`，并在执行前验证上游产物存在。
- **FR-013**: 一致性验证 Skill 必须在每次运行后保存 codegraph 符号快照；下次运行时对比两次快照的符号集合差异（新增/删除/变更符号），存在差异则自动输出 consistency-diff.md。（阶段 3 延期，原实现已随 `skills/generate/` 退役；阶段 3 启动时重建。）
- **FR-014**: 阶段 3（生成至 IIDP）延期至下一阶段规划，当前版本不实现。阶段 0（文档生成）已通过 `/run-pipeline` agent skill 实现，并于 2026-06-09 改为 Codegraph CLI-first；Python pipeline.py 已退役，`skills/generate/` 静态代码已删除。
- **FR-011**: 每次运行必须输出机器可读的 `quality.json` 质量报告，至少包含：完整性得分、技术无关性得分、UML 覆盖率得分、已解析文件数/总文件数、已提取符号节点数、降级为静态扫描的文件数。
- **FR-012**: Qdrant 向量库集成为可选，仅在 Phase E 使用，不得阻塞阶段 1–3 的执行。

### Key Entities

- **Skill**：流水线中的最小执行单元，归属四阶段之一（阶段 0 文档生成、阶段 1 采集、阶段 2 转译、阶段 3 生成），具备 self-eval 和 refine 能力。当前实现为 `/run-pipeline` Claude Code skill（Codegraph CLI-first），不依赖 MCP 服务或独立 Python 流水线脚本。
- **SRS 文档**：阶段间唯一交接产物，技术无关，包含 FR 编号体系和 NFR 表格。
- **codegraph 数据库**：SQLite 格式，存储符号节点、调用边、文件记录、路由节点；通过 Codegraph CLI JSON 命令访问，流水线不直接读取数据库。
- **质量报告**：每次运行产出的 `quality.json`，包含各维度得分、覆盖度指标和精化记录。
- **提案文件**：Skill 检测到系统性缺陷后自动生成，含 `status` 字段（pending/approved/rejected），Skill 下次运行时自动检测并应用或归档。
- **符号快照**：一致性验证每次运行后保存的 codegraph 符号集合，用于下次运行时做 diff 检测源码变更。
- **Phase E**：可选的 SRS 后期增强阶段，依赖 Qdrant 向量库；不可用时静默跳过，不阻塞阶段 0–3。

## Success Criteria *(mandatory)*

- **SC-001**: 给定任意单一技术栈代码库，srs.md 中技术术语零泄漏率（人工抽查 20 条 FR，无一包含语言/框架名）。
- **SC-002**: 给定包含两种及以上技术栈的代码库，SRS 生成成功率不低于 95%（不因技术栈混用而中断）。
- **SC-003**: 六类 UML 图在存在对应源码证据时的生成覆盖率不低于 90%。
- **SC-004**: `self-eval` 触发 `refine` 后，精化版 srs.md 技术术语数量相比原版减少 80% 以上。
- **SC-005**: 系统性缺陷提案文件在连续三次相同类型 refine 后，于当次运行结束前自动生成。
- **SC-006**: 完整四阶段流水线（阶段 0-3，不含 Phase E）端到端运行时间，对于 10 万行以下代码库不超过 10 分钟。

## Clarifications

### Session 2026-06-05

- Q: 当 codegraph 不支持某种技术栈时，采集阶段如何处理？ → A: 降级为文件级静态扫描，输出有限 SRS，quality.json 标注覆盖度不足，不阻断流程。
- Q: hla.md 与 srs.md 的输出触发时机？ → A: 同一次转译阶段运行同时产出两层，共享 codegraph 查询缓存，srs.md 优先写入。
- Q: quality.json 中应包含哪些 codegraph 覆盖度指标？ → A: 已解析文件数/总文件数、已提取符号节点数、降级为静态扫描的文件数。
- Q: 单次运行中 refine 最多执行几次？ → A: 最多 3 次，超限后输出最佳版本并在 quality.json 中标注"已达最大精化次数"。
- Q: 源码中缺乏对应证据时，缺失的 UML 图如何处理？ → A: 跳过无证据的图类型，quality.json 记录"无对应源码证据，已跳过"，不生成空图或占位文件。

### Session 2026-06-05（可实现/可进化审视）

- Q: self-eval 评分机制是 LLM 还是规则？ → A: 规则优先 + LLM 兜底——结构性指标用规则计算，语义判断调用 LLM。
- Q: 源码变更如何检测以触发一致性验证？ → A: codegraph 符号集合 diff——对比两次索引快照，新增/删除/变更符号即触发。
- Q: 覆盖率不足阻断生成阶段时如何解除？ → A: 提供 --force 标志强制跳过，产物顶部添加警告，quality.json 记录"强制运行，覆盖率未达标"。
- Q: 进化提案的人工审批交互形式？ → A: 文件 status 字段标记（pending/approved/rejected），Skill 在下次运行时自动检测并应用或归档。
- Q: coverage-matrix.md 的覆盖粒度？ → A: 函数/方法级，以 codegraph 符号节点为最小单位。

### Session 2026-06-05（实现决策同步）

- Q: 转译写作和评估分别用什么模型？ → A: 写作（符号→业务语义）用 Claude Opus，评估（self-eval 语义确认）用 MiniMax。
- Q: 四阶段流水线各阶段的实现状态？ → A: 阶段 1-2 已实现并可用；阶段 0（文档生成）和阶段 3（生成）待下一阶段规划；pipeline.py 当前执行阶段 1-2。（⚠ 已过时，见下方 2026-06-06 更新）
- Q: 环境变量如何管理？ → A: 通过项目根目录 .env 文件注入，llm_router.py 自动加载，不需要手动 export。

### Session 2026-06-08（架构状态更新）

- Q: 四阶段流水线当前实现状态？ → A: 阶段 0（文档生成）已通过 `/run-pipeline` agent skill 实现；阶段 1-2 集成在同一 skill 中；阶段 3（生成至 IIDP）仍延期；Python pipeline.py 和 skills/document/ingest/translate 静态代码已全部退役删除。
- Q: `/run-pipeline` skill 的执行入口是什么？ → A: `.claude/skills/run-pipeline/SKILL.md`，直接在 agent 上下文中执行 Codegraph CLI JSON 命令，无需 MCP 服务或独立 Python 进程。
- Q: SC-006（≤10 分钟）如何验收？ → A: 当前标注为人工验收项，尚无自动化基准测试；阶段 3 接入后再补充自动化测试。

## Assumptions

- 代码库已可被本地文件系统访问，Skill 无需处理远程仓库拉取。
- Codegraph CLI 0.9.9 或兼容版本已安装，目标源码目录已完成索引初始化。
- 质量评分阈值采用默认值（完整性 ≥ 0.8，技术无关性 = 1.0，UML 覆盖率 ≥ 0.9），具体值可在 Skill 配置中覆盖。
- Qdrant 不可用时，Phase E 静默跳过，不抛出错误。
- 用户拥有对 `.codebook/` 目录的写入权限。

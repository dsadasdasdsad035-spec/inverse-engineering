# Feature Specification: 可配置的包/模组遍历与 Codebook 模板化

**Feature Branch**: `003-configurable-codebook-traversal`

**Created**: 2026-06-08

**Status**: Implemented

## User Stories & Testing

### User Story 1 — 顶级入口自适应发现（Priority: P1）

流水线使用者希望 `/run-pipeline` 能按包名或模组逐个遍历源码，而不是依赖硬编码目录。多模组项目以模组为入口，无模组后端以“公共根包 + 下一层包”为入口，纯前端项目以前端源码根目录为入口。

**Acceptance Scenarios**:

1. **Given** 用户传入 `--module` 或 `--package <包名>`，**When** 初始化 Codebook，**Then** `entries.json` 优先使用显式入口。
2. **Given** 后端项目没有模组标记，**When** 识别包名，**Then** 按公共根包下一层生成 `backend_package` 入口。
3. **Given** 纯前端项目没有后端包名，**When** 识别源码根，**Then** 生成 `frontend_root` 入口。

### User Story 2 — Codegraph CLI 参数配置化（Priority: P1）

流水线使用者希望 Codegraph CLI 命令、`maxDepth`、`limit`、`kind`、源码读取和错误策略通过配置调整，避免频繁修改 skill 正文，并避开 MCP 搜索最多返回 100 条结果导致的路径查询漏数。

**Acceptance Scenarios**:

1. **Given** `<output>/.codebook/codegraph-tools.json` 已存在，**When** 运行流水线，**Then** 使用该文件中的 Codegraph CLI 参数数组执行命令。
2. **Given** `inventory.json` 中存在源码文件，**When** 枚举原生符号，**Then** 使用 `codegraph query -j path:<精确文件路径>` 查询该文件全部节点，按 `node.filePath` 精确过滤、按 `node.id` 去重，并与 `codegraph files -j` 的 `nodeCount` 对账。
3. **Given** 任一文件的实际节点数与 `nodeCount` 不一致，**When** 完成入口采集，**Then** 标记该入口符号枚举不完整并阻止其进入文档生成。
4. **Given** 前端语义需要 `store/page/hook`，**When** 执行 Codegraph CLI 查询，**Then** 这些值不作为原生 `kind` 传入，只由 `semantic-kinds.json` 分类。
5. **Given** CLI 没有独立节点详情命令，**When** 深挖符号，**Then** 使用查询节点的 `filePath/startLine/endLine` 读取源码，不依赖 Codegraph MCP。
6. **Given** `codegraph files -j` 的 glob 没有匹配文件，**When** CLI 返回信息文本而不是 JSON，**Then** 将该结果归一化为空数组，其他非法 JSON 仍阻断当前入口。

### User Story 3 — prompt 模板外置与 UI 布局 JSON（Priority: P2）

流水线维护者希望文档和 UI 布局提示词外置到 JSON 模板，便于按项目调整，不再把提示词硬编码在 skill 正文。

**Acceptance Scenarios**:

1. **Given** `<output>/.codebook/prompts/temp_srs.json` 存在，**When** 生成 SRS，**Then** 使用该模板并保留需求追溯信息。
2. **Given** 前端入口存在页面、组件、Store 或 Hook 证据，**When** 读取 `temp_ui.json`，**Then** 生成 `evidence/<entry-id>/ui-layout.json`。
3. **Given** 没有前端证据，**When** 运行 UI 阶段，**Then** `quality.json.ui_layout` 记录中文跳过原因，不生成静态页面。

### User Story 4 — 入口级完整文档门禁（Priority: P1）

流水线使用者希望每个入口只在证据完整时生成可独立阅读的完整文档，避免局部片段或关键节点抽样污染系统级汇总。

**Acceptance Scenarios**:

1. **Given** 入口已完成全部文件、符号、节点和 TypeCard 采集，**When** 生成入口文档，**Then** 每份文档使用该入口全部证据一次性生成并原子写入。
2. **Given** 入口符号枚举不完整，**When** 到达文档生成阶段，**Then** 跳过该入口文档并记录中文错误。
3. **Given** 存在任一非跳过入口不完整，**When** 到达系统级汇总阶段，**Then** 阻止生成系统级文档、SRS 和 UML。

## Requirements

- **FR-001**: 流水线必须在 `<output>/.codebook/` 初始化并读取 `manifest.json`、`entries.json`、`codegraph-tools.json`、`semantic-kinds.json` 和 `prompts/*.json`。
- **FR-002**: 配置缺失时自动初始化；配置已存在时不得覆盖人工修改。
- **FR-003**: `--refresh-entries` 只能覆盖 `entries.json`，不得覆盖 prompt 和工具策略。
- **FR-004**: 顶级入口发现优先级必须固定为：显式参数 → 模组 → 后端包 → 前端源码根目录 → 项目根目录。
- **FR-005**: `codegraph files -j` 必须作为文件枚举入口；`codegraph query -j` 必须使用 `path:<精确文件路径>` 逐文件全量定位符号，禁止按文件名、符号名、关键字或关键文件抽样。
- **FR-006**: Codegraph CLI 二进制、最低版本、命令参数数组、`maxDepth`、`limit`、`kind`、源码读取和错误策略必须通过 `codegraph-tools.json` 配置。
- **FR-007**: `store/page/hook` 必须作为 `semantic-kinds.json` 中的语义 kind，不得作为 codegraph 原生 kind。
- **FR-008**: 每个入口必须独立生成 `inventory.json`、`nodes.json`、`typecards.json`，前端入口额外生成 `ui-layout.json`。
- **FR-009**: `quality.json` 必须新增 `entry_coverage`、`config_snapshot`、`query_truncation_warnings` 和 `ui_layout` 字段，同时保留旧统计字段。
- **FR-010**: 配置、prompt、evidence、checkpoint、proposal 和 evolution log 必须统一写入 `<output>/.codebook/`。
- **FR-011**: 项目根目录现有 `.codebook/` 必须作为旧数据保留；新运行不得读取、覆盖、自动迁移或删除。
- **FR-012**: 每个文件的精确路径查询结果必须与 `codegraph files -j` 的 `nodeCount` 对账；任一文件不一致时必须阻断该入口进入文档生成。
- **FR-013**: 每份入口文档必须使用该入口全部证据一次性生成，通过完整性校验后原子写入，禁止关键 TypeCard 抽样和局部片段输出。
- **FR-014**: 存在任一非跳过入口的符号枚举或入口文档不完整时，流水线必须阻断系统级文档、SRS 和 UML 汇总。
- **FR-015**: 流水线必须使用 Codegraph CLI JSON 输出作为原生证据来源，不依赖 Codegraph MCP 服务，也不得直接读取 Codegraph SQLite 数据库。
- **FR-016**: `quality.json` 必须记录 Codegraph CLI 版本、传输方式、已执行命令、查询失败和数量对账失败。
- **FR-017**: 仅允许将 `codegraph files -j` 的无匹配信息归一化为空数组；其他 CLI 非零退出码或非法 JSON 必须按错误策略处理。

## Success Criteria

- **SC-001**: 契约测试能验证默认 JSON 模板完整、可解析并包含必需字段。
- **SC-002**: 当前唯一维护的 `.claude/skills/run-pipeline/SKILL.md` 通过配置化流程契约测试。
- **SC-003**: `temp_ui.json` 的输出 Schema 至少要求 `layout`、`source_nodes`、`confidence`。
- **SC-004**: 调整 `codegraph-tools.json` 不需要修改 skill 正文即可改变工具参数。
- **SC-005**: 每个已完成入口的 `enumerated_files == inventory_files` 且 `enumerated_symbols == expected_symbols`。
- **SC-006**: 系统级汇总只在所有非跳过入口的 `symbol_enumeration_complete` 与 `document_generation_complete` 均为 `true` 时执行。
- **SC-007**: 在大型索引中，位于全局前 500 个候选之外的文件仍能通过 CLI 精确路径查询完成节点数量对账。

## Assumptions

- Codebook 位于 `<output>/.codebook/`，不同输出目录之间互不共享。
- 项目根目录现有 `.codebook/` 保留为旧数据，本次不自动迁移。
- 后端默认包粒度为“公共根包 + 下一层包”。
- UI 阶段仅产出结构化布局 JSON，不生成静态页面。
- 当前仓库只维护 `.claude/skills/run-pipeline/SKILL.md`，不恢复 `.agents` 或 `.cursor` 镜像。
- Codegraph CLI `status -j` 能提供索引全部节点数，作为逐文件精确路径查询的上限。
- Codegraph CLI 版本为 `0.9.9` 或兼容版本。
- 已退役 Python pipeline 的旧测试不纳入本特性修复范围。

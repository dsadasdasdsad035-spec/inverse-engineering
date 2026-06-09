# Tasks: 可配置的包/模组遍历与 Codebook 模板化

**Input**: `specs/003-configurable-codebook-traversal/`

## Phase 1: Contract Tests

- [x] T001 添加 `tests/unit/test_codebook_configuration_contract.py`，验证默认配置、prompt 模板、当前维护的 `.claude` Skill 和 003 规格存在。
- [x] T002 先运行契约测试并确认失败，失败原因应为默认资产和 003 规格缺失。

## Phase 2: Default Assets

- [x] T003 新增 `resources/codebook/defaults/manifest.json`。
- [x] T004 新增 `entries.json`，声明入口发现优先级和 EntryDefinition 契约。
- [x] T005 新增 `codegraph-tools.json`，配置 `maxDepth`、`maxFiles`、`limit`、`kind`、`includeCode`。
- [x] T006 新增 `semantic-kinds.json`，将前端 page/component/store/hook/api/route/function 作为语义 kind。
- [x] T007 新增 6 个 prompt 模板，包含 `temp_srs.json` 和 `temp_ui.json`。

## Phase 3: Skill Update

- [x] T008 更新当前唯一维护的 `.claude/skills/run-pipeline/SKILL.md`。
- [x] T009 在 skill 中新增 `--package <包名>`、`--init-only`、`--refresh-entries` 参数。
- [x] T010 在 skill 中明确 `<output>/.codebook/` 初始化、逐入口采集、截断警告、UI 布局 JSON 和 `quality.json` 扩展。

## Phase 4: Verification

- [x] T011 运行新增契约测试。
- [x] T012 记录旧 pytest 全量收集失败仍来自已退役 Python pipeline 模块，不混入本特性修复。

## Phase 5: Output-local Codebook

- [x] T013 将 `codebook_root` 改为 `<output>/.codebook/`，所有运行态目录通过该变量访问。
- [x] T014 在 manifest 中声明 evidence、checkpoints、proposals 和 evolution log。
- [x] T015 明确项目根目录现有 `.codebook/` 为旧数据，不读取、不覆盖、不自动迁移、不删除。

## Phase 6: Exhaustive Symbols and Complete Entry Documents

- [x] T016 使用 `path:<精确文件路径>` 逐文件枚举全部 Codegraph 原生节点，并与 `codegraph files -j` 的 `nodeCount` 对账。
- [x] T017 任一文件对账失败时阻断对应入口进入文档生成。
- [x] T018 入口文档使用全部证据一次性生成，通过完整性校验后原子写入。
- [x] T019 存在任一非跳过入口不完整时，阻断系统级文档、SRS 和 UML 汇总。

## Phase 7: Codegraph CLI-first

- [x] T020 将 Codegraph 状态、文件、符号、调用者和被调用者采集改为 CLI JSON 命令模板。
- [x] T021 对每个路径查询结果执行 `node.filePath` 精确过滤和 `node.id` 去重。
- [x] T022 使用 `filePath/startLine/endLine` 读取源码，替代 MCP `codegraph_node`。
- [x] T023 在 `quality.json` 记录 CLI 版本、命令执行、查询失败和数量对账失败。
- [x] T024 增加 CLI-only 配置与 Skill 契约测试。
- [x] T025 将 `files -j` 无匹配信息文本归一化为空数组，其他非法 JSON 继续阻断。

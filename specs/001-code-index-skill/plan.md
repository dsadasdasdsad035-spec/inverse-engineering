# Implementation Plan: 异构代码逆向工程 Skill 套件

**Branch**: `001-code-index-skill` | **Date**: 2026-06-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-code-index-skill/spec.md`

## 摘要

构建一套四阶段流水线 Skill：阶段 0–2 已通过 `/run-pipeline` agent skill 实现，并于 2026-06-09 改为 Codegraph CLI-first；阶段 3（IIDP 代码生成）延期至下一阶段规划。Python pipeline.py 和静态 skills/ 目录已全部退役。

## Technical Context

**Language/Version**: Python 3.11（Skill 脚本）；Mermaid（UML 输出）

**Primary Dependencies**: Codegraph CLI 0.9.9+（https://github.com/colbymchenry/codegraph）、anthropic SDK、httpx、Jinja2

**LLM 分工**:
- **写作模型**：Claude Opus（`claude-opus-4-7`，base_url: `https://code.newcli.com/droid/ultra`）
  - 用途：词表未覆盖的符号 → 业务语义翻译
- **评估模型**：MiniMax（`abab6.5s-chat`，base_url: `https://api.minimax.chat/v1`）
  - 用途：self-eval 技术术语语义确认

**凭证管理**: 项目根目录 `.env` 文件（已加入 `.gitignore`），由 `skills/shared/llm_router.py` 自动加载。

**Storage**: SQLite（codegraph.db）；JSON（quality.json、符号快照）；Markdown（所有文档产物）

**Testing**: pytest；Java+Vue fixture 代码库（`tests/fixtures/java-vue-sample/`）

**Target Platform**: 本地文件系统（CLI，通过 `/run-pipeline` Claude Code skill 调用；pipeline.py 已退役）

**Performance Goals**: 10 万行以下代码库完整两阶段运行 ≤ 10 分钟

**Constraints**: Codegraph CLI 须预先安装且目标源码已初始化索引；`.env` 须配置两个模型 key

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. 四阶段流水线完整性** — `/run-pipeline` skill frontmatter 声明 stage；阶段 0-2 已实现
- [x] **II. 技术无关 SRS 层** — 转译阶段输出前强制过术语词表；违规则 halt
- [x] **III. 分层输出结构** — 同次运行产出 srs.md（优先）+ hla.md，共享 codegraph 查询缓存
- [x] **IV. UML 图覆盖要求** — 无证据时跳过并在 quality.json 记录；不生成空图
- [x] **V. Skill 自主进化** — self-eval 规则+MiniMax 兜底；max 3 refine；log 写 skill-evolution.log
- [x] **VI. 文档先行原则** — 质量门禁已实现（`.claude/skills/run-pipeline/skill.md` 步骤 3g，T052）
- [x] **VII. Codegraph 优先提取** — 采集使用 Codegraph CLI JSON 命令，不依赖 MCP 服务
- [ ] **VIII. Functional coverage**（原 VII）— 延期（阶段 3）
- [ ] **IX. Logic doc completeness**（原 VIII）— blind-spots.md 已实现；一致性验证延期（阶段 3）
- [ ] **X. Requirement consistency**（原 IX）— consistency-diff.md 代码已实现，未接入主流程（延期）

> **复杂度说明**：原则 VIII/X 依赖目标平台代码生成，阶段 3 延期故暂不满足，已在 FR-014 中记录。原则 VI 质量门禁由 T052 补充实现。

## Project Structure

### Documentation (this feature)

```text
specs/001-code-index-skill/
├── plan.md              ← 本文件
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── skill-frontmatter.md
│   ├── quality-json.md
│   └── proposal-file.md
└── tasks.md
```

### Source Code (repository root)

```text
# pipeline.py / run_pipeline.py 已退役（2026-06-06）
.env                    ← 凭证配置（gitignored）
requirements.txt
.claude/skills/
└── run-pipeline/
    └── skill.md        ← 唯一执行入口（阶段 0-2，Codegraph CLI-first）
skills/
└── shared/             ← 保留供参考
    ├── llm_router.py   MiniMax API 封装
    └── translate/
        └── self_eval.py  质量评分逻辑
# skills/ingest/ skills/translate/main.py skills/generate/ skills/document/ 已退役
.codebook/
├── skill-evolution.log
├── proposals/
└── snapshots/
tests/
├── fixtures/java-vue-sample/
├── unit/
└── integration/
```

**Structure Decision**: `/run-pipeline` agent skill 作为唯一执行入口，使用 Codegraph CLI JSON 命令采集证据；`pipeline.py` 和静态 skills/ 目录已退役。

## Complexity Tracking

| 项目 | 说明 | 理由 |
|------|------|------|
| 原则 VIII/X 暂不满足 | 依赖目标平台代码，阶段 3 延期 | 延期决策已记录在 spec FR-014 |
| 原则 VI 质量门禁（T052）| 阶段 0 文档质量未达标时阻断阶段 1 | 章程 v1.1.0 新增原则，tasks.md T052 补充实现 |
| 双模型分工 | Opus（写作）+ MiniMax（评估）| 写作需要高质量语义输出，评估需要快速低成本重复调用 |
| Refine 上限统一为 3 次 | FR-007、章程原则五、T050 均对齐为 3 次 | 修复 plan.md T050 原写"2 轮"的不一致 |

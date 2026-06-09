# 异构代码逆向工程流水线

将任意技术栈的源码转换为技术无关的需求文档（SRS），为跨平台代码迁移奠定基础。

## 项目目的

```
异构源码（Java / Python / Go / Node / C# / Vue / React）
  ↓ 采集（codegraph + SQLite）
  ↓ 转译（LLM 语义分析）
技术无关 SRS + UML 图
  ↓ 生成（未来阶段）
目标平台代码（IIDP 等）
```

SRS 是跨技术栈迁移的**中间语言**，禁止出现任何编程语言、框架、类名等技术词汇，确保下游代码生成无需再查看原始代码。

## 目标读者

- 需要将旧系统迁移至新平台的工程师
- 需要从现有代码库提取业务文档的团队

## 前提条件

### 1. Claude Code（Kiro CLI）

本项目通过 Claude Code（即 `kiro` 命令行）驱动，所有流水线均以对话方式触发。

配置 `~/.claude/settings.json`：

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "<your-api-key>",
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com"
  }
}
```

### 2. Codegraph CLI

Codegraph 将代码库索引为 SQLite 知识图，`/run-pipeline` 通过 CLI JSON 命令访问索引，不依赖 MCP 服务。

**安装 CLI：**
```bash
npm install -g codegraph
```

**对目标项目初始化索引（每个待分析的项目执行一次）：**
```bash
cd /path/to/target-repo
codegraph init -i
codegraph status -j
```

### 3. Python 依赖

```bash
pip install anthropic jinja2
```

### 4. Skill 安装

项目内置 skill（`/run-pipeline` 等）位于 `.claude/skills/`，Claude Code 启动时自动加载，无需额外安装。

## 使用方式

### 阶段 0 — 文档预生成（可选但推荐）

在逆向工程前，先用 Spec Kit 为目标系统生成架构文档：

```bash
# 在 Claude Code 中执行
/speckit-specify <目标系统描述>
```

产物：`specs/<feature>/`（架构、数据模型、接口契约）

### 阶段 1 — 采集

```bash
python skills/ingest/main.py --source /path/to/target-repo
```

产物：`.codegraph/codegraph.db`、`<output>/.codebook/evidence/`、`<output>/quality.json`

### 阶段 2 — 转译

```bash
python skills/translate/main.py --source /path/to/target-repo
```

产物：

| 文件 | 内容 |
|------|------|
| `srs.md` | 技术无关需求文档（FR/NFR 编号体系） |
| `hla.md` | 高层架构（技术参考层） |
| `uml/business/` | 业务状态图、业务类图 |
| `uml/technical/` | 技术组件图、调用链 |
| `flowcharts/` | 流程图、序列图 |
| `database.md` | ER 图 |
| `blind-spots.md` | 未能解析的盲区报告 |

### 阶段 3 — 代码生成

```bash
python skills/generate/main.py --target-platform <platform> --srs srs.md
```

强制跳过覆盖率阻断：

```bash
python skills/generate/main.py --target-platform <platform> --srs srs.md --force
```

产物：目标平台代码、`coverage-matrix.md`、`quality.json`

## 验证输出

检查 `quality.json` 中的关键指标：

```json
{
  "tech_agnostic_score": 1.0,
  "completeness_score": 0.85,
  "uml_coverage_score": 0.92,
  "parsed_files": 120,
  "total_files": 125
}
```

- `tech_agnostic_score` 应为 **1.0**（SRS 不含技术词汇）
- `completeness_score` 建议 **≥ 0.80**
- `uml_coverage_score` 建议 **≥ 0.85**

查看盲区报告：

```bash
cat blind-spots.md
```

## 输出文档阅读顺序

每次流水线运行后，`output/<project>/` 下会生成多份文档。建议按以下顺序阅读：

| 顺序 | 文件 | 目的 |
|------|------|------|
| 1 | `architecture.md` | 系统整体结构，建立全局认知 |
| 2 | `business-flows.md` | 核心业务流程 |
| 3 | `data-model.md` | 核心实体与关系 |
| 4 | `state-machines.md` | 状态机与生命周期 |
| 5 | `flowcharts/flowchart.md` | 主流程图 |
| 6 | `flowcharts/sequence-*.md` | 各操作时序图（install / upapp / uninstall / model-change） |
| 7 | `uml/business/class-diagram.md` | 业务类图 |
| 8 | `uml/business/class-handler-chain.md` | Handler 责任链 |
| 9 | `uml/technical/` | 技术组件图、调用链、热点图 |
| 10 | `database.md` | 数据库结构 |
| 11 | `srs.md` | 需求规格，验证理解是否正确 |
| 12 | `DOCUMENTATION.md` | 综合文档，按章节查阅 |
| 13 | `quality.json` | 查看 `known_issues`，了解系统已知坑点 |

> 时间有限时，只读前 4 个文档即可建立完整的系统心智模型。

## 进化提案审批

Skill 运行后可能生成自我优化提案，存放于本次输出目录的 `<output>/.codebook/proposals/`：

```bash
# 查看待审提案
ls output/<project>/.codebook/proposals/

# 批准：将 status: pending 改为 status: approved
# 下次 Skill 运行时自动应用
```

## 项目结构

```
specs/                  # 功能规范（spec.md / plan.md / tasks.md）
skills/                 # 流水线实现脚本
  ingest/               # 阶段 1：采集
  translate/            # 阶段 2：转译
  generate/             # 阶段 3：生成
output/                 # 流水线输出目录
  <project>/
    .codebook/          # 配置、证据、检查点、提案、进化日志
    quality.json        # 当前项目质量指标
```

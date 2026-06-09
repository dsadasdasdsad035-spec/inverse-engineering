# Research: 异构代码逆向工程 Skill 套件

**Date**: 2026-06-05 | **Feature**: 001-code-index-skill

---

## 1. codegraph MCP 工具能力边界

**Decision**: 以 codegraph 四工具为主提取机制，不支持的技术栈降级静态扫描。

**Rationale**: codegraph（https://github.com/colbymchenry/codegraph）基于 Tree-sitter 解析，覆盖 JS/TS/Python/Java/Go/Ruby/C/C++；C#/.NET 支持有限，需静态扫描兜底。Vue/React 作为 JS/TS 超集可通过 JS 解析器部分覆盖。

**Alternatives considered**: 直接读文件 + LLM 解析——不可重复，缓存效率低；LSP 协议——需各语言服务器，运维成本高。

---

## 2. 技术术语过滤策略

**Decision**: 维护可扩展词表（JSON），规则扫描 + 正则匹配，LLM 做二次语义检查。

**Rationale**: 词表规则速度快、可单元测试；LLM 兜底处理"Spring"在"春天"语境中不触发等歧义场景。词表分层：编程语言名、框架名、注解名、类名模式（驼峰+大写开头）。

**Alternatives considered**: 纯 LLM 过滤——不可重复，每次运行结果不稳定；纯词表——漏检语义性技术术语。

---

## 3. self-eval 评分算法

**Decision**: 三维评分，规则优先 + LLM 兜底。

| 维度 | 规则部分 | LLM 兜底 |
|------|----------|----------|
| 技术无关性 | 词表命中数 / FR 总数 | 抽样 FR 语义审查 |
| 完整性 | FR 数量 / codegraph 路由节点数 | 业务逻辑完整性判断 |
| UML 覆盖率 | 已生成图数 / 应生成图数 | 图内容语义合理性 |

阈值：技术无关性 = 1.0，完整性 ≥ 0.8，UML 覆盖率 ≥ 0.9。

**Alternatives considered**: 纯 LLM——不可重复；纯规则——无法判断语义合理性。

---

## 4. 覆盖矩阵粒度与生成策略

**Decision**: 函数/方法级，以 codegraph 符号节点 ID 为主键。

**Rationale**: codegraph `codegraph_node` 工具返回符号节点含唯一 ID，直接作为矩阵行键，目标代码生成后按函数签名回填覆盖状态（COVERED / MISSING / PARTIAL）。

**Alternatives considered**: 类级——粒度太粗，同类中部分方法未覆盖无法发现；语句级——维护成本过高。

---

## 5. 符号快照格式

**Decision**: JSON 文件 `.codebook/snapshots/<timestamp>.json`，存储符号 ID、名称、文件路径、类型的集合；diff 时比较两个集合的对称差。

**Rationale**: JSON 结构化、可版本控制、diff 算法简单（集合运算）；时间戳命名支持多版本留存。

**Alternatives considered**: SQLite diff——引入 schema 管理复杂度；git blame——依赖 git 历史，不适用首次运行。

---

## 6. Jinja2 文档模板渲染

**Decision**: 使用 Jinja2 渲染 srs.md、hla.md、coverage-matrix.md 等文档产物。

**Rationale**: Python 生态标准选择，支持条件块（无证据时跳过 UML section）、循环（FR 列表、矩阵行），模板与逻辑分离便于进化提案修改模板而无需改代码。

**Alternatives considered**: f-string 拼接——不可维护；Mako——社区较小。

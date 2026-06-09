# 会话诉求整理：code-index Skill 优化

**日期**：2026-06-05  
**主题**：异构系统代码 → 技术无关需求文档 → 目标平台代码生成

---

## 一、核心意图

建立一条完整的四阶段流水线：

```
异构系统源码（Java / Python / Go / Node / C# / .NET / Vue / React）
    ↓  code-index skill（本次优化目标）
技术无关需求文档（SRS）← 跨技术栈迁移的中间语言
    ↓  未来 skill（create-project + backend 或通用代码生成）
目标平台代码（IIDP 或任意技术平台）
```

需求文档是**中间语言**，必须足够完整，使下游代码生成 skill 无需再查看原始代码。

---

## 二、诉求明细

### 2.1 codegraph + SQLite 原理理解

- 使用 `@colbymchenry/codegraph`，后端为轻量 SQLite（`.codegraph/codegraph.db`）
- SQLite 存储四类信息：符号节点（symbols）、调用边（edges）、文件记录（files）、路由节点（route_nodes）
- 从 SQLite 到需求文档分三层：
  1. **结构提取**：codegraph MCP 工具（`codegraph_files` / `codegraph_search` / `codegraph_callers` / `codegraph_node`）
  2. **语义推断**：LLM 分析 `source_text`，将技术事实转译为业务语义
  3. **文档生成**：Prompt 模板驱动输出 SRS / UML / 流程图
- 向量库（Qdrant）定位为 Codebook 的下游消费，不进主流程，仅作可选 Phase E

### 2.2 需求文档技术无关原则

SRS 层禁止出现：编程语言名、框架名、注解/装饰器名、类名/方法名、数据库技术术语。

异构转译规则（任意技术栈 → 业务语义）：

| 代码事实 | 业务语义输出 |
|---------|------------|
| 参数有必填校验 | 该字段为必填项 |
| 有权限校验注解/中间件 | 需要"[业务权限名]"权限 |
| 有事务注解/装饰器 | 操作具有原子性保证（NFR-可靠性）|
| 有缓存注解/配置 | 查询结果有 N 分钟有效缓存（NFR-性能）|
| 有软删除字段 | 删除操作为逻辑删除，数据可恢复 |
| 有乐观锁/版本字段 | 并发修改时系统自动检测冲突 |
| 有状态枚举 | 触发状态图生成 |

### 2.3 分层输出结构

```
Layer 1（技术无关）：srs.md
  - FR 编号体系（FR-001+）、NFR 5 类表格
  - UML 业务视角：状态图（业务状态名）、业务类图（业务实体）

Layer 2（技术参考）：hla.md + uml/technical/
  - 技术调用链、组件依赖、通信协议
```

### 2.4 UML 图完整覆盖

| 优先级 | 图类型 | Mermaid 语法 | 位置 |
|--------|--------|-------------|------|
| 已有 | 流程图 | `flowchart TD` | `flowcharts/` |
| 已有 | 序列图 | `sequenceDiagram` | `flowcharts/` |
| 已有 | ER 图 | `erDiagram` | `database.md` |
| P1 新增 | 业务状态图 | `stateDiagram-v2` | `uml/business/` |
| P1 新增 | 业务类图 | `classDiagram` | `uml/business/` |
| P1 新增 | 技术组件图 | `graph LR` | `uml/technical/` |

# Research: 流水线查询策略优化

## 决策 1：分模块文档生成的实现方式

**决策**: 将步骤 2（采集）和步骤 3（生成）合并为 6 个局部闭环单元，每个单元"查询 → 立即生成对应文档"。

**理由**:
- 每次 LLM 调用的上下文窗口只包含单一领域的源码，减少跨领域干扰
- 单个模块生成失败不阻断其他模块，故障隔离更好
- 与现有 `codegraph_explore` 的分领域查询结构天然对齐，改动最小

**备选方案**: 保留全量采集 + 分领域过滤后再生成 → 拒绝，因为 LLM 上下文仍然很大，过滤精度有限

---

## 决策 2：循环查询的触发条件和批次控制

**决策**: 先用 `codegraph_files` 获取领域文件数，与 `--max-files-per-batch` 比较，超限则循环查询（offset 递增）直至覆盖全部或达到 `--max-batches`。

**参数默认值**:
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-files-per-batch` | 8 | 与现有 maxFiles=8 保持一致，不破坏已有行为 |
| `--max-batches` | 5 | 单领域最多 5 批，防止超大项目无限循环 |

**理由**: 保留现有默认值（8）确保向后兼容；5 批上限 × 8 文件 = 最多覆盖 40 个文件/领域，对绝大多数项目足够；超限时记录警告而非报错，不阻断流程。

**备选方案**: 自动根据项目规模动态计算 → 拒绝，增加复杂度，且 skill.md 是 Markdown 伪代码，运行时计算逻辑难以精确描述

---

## 决策 3：覆盖率记录格式

**决策**: 在 `quality.json` 新增 `domain_coverage` 字段，结构如下：

```json
"domain_coverage": {
  "architecture":    { "queried_files": 6, "total_files": 8,  "coverage": 0.75 },
  "business_flows":  { "queried_files": 8, "total_files": 8,  "coverage": 1.0  },
  "data_model":      { "queried_files": 5, "total_files": 5,  "coverage": 1.0  },
  "api_docs":        { "queried_files": 0, "total_files": 0,  "coverage": null, "skipped": "无源码证据" },
  "state_machines":  { "queried_files": 3, "total_files": 3,  "coverage": 1.0  },
  "error_handling":  { "queried_files": 5, "total_files": 6,  "coverage": 0.83 }
}
```

**理由**: 与现有 `quality.json` 结构保持一致（JSON 扁平结构），`skipped` 字段标识无源码领域，`null` coverage 表示不参与计算。

---

## 决策 4：doc_completeness_score 分母调整

**决策**: 分母从固定值 6 改为"非 skipped 的领域数"，分子为"有实质内容（字符数 > 200）的已生成文档数"。

**理由**: 与章程原则六对齐——纯前端项目没有后端接口层，强行要求 api-docs.md 会导致永远无法通过质量门禁。

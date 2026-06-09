# Contract: Proposal File 格式

进化提案文件存于 `.codebook/proposals/<skill-name>-YYYY-MM-DD.md`，格式如下：

```markdown
---
status: pending
skill_name: translate
created_at: 2026-06-05
trigger_type: tech_term_leak
trigger_count: 3
---

## 问题描述

连续 3 次运行均检测到技术术语"Repository"未被词表过滤拦截。

## 建议修改

在词表 `term_filter.json` 的 `framework_patterns` 中新增正则：`\bRepository\b`。

## 影响范围

仅影响 translate Skill 的词表文件，不影响其他 Skill。
```

**状态流转规则**：
- 初始值必须为 `pending`。
- 人工将 `status` 改为 `approved` 后，Skill 下次运行时自动应用建议修改。
- 人工将 `status` 改为 `rejected` 后，Skill 下次运行时将文件移至 `.codebook/proposals/archived/`。
- Skill 不得自行将 `pending` 变为 `approved`。

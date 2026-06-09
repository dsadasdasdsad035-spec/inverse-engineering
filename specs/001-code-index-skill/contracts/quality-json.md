# Contract: quality.json 格式

每个 Skill 运行结束时必须在工作目录写入 `quality.json`，格式如下：

```json
{
  "source": "/path/to/source-repo",
  "output": "/path/to/output-dir",
  "generated_at": "2026-06-05T10:30:00Z",
  "evolution_applied": ["proposal-file-1.md", "proposal-file-2.md"],
  "index": {
    "files_indexed": 120,
    "total_nodes": 3420,
    "total_edges": 8900
  },
  "quality": {
    "tech_agnostic_score": 1.0,
    "completeness_score": 0.85,
    "uml_coverage_score": 0.92,
    "consistency_score": 1.0,
    "refine_count": 1,
    "max_refine_reached": false,
    "force_run": false,
    "skipped_uml_types": []
  },
  "test_coverage": {
    "classes_with_tests": [],
    "classes_with_no_tests": [],
    "note": ""
  },
  "known_issues": [],
  "artifacts": {
    "core": [
      "architecture.md", "business-flows.md", "data-model.md",
      "state-machines.md", "database.md", "srs.md",
      "uml/business/class-diagram.md", "uml/business/state-diagram.md",
      "uml/technical/component-diagram.md",
      "flowcharts/flowchart.md", "flowcharts/sequence-diagram.md"
    ],
    "extended": []
  }
}
```

**规则**：
- `evolution_applied`：本次运行前已应用的 proposal 文件名列表，无则为 `[]`。
- `index.*`：来自 `codegraph_status` 的原始数据。
- `quality.tech_agnostic_score` 必须为 1.0 才视为通过；低于此值阻断下一阶段。
- `quality.force_run: true` 时下游 Skill 在产物顶部追加警告注释。
- `quality.skipped_uml_types`：无跳过时为空数组 `[]`。
- `artifacts.core`：spec 定义的 6 类文档 + 6 类 UML 图（必须生成）。
- `artifacts.extended`：超出 core 范围的额外产物（hotspot、handler-chain 等）。

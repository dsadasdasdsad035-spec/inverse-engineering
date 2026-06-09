# Contract: Skill Frontmatter

每个 Skill 文件必须包含 `skill.yml`，格式如下：

```yaml
name: ingest          # kebab-case，唯一
stage: ingest         # spec | ingest | translate | generate
version: 1.0.0        # semver
inputs:
  - source_dir        # 上游产物或输入路径（相对或绝对）
outputs:
  - .codegraph/codegraph.db
  - .codebook/snapshots/{timestamp}.json
  - quality.json
entry: main.py        # 入口脚本
```

**规则**：
- `stage` 必填，必须是四个合法值之一：
  - `spec`：阶段 0，文档生成
  - `ingest`：阶段 1，源码采集
  - `translate`：阶段 2，技术无关转译
  - `generate`：阶段 3，代码生成
- `inputs` 中列出的路径在执行前必须存在，否则 Skill 中止并报错。
- `outputs` 中列出的路径必须在运行结束时存在，否则视为运行失败。

---
name: pipeline-source-type
description: Pipeline 只读取源代码，不读取 JAR 包
metadata:
  type: feedback
---

Pipeline 的 `ingest` 阶段只扫描源代码文件（`.java .py .go .js .ts .jsx .tsx .vue .cs`），**不会读取 JAR 包**。

**Why:** sie-snest 项目只有 JAR 文件导致 `total_files=0`，pipeline 无法生成任何文档。用户已确认源代码目录下不应包含 JAR 文件。

**How to apply:** 运行 `/run-pipeline` 时，`--source` 必须指向包含**源代码**的目录，不能是只包含 JAR/二进制产物的目录。

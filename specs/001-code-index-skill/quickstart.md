# Quickstart: 异构代码逆向工程 Skill 套件

**Date**: 2026-06-05

---

## 前提条件

1. Python 3.11+
2. Codegraph CLI 0.9.9+ 已安装，目标项目已执行 `codegraph init -i`
3. 安装依赖：
   ```bash
   pip install anthropic jinja2
   ```
4. 设置环境变量：
   ```bash
   export ANTHROPIC_API_KEY=<your-key>
   ```

---

## 基本用法

### 阶段 0 — 文档生成

> **重要**：constitution v1.1.0 原则六要求，在对任意代码库执行逆向工程之前，必须先用 spec kit 生成该系统的完整技术文档。

```bash
# 使用 spec kit 生成目标系统的完整技术文档
# 具体命令取决于 spec kit 套件配置
speckit-specify <目标代码库描述>
```

产物：`specs/<feature>/` 下的文档（架构、数据模型、接口契约）

### 阶段 1 — 采集

```bash
python skills/ingest/main.py --source /path/to/target-repo
```

产物：`.codegraph/codegraph.db`，`.codebook/snapshots/<timestamp>.json`，`quality.json`

### 阶段 2 — 转译

```bash
python skills/translate/main.py --source /path/to/target-repo
```

产物：`srs.md`，`hla.md`，`uml/business/`，`uml/technical/`，`flowcharts/`，`database.md`，`blind-spots.md`，`quality.json`

### 阶段 3 — 生成

```bash
python skills/generate/main.py --target-platform <platform> --srs srs.md
```

产物：目标平台代码，`coverage-matrix.md`，`quality.json`

强制跳过覆盖率阻断：

```bash
python skills/generate/main.py --target-platform <platform> --srs srs.md --force
```

---

## 验证输出

运行后检查 `quality.json` 中的关键指标：

```json
{
  "tech_agnostic_score": 1.0,
  "completeness_score": 0.85,
  "uml_coverage_score": 0.92,
  "parsed_files": 120,
  "total_files": 125,
  "degraded_files": 5
}
```

查看盲区报告：

```bash
cat blind-spots.md
```

查看进化日志：

```bash
tail -f .codebook/skill-evolution.log
```

---

## 审批进化提案

```bash
# 查看待审提案
ls .codebook/proposals/

# 编辑 status 字段批准或拒绝
# status: pending → status: approved
# 下次 Skill 运行时自动应用
```

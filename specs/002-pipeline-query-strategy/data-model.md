# Data Model: 流水线查询策略优化

## 核心实体

### DomainQuery（领域查询单元）

| 字段 | 类型 | 说明 |
|------|------|------|
| domain | enum | 领域标识：architecture / business_flows / data_model / api_docs / state_machines / error_handling |
| query_keywords | string | 传给 codegraph_explore 的 query 参数 |
| output_file | string | 对应生成的文档文件名 |
| max_files_per_batch | int | 单批查询文件数上限（默认 8） |
| max_batches | int | 最大循环批次数（默认 5） |

### DomainResult（领域查询结果）

| 字段 | 类型 | 说明 |
|------|------|------|
| domain | enum | 同上 |
| source_chunks | list[string] | 各批次 codegraph_explore 返回内容的合并列表 |
| queried_files | int | 实际查询到的文件数 |
| total_files | int | codegraph_files 估算的该领域总文件数 |
| coverage | float \| null | queried_files / total_files；领域不存在时为 null |
| skipped | string \| null | 若为"无源码证据"则跳过文档生成 |

### DocumentOutput（文档产物）

| 字段 | 类型 | 说明 |
|------|------|------|
| domain | enum | 同上 |
| file_path | string | 输出路径（如 `<output>/business-flows.md`） |
| char_count | int | 生成内容字符数，用于判断是否"有实质内容"（阈值 200） |
| generated | bool | 是否成功生成 |
| error | string \| null | 生成失败原因 |

### QualityReport 扩展（quality.json 新增字段）

```json
{
  "domain_coverage": {
    "<domain>": {
      "queried_files": int,
      "total_files": int,
      "coverage": float | null,
      "skipped": string | null
    }
  },
  "doc_completeness_score": float,   // 有内容文档数 / 非skipped领域数
  "doc_completeness_denominator": int // 非skipped领域数（透明化分母）
}
```

## 领域到文档的映射表

| domain | query_keywords | output_file |
|--------|---------------|-------------|
| architecture | 系统架构 模块 入口 主类 启动 | architecture.md |
| business_flows | service facade controller handler 核心业务流程 | business-flows.md |
| data_model | model entity data 数据模型 实体 | data-model.md |
| api_docs | route api endpoint 接口 | api-docs.md |
| state_machines | enum state status 状态枚举 | state-machines.md |
| error_handling | exception error 异常处理 | error-handling.md |

## 状态流转

```
DomainQuery → [codegraph_files 估算 total_files]
           → [循环 codegraph_explore 直至覆盖或达批次上限]
           → DomainResult
           → [total_files == 0 → skipped="无源码证据"]
           → [char_count > 200 → generated=true]
           → DocumentOutput
           → QualityReport.domain_coverage 条目
```

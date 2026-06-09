# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`

**Created**: [DATE]

**Status**: Draft

**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.

  IMPORTANT — Constitution Principle 2 (Technology-Agnostic SRS Layer):
  Functional Requirements MUST use business semantics only.

  **禁止条款 — Prohibited Terms**:
  需求规范中严禁出现以下术语（出现即违规）：
  - 编程语言名：Python, Java, JavaScript, TypeScript, C#, Go, Rust, Ruby, PHP, Swift, Kotlin 等
  - 框架名：React, Vue, Angular, Django, FastAPI, Spring, Express, Flask, Rails 等
  - 数据库名：PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch, SQLite, Oracle 等
  - 协议名：REST, GraphQL, gRPC, WebSocket, HTTP, TCP, UDP, MQTT 等
  - 中间件名：Nginx, Apache, Kafka, RabbitMQ, Celery 等
  - API 名：REST API, GraphQL API, WebSocket 等
  - 任何其他实现技术名称

  **技术术语处理示例 — Technical Term Mapping**:
  当功能描述包含技术术语时，必须按以下标准映射转译为业务语义：
  | 代码事实 | 业务语义输出 |
  |---------|------------|
  | 参数有必填校验 | 该字段为必填项 |
  | 有权限校验注解/中间件 | 需要"[业务权限名]"权限 |
  | 有事务注解/装饰器 | 操作具有原子性保证（NFR-可靠性）|
  | 有缓存注解/配置 | 查询结果有 N 分钟有效缓存（NFR-性能）|
  | 有软删除字段 | 删除操作为逻辑删除，数据可恢复 |
  | 有乐观锁/版本字段 | 并发修改时系统自动检测冲突 |
  | 有状态枚举 | 触发业务状态图生成 |

  [NEEDS CLARIFICATION] 使用规则（最多 3 个标记，仅限业务范围）:
  [NEEDS CLARIFICATION] 仅用于业务范围决策，例如：
  - 用户类型和权限边界
  - 数据保留策略
  - 范围排除
  - 业务规则选择

  禁止用于：编程语言选择、框架选择、数据库类型选择、协议选择、API 选择或任何其他技术实现决策。
  如需超过 3 个标记，请合并或转换为默认假设。
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate required information fields"]
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "record all security-related events"]

*Example of marking unclear requirements (business-scope only):*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: user identity verification method not specified — e.g., credential-based, biometric, token-based?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: data retention period not specified — e.g., 30 days, 1 year, indefinitely?]

**Technical Term Handling**: When user input contains heavy technical terminology (e.g., names of programming languages, frameworks, databases, protocols), the AI agent MUST translate them into business semantics before writing FRs. For example: "The service uses PostgreSQL and Redis" → "The service stores persistent data with retrieval performance guarantees." *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.

  IMPORTANT — Constitution Principle 2 (Technology-Agnostic SRS Layer):
  Success Criteria 必须使用业务/结果指标，不得使用技术实现指标。

  **正确示例**：
  - "用户可在 3 秒内完成主要操作"
  - "系统支持 1000 并发用户无性能下降"
  - "90% 用户首次尝试即成功完成核心任务"
  - "与 [X] 相关的问题报告减少 50%"

  **禁止示例**（技术实现指标，禁止出现）：
  - "API p99 响应时间 < 200ms"（禁止提及 API）
  - "数据库吞吐量 10000 TPS"（禁止提及数据库）
  - "缓存命中率 > 80%"（禁止提及缓存技术）
  - "HTTP 请求成功率达 99.9%"（禁止提及 HTTP 协议）
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System supports 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.

  IMPORTANT — Constitution Principle 3 (Technology-Agnostic SRS Layer):
  Use business-scope assumptions only. Do not reference implementation technologies.
-->

- [Assumption about target users, e.g., "Users have stable network connectivity"]
- [Assumption about scope boundaries, e.g., "Mobile support is out of scope for v1"]
- [Assumption about data/environment, e.g., "Existing identity provider will be reused"]
- [Dependency on existing system/service, e.g., "Requires access to the existing user profile service"]

**AI Agent Compliance**: AI agents generating specs from this template are expected to follow all embedded constraints (technology prohibition, [NEEDS CLARIFICATION] rules, metric style). Violations should be caught by the `/speckit-analyze` command, which validates spec output against quality.json thresholds.

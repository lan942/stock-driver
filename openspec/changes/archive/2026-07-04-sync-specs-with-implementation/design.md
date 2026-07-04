## Context

代码迭代过程中，trading-day-utils spec 文档描述的"调休工作日是交易日"与实际实现（周末永远不是交易日）产生了偏移。同时 daily-data-summary spec 的 Purpose 仍为 TBD，需要补充完整描述。

## Goals / Non-Goals

**Goals:**
- 同步 trading-day-utils spec 与实际实现
- 补充 daily-data-summary spec 的 Purpose 描述
- 验证后端代码无引用已移除的 WORKING_WEEKENDS_2026 和 is_working_weekend

**Non-Goals:**
- 不修改业务逻辑，仅同步文档
- 不新增功能

## Decisions

### Decision: 周末永远不是交易日

**选择**: 周末（周六、周日）永远不是交易日，无论是否调休补班

**理由**:
- A股实际交易规则：周末不开盘
- 简化逻辑，避免维护复杂的调休工作日列表
- 符合用户预期

## Risks / Trade-offs

**[风险]**: spec 与实现不一致可能导致后续开发误解

**缓解措施**: 定期检查 spec 与实现的一致性，在代码提交时同步更新 spec
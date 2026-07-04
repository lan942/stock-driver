## Why

代码迭代过程中，spec 文档与实际实现产生了偏移（如 trading-day-utils 仍描述调休工作日是交易日，但实际代码已改为周末永远不是交易日），同时部分 spec 文件缺少完整的 Purpose 描述。需要统一同步 spec 与实现，清理无用代码。

## What Changes

- 更新 trading-day-utils spec：移除调休工作日相关描述，同步与实际实现一致
- 更新 daily-data-summary spec：补充完整的 Purpose 描述
- 清理 trading_day.py 中已移除的 WORKING_WEEKENDS_2026 和 is_working_weekend 函数引用
- 更新 DataSummary.vue 表格布局和列宽设置

## Capabilities

### Modified Capabilities
- `trading-day-utils`: 移除调休工作日逻辑，周末永远不是交易日
- `daily-data-summary`: 补充完整的 Purpose 描述

## Impact

- `openspec/specs/trading-day-utils/spec.md`: 更新交易日判断规则
- `openspec/specs/daily-data-summary/spec.md`: 补充 Purpose
- `backend/utils/trading_day.py`: 已清理无用代码
- `frontend/src/views/DataSummary.vue`: 表格布局调整
# trading-day-utils Specification (Delta)

## Purpose
同步 trading-day-utils spec 与实际实现。

## MODIFIED Requirements

### Requirement: 判断是否为交易日

The system SHALL provide `is_trading_day(date)` function that returns False for weekends regardless of workday adjustments.

#### Scenario: 周末不是交易日（无论是否调休）
- **WHEN** 输入日期为周六或周日（即使是调休补班日）
- **THEN** 函数 SHALL 返回False
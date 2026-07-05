## Context

当前 Transaction 模型仅有 `created_at` 字段（自动记录创建时间），无法记录交易实际发生的日期。用户需要能够在添加交易时指定日期，默认当天，以便回溯录入历史交易。

## Goals / Non-Goals

**Goals:**
- Transaction 模型新增 `trade_date` 字段（DATE 类型），记录交易发生日期
- 添加交易 API 支持可选 `trade_date` 参数，未传时默认当天
- 交易记录列表 API 返回 `trade_date` 字段
- 前端添加交易对话框增加日期选择器，默认今天
- 前端交易记录表格增加"交易日期"列
- 数据库迁移：为已有 `transactions` 表添加 `trade_date` 列

**Non-Goals:**
- 不修改 `created_at` 字段的自动记录行为（保持记录创建时间的语义）
- 不修改持仓模型
- 不修改现金余额相关功能

## Decisions

### 1. 新增 `trade_date` 字段而非复用 `created_at`
- **选择**：新增独立的 `trade_date`（DATE 类型），保留 `created_at`（DATETIME 类型）作为记录创建时间戳
- **理由**：`created_at` 记录的是数据录入时间，`trade_date` 记录的是交易实际发生日期，两者语义不同。如果复用 `created_at` 并允许用户修改，会丢失数据录入时间的审计信息
- **备选方案**：直接让用户修改 `created_at` — 被否决，因为会丢失记录创建时间的原始信息

### 2. 使用 DATE 类型而非 DATETIME
- **选择**：`trade_date` 使用 SQLAlchemy `Date` 类型，仅存储日期（年-月-日）
- **理由**：A 股交易以天为单位，不需要精确到时分秒；前端默认值"今天"也是指日期。更简单的类型减少了用户输入负担和验证复杂度

### 3. 数据库迁移策略：ALTER TABLE ADD COLUMN
- **选择**：使用 `ALTER TABLE transactions ADD COLUMN trade_date DATE` 直接在现有表上添加列
- **理由**：SQLite 支持 `ALTER TABLE ADD COLUMN`，且该列允许 NULL（已有行的 trade_date 设为 NULL，表示未知）
- **备选方案**：使用 `CREATE TABLE ... AS SELECT` 重建表 — 过于复杂，没有必要

### 4. 前端使用 Element Plus DatePicker
- **选择**：使用 `el-date-picker` 组件，`type="date"`，`value-format="YYYY-MM-DD"`
- **理由**：Element Plus 已作为项目依赖，`el-date-picker` 功能完善，支持日期选择、默认值、格式控制，与现有 UI 风格一致

## Risks / Trade-offs

- **已有交易记录**：新增列的已有行 `trade_date` 为 NULL。迁移脚本可运行 UPDATE 将 NULL 回填为 `created_at` 的日期部分
- **SQLite 类型亲和**：SQLite 的 DATE 类型实际存储为文本字符串，不影响功能但需注意查询时的类型转换
- **数据一致性**：用户选择的日期可能与交易录入时间相差很大（如录入几个月前的交易），
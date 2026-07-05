## Why

当前添加交易记录时，交易时间自动设为当前时间，无法记录过去某一天的交易。用户需要能够指定交易发生的日期，便于回溯录入历史交易。

## What Changes

- **Transaction 数据模型**：新增 `trade_date` 字段（DATE 类型），用于记录交易发生的日期
- **添加交易 API**：`POST /api/portfolio/transactions` 新增可选参数 `trade_date`，默认值为当天
- **交易记录列表 API**：`GET /api/portfolio/transactions` 返回结果中包含 `trade_date` 字段
- **前端添加交易对话框**：新增日期选择器，默认显示今天，允许用户选择过去日期
- **前端交易记录表格**：新增"交易日期"列，显示 `trade_date`

## Capabilities

### Modified Capabilities
- `portfolio-api`: 添加交易 API 和查询交易记录 API 增加 `trade_date` 字段支持
- `portfolio-ui`: 添加交易对话框增加日期选择器，交易记录表格增加交易日期列

## Impact

- `backend/models/portfolio.py` — Transaction 模型增加 `trade_date` 字段
- `backend/services/portfolio_service.py` — `add_transaction()` 接受 `trade_date` 参数
- `backend/api/routes.py` — POST /api/portfolio/transactions 接收 `trade_date` 参数
- `frontend/src/views/Portfolio.vue` — 添加交易对话框增加日期选择器，表格增加日期列
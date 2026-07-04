## Why

当前系统缺少持仓管理功能，用户无法记录和追踪自己的股票持仓情况。随着后续买卖策略验证功能的开发，持仓管理是基础支撑模块，可以帮助用户记录真实交易数据，验证策略效果，评估投资收益。

## What Changes

- 新增持仓管理页面，作为前端导航的一个新tab
- 创建持仓模型（Portfolio），记录用户的持仓信息
- 创建交易记录模型（Transaction），记录股票买入卖出操作
- 提供持仓总览、收益统计、持仓明细功能
- 支持现金余额管理和股票持仓的增删改操作
- 实时计算持仓收益和收益率

## Capabilities

### New Capabilities

- `portfolio-management`: 持仓管理功能，包括持仓模型、交易记录、收益计算
- `portfolio-api`: 持仓管理相关的REST API接口
- `portfolio-ui`: 持仓管理前端页面组件

### Modified Capabilities

- 无

## Impact

- **后端**: 新增 models/portfolio.py、services/portfolio_service.py、api/routes.py 中新增持仓相关路由
- **前端**: 新增 views/Portfolio.vue、api/stock.js 中新增持仓API调用、App.vue 和 router/index.js 中新增导航和路由
- **数据库**: 新增 portfolio 和 transactions 两张表
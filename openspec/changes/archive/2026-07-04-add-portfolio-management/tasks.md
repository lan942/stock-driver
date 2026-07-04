## 1. 后端模型层

- [x] 1.1 创建 Portfolio 模型（持仓表），包含 code、quantity、cost_price、created_at、updated_at 字段
- [x] 1.2 创建 Transaction 模型（交易记录表），包含 type、code、quantity、price、amount、created_at 字段
- [x] 1.3 创建 CashBalance 模型（现金余额表），包含 balance、updated_at 字段

## 2. 后端服务层

- [x] 2.1 创建 portfolio_service.py，实现持仓 CRUD 操作
- [x] 2.2 实现获取持仓总览功能（计算总价值、总收益）
- [x] 2.3 实现获取持仓明细功能（结合 StockDaily 最新价格计算收益）
- [x] 2.4 实现交易记录 CRUD 操作
- [x] 2.5 实现现金余额管理功能

## 3. 后端API层

- [x] 3.1 在 routes.py 中添加 `/api/portfolio/overview` GET 接口
- [x] 3.2 添加 `/api/portfolio/holdings` GET/POST 接口
- [x] 3.3 添加 `/api/portfolio/holdings/<id>` PUT/DELETE 接口
- [x] 3.4 添加 `/api/portfolio/transactions` GET/POST 接口
- [x] 3.5 添加 `/api/portfolio/cash` POST 接口

## 4. 数据库迁移

- [x] 4.1 在 migrate_db.py 中添加创建 portfolio、transactions、cash_balance 表的函数
- [x] 4.2 在 manage.py 中添加迁移命令或确保启动时自动创建表

## 5. 前端API封装

- [x] 5.1 在 api/stock.js 中添加 portfolioOverview、getHoldings、addHolding、updateHolding、deleteHolding API
- [x] 5.2 添加 getTransactions、addTransaction API
- [x] 5.3 添加 updateCashBalance API

## 6. 前端页面组件

- [x] 6.1 创建 Portfolio.vue 页面，包含持仓总览卡片区域
- [x] 6.2 实现持仓明细表格，展示股票代码、名称、数量、成本价、现价、市值、收益、收益率
- [x] 6.3 实现添加持仓对话框
- [x] 6.4 实现编辑持仓对话框
- [x] 6.5 实现删除持仓功能（带确认提示）
- [x] 6.6 实现交易记录表格
- [x] 6.7 实现添加交易对话框（支持买入/卖出）
- [x] 6.8 实现现金余额更新对话框

## 7. 前端路由和导航

- [x] 7.1 在 router/index.js 中添加 `/portfolio` 路由
- [x] 7.2 在 App.vue 导航栏中添加 "持仓管理" 链接
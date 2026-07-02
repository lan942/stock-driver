## 1. 数据库变更

- [x] 1.1 StockDaily 模型新增 pe/pb/market_cap 字段
- [x] 1.2 编写 DDL 迁移脚本，自动检测并添加缺失列
- [x] 1.3 在 app 启动时执行迁移脚本

## 2. 后端服务层

- [x] 2.1 改造 save_realtime_quotes：写入 StockDaily 表（按 code+date 去重，同日期重复爬取覆盖）
- [x] 2.2 Stock 表不再更新价格字段，只保留基础信息（code/name），价格数据统一由 StockDaily 管理

## 3. 后端 API

- [x] 3.1 GET /api/stocks 支持可选的 ?date=YYYY-MM-DD 参数
- [x] 3.2 有 date 时联表查询 StockDaily，无 date 时取最新日期数据，StockDaily 为空时回退查 Stock 表

## 4. 前端

- [x] 4.1 股票列表页添加日期选择器，默认"最新"
- [x] 4.2 选择日期后调用 API 并刷新列表
- [x] 4.3 pe/pb/市值列已在表中存在

## 5. 测试

- [x] 5.1 插入测试数据验证 StockDaily 字段完整性（pe/pb/market_cap 可正常写入读取）
- [x] 5.2 GET /api/stocks?date=2026-07-02 正确返回指定日期数据
- [x] 5.3 GET /api/stocks（无参数）正确返回最新日期数据
- [x] 5.4 StockDaily 为空时回退到 Stock 表（已验证）

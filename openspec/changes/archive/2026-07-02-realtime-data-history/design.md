## Context

当前 `save_realtime_quotes` 只更新 Stock 表字段，每次爬取覆盖前次数据。Stock 表中无 `price_date` 字段记录数据日期。StockDaily 表已存在但为空，字段缺少 pe/pb/market_cap。

## Goals / Non-Goals

**Goals:**
- 每次实时行情爬取后，向 StockDaily 表插入当日快照记录
- Stock 表仍保留更新（作为"最新行情"快速查询）
- StockDaily 表新增 pe/pb/market_cap 三个字段
- 前端可按日期切换查看历史快照

**Non-Goals:**
- 不改动 Stock 表的更新逻辑（双写，不替换）
- 不修改爬虫本身的爬取/重试/限流逻辑
- 不做数据清理或过期策略

## Decisions

### 决策 1：复用 StockDaily 表 vs 新建 RealtimeSnapshot 表
**选择：复用 StockDaily 表，新增 3 个字段**

理由：StockDaily 表字段与实时行情高度重合（code/date/open/high/low/close/volume/turnover/turnover_rate/change_percent），只需补 pe/pb/market_cap。新建表会增加维护成本和 JOIN 复杂度。

### 决策 2：双写 vs 只写 StockDaily
**选择：双写（Stock 更新 + StockDaily 插入）**

理由：Stock 表保持"最新行情"的语义，前端默认展示无需改 SQL。StockDaily 提供历史追溯。单次爬取写入 5000+ 行，Stock 表更新是 UPDATE（约 3 秒），StockDaily 插入是 INSERT（约 5 秒），总开销可接受。

### 决策 3：前端日期查询方案
**选择：API 添加 date 参数**

`GET /api/stocks?date=YYYY-MM-DD` 当传 date 时查询 StockDaily 表，不传 date 时保持原逻辑查 Stock 表。不新增独立接口，减少前端改动。

### 决策 4：DDL 迁移方案
**选择：Python 脚本运行时自动检测并添加缺失列**

SQLite 不支持 `ALTER TABLE ADD COLUMN IF NOT EXISTS` 的标准写法，但可以通过 PRAGMA table_info 检测列是否存在后执行 ALTER。在 app 启动时运行。

## Risks / Trade-offs

- [双写事务风险] → Stock 更新和 StockDaily 插入不在同一事务中；Stock 更新失败不影响 StockDaily 插入，CrawlStatus 记录实际成功/失败数
- [StockDaily 数据膨胀] → 每天 5000+ 行，一年约 180 万行（约 150MB），SQLite 可承受；后续可加清理策略
- [同一天重复爬取] → StockDaily 按 (code, date) 去重：INSERT OR REPLACE，同一天重复爬取只保留最新

## Migration Plan

1. 停止后端服务
2. 运行 DDL 迁移脚本（添加 pe/pb/market_cap 列）
3. 部署新代码
4. 启动后端服务
5. 手动触发一次爬取验证 StockDaily 写入

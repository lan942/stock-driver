## Context

当前涨跌排行后端接口 `/stocks/top/gainers` 和 `/stocks/top/losers` 通过 `StockAnalysis.get_top_gainers/losers` 查询 **Stock 表**（实时行情快照），按 `change_percent` 排序返回 Top N。前端 `TopStocks.vue` 在 `onMounted` 时调用一次，无任何日期控件。

问题：
- Stock 表只保存最新一次爬取的快照，无法回溯历史排行
- 页面无日期标识，用户看到排行不知道是哪天的数据
- 数据源已切换到腾讯 `stock_daily` 表，已积累 25+ 天历史数据，但排行功能未利用这部分数据

## Goals / Non-Goals

**Goals:**
- 排行榜支持按任意交易日查询（基于 `stock_daily` 表）
- 不传日期时默认返回最新交易日排行
- 接口和页面都明确标注当前数据日期
- 保持 `limit` 参数向后兼容

**Non-Goals:**
- 不做多日排行对比（如"本周涨幅榜"）
- 不对排行结果做缓存（单日 5000 条排序性能足够）
- 不修改 Stock 表实时排行的逻辑（保留 Stock 表作为实时数据源，但排行改用 StockDaily）

## Decisions

### 决策 1：排行榜数据源从 Stock 表切换到 StockDaily 表

**选择**：`get_top_gainers/losers` 改为查询 `StockDaily` 表，按 `date` 过滤后排序 `change_percent`。

**理由**：
- StockDaily 表有完整历史数据（每天一条），支持任意日期回溯
- Stock 表只有最新快照，无法满足"查看历史某天排行"的需求
- StockDaily 表已通过腾讯爬虫积累了多日数据，字段完整（close, change_percent 等）

**备选方案**：
- 保持查 Stock 表 + 新增日期参数：Stock 表无历史日期维度，无法按日期查询，否决
- 新建独立排行表：过度设计，StockDaily 已有全部所需字段，否决

### 决策 2：默认日期用 `MAX(date)` 而非 `date.today()`

**选择**：不传 `date` 参数时，查询 `SELECT MAX(date) FROM stock_daily` 作为默认日期。

**理由**：
- `today()` 可能是非交易日、或当天数据尚未爬取，会返回空结果误导用户
- `MAX(date)` 保证一定返回有数据的最新一天

**与 StockList 页面一致**：该页面已采用相同策略（`latest_date` 字段），保持系统一致性。

### 决策 3：接口返回结构渐进增强

**选择**：响应体保持现有字段（code, name, price, change_percent），新增 `price_date` 字段。`price` 字段映射 StockDaily 的 `close`（收盘价）。

**理由**：
- 前端旧代码无需修改即可继续工作
- `price_date` 作为新增字段渐进增强，前端用于显示日期标识

### 决策 4：前端日期选择器复用 StockList 模式

**选择**：TopStocks.vue 顶部新增 `el-date-picker`，逻辑复用 StockList 已验证的模式：
- 默认填入最新日期
- 支持 `clearable` 清空回到最新
- 切换日期自动重新加载

**理由**：保持两个列表页交互一致，降低用户学习成本，复用已验证代码模式。

## Risks / Trade-offs

- **[风险] StockDaily 表某天数据缺失** → 该日期查询返回空列表，前端显示"该日期暂无排行数据"提示，不报错
- **[风险] 全表排序性能** → 单日约 5000 条记录，按 `change_percent` 排序 + limit，SQLite 在毫秒级完成；已对 `stock_daily(date)` 建索引考虑（如慢可后续追加）
- **[权衡] 实时性降低** → 改用 StockDaily 后，排行反映的是爬取时的收盘数据，而非"此刻"实时行情。可接受，因为项目定位是历史数据分析而非实时交易
- **[权衡] price 字段语义变化** → 从 Stock.price（实时价）变为 StockDaily.close（收盘价）。前端标签保持"价格"，语义上可接受

## 1. 后端排行接口改造

- [x] 1.1 修改 `StockAnalysis.get_top_gainers(db, limit, query_date)`：增加 `query_date` 参数，从 `StockDaily` 表按日期过滤后按 `change_percent` 降序排序，关联 `Stock` 表取 name
- [x] 1.2 修改 `StockAnalysis.get_top_losers(db, limit, query_date)`：同上，按 `change_percent` 升序排序
- [x] 1.3 修改 `backend/api/routes.py` 的 `/stocks/top/gainers`：读取 `date` 查询参数，未传时用 `MAX(date)` 默认值，校验日期格式（非法返回 400），调用改造后的 `get_top_gainers`，响应每条记录新增 `price_date` 字段
- [x] 1.4 修改 `backend/api/routes.py` 的 `/stocks/top/losers`：同上逻辑

## 2. 前端 API 层适配

- [x] 2.1 修改 `frontend/src/api/stock.js` 的 `getTopGainers(limit)`：增加可选 `date` 参数，传入时拼到 query string
- [x] 2.2 修改 `frontend/src/api/stock.js` 的 `getTopLosers(limit)`：同上

## 3. 前端 TopStocks 页面改造

- [x] 3.1 `TopStocks.vue` 顶部新增 `el-date-picker`（clearable，placeholder="选择日期（留空=最新）"）和日期提示条
- [x] 3.2 新增 `queryDate`、`priceDate`、`latestDate` 响应式状态；`loadTopStocks` 读取响应中的 `price_date` 更新提示条
- [x] 3.3 `onMounted` 首次加载获取 `latest_date` 后回填日期选择器；新增 `onDateChange` 切换日期自动重载
- [x] 3.4 涨/跌 tab 切换时保持当前日期不变（无需特殊处理，确认 `activeTab` 切换不触发重载即可，因两个榜单同时加载）

## 4. 测试验证

- [x] 4.1 后端验证：指定日期返回正确排行（如 `date=2026-07-02` 返回该日数据），不传日期返回最新日，非法格式返回 400
- [x] 4.2 前端验证：页面加载默认显示最新日期，切换日期后榜单更新，清空日期回到最新，提示条日期同步更新
- [x] 4.3 边界验证：查询无数据日期返回空列表，页面显示空状态不报错

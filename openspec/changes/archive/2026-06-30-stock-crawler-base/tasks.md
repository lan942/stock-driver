## 1. 爬虫基础层架构

- [x] 1.1 创建 `backend/services/crawler/base.py` - 定义 `CrawlerBase` 抽象基类
- [x] 1.2 创建 `CrawlerError` 和 `RateLimitError` 异常类
- [x] 1.3 定义 `CrawlerResult` 数据类，统一返回格式

## 2. 限流管理器实现

- [x] 2.1 创建 `backend/services/crawler/rate_limiter.py` - 限流管理器核心逻辑
- [x] 2.2 实现滑动窗口计数器
- [x] 2.3 实现指数退避算法
- [x] 2.4 实现接口切换逻辑

## 3. 数据标准化工具

- [x] 3.1 创建 `backend/services/crawler/normalizer.py` - 标准化器核心
- [x] 3.2 实现 `normalize_price()` - 价格单位统一
- [x] 3.3 实现 `normalize_volume()` - 成交量单位统一
- [x] 3.4 实现 `normalize_turnover_rate()` - 换手率标准化
- [x] 3.5 实现 `normalize_change_percent()` - 涨跌幅标准化
- [x] 3.6 添加单位检测和未知单位处理

## 4. 股票列表爬虫

- [x] 4.1 创建 `backend/services/crawler/stock_list.py` - 股票列表爬虫
- [x] 4.2 实现 `StockListCrawler` 类继承 `CrawlerBase`
- [x] 4.3 实现 `fetch()` 方法调用 akshare 接口
- [x] 4.4 集成数据标准化

## 5. 实时行情爬虫

- [x] 5.1 创建 `backend/services/crawler/stock_realtime.py` - 实时行情爬虫
- [x] 5.2 实现 `StockRealtimeCrawler` 类继承 `CrawlerBase`
- [x] 5.3 实现单只和批量获取方法
- [x] 5.4 集成限流管理和数据标准化
- [x] 5.5 配置主/备接口列表

## 6. 模块导出和集成

- [x] 6.1 更新 `backend/services/crawler/__init__.py` - 导出公共接口
- [x] 6.2 更新现有 `backend/services/crawler.py` - 重构为使用新基础层
- [x] 6.3 验证现有 API 路由兼容新爬虫

## 7. 测试验证

- [x] 7.1 编写单元测试：限流管理器
- [x] 7.2 编写单元测试：数据标准化
- [x] 7.3 手动测试：股票列表爬取
- [x] 7.4 手动测试：实时行情爬取
- [x] 7.5 验证限流重试和接口切换

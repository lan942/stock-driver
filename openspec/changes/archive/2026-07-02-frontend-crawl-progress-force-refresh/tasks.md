## 1. 后端 API 扩展

- [x] 1.1 更新 `update_realtime` 接口支持 `force` 参数，跳过当日成功检查
- [x] 1.2 更新 `update_realtime` 接口支持 `date` 参数，指定价格日期
- [x] 1.3 更新 `update_list` 和 `update_realtime` 返回值包含 success_count、fail_count、elapsed_seconds

## 2. 后端服务层

- [x] 2.1 `save_realtime_quotes` 支持传入 quote_date 参数（已有，无需改动）
- [x] 2.2 新增 `force_update_realtime` 或修改现有函数支持 force 模式（在 routes.py 中实现）

## 3. 前端 API 封装

- [x] 3.1 更新 `stockAPI.updateRealtime` 支持 `force` 和 `date` 参数
- [x] 3.2 统一 API 返回值结构处理（提取 success_count、fail_count 等）

## 4. 前端 Crawler 页面重构

- [x] 4.1 股票列表更新：增加加载状态和结果摘要展示（成功数、失败数、耗时）
- [x] 4.2 实时行情更新：增加加载状态和结果摘要展示（成功数、失败数、耗时、数据日期）
- [x] 4.3 实时行情更新：增加"强制刷新"复选框
- [x] 4.4 实时行情更新：增加日期选择器（默认当天）
- [x] 4.5 结果展示使用 Element Plus 组件（el-progress、结果卡片等）
- [x] 4.6 保留现有操作日志区域

## 5. 测试验证

- [x] 5.1 测试股票列表更新：正常流程、失败场景、结果展示
- [x] 5.2 测试实时行情更新：正常流程、强制刷新、日期指定
- [x] 5.3 测试强制刷新：当日已有记录时仍能重新爬取
- [x] 5.4 测试日期指定：验证 price_date 字段保存正确
## Why

当前启动服务和触发爬虫需要手动执行多个命令，操作繁琐且容易出错。例如：启动后端需要记住 `py -m backend.app`，触发爬虫需要调用 curl/requests，查询进度需要单独命令。需要一个统一的 CLI 脚本封装常用操作，提高开发效率和运维便捷性。

## What Changes

- 创建 `manage.py` CLI 管理脚本，提供以下子命令：
  - `start`：启动后端服务（Flask）
  - `stop`：停止后端服务（查找并杀死端口进程）
  - `crawler list`：手动触发股票列表更新
  - `crawler realtime`：手动触发实时行情爬取
  - `crawler daily`：手动触发日线数据爬取（支持指定日期范围）
  - `crawler status`：查询爬取状态历史
  - `db migrate`：执行数据库迁移
  - `db backup`：备份数据库
  - `health`：检查服务健康状态

## Capabilities

### New Capabilities
- `cli-management`: CLI 管理脚本，封装服务启动、爬虫触发、数据库管理等常用操作

### Modified Capabilities
<!-- 无现有 spec 的需求变更 -->

## Impact

- 新增文件：`manage.py`（项目根目录）
- 依赖：`requests`（已有）、`psutil`（用于进程管理，需新增依赖）
- 不涉及现有代码修改，仅调用已有的 API 和服务函数
- 提供便捷的开发运维入口，不影响系统核心功能

# Capability: CLI Management

## Purpose

Provide command-line interface for managing stock-driver service lifecycle, crawler tasks, and database operations.

## Requirements

### Requirement: 服务启停命令
`manage.py` SHALL 提供 `start` 和 `stop` 子命令管理后端服务生命周期。

#### Scenario: 启动后端服务
- **WHEN** 用户执行 `python manage.py start`
- **THEN** 脚本 SHALL 在后台启动 Flask 应用（端口5000）
- **AND** 输出启动日志和服务地址
- **AND** 支持 `--debug` 参数启用调试模式

#### Scenario: 停止后端服务
- **WHEN** 用户执行 `python manage.py stop`
- **THEN** 脚本 SHALL 查找占用端口5000的进程并终止
- **AND** 输出终止的进程ID和状态信息

#### Scenario: 服务已停止时执行 stop
- **WHEN** 用户执行 `python manage.py stop` 且无进程占用端口5000
- **THEN** 脚本 SHALL 输出提示信息"服务未运行"，不报错

### Requirement: 爬虫管理命令
`manage.py` SHALL 提供 `crawler` 子命令组，支持手动触发各类爬虫任务。

#### Scenario: 触发股票列表更新
- **WHEN** 用户执行 `python manage.py crawler list`
- **THEN** 脚本 SHALL 调用 `/api/crawler/update_list` API
- **AND** 输出成功/失败数量和耗时

#### Scenario: 触发实时行情爬取
- **WHEN** 用户执行 `python manage.py crawler realtime`
- **THEN** 脚本 SHALL 调用 `/api/crawler/update_realtime` API
- **AND** 支持 `--force` 参数强制爬取（忽略幂等性检查）
- **AND** 输出成功/失败数量和耗时

#### Scenario: 触发日线数据爬取
- **WHEN** 用户执行 `python manage.py crawler daily`
- **THEN** 脚本 SHALL 调用 `/api/crawler/fetch_daily_batch` API
- **AND** 支持 `--start-date` 和 `--end-date` 参数指定日期范围（格式 YYYYMMDD）
- **AND** 支持 `--codes` 参数指定股票代码列表（逗号分隔）
- **AND** 启动后显示进度轮询，输出实时进度（当前/总数/成功/失败）

#### Scenario: 查询爬取状态历史
- **WHEN** 用户执行 `python manage.py crawler status`
- **THEN** 脚本 SHALL 调用 `/api/crawl_status` API
- **AND** 支持 `--limit` 参数限制返回数量（默认10）
- **AND** 支持 `--type` 参数过滤爬取类型（list/realtime/daily）
- **AND** 以表格形式输出状态记录

### Requirement: 数据库管理命令
`manage.py` SHALL 提供 `db` 子命令组，支持数据库迁移和备份。

#### Scenario: 执行数据库迁移
- **WHEN** 用户执行 `python manage.py db migrate`
- **THEN** 脚本 SHALL 调用 `backend.utils.migrate_db.migrate()` 函数
- **AND** 输出迁移步骤和结果（成功/失败）

#### Scenario: 备份数据库
- **WHEN** 用户执行 `python manage.py db backup`
- **THEN** 脚本 SHALL 将 `data/stock.db` 备份到 `data/stock.db.backup.<timestamp>`
- **AND** 输出备份文件路径和大小

### Requirement: 健康检查命令
`manage.py` SHALL 提供 `health` 子命令检查服务状态。

#### Scenario: 服务运行正常
- **WHEN** 用户执行 `python manage.py health`
- **AND** 后端服务正在运行（端口5000可访问）
- **THEN** 脚本 SHALL 输出服务状态"正常"，显示版本信息和数据库连接状态

#### Scenario: 服务未运行
- **WHEN** 用户执行 `python manage.py health`
- **AND** 后端服务未运行（端口5000不可访问）
- **THEN** 脚本 SHALL 输出服务状态"未运行"，提示用户启动服务

### Requirement: 友好的命令行输出
`manage.py` SHALL 提供彩色输出和清晰的进度展示。

#### Scenario: 成功操作绿色输出
- **WHEN** 命令执行成功
- **THEN** 关键信息（成功数量、状态正常）SHALL 以绿色显示

#### Scenario: 错误信息红色输出
- **WHEN** 命令执行失败或服务异常
- **THEN** 错误信息（失败数量、服务未运行）SHALL 以红色显示

#### Scenario: 信息性输出蓝色/灰色
- **WHEN** 输出普通信息（进度、提示、说明）
- **THEN** 信息 SHALL 以蓝色或灰色显示，不刺眼

### Requirement: 帮助信息
`manage.py` SHALL 提供完整的帮助信息，支持 `-h`/`--help` 参数。

#### Scenario: 全局帮助
- **WHEN** 用户执行 `python manage.py -h`
- **THEN** 脚本 SHALL 输出所有可用命令和简要说明

#### Scenario: 子命令帮助
- **WHEN** 用户执行 `python manage.py crawler -h` 或 `python manage.py crawler daily -h`
- **THEN** 脚本 SHALL 输出该子命令的详细参数说明

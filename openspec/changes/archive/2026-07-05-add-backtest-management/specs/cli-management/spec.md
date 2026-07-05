## MODIFIED Requirements

### Requirement: 服务启停命令
`manage.py` SHALL 提供 `start` 和 `stop` 子命令管理后端服务生命周期。

#### Scenario: 启动后端服务
- **WHEN** 用户执行 `python manage.py start`
- **THEN** 脚本 SHALL 在前台启动 Flask 应用（端口5000），按 Ctrl+C 停止
- **AND** 支持 `--frontend` 参数同时启动前端开发服务器（端口3000）
- **AND** 输出服务地址信息
- **AND** 支持 `--debug` 参数启用调试模式

#### Scenario: 停止后端服务
- **WHEN** 用户执行 `python manage.py stop`
- **THEN** 脚本 SHALL 查找占用端口5000和3000的进程并终止
- **AND** 输出终止的进程ID和状态信息

#### Scenario: 服务已停止时执行 stop
- **WHEN** 用户执行 `python manage.py stop` 且无进程占用端口5000
- **THEN** 脚本 SHALL 输出提示信息"服务未运行"，不报错

### Requirement: 爬虫管理命令
`manage.py` SHALL 提供 `crawler` 子命令组，支持手动触发各类爬虫任务。

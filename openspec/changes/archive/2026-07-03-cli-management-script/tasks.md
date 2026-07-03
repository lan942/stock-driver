## 1. 创建 manage.py CLI 脚本

- [x] 1.1 创建 `manage.py` 文件，导入必要依赖（argparse、requests、psutil、colorama、subprocess、time）
- [x] 1.2 实现彩色输出工具函数（green/red/blue/gray 输出）
- [x] 1.3 实现 `start` 命令：subprocess 启动 Flask 后端，支持 --debug 参数
- [x] 1.4 实现 `stop` 命令：psutil 查找端口5000进程并终止
- [x] 1.5 实现 `health` 命令：检查端口5000是否可访问，输出服务状态

## 2. 实现 crawler 子命令组

- [x] 2.1 创建 crawler 子命令解析器
- [x] 2.2 实现 `crawler list`：调用 `/api/crawler/update_list`，输出结果
- [x] 2.3 实现 `crawler realtime`：调用 `/api/crawler/update_realtime`，支持 --force 参数
- [x] 2.4 实现 `crawler daily`：调用 `/api/crawler/fetch_daily_batch`，支持 --start-date/--end-date/--codes，轮询进度输出
- [x] 2.5 实现 `crawler status`：调用 `/api/crawl_status`，支持 --limit/--type，表格形式输出

## 3. 实现 db 子命令组

- [x] 3.1 创建 db 子命令解析器
- [x] 3.2 实现 `db migrate`：导入并调用 `backend.utils.migrate_db.migrate()`
- [x] 3.3 实现 `db backup`：备份 data/stock.db 到带时间戳的备份文件，输出文件路径和大小

## 4. 添加依赖

- [x] 4.1 在 `requirements.txt` 中添加 `psutil` 和 `colorama`

## 5. 测试验证

- [x] 5.1 测试 `manage.py -h` 输出帮助信息
- [x] 5.2 测试 `manage.py start` 和 `manage.py stop` 启停服务
- [x] 5.3 测试 `manage.py health` 检查服务状态
- [x] 5.4 测试 `manage.py crawler status` 查询状态
- [x] 5.5 测试 `manage.py db backup` 备份数据库

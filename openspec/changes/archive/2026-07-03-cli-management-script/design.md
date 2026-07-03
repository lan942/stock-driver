## Context

项目目前缺少统一的管理入口，日常开发运维需要手动执行多个分散的命令：
- 启动后端：`py -m backend.app`
- 停止后端：先查端口进程再 kill
- 触发爬虫：用 curl/requests 调用 API
- 数据库迁移：`py -m backend.utils.migrate_db`

这些操作繁琐且容易出错，需要一个统一的 CLI 脚本。

## Goals / Non-Goals

**Goals:**
- 提供统一的 `manage.py` 入口，封装所有常用操作
- 支持服务启停、爬虫触发、数据库管理、健康检查
- 命令行参数清晰，有帮助信息
- 输出友好（颜色、进度、状态指示）
- 支持 Windows 和 Linux 跨平台

**Non-Goals:**
- 不实现前端启动（前端已有 `npm run dev`）
- 不实现复杂的进程管理（如守护进程、日志轮转）
- 不实现分布式部署（当前仅单机）

## Decisions

### 决策 1：使用 argparse 构建 CLI

**选择**：使用 Python 标准库 `argparse` 构建命令行接口。

**理由**：
- 标准库，无需额外依赖
- 支持子命令、参数解析、帮助信息自动生成
- 足够满足当前需求（不复杂的命令结构）

**备选方案**：
- Click 库：更强大但需要额外依赖，当前需求简单，标准库足够
- Typer：现代 CLI 框架，但需要额外依赖

### 决策 2：进程管理使用 psutil

**选择**：使用 `psutil` 库查找和终止端口进程。

**理由**：
- 跨平台支持（Windows/Linux/macOS）
- API 简洁：`netstat` 命令输出解析复杂且平台差异大
- `psutil.net_connections()` 可直接获取端口对应的进程

**备选方案**：
- 调用系统命令（`netstat -ano`/`lsof`）：平台差异大，解析复杂
- 记录 PID 文件：需要修改 Flask 启动逻辑，侵入性强

### 决策 3：爬虫命令调用已有 API

**选择**：`crawler` 子命令通过 HTTP 调用已有 API（如 `/api/crawler/update_list`）。

**理由**：
- 复用已有逻辑，避免代码重复
- 服务必须先启动才能触发爬虫，符合预期
- 实现简单，只需构造 HTTP 请求

**备选方案**：
- 直接调用服务函数：需要导入后端模块，初始化数据库连接，复杂度高

### 决策 4：输出格式使用 colorama

**选择**：使用 `colorama` 库实现跨平台终端颜色输出。

**理由**：
- Windows 原生不支持 ANSI 颜色代码，colorama 提供兼容层
- 轻量级，输出更友好（成功绿色、错误红色、信息蓝色）

**备选方案**：
- 不使用颜色：输出单调，可读性差
- 使用 ANSI 转义码：Windows 不兼容

## Risks / Trade-offs

- **[风险] psutil 在某些环境下权限不足** → 在 Windows 上需要管理员权限才能终止系统进程，建议以管理员身份运行 stop 命令
- **[权衡] 依赖新增** → 需要添加 `psutil` 和 `colorama` 到 requirements.txt，增加部署步骤
- **[权衡] 爬虫命令依赖服务运行** → 需要先 `manage.py start` 再调用 `crawler` 命令，用户需要理解这个顺序

## Migration Plan

- 新增 `manage.py` 文件到项目根目录
- 在 `requirements.txt` 中添加 `psutil` 和 `colorama`
- 无需数据库迁移，不修改现有代码
- 验证各子命令功能正常

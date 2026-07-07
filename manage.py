#!/usr/bin/env python3
"""Stock Driver CLI Management Script

统一管理入口，支持服务启停、爬虫触发、数据库管理等操作。
"""
import argparse
import subprocess
import time
import os
import shutil
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: requests module not installed. Run: pip install requests")
    exit(1)

try:
    import psutil
except ImportError:
    print("Error: psutil module not installed. Run: pip install psutil")
    exit(1)

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    print("Error: colorama module not installed. Run: pip install colorama")
    exit(1)


API_BASE = "http://127.0.0.1:5000/api"
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "stock.db")


def green(text):
    return f"{Fore.GREEN}{text}{Style.RESET_ALL}"


def red(text):
    return f"{Fore.RED}{text}{Style.RESET_ALL}"


def blue(text):
    return f"{Fore.BLUE}{text}{Style.RESET_ALL}"


def gray(text):
    return f"{Fore.LIGHTBLACK_EX}{text}{Style.RESET_ALL}"


def print_separator():
    print("-" * 60)


def cmd_start(args):
    """启动后端服务"""
    debug = args.debug
    frontend = args.frontend

    print(blue("启动服务..."))

    frontend_proc = None
    if frontend:
        frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
        print(gray("启动前端服务..."))
        try:
            node_modules_path = os.path.join(frontend_dir, "node_modules")
            if not os.path.exists(node_modules_path):
                print(gray("未找到 node_modules，正在安装依赖..."))
                install_result = subprocess.run(
                    ["cmd", "/c", "npm", "install"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if install_result.returncode != 0:
                    print(red(f"依赖安装失败: {install_result.stderr[-500:] if len(install_result.stderr) > 500 else install_result.stderr}"))
                else:
                    print(green("依赖安装成功"))

            frontend_proc = subprocess.Popen(
                ["cmd", "/c", "npm", "run", "dev"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            time.sleep(2)
            if frontend_proc.poll() is not None:
                output = frontend_proc.stdout.read() if frontend_proc.stdout else ""
                print(red(f"前端服务启动失败，退出码: {frontend_proc.returncode}"))
                if output:
                    print(red(f"错误输出: {output[-1000:] if len(output) > 1000 else output}"))
                frontend_proc = None
            else:
                print(green("前端服务已启动"))
                print(gray("前端地址: http://localhost:3000"))
        except Exception as e:
            print(red(f"前端启动失败: {e}"))

    print(gray(f"启动后端服务 (debug={debug})..."))
    print(gray("后端地址: http://localhost:5000"))
    print(gray("按 Ctrl+C 停止服务"))
    print()

    try:
        cmd = ["py", "-m", "backend.app"]
        if debug:
            cmd.append("--debug")
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print()
        if frontend_proc:
            print(blue("停止前端服务..."))
            frontend_proc.terminate()
            frontend_proc.wait(timeout=5)
            print(green("前端服务已停止"))
        print(green("后端服务已停止"))
    except subprocess.CalledProcessError as e:
        if frontend_proc:
            frontend_proc.terminate()
        print(red(f"后端服务启动失败: {e}"))
        exit(1)


def cmd_stop(args):
    """停止服务"""
    print(blue("停止服务..."))
    stopped_backend = False
    stopped_frontend = False

    ports = {5000: "后端", 3000: "前端"}
    for port, name in ports.items():
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    try:
                        proc = psutil.Process(conn.pid)
                        proc_name = proc.name()
                        print(gray(f"找到{name}进程: PID={conn.pid}, 名称={proc_name}"))
                        proc.terminate()
                        proc.wait(timeout=5)
                        print(green(f"已终止{name}进程 PID={conn.pid}"))
                        if port == 5000:
                            stopped_backend = True
                        else:
                            stopped_frontend = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        print(red(f"无法终止{name}进程 PID={conn.pid}: {e}"))
        except Exception as e:
            print(red(f"查找{name}进程失败: {e}"))

    if not stopped_backend and not stopped_frontend:
        print(gray("服务未运行"))
    else:
        print(green("服务已停止"))


def cmd_health(args):
    """检查服务健康状态"""
    print(blue("检查服务健康状态..."))
    try:
        resp = requests.get(f"{API_BASE}/stocks", params={"limit": 1}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            latest_date = data.get("latest_date", "N/A")
            print(green(f"服务状态: 正常"))
            print(gray(f"版本: Stock Driver v1.0"))
            print(gray(f"最新数据日期: {latest_date}"))
            print(gray(f"API 地址: {API_BASE}"))
        else:
            print(red(f"服务状态: 异常 (HTTP {resp.status_code})"))
    except requests.exceptions.ConnectionError:
        print(red("服务状态: 未运行"))
        print(gray("提示: 使用 'python manage.py start' 启动服务"))


def crawler_list(args):
    """触发股票列表更新"""
    print(blue("触发股票列表更新..."))
    try:
        resp = requests.post(f"{API_BASE}/crawler/update_list", timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            print(green(f"成功更新 {data['success_count']} 只股票"))
            if data['fail_count'] > 0:
                print(red(f"失败 {data['fail_count']} 只"))
            print(gray(f"耗时: {data.get('elapsed', 'N/A')}秒"))
        else:
            print(red(f"请求失败: HTTP {resp.status_code}"))
            print(red(f"错误: {resp.text}"))
    except requests.exceptions.ConnectionError:
        print(red("无法连接到服务"))
        print(gray("提示: 使用 'python manage.py start' 启动服务"))


def crawler_realtime(args):
    """触发实时行情爬取"""
    print(blue("触发实时行情爬取..."))
    payload = {"force": args.force}
    try:
        resp = requests.post(f"{API_BASE}/crawler/update_realtime", json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("skipped"):
                print(gray(data["message"]))
            else:
                print(green(f"成功更新 {data['success_count']} 只股票"))
                if data['fail_count'] > 0:
                    print(red(f"失败 {data['fail_count']} 只"))
                print(gray(f"耗时: {data.get('elapsed', 'N/A')}秒"))
                print(gray(f"数据日期: {data.get('price_date', 'N/A')}"))
        else:
            print(red(f"请求失败: HTTP {resp.status_code}"))
            print(red(f"错误: {resp.text}"))
    except requests.exceptions.ConnectionError:
        print(red("无法连接到服务"))
        print(gray("提示: 使用 'python manage.py start' 启动服务"))


def crawler_daily(args):
    """触发日线数据爬取"""
    print(blue("触发日线数据爬取..."))
    payload = {}
    if args.start_date:
        payload["start_date"] = args.start_date
    if args.end_date:
        payload["end_date"] = args.end_date
    if args.codes:
        payload["codes"] = [c.strip() for c in args.codes.split(",") if c.strip()]

    print(gray(f"日期范围: {args.start_date or '默认'} ~ {args.end_date or '默认'}"))
    if args.codes:
        print(gray(f"股票代码: {args.codes}"))
    print()

    try:
        resp = requests.post(f"{API_BASE}/crawler/fetch_daily_batch", json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            print(green(f"批量爬取已启动，共 {data['total']} 只股票"))
            print(gray(f"开始日期: {data['start_date']}"))
            print(gray(f"结束日期: {data['end_date']}"))
            print()
            print(blue("正在轮询进度..."))
            print_separator()

            while True:
                time.sleep(2)
                try:
                    progress_resp = requests.get(f"{API_BASE}/crawler/progress/daily", timeout=5)
                    if progress_resp.status_code == 200:
                        progress = progress_resp.json()
                        if not progress.get("running"):
                            print()
                            print_separator()
                            print(green(f"爬取完成"))
                            print(gray(f"成功: {progress.get('success', 0)} 只"))
                            print(gray(f"失败: {progress.get('failed', 0)} 只"))
                            print(gray(f"新增: {progress.get('added', 0)} 条"))
                            print(gray(f"更新: {progress.get('updated', 0)} 条"))
                            if progress.get("error"):
                                print(red(f"错误: {progress['error']}"))
                            break

                        current = progress.get("current", 0)
                        total = progress.get("total", 0)
                        current_code = progress.get("current_code", "")
                        success = progress.get("success", 0)
                        failed = progress.get("failed", 0)
                        added = progress.get("added", 0)
                        updated = progress.get("updated", 0)
                        percentage = (current / total) * 100 if total > 0 else 0

                        bar_len = 30
                        bar = "█" * int(bar_len * percentage / 100) + "░" * (bar_len - int(bar_len * percentage / 100))
                        print(f"\r{bar} {percentage:.1f}% [{current}/{total}] {current_code} | 成功:{success} 失败:{failed} 新增:{added} 更新:{updated}", end="")
                except requests.exceptions.ConnectionError:
                    print(red("\n连接中断，进度查询失败"))
                    break
        else:
            print(red(f"请求失败: HTTP {resp.status_code}"))
            print(red(f"错误: {resp.text}"))
    except requests.exceptions.ConnectionError:
        print(red("无法连接到服务"))
        print(gray("提示: 使用 'python manage.py start' 启动服务"))


def crawler_status(args):
    """查询爬取状态历史"""
    print(blue("查询爬取状态历史..."))
    params = {"limit": args.limit}
    if args.type:
        params["crawl_type"] = args.type

    try:
        resp = requests.get(f"{API_BASE}/crawl_status", params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if not data:
                print(gray("暂无爬取记录"))
                return

            print_separator()
            print(f"{'ID':<4} {'类型':<10} {'状态':<10} {'时间':<20} {'成功':<6} {'失败':<6} {'错误'}")
            print_separator()
            for item in data:
                status_color = green if item["status"] == "success" else red if item["status"] == "failed" else blue
                print(f"{item['id']:<4} {item['crawl_type']:<10} {status_color(item['status']):<10} {item['crawl_time']:<20} {item['success_count']:<6} {item['fail_count']:<6} {item.get('error_message', '')}")
            print_separator()
        else:
            print(red(f"请求失败: HTTP {resp.status_code}"))
    except requests.exceptions.ConnectionError:
        print(red("无法连接到服务"))
        print(gray("提示: 使用 'python manage.py start' 启动服务"))


def db_migrate(args):
    """初始化数据库表结构"""
    print(blue("初始化数据库表结构..."))
    try:
        from backend.utils.db import engine, Base
        import backend.models  # noqa: F401 — 注册所有 ORM 模型
        Base.metadata.create_all(bind=engine)
        print(green("数据库表结构初始化完成"))
    except Exception as e:
        print(red(f"初始化失败: {e}"))
        exit(1)


def db_backup(args):
    """备份数据库"""
    print(blue("备份数据库..."))
    if not os.path.exists(DB_PATH):
        print(red(f"数据库文件不存在: {DB_PATH}"))
        exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH + f".backup.{timestamp}"

    try:
        shutil.copy2(DB_PATH, backup_path)
        file_size = os.path.getsize(backup_path)
        file_size_mb = file_size / (1024 * 1024)
        print(green(f"备份成功"))
        print(gray(f"备份文件: {backup_path}"))
        print(gray(f"文件大小: {file_size_mb:.2f} MB"))
    except Exception as e:
        print(red(f"备份失败: {e}"))
        exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Stock Driver CLI Management Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python manage.py start                      # 启动后端服务
  python manage.py start --frontend           # 同时启动前后端服务 (前端:3000, 后端:5000)
  python manage.py stop                       # 停止后端服务
  python manage.py health                     # 检查服务状态
  python manage.py crawler list               # 更新股票列表
  python manage.py crawler realtime --force   # 强制爬取实时行情
  python manage.py crawler daily --start-date 20260701 --end-date 20260703
  python manage.py crawler status --limit 20  # 查询最近20条爬取记录
  python manage.py db migrate                # 初始化数据库表结构
  python manage.py db backup                 # 备份数据库
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    start_parser = subparsers.add_parser("start", help="启动服务")
    start_parser.add_argument("--debug", action="store_true", help="启用调试模式")
    start_parser.add_argument("--frontend", action="store_true", help="同时启动前端服务")
    start_parser.set_defaults(func=cmd_start)

    stop_parser = subparsers.add_parser("stop", help="停止后端服务")
    stop_parser.set_defaults(func=cmd_stop)

    health_parser = subparsers.add_parser("health", help="检查服务健康状态")
    health_parser.set_defaults(func=cmd_health)

    crawler_parser = subparsers.add_parser("crawler", help="爬虫管理")
    crawler_subparsers = crawler_parser.add_subparsers(dest="crawler_command")

    crawl_list_parser = crawler_subparsers.add_parser("list", help="更新股票列表")
    crawl_list_parser.set_defaults(func=crawler_list)

    crawl_realtime_parser = crawler_subparsers.add_parser("realtime", help="爬取实时行情")
    crawl_realtime_parser.add_argument("--force", action="store_true", help="强制爬取（忽略幂等性检查）")
    crawl_realtime_parser.set_defaults(func=crawler_realtime)

    crawl_daily_parser = crawler_subparsers.add_parser("daily", help="爬取日线数据")
    crawl_daily_parser.add_argument("--start-date", type=str, help="开始日期 (YYYYMMDD)")
    crawl_daily_parser.add_argument("--end-date", type=str, help="结束日期 (YYYYMMDD)")
    crawl_daily_parser.add_argument("--codes", type=str, help="股票代码，逗号分隔")
    crawl_daily_parser.set_defaults(func=crawler_daily)

    crawl_status_parser = crawler_subparsers.add_parser("status", help="查询爬取状态")
    crawl_status_parser.add_argument("--limit", type=int, default=10, help="返回条数")
    crawl_status_parser.add_argument("--type", type=str, choices=["list", "realtime", "daily"], help="爬取类型过滤")
    crawl_status_parser.set_defaults(func=crawler_status)

    db_parser = subparsers.add_parser("db", help="数据库管理")
    db_subparsers = db_parser.add_subparsers(dest="db_command")

    db_migrate_parser = db_subparsers.add_parser("migrate", help="初始化数据库表结构")
    db_migrate_parser.set_defaults(func=db_migrate)

    db_backup_parser = db_subparsers.add_parser("backup", help="备份数据库")
    db_backup_parser.set_defaults(func=db_backup)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        exit(0)

    args.func(args)


if __name__ == "__main__":
    main()

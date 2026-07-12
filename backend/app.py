from flask import Flask
from flask_cors import CORS
from backend.config import Config
from backend.api.routes import api
from backend.utils.db import engine, Base
from backend.services.scheduler import get_scheduler
import atexit
import logging

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r'/api/*': {'origins': '*'}})

    app.register_blueprint(api, url_prefix='/api')

    @app.route('/')
    def index():
        return 'Stock Driver API'

    # 初始化数据库
    init_db()

    # 启动定时任务调度器
    scheduler = get_scheduler()
    scheduler.start()

    # 注册应用关闭时的清理函数
    atexit.register(scheduler.shutdown)

    return app

def init_db():
    Base.metadata.create_all(bind=engine)
    # 数据库迁移：为已有表添加新字段
    _migrate_db()

def _migrate_db():
    """为已有数据库添加新字段（幂等操作）"""
    migrations = [
        "ALTER TABLE backtest_transactions ADD COLUMN reason VARCHAR(50)",
    ]
    conn = engine.connect()
    for sql in migrations:
        try:
            conn.exec_driver_sql(sql)
        except Exception:
            pass  # 字段已存在则忽略
    conn.close()

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)

from flask import Flask
from flask_cors import CORS
from backend.config import Config
from backend.api.routes import api
from backend.utils.db import engine, Base
from backend.services.scheduler import get_scheduler
import atexit

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
    _migrate_db(engine)


def _migrate_db(db_engine):
    """迁移数据库：添加缺失的列"""
    try:
        from sqlalchemy import text
        with db_engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info('stock_daily')"))
            existing_cols = {row[1] for row in result.fetchall()}
            for col_name, col_type in [
                ('pe', 'FLOAT'),
                ('pb', 'FLOAT'),
                ('market_cap', 'FLOAT'),
            ]:
                if col_name not in existing_cols:
                    conn.execute(text(
                        f"ALTER TABLE stock_daily ADD COLUMN {col_name} {col_type}"
                    ))
                    conn.commit()
                    print(f"[migrate] Added column {col_name} to stock_daily")
    except Exception as e:
        print(f"[migrate] Migration note: {e}")

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)

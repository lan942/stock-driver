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
    try:
        from backend.utils.migrate_db import add_stock_daily_columns, add_stock_daily_unique_constraint, add_trade_date_column
        add_stock_daily_columns(engine)
        add_stock_daily_unique_constraint(engine)
        add_trade_date_column(engine)
    except Exception as e:
        print(f"[migrate] Migration note: {e}")

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)

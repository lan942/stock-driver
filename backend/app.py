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

    # 启动定时任务调度器
    scheduler = get_scheduler()
    scheduler.start()

    # 注册应用关闭时的清理函数
    atexit.register(scheduler.shutdown)

    return app

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    init_db()
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

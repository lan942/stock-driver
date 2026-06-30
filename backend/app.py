from flask import Flask
from flask_cors import CORS
from backend.config import Config
from backend.api.routes import api
from backend.utils.db import engine, Base

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    CORS(app, resources={r'/api/*': {'origins': '*'}})
    
    app.register_blueprint(api, url_prefix='/api')
    
    @app.route('/')
    def index():
        return 'Stock Driver API'
    
    return app

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    init_db()
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

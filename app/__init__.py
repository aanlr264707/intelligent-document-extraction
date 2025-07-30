from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
import os

try:
    from flask_caching import Cache
    CACHING_AVAILABLE = True
except ImportError:
    CACHING_AVAILABLE = False

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
cache = Cache() if CACHING_AVAILABLE else None

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///intelligent_extraction.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_DOCUMENT_SIZE_MB', 50)) * 1024 * 1024
    
    if CACHING_AVAILABLE:
        app.config['CACHE_TYPE'] = 'redis' if os.getenv('REDIS_URL') else 'simple'
        app.config['CACHE_REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        app.config['CACHE_DEFAULT_TIMEOUT'] = 300
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    if CACHING_AVAILABLE and cache:
        cache.init_app(app, config={
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            'CACHE_DEFAULT_TIMEOUT': 300
        })
    
    CORS(app)
    
    from app.views.main import main_bp
    from app.views.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app

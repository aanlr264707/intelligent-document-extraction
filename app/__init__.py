from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging

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
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///intelligent_extraction.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_DOCUMENT_SIZE_MB', 50)) * 1024 * 1024
    
    # Upload and output directories
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads')
    app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'outputs')
    
    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    
    # Performance and security configuration
    app.config['MAX_CONCURRENT_EXTRACTIONS'] = int(os.getenv('MAX_CONCURRENT_EXTRACTIONS', 5))
    app.config['PROCESSING_TIMEOUT_SECONDS'] = int(os.getenv('PROCESSING_TIMEOUT_SECONDS', 300))  # 5 minutes default
    app.config['GDPR_COMPLIANCE'] = os.getenv('GDPR_COMPLIANCE', 'True').lower() == 'true'
    app.config['DATA_RETENTION_DAYS'] = int(os.getenv('DATA_RETENTION_DAYS', 90))
    app.config['AUDIT_LOG_ENABLED'] = os.getenv('AUDIT_LOG_ENABLED', 'True').lower() == 'true'
    
    # Email monitoring configuration
    app.config['EMAIL_MONITORING_ENABLED'] = os.getenv('EMAIL_ADDRESS') is not None
    app.config['EMAIL_RESULTS_ENABLED'] = os.getenv('EMAIL_RESULTS_ENABLED', 'false').lower() == 'true'
    
    # RAG configuration
    app.config['RAG_ENABLED'] = os.getenv('RAG_ENABLED', 'True').lower() == 'true'
    app.config['RAG_KNOWLEDGE_BASE_PATH'] = os.getenv('RAG_KNOWLEDGE_BASE_PATH', 'data/rag_knowledge_base')
    
    # Caching configuration
    if CACHING_AVAILABLE:
        app.config['CACHE_TYPE'] = 'redis' if os.getenv('REDIS_URL') else 'simple'
        app.config['CACHE_REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        app.config['CACHE_DEFAULT_TIMEOUT'] = 300
    
    # Logging configuration
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.getenv('LOG_FILE', 'logs/extraction.log')),
            logging.StreamHandler()
        ]
    )
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import models to ensure they're registered
    from app.models import Document, ExtractionRequest, AuditLog
    
    # Initialize caching if available
    if CACHING_AVAILABLE and cache:
        cache.init_app(app, config={
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            'CACHE_DEFAULT_TIMEOUT': 300
        })
    
    # Enable CORS
    CORS(app)
    
    # Register blueprints
    from app.views.main import main_bp
    from app.views.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register enhanced API blueprint if available
    try:
        from app.views.enhanced_api import enhanced_api_bp
        app.register_blueprint(enhanced_api_bp, url_prefix='/api/v2')
        app.logger.info("Enhanced API v2 endpoints registered")
    except ImportError as e:
        app.logger.info(f"Enhanced API not available: {e}")
    except Exception as e:
        app.logger.error(f"Error registering enhanced API: {e}")
    
    # Initialize services
    with app.app_context():
        _initialize_services(app)
    
    return app

def _initialize_services(app):
    """Initialize application services"""
    try:
        # Initialize performance monitoring
        try:
            from app.services.performance_monitor import performance_monitor
            if not performance_monitor.monitoring_active:
                performance_monitor.start_monitoring()
                app.logger.info("Performance monitoring started")
        except ImportError:
            app.logger.info("Performance monitoring not available")
        
        # Initialize email monitoring if configured
        if app.config.get('EMAIL_MONITORING_ENABLED'):
            try:
                from app.services.email_monitor import email_monitor
                if email_monitor.start_monitoring():
                    app.logger.info("Email monitoring started")
                else:
                    app.logger.warning("Email monitoring failed to start - check configuration")
            except ImportError:
                app.logger.info("Email monitoring not available")
        
        # Initialize enhanced extraction engine
        try:
            from app.services.extraction_engine_enhanced import enhanced_extraction_engine
            features = enhanced_extraction_engine.get_supported_features()
            enabled_features = [k for k, v in features.items() if v]
            app.logger.info(f"Enhanced extraction engine initialized with features: {enabled_features}")
        except ImportError:
            app.logger.warning("Enhanced extraction engine not available")
        
        # Create necessary directories
        os.makedirs('static/uploads', exist_ok=True)
        os.makedirs('static/outputs', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        if app.config.get('RAG_ENABLED'):
            os.makedirs(app.config['RAG_KNOWLEDGE_BASE_PATH'], exist_ok=True)
        
        app.logger.info("Application services initialized successfully")
        
    except Exception as e:
        app.logger.error(f"Error initializing services: {e}")

# Cleanup function for graceful shutdown
def cleanup_services():
    """Clean up services on application shutdown"""
    try:
        from app.services.performance_monitor import performance_monitor
        performance_monitor.stop_monitoring()
    except:
        pass
    
    try:
        from app.services.email_monitor import email_monitor
        email_monitor.stop_monitoring()
    except:
        pass

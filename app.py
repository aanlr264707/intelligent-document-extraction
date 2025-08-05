import os
from app import create_app, db
from app.models import Document, ExtractionRequest, AuditLog

app = create_app()

# Database tables are managed by Flask-Migrate
# Comment out db.create_all() to avoid conflicts with migrations
# with app.app_context():
#     db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)

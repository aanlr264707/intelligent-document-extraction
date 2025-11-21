import os
from app import create_app, db
from app.models import Document, ExtractionRequest, AuditLog

app = create_app()

# Database tables are managed by Flask-Migrate
# Comment out db.create_all() to avoid conflicts with migrations
# with app.app_context():
#     db.create_all()

if __name__ == '__main__':
    # Always use port 5001 unless explicitly overridden by environment
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"Starting Flask application on port {port}")
    print("To use a different port, set the PORT environment variable")
    
    # Try ports 5001, 5002, 5003, etc. until we find one that's available
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            current_port = port + attempt
            print(f"Attempting to start on port {current_port}...")
            app.run(host='0.0.0.0', port=current_port, debug=debug)
            break
        except OSError as e:
            if "Address already in use" in str(e):
                if attempt < max_attempts - 1:
                    print(f"Port {current_port} is already in use. Trying port {current_port + 1}...")
                    continue
                else:
                    print(f"Unable to find an available port after trying ports {port}-{port + max_attempts - 1}")
                    print("Please stop other services or set a specific PORT environment variable")
                    raise
            else:
                raise

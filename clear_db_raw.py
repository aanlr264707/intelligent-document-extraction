#!/usr/bin/env python3
"""Clear database records using raw SQL to bypass enum validation"""

from app import create_app, db

def clear_database_raw():
    app = create_app()
    
    with app.app_context():
        try:
            db.engine.execute("DELETE FROM extraction_requests")
            db.session.commit()
            print("✓ Cleared all extraction requests using raw SQL")
            
            db.engine.execute("DELETE FROM documents")
            db.session.commit()
            print("✓ Cleared all documents using raw SQL")
            
        except Exception as e:
            print(f"❌ Error clearing records: {e}")
            db.session.rollback()

if __name__ == '__main__':
    clear_database_raw()

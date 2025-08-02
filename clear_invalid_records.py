#!/usr/bin/env python3
"""Clear invalid database records with string status values"""

from app import create_app, db
from app.models.extraction_request import ExtractionRequest

def clear_invalid_records():
    app = create_app()
    
    with app.app_context():
        try:
            invalid_requests = ExtractionRequest.query.all()
            for request in invalid_requests:
                db.session.delete(request)
            
            db.session.commit()
            print(f"✓ Cleared {len(invalid_requests)} extraction requests")
            
        except Exception as e:
            print(f"❌ Error clearing records: {e}")
            db.session.rollback()

if __name__ == '__main__':
    clear_invalid_records()

from app import db
from datetime import datetime
import enum

class AuditAction(enum.Enum):
    DOCUMENT_UPLOAD = "document_upload"
    EXTRACTION_REQUEST = "extraction_request"
    EXTRACTION_COMPLETED = "extraction_completed"
    EXTRACTION_FAILED = "extraction_failed"
    USER_FEEDBACK = "user_feedback"
    DATA_EXPORT = "data_export"
    MANUAL_CORRECTION = "manual_correction"

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.Enum(AuditAction), nullable=False)
    user_id = db.Column(db.String(100))  # For future user management
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    extraction_request_id = db.Column(db.Integer, db.ForeignKey('extraction_requests.id'))
    
    details = db.Column(db.Text)  # JSON string with action-specific details
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    
    def __repr__(self):
        return f'<AuditLog {self.id} - {self.action.value}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'action': self.action.value,
            'user_id': self.user_id,
            'document_id': self.document_id,
            'extraction_request_id': self.extraction_request_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }

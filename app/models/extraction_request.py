from app import db
from datetime import datetime
import enum
import json

class ExtractionStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    FLAGGED = "flagged"

class OutputFormat(enum.Enum):
    JSON = "json"
    CSV = "csv"
    XML = "xml"

class ExtractionRequest(db.Model):
    __tablename__ = 'extraction_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    natural_language_request = db.Column(db.Text, nullable=False)
    output_format = db.Column(db.Enum(OutputFormat), default=OutputFormat.JSON)
    status = db.Column(db.Enum(ExtractionStatus), default=ExtractionStatus.PENDING)
    
    created_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    started_timestamp = db.Column(db.DateTime)
    completed_timestamp = db.Column(db.DateTime)
    processing_time_seconds = db.Column(db.Float)
    
    extracted_data = db.Column(db.Text)  # JSON string
    confidence_score = db.Column(db.Float)
    flagged_fields = db.Column(db.Text)  # JSON string of flagged fields
    error_message = db.Column(db.Text)
    
    identified_clauses = db.Column(db.Text)  # JSON string
    risk_flags = db.Column(db.Text)  # JSON string
    document_summary = db.Column(db.Text)
    reference_materials = db.Column(db.Text)  # JSON string
    
    def __repr__(self):
        return f'<ExtractionRequest {self.id} - {self.status.value}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'natural_language_request': self.natural_language_request,
            'output_format': self.output_format.value,
            'status': self.status.value,
            'created_timestamp': self.created_timestamp.isoformat(),
            'started_timestamp': self.started_timestamp.isoformat() if self.started_timestamp else None,
            'completed_timestamp': self.completed_timestamp.isoformat() if self.completed_timestamp else None,
            'processing_time_seconds': self.processing_time_seconds,
            'extracted_data': json.loads(self.extracted_data) if self.extracted_data else None,
            'confidence_score': self.confidence_score,
            'flagged_fields': json.loads(self.flagged_fields) if self.flagged_fields else None,
            'error_message': self.error_message,
            'identified_clauses': json.loads(self.identified_clauses) if self.identified_clauses else None,
            'risk_flags': json.loads(self.risk_flags) if self.risk_flags else None,
            'document_summary': self.document_summary,
            'reference_materials': json.loads(self.reference_materials) if self.reference_materials else None
        }

from app import db
from datetime import datetime
import enum

class DocumentType(enum.Enum):
    PDF = "pdf"
    WORD = "word"
    IMAGE = "image"
    HANDWRITTEN = "handwritten"
    OTHER = "other"

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    document_type = db.Column(db.Enum(DocumentType), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    
    extraction_requests = db.relationship('ExtractionRequest', backref='document', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Document {self.filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'document_type': self.document_type.value,
            'mime_type': self.mime_type,
            'upload_timestamp': self.upload_timestamp.isoformat(),
            'processed': self.processed
        }

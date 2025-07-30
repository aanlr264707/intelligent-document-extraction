import pytest
import tempfile
import os
from app import create_app, db
from app.models.document import Document
from app.models.document import DocumentType
from app.models.extraction_request import ExtractionRequest
from app.models.audit_log import AuditLog

@pytest.fixture
def app():
    """Create application for testing"""
    
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create test runner"""
    return app.test_cli_runner()

@pytest.fixture
def sample_document(app):
    """Create a sample document for testing"""
    with app.app_context():
        document = Document(
            filename='test_document.txt',
            file_path='/tmp/test_document.txt',
            document_type=DocumentType.OTHER,
            file_size=1024,
            upload_timestamp=None
        )
        db.session.add(document)
        db.session.commit()
        return document

@pytest.fixture
def sample_extraction_request(app, sample_document):
    """Create a sample extraction request for testing"""
    with app.app_context():
        request_data = {
            'fields': ['name', 'date', 'amount'],
            'output_format': 'json',
            'natural_language_request': 'Extract name, date, and amount from the document'
        }
        
        extraction_request = ExtractionRequest(
            document_id=sample_document.id,
            request_data=request_data,
            status='pending'
        )
        db.session.add(extraction_request)
        db.session.commit()
        return extraction_request

@pytest.fixture
def sample_text_content():
    """Sample text content for testing"""
    return """
    Invoice #12345
    Date: 2024-01-15
    Customer: John Doe
    Amount: $1,250.00
    
    Description: Professional services rendered
    Payment due: 2024-02-15
    """

@pytest.fixture
def sample_extracted_data():
    """Sample extracted data for testing"""
    return {
        'invoice_number': '12345',
        'date': '2024-01-15',
        'customer_name': 'John Doe',
        'amount': '$1,250.00',
        'description': 'Professional services rendered',
        'due_date': '2024-02-15',
        'confidence_scores': {
            'invoice_number': 0.95,
            'date': 0.90,
            'customer_name': 0.85,
            'amount': 0.92,
            'description': 0.80,
            'due_date': 0.88
        }
    }

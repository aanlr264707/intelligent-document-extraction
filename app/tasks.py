from app.celery_app import celery
from app import create_app, db
from app.models.document import Document
from app.models.extraction_request import ExtractionRequest
from app.services.extraction_engine import ExtractionEngine
from app.services.advanced_nlp import AdvancedNLPProcessor
import json

@celery.task(bind=True)
def async_document_extraction(self, document_id, extraction_request_id):
    """Perform document extraction asynchronously"""
    
    app = create_app()
    
    with app.app_context():
        try:
            self.update_state(state='PROGRESS', meta={'status': 'Starting extraction'})
            
            document = Document.query.get(document_id)
            extraction_request = ExtractionRequest.query.get(extraction_request_id)
            
            if not document or not extraction_request:
                raise ValueError("Document or extraction request not found")
            
            self.update_state(state='PROGRESS', meta={'status': 'Initializing extraction engine'})
            
            extraction_engine = ExtractionEngine()
            advanced_nlp = AdvancedNLPProcessor()
            
            self.update_state(state='PROGRESS', meta={'status': 'Processing document'})
            
            result = extraction_engine.extract_data(document, extraction_request.request_data)
            
            if advanced_nlp.models_loaded:
                self.update_state(state='PROGRESS', meta={'status': 'Enhancing with advanced NLP'})
                
                text_content = result.get('extracted_data', {}).get('text_content', '')
                if text_content:
                    result['extracted_data'] = advanced_nlp.enhance_extraction_results(
                        text_content, 
                        result.get('extracted_data', {})
                    )
            
            extraction_request.status = 'completed'
            extraction_request.result_data = result
            db.session.commit()
            
            return {
                'status': 'completed',
                'result': result,
                'document_id': document_id,
                'extraction_request_id': extraction_request_id
            }
            
        except Exception as e:
            extraction_request.status = 'failed'
            extraction_request.error_message = str(e)
            db.session.commit()
            
            self.update_state(
                state='FAILURE',
                meta={'error': str(e), 'document_id': document_id}
            )
            raise

@celery.task
def cleanup_old_extractions():
    """Clean up old extraction results"""
    
    app = create_app()
    
    with app.app_context():
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        old_requests = ExtractionRequest.query.filter(
            ExtractionRequest.created_at < cutoff_date,
            ExtractionRequest.status.in_(['completed', 'failed'])
        ).all()
        
        for request in old_requests:
            db.session.delete(request)
        
        db.session.commit()
        
        return f"Cleaned up {len(old_requests)} old extraction requests"

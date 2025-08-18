from app.celery_app import celery
from app import create_app, db
from app.models.document import Document
from app.models.extraction_request import ExtractionRequest, ExtractionStatus
from app.services.extraction_engine_enhanced import enhanced_extraction_engine
from app.services.document_processor import DocumentProcessor
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@celery.task(bind=True)
def async_document_extraction(self, document_id, extraction_request_id):
    """Perform comprehensive document extraction asynchronously"""
    
    app = create_app()
    
    with app.app_context():
        try:
            self.update_state(state='PROGRESS', meta={'status': 'Starting comprehensive extraction'})
            logger.info(f"Starting extraction for document {document_id}, request {extraction_request_id}")
            
            # Get document and extraction request
            document = Document.query.get(document_id)
            extraction_request = ExtractionRequest.query.get(extraction_request_id)
            
            if not document or not extraction_request:
                raise ValueError("Document or extraction request not found")
            
            # Update status to processing
            extraction_request.status = ExtractionStatus.PROCESSING
            extraction_request.started_timestamp = datetime.utcnow()
            db.session.commit()
            
            self.update_state(state='PROGRESS', meta={'status': 'Initializing enhanced extraction engine'})
            
            # Use the global enhanced extraction engine
            extraction_engine = enhanced_extraction_engine
            
            self.update_state(state='PROGRESS', meta={'status': 'Extracting document content'})
            
            # Perform comprehensive extraction
            result = extraction_engine.extract_data(document, extraction_request)
            
            if not result or not result.get('success', False):
                error_msg = result.get('error', 'Extraction failed with unknown error') if result else 'No extraction result returned'
                raise Exception(error_msg)
            
            self.update_state(state='PROGRESS', meta={'status': 'Processing legal analysis'})
            
            # Ensure we have comprehensive legal analysis
            if 'legal_analysis' not in result.get('extracted_data', {}):
                # Extract text for legal analysis
                doc_processor = DocumentProcessor()
                text_content = doc_processor.extract_text_from_document(document)
                
                if text_content:
                    # Use built-in legal analysis from enhanced engine
                    from app.services.legal_processor_enhanced import enhanced_legal_processor
                    legal_analysis = enhanced_legal_processor.analyze_comprehensive_legal_document_sync(text_content)
                    
                    if not result.get('extracted_data'):
                        result['extracted_data'] = {}
                    result['extracted_data']['legal_analysis'] = legal_analysis
            
            self.update_state(state='PROGRESS', meta={'status': 'Finalizing extraction results'})
            
            # Update extraction request with results
            extraction_request.status = ExtractionStatus.COMPLETED
            extraction_request.completed_timestamp = datetime.utcnow()
            extraction_request.confidence_score = result.get('confidence_score', 0.0)
            extraction_request.processing_time_seconds = result.get('processing_time_seconds', 0.0)
            
            # Store extracted data
            extraction_request.extracted_data = json.dumps(result.get('extracted_data', {}))
            
            # Store legal analysis in separate fields for backward compatibility
            legal_analysis = result.get('extracted_data', {}).get('legal_analysis', {})
            if legal_analysis:
                if 'legal_clauses' in legal_analysis:
                    extraction_request.identified_clauses = json.dumps(legal_analysis['legal_clauses'])
                
                if 'risk_assessment' in legal_analysis:
                    risk_factors = legal_analysis['risk_assessment'].get('risk_factors', [])
                    extraction_request.risk_flags = json.dumps(risk_factors)
                
                if 'contract_summary' in legal_analysis:
                    extraction_request.document_summary = legal_analysis['contract_summary']
                
                # Store comprehensive reference materials
                reference_data = {
                    'document_overview': legal_analysis.get('document_overview', {}),
                    'main_parties': legal_analysis.get('main_parties', []),
                    'key_dates': legal_analysis.get('key_dates', []),
                    'financial_terms': legal_analysis.get('financial_terms', []),
                    'document_tables': legal_analysis.get('document_tables', [])
                }
                extraction_request.reference_materials = json.dumps(reference_data)
            
            db.session.commit()
            logger.info(f"Extraction completed successfully for document {document_id}")
            
            return {
                'status': 'completed',
                'result': result,
                'document_id': document_id,
                'extraction_request_id': extraction_request_id,
                'confidence_score': result.get('confidence_score', 0.0),
                'processing_time': result.get('processing_time_seconds', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Extraction failed for document {document_id}: {str(e)}")
            
            # Update extraction request with failure
            if 'extraction_request' in locals():
                extraction_request.status = ExtractionStatus.FAILED
                extraction_request.error_message = str(e)
                extraction_request.completed_timestamp = datetime.utcnow()
                db.session.commit()
            
            self.update_state(
                state='FAILURE',
                meta={
                    'error': str(e), 
                    'document_id': document_id,
                    'extraction_request_id': extraction_request_id
                }
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
            ExtractionRequest.created_timestamp < cutoff_date,
            ExtractionRequest.status.in_([ExtractionStatus.COMPLETED, ExtractionStatus.FAILED])
        ).all()
        
        for request in old_requests:
            db.session.delete(request)
        
        db.session.commit()
        
        return f"Cleaned up {len(old_requests)} old extraction requests"

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

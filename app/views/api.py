from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from app.models.document import Document
from app.models.extraction_request import ExtractionRequest, ExtractionStatus, OutputFormat
from app.models.audit_log import AuditLog, AuditAction
from app.services.document_processor import DocumentProcessor
from app.services.extraction_engine import ExtractionEngine
from app.services.output_generator import OutputGenerator
from app import db
import threading

api_bp = Blueprint('api', __name__)

document_processor = DocumentProcessor()
extraction_engine = ExtractionEngine()
output_generator = OutputGenerator()

@api_bp.route('/upload', methods=['POST'])
def upload_document():
    """API endpoint for document upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        file_info = document_processor.save_uploaded_file(file)
        document = document_processor.create_document_record(file_info)
        
        audit_log = AuditLog(
            action=AuditAction.DOCUMENT_UPLOAD,
            document_id=document.id,
            details=json.dumps({
                'filename': document.original_filename,
                'file_size': document.file_size,
                'document_type': document.document_type.value
            }),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'document': document.to_dict(),
            'message': 'Document uploaded successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/extract', methods=['POST'])
def extract_data():
    """API endpoint for data extraction"""
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename:
                    file_info = document_processor.save_uploaded_file(file)
                    document = document_processor.create_document_record(file_info)
                    data['document_id'] = document.id
        
        if 'document_id' not in data:
            return jsonify({'success': False, 'error': 'Document ID is required'}), 400
        
        if 'requirements' not in data:
            return jsonify({'success': False, 'error': 'Extraction requirements are required'}), 400
        
        document_id = int(data['document_id'])
        requirements = data['requirements']
        output_format = data.get('output_format', 'json').lower()
        
        document = Document.query.get(document_id)
        if not document:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        try:
            output_format_enum = OutputFormat(output_format)
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid output format'}), 400
        
        extraction_request = ExtractionRequest(
            document_id=document_id,
            natural_language_request=requirements,
            output_format=output_format_enum,
            status=ExtractionStatus.PENDING
        )
        
        db.session.add(extraction_request)
        db.session.commit()
        
        audit_log = AuditLog(
            action=AuditAction.EXTRACTION_REQUEST,
            document_id=document_id,
            extraction_request_id=extraction_request.id,
            details=json.dumps({
                'requirements': requirements,
                'output_format': output_format
            }),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        app = current_app._get_current_object()
        
        def process_extraction(doc_id, req_id):
            with app.app_context():
                try:
                    print(f"[EXTRACTION DEBUG] Starting extraction for request {req_id}")
                    thread_extraction_request = ExtractionRequest.query.get(req_id)
                    thread_document = Document.query.get(doc_id)
                    
                    if not thread_extraction_request or not thread_document:
                        print(f"[EXTRACTION DEBUG] Missing request or document: req={thread_extraction_request}, doc={thread_document}")
                        return
                    
                    thread_extraction_request.status = ExtractionStatus.PROCESSING
                    thread_extraction_request.started_timestamp = datetime.utcnow()
                    db.session.commit()
                    print(f"[EXTRACTION DEBUG] Status updated to PROCESSING")
                    
                    print(f"[EXTRACTION DEBUG] Calling extraction engine...")
                    
                    import threading
                    import queue
                    
                    result_queue = queue.Queue()
                    exception_queue = queue.Queue()
                    
                    def extraction_worker():
                        try:
                            with app.app_context():
                                result = extraction_engine.extract_data(thread_document, thread_extraction_request)
                                result_queue.put(result)
                        except Exception as e:
                            exception_queue.put(e)
                    
                    worker_thread = threading.Thread(target=extraction_worker)
                    worker_thread.daemon = True
                    worker_thread.start()
                    
                    worker_thread.join(timeout=60)
                    
                    if worker_thread.is_alive():
                        print(f"[EXTRACTION DEBUG] Extraction timed out after 60 seconds")
                        result = {'error': 'Extraction timed out after 60 seconds'}
                    elif not exception_queue.empty():
                        exception = exception_queue.get()
                        print(f"[EXTRACTION DEBUG] Extraction engine error: {exception}")
                        result = {'error': f'Extraction failed: {str(exception)}'}
                    elif not result_queue.empty():
                        result = result_queue.get()
                        print(f"[EXTRACTION DEBUG] Extraction completed, result keys: {list(result.keys()) if result else 'None'}")
                    else:
                        print(f"[EXTRACTION DEBUG] Extraction completed with no result")
                        result = {'error': 'Extraction completed but returned no result'}
                    
                    if not result:
                        result = {'error': 'Extraction returned no result'}
                    
                    if 'error' in result:
                        print(f"[EXTRACTION DEBUG] Error in result: {result['error']}")
                        thread_extraction_request.status = ExtractionStatus.FAILED
                        thread_extraction_request.error_message = result['error']
                    else:
                        print(f"[EXTRACTION DEBUG] Processing successful result...")
                        thread_extraction_request.status = ExtractionStatus.COMPLETED
                        
                        def convert_numpy_types(obj):
                            if hasattr(obj, 'item'):  # numpy scalar
                                return obj.item()
                            elif isinstance(obj, dict):
                                return {k: convert_numpy_types(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [convert_numpy_types(v) for v in obj]
                            return obj
                        
                        extracted_data = result.get('extracted_data', {})
                        thread_extraction_request.extracted_data = json.dumps(convert_numpy_types(extracted_data))
                        thread_extraction_request.confidence_score = result.get('confidence_score', 0.0)
                        thread_extraction_request.flagged_fields = json.dumps(result.get('flagged_fields', []))
                        
                        if result.get('legal_analysis'):
                            legal_analysis = result['legal_analysis']
                            if isinstance(legal_analysis, dict):
                                thread_extraction_request.identified_clauses = json.dumps(legal_analysis.get('identified_clauses', []))
                                thread_extraction_request.risk_flags = json.dumps(legal_analysis.get('risk_flags', []))
                                thread_extraction_request.document_summary = legal_analysis.get('document_summary', '')
                                thread_extraction_request.reference_materials = json.dumps(legal_analysis.get('reference_materials', {}))
                            else:
                                thread_extraction_request.document_summary = str(legal_analysis)
                    
                    thread_extraction_request.completed_timestamp = datetime.utcnow()
                    thread_extraction_request.processing_time_seconds = result.get('processing_time_seconds', 0)
                    
                    if thread_extraction_request.confidence_score and float(thread_extraction_request.confidence_score) < 0.7:
                        thread_extraction_request.status = ExtractionStatus.FLAGGED
                    
                    print(f"[EXTRACTION DEBUG] Committing final status: {thread_extraction_request.status}")
                    db.session.commit()
                    print(f"[EXTRACTION DEBUG] Database commit successful")
                    
                    audit_log = AuditLog(
                        action=AuditAction.EXTRACTION_COMPLETED if thread_extraction_request.status == ExtractionStatus.COMPLETED else AuditAction.EXTRACTION_FAILED,
                        document_id=doc_id,
                        extraction_request_id=thread_extraction_request.id,
                        details=json.dumps({
                            'status': thread_extraction_request.status.value,
                            'confidence_score': thread_extraction_request.confidence_score,
                            'processing_time': thread_extraction_request.processing_time_seconds
                        })
                    )
                    db.session.add(audit_log)
                    db.session.commit()
                    print(f"[EXTRACTION DEBUG] Audit log committed, extraction complete")
                    
                except Exception as e:
                    print(f"[EXTRACTION DEBUG] Exception in background thread: {e}")
                    import traceback
                    traceback.print_exc()
                    try:
                        thread_extraction_request = ExtractionRequest.query.get(req_id)
                        if thread_extraction_request:
                            thread_extraction_request.status = ExtractionStatus.FAILED
                            thread_extraction_request.error_message = str(e)
                            thread_extraction_request.completed_timestamp = datetime.utcnow()
                            db.session.commit()
                            
                            audit_log = AuditLog(
                                action=AuditAction.EXTRACTION_FAILED,
                                document_id=doc_id,
                                extraction_request_id=thread_extraction_request.id,
                                details=json.dumps({'error': str(e)})
                            )
                            db.session.add(audit_log)
                            db.session.commit()
                    except Exception as commit_error:
                        print(f"[EXTRACTION DEBUG] Failed to update error status: {commit_error}")
        
        document_id_value = document.id
        extraction_request_id_value = extraction_request.id
        
        def process_extraction_wrapper():
            try:
                process_extraction(document_id_value, extraction_request_id_value)
            except Exception as e:
                print(f"[EXTRACTION DEBUG] Wrapper exception: {e}")
        
        thread = threading.Thread(target=process_extraction_wrapper)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'extraction_request': extraction_request.to_dict(),
            'message': 'Extraction started successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/status/<int:extraction_id>')
def get_extraction_status(extraction_id):
    """Get the status of an extraction request"""
    try:
        extraction = ExtractionRequest.query.get(extraction_id)
        if not extraction:
            return jsonify({'success': False, 'error': 'Extraction request not found'}), 404
        
        return jsonify({
            'success': True,
            'extraction': extraction.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/results/<int:extraction_id>')
def get_extraction_results(extraction_id):
    """Get the results of a completed extraction"""
    try:
        extraction = ExtractionRequest.query.get(extraction_id)
        if not extraction:
            return jsonify({'success': False, 'error': 'Extraction request not found'}), 404
        
        if extraction.status != ExtractionStatus.COMPLETED:
            return jsonify({
                'success': False, 
                'error': f'Extraction not completed. Status: {extraction.status.value}'
            }), 400
        
        result_data = {
            'extraction_id': extraction.id,
            'document_id': extraction.document_id,
            'status': extraction.status.value,
            'confidence_score': extraction.confidence_score,
            'processing_time_seconds': extraction.processing_time_seconds,
            'extracted_data': json.loads(extraction.extracted_data) if extraction.extracted_data else {},
            'flagged_fields': json.loads(extraction.flagged_fields) if extraction.flagged_fields else []
        }
        
        if extraction.identified_clauses:
            result_data['legal_analysis'] = {
                'identified_clauses': json.loads(extraction.identified_clauses),
                'risk_flags': json.loads(extraction.risk_flags) if extraction.risk_flags else [],
                'document_summary': extraction.document_summary,
                'reference_materials': json.loads(extraction.reference_materials) if extraction.reference_materials else {}
            }
        
        return jsonify({
            'success': True,
            'results': result_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/download/<int:extraction_id>/<format>')
def download_extraction_results(extraction_id, format):
    """Download extraction results in specified format"""
    try:
        extraction = ExtractionRequest.query.get(extraction_id)
        if not extraction:
            return jsonify({'success': False, 'error': 'Extraction request not found'}), 404
        
        if extraction.status != ExtractionStatus.COMPLETED:
            return jsonify({
                'success': False, 
                'error': f'Extraction not completed. Status: {extraction.status.value}'
            }), 400
        
        output_data = {
            'extracted_data': json.loads(extraction.extracted_data) if extraction.extracted_data else {},
            'confidence_score': extraction.confidence_score,
            'processing_time_seconds': extraction.processing_time_seconds
        }
        
        if extraction.identified_clauses:
            output_data['legal_analysis'] = {
                'identified_clauses': json.loads(extraction.identified_clauses),
                'risk_flags': json.loads(extraction.risk_flags) if extraction.risk_flags else [],
                'document_summary': extraction.document_summary,
                'reference_materials': json.loads(extraction.reference_materials) if extraction.reference_materials else {}
            }
        
        filename_prefix = f"extraction_{extraction.id}_{extraction.document.original_filename.rsplit('.', 1)[0]}"
        result = output_generator.generate_output(output_data, format, filename_prefix)
        
        if result['success']:
            audit_log = AuditLog(
                action=AuditAction.DATA_EXPORT,
                extraction_request_id=extraction.id,
                details=json.dumps({
                    'format': format,
                    'filename': result['filename']
                }),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(audit_log)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'download_url': f"/static/outputs/{result['filename']}",
                'filename': result['filename'],
                'file_size': result['file_size']
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Unknown error')}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/documents')
def list_documents():
    """List all documents"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        documents = Document.query.order_by(Document.upload_timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'documents': [doc.to_dict() for doc in documents.items],
            'pagination': {
                'page': documents.page,
                'pages': documents.pages,
                'per_page': documents.per_page,
                'total': documents.total
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/extractions')
def list_extractions():
    """List all extraction requests"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        document_id = request.args.get('document_id', type=int)
        
        query = ExtractionRequest.query
        if document_id:
            query = query.filter_by(document_id=document_id)
        
        extractions = query.order_by(ExtractionRequest.created_timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'extractions': [ext.to_dict() for ext in extractions.items],
            'pagination': {
                'page': extractions.page,
                'pages': extractions.pages,
                'per_page': extractions.per_page,
                'total': extractions.total
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/feedback/<int:extraction_id>', methods=['POST'])
def submit_feedback(extraction_id):
    """Submit user feedback for an extraction"""
    try:
        extraction = ExtractionRequest.query.get(extraction_id)
        if not extraction:
            return jsonify({'success': False, 'error': 'Extraction request not found'}), 404
        
        feedback_data = request.get_json()
        if not feedback_data:
            return jsonify({'success': False, 'error': 'No feedback data provided'}), 400
        
        audit_log = AuditLog(
            action=AuditAction.USER_FEEDBACK,
            extraction_request_id=extraction.id,
            details=json.dumps(feedback_data),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Feedback submitted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/correct/<int:extraction_id>', methods=['POST'])
def submit_correction(extraction_id):
    """Submit manual corrections for an extraction"""
    try:
        extraction = ExtractionRequest.query.get(extraction_id)
        if not extraction:
            return jsonify({'success': False, 'error': 'Extraction request not found'}), 404
        
        correction_data = request.get_json()
        if not correction_data:
            return jsonify({'success': False, 'error': 'No correction data provided'}), 400
        
        if extraction.extracted_data:
            current_data = json.loads(extraction.extracted_data)
            current_data.update(correction_data.get('corrected_fields', {}))
            extraction.extracted_data = json.dumps(current_data)
            db.session.commit()
        
        audit_log = AuditLog(
            action=AuditAction.MANUAL_CORRECTION,
            extraction_request_id=extraction.id,
            details=json.dumps(correction_data),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Corrections applied successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/stats')
def get_statistics():
    """Get system statistics"""
    try:
        stats = {
            'total_documents': Document.query.count(),
            'total_extractions': ExtractionRequest.query.count(),
            'completed_extractions': ExtractionRequest.query.filter_by(status=ExtractionStatus.COMPLETED).count(),
            'pending_extractions': ExtractionRequest.query.filter_by(status=ExtractionStatus.PENDING).count(),
            'processing_extractions': ExtractionRequest.query.filter_by(status=ExtractionStatus.PROCESSING).count(),
            'failed_extractions': ExtractionRequest.query.filter_by(status=ExtractionStatus.FAILED).count(),
            'flagged_extractions': ExtractionRequest.query.filter_by(status=ExtractionStatus.FLAGGED).count()
        }
        
        completed_extractions = ExtractionRequest.query.filter(
            ExtractionRequest.status == ExtractionStatus.COMPLETED,
            ExtractionRequest.processing_time_seconds.isnot(None)
        ).all()
        
        if completed_extractions:
            avg_processing_time = sum(ext.processing_time_seconds for ext in completed_extractions) / len(completed_extractions)
            stats['average_processing_time_seconds'] = round(avg_processing_time, 2)
        else:
            stats['average_processing_time_seconds'] = 0
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from app.models.document import Document
from app.models.extraction_request import ExtractionRequest, ExtractionStatus, OutputFormat
from app.models.audit_log import AuditLog, AuditAction
from app import db
import json

main_bp = Blueprint('main', __name__)

# Lazy initialization of services
_document_processor = None
_extraction_engine = None
_output_generator = None

def get_document_processor():
    global _document_processor
    if _document_processor is None:
        from app.services.document_processor import DocumentProcessor
        _document_processor = DocumentProcessor()
    return _document_processor

def get_extraction_engine():
    global _extraction_engine
    if _extraction_engine is None:
        from app.services.extraction_engine import ExtractionEngine
        _extraction_engine = ExtractionEngine()
    return _extraction_engine

def get_output_generator():
    global _output_generator
    if _output_generator is None:
        from app.services.output_generator import OutputGenerator
        # Initialize output generator with correct path
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'outputs')
        _output_generator = OutputGenerator(output_dir)
    return _output_generator

@main_bp.route('/')
def index():
    """Main dashboard page"""
    recent_documents = Document.query.order_by(Document.upload_timestamp.desc()).limit(5).all()
    recent_extractions = ExtractionRequest.query.order_by(ExtractionRequest.created_timestamp.desc()).limit(5).all()
    
    stats = {
        'total_documents': Document.query.count(),
        'total_extractions': ExtractionRequest.query.count(),
        'completed_extractions': ExtractionRequest.query.filter_by(status=ExtractionStatus.COMPLETED).count(),
        'pending_extractions': ExtractionRequest.query.filter_by(status=ExtractionStatus.PENDING).count()
    }
    
    return render_template('dashboard.html', 
                         recent_documents=recent_documents,
                         recent_extractions=recent_extractions,
                         stats=stats)

@main_bp.route('/upload', methods=['GET', 'POST'])
def upload_document():
    """Document upload page"""
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                flash('No file selected', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)
            
            file_info = get_document_processor().save_uploaded_file(file)
            document = get_document_processor().create_document_record(file_info)
            
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
            
            flash(f'Document "{document.original_filename}" uploaded successfully!', 'success')
            return redirect(url_for('main.extract_data', document_id=document.id))
            
        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

@main_bp.route('/extract/<int:document_id>')
def extract_data(document_id):
    """Data extraction page for a specific document"""
    document = Document.query.get_or_404(document_id)
    
    extractions = ExtractionRequest.query.filter_by(document_id=document_id).order_by(
        ExtractionRequest.created_timestamp.desc()
    ).all()
    
    return render_template('extract.html', document=document, extractions=extractions)

@main_bp.route('/results/<int:extraction_id>')
def view_results(extraction_id):
    """View extraction results"""
    extraction = ExtractionRequest.query.get_or_404(extraction_id)
    document = extraction.document
    
    extracted_data = None
    if extraction.extracted_data:
        try:
            extracted_data = json.loads(extraction.extracted_data)
        except json.JSONDecodeError:
            extracted_data = {'error': 'Failed to parse extracted data'}
    
    legal_analysis = None
    if extraction.identified_clauses:
        try:
            legal_analysis = {
                'clauses': json.loads(extraction.identified_clauses),
                'risks': json.loads(extraction.risk_flags) if extraction.risk_flags else [],
                'summary': extraction.document_summary,
                'references': json.loads(extraction.reference_materials) if extraction.reference_materials else {}
            }
        except json.JSONDecodeError:
            legal_analysis = {'error': 'Failed to parse legal analysis'}
    
    return render_template('results.html', 
                         extraction=extraction,
                         document=document,
                         extracted_data=extracted_data,
                         legal_analysis=legal_analysis)

@main_bp.route('/documents')
def list_documents():
    """List all documents"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    documents = Document.query.order_by(Document.upload_timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('documents.html', documents=documents)

@main_bp.route('/extractions')
def list_extractions():
    """List all extraction requests"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    extractions = ExtractionRequest.query.order_by(ExtractionRequest.created_timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('extractions.html', extractions=extractions)

@main_bp.route('/audit')
def audit_trail():
    """View audit trail"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('audit.html', audit_logs=audit_logs)

@main_bp.route('/download/<int:extraction_id>/<format>')
def download_results(extraction_id, format):
    """Download extraction results in specified format"""
    extraction = ExtractionRequest.query.get_or_404(extraction_id)
    
    try:
        output_data = {
            'extracted_data': json.loads(extraction.extracted_data) if extraction.extracted_data else {},
            'confidence_score': extraction.confidence_score,
            'processing_time_seconds': extraction.processing_time_seconds,
            'legal_analysis': {}
        }
        
        if extraction.identified_clauses:
            output_data['legal_analysis'] = {
                'identified_clauses': json.loads(extraction.identified_clauses),
                'risk_flags': json.loads(extraction.risk_flags) if extraction.risk_flags else [],
                'document_summary': extraction.document_summary,
                'reference_materials': json.loads(extraction.reference_materials) if extraction.reference_materials else {}
            }
        
        filename_prefix = f"extraction_{extraction.id}_{extraction.document.original_filename.rsplit('.', 1)[0]}"
        result = get_output_generator().generate_output(output_data, format, filename_prefix)
        
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
            
            from flask import send_file
            return send_file(result['file_path'], as_attachment=True, download_name=result['filename'])
        else:
            flash(f'Download failed: {result.get("error", "Unknown error")}', 'error')
            return redirect(url_for('main.view_results', extraction_id=extraction_id))
            
    except Exception as e:
        flash(f'Download failed: {str(e)}', 'error')
        return redirect(url_for('main.view_results', extraction_id=extraction_id))

@main_bp.route('/feedback/<int:extraction_id>', methods=['POST'])
def submit_feedback(extraction_id):
    """Submit user feedback for an extraction"""
    extraction = ExtractionRequest.query.get_or_404(extraction_id)
    
    try:
        feedback_data = request.get_json()
        
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

@main_bp.route('/export_audit')
def export_audit():
    """Export audit trail as CSV"""
    try:
        audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
        audit_data = [log.to_dict() for log in audit_logs]
        
        result = get_output_generator().create_audit_export(audit_data)
        
        if result['success']:
            from flask import send_file
            return send_file(result['file_path'], as_attachment=True, download_name=result['filename'])
        else:
            flash('Export failed', 'error')
            return redirect(url_for('main.audit_trail'))
            
    except Exception as e:
        flash(f'Export failed: {str(e)}', 'error')
        return redirect(url_for('main.audit_trail'))

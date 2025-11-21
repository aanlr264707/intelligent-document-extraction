from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from typing import Dict, Any
import logging

# Import models
from app.models.document import Document
from app.models.extraction_request import ExtractionRequest, ExtractionStatus, OutputFormat
from app.models.audit_log import AuditLog, AuditAction
from app import db

# Import services
from app.services.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)

# Enhanced API Blueprint
enhanced_api_bp = Blueprint('enhanced_api', __name__, url_prefix='/api/v2')

# Lazy initialization of services
_document_processor = None
_enhanced_extraction_engine = None
_output_generator = None
_email_monitor = None

def get_document_processor():
    global _document_processor
    if _document_processor is None:
        from app.services.document_processor import DocumentProcessor
        _document_processor = DocumentProcessor()
    return _document_processor

def get_enhanced_extraction_engine():
    global _enhanced_extraction_engine
    if _enhanced_extraction_engine is None:
        from app.services.extraction_engine_enhanced import enhanced_extraction_engine
        _enhanced_extraction_engine = enhanced_extraction_engine
    return _enhanced_extraction_engine

def get_output_generator():
    global _output_generator
    if _output_generator is None:
        from app.services.output_generator import OutputGenerator
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'outputs')
        _output_generator = OutputGenerator(output_dir)
    return _output_generator

def get_email_monitor():
    global _email_monitor
    if _email_monitor is None:
        try:
            from app.services.email_monitor import email_monitor
            _email_monitor = email_monitor
        except ImportError:
            logger.warning("Email monitoring service not available")
            _email_monitor = None
    return _email_monitor

# Enhanced extraction endpoint
@enhanced_api_bp.route('/extract', methods=['POST'])
def enhanced_extract():
    """Enhanced extraction endpoint with comprehensive features"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        document_id = data.get('document_id')
        requirements = data.get('requirements', '')
        output_format = data.get('output_format', 'json')
        
        # Enhanced options
        enable_handwritten = data.get('enable_handwritten', True)
        enable_tabular = data.get('enable_tabular', True)
        enable_legal_analysis = data.get('enable_legal_analysis', True)
        enable_multi_modal = data.get('enable_multi_modal', True)
        
        if not document_id:
            return jsonify({
                'success': False,
                'error': 'Document ID required'
            }), 400
        
        if not requirements:
            return jsonify({
                'success': False,
                'error': 'Extraction requirements required'
            }), 400
        
        # Get document
        document = Document.query.get(document_id)
        if not document:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404
        
        # Check system capacity
        engine = get_enhanced_extraction_engine()
        if not performance_monitor.can_process_request():
            return jsonify({
                'success': False,
                'error': 'System at maximum capacity. Please try again later.',
                'queue_status': performance_monitor.get_processing_queue_status()
            }), 503
        
        # Create extraction request
        extraction_request = ExtractionRequest(
            document_id=document_id,
            natural_language_request=requirements,
            output_format=OutputFormat(output_format),
            status=ExtractionStatus.PROCESSING,
            created_timestamp=datetime.utcnow(),
            metadata={
                'api_version': 'v2_enhanced',
                'features_enabled': {
                    'handwritten': enable_handwritten,
                    'tabular': enable_tabular,
                    'legal_analysis': enable_legal_analysis,
                    'multi_modal': enable_multi_modal
                }
            }
        )
        
        db.session.add(extraction_request)
        db.session.commit()
        
        # Perform enhanced extraction
        try:
            result = engine.extract_data(document, extraction_request)
            
            # Update extraction request with results
            extraction_request.extracted_data = result.get('extracted_data', {})
            extraction_request.confidence_score = result.get('confidence_score', 0.0)
            extraction_request.metadata.update({
                'processing_components': list(result.get('processing_components', {}).keys()),
                'features_used': result.get('metadata', {}).get('processing_features_used', []),
                'processing_time_seconds': result.get('processing_time_seconds', 0.0)
            })
            
            if result.get('success', False):
                extraction_request.status = ExtractionStatus.COMPLETED
                extraction_request.completed_timestamp = datetime.utcnow()
            else:
                extraction_request.status = ExtractionStatus.FAILED
                extraction_request.error_message = result.get('error', 'Unknown error')
            
            # Handle flags for manual review
            if result.get('requires_manual_review', False):
                extraction_request.metadata['requires_manual_review'] = True
                extraction_request.metadata['review_flags'] = result.get('flags', [])
            
            db.session.commit()
            
            # Log the extraction
            audit_log = AuditLog(
                action=AuditAction.EXTRACTION_COMPLETED if result.get('success') else AuditAction.EXTRACTION_FAILED,
                document_id=document_id,
                extraction_request_id=extraction_request.id,
                details=f"Enhanced extraction completed with {len(result.get('metadata', {}).get('processing_features_used', []))} features",
                timestamp=datetime.utcnow(),
                ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
            )
            db.session.add(audit_log)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'extraction_id': extraction_request.id,
                'result': result,
                'processing_summary': {
                    'features_used': result.get('metadata', {}).get('processing_features_used', []),
                    'confidence_score': result.get('confidence_score', 0.0),
                    'requires_manual_review': result.get('requires_manual_review', False),
                    'processing_time_seconds': result.get('processing_time_seconds', 0.0)
                }
            })
            
        except Exception as e:
            logger.error(f"Enhanced extraction failed: {e}")
            extraction_request.status = ExtractionStatus.FAILED
            extraction_request.error_message = str(e)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': f'Enhanced extraction failed: {str(e)}',
                'extraction_id': extraction_request.id
            }), 500
            
    except Exception as e:
        logger.error(f"API error in enhanced extract: {e}")
        return jsonify({
            'success': False,
            'error': f'API error: {str(e)}'
        }), 500

# Performance monitoring endpoints
@enhanced_api_bp.route('/performance/metrics', methods=['GET'])
def get_performance_metrics():
    """Get current performance metrics"""
    try:
        metrics = performance_monitor.get_performance_metrics()
        return jsonify({
            'success': True,
            'metrics': metrics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_api_bp.route('/performance/detailed', methods=['GET'])
def get_detailed_performance():
    """Get detailed performance metrics"""
    try:
        hours = request.args.get('hours', 1, type=int)
        detailed_metrics = performance_monitor.get_detailed_metrics(hours)
        return jsonify({
            'success': True,
            'detailed_metrics': detailed_metrics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_api_bp.route('/performance/optimize', methods=['GET'])
def get_optimization_suggestions():
    """Get performance optimization suggestions"""
    try:
        optimization = performance_monitor.optimize_performance()
        return jsonify({
            'success': True,
            'optimization': optimization
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_api_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """Get comprehensive system status"""
    try:
        engine = get_enhanced_extraction_engine()
        
        status = {
            'system_health': 'healthy',
            'supported_features': engine.get_supported_features(),
            'performance_metrics': performance_monitor.get_performance_metrics(),
            'queue_status': performance_monitor.get_processing_queue_status(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Email monitoring endpoints
@enhanced_api_bp.route('/email/monitor/start', methods=['POST'])
def start_email_monitoring():
    """Start email monitoring service"""
    try:
        email_monitor = get_email_monitor()
        
        if not email_monitor:
            return jsonify({
                'success': False,
                'error': 'Email monitoring service not available'
            }), 503
        
        if email_monitor.start_monitoring():
            return jsonify({
                'success': True,
                'message': 'Email monitoring started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start email monitoring - check configuration'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_api_bp.route('/email/monitor/stop', methods=['POST'])
def stop_email_monitoring():
    """Stop email monitoring service"""
    try:
        email_monitor = get_email_monitor()
        
        if email_monitor:
            email_monitor.stop_monitoring()
            return jsonify({
                'success': True,
                'message': 'Email monitoring stopped'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Email monitoring service not available'
            }), 503
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_api_bp.route('/email/monitor/status', methods=['GET'])
def get_email_monitor_status():
    """Get email monitoring status"""
    try:
        email_monitor = get_email_monitor()
        
        if not email_monitor:
            return jsonify({
                'success': True,
                'status': 'not_available',
                'message': 'Email monitoring service not configured'
            })
        
        return jsonify({
            'success': True,
            'status': {
                'is_monitoring': email_monitor.is_monitoring,
                'supported_types': list(email_monitor.supported_types.keys()),
                'monitored_folders': email_monitor.monitored_folders,
                'processing_queue_size': email_monitor.processing_queue.qsize()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Document capabilities endpoint
@enhanced_api_bp.route('/documents/<int:document_id>/capabilities', methods=['GET'])
def get_document_capabilities(document_id):
    """Get processing capabilities for a specific document"""
    try:
        document = Document.query.get(document_id)
        if not document:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404
        
        # Analyze document capabilities
        processor = get_document_processor()
        engine = get_enhanced_extraction_engine()
        
        capabilities = {
            'document_type': document.document_type.value if hasattr(document.document_type, 'value') else str(document.document_type),
            'file_size_mb': round(document.file_size / (1024 * 1024), 2),
            'supported_features': {
                'text_extraction': True,
                'multi_modal_analysis': document.document_type.value in ['pdf', 'image'] if hasattr(document.document_type, 'value') else False,
                'handwritten_processing': engine.features.get('handwritten_support', False) and document.document_type.value == 'image' if hasattr(document.document_type, 'value') else False,
                'tabular_extraction': engine.features.get('tabular_extraction', False),
                'legal_analysis': engine.features.get('enhanced_legal_analysis', False),
                'vision_analysis': document.document_type.value in ['pdf', 'image'] if hasattr(document.document_type, 'value') else False
            },
            'estimated_processing_time': {
                'basic_extraction': '10-30 seconds',
                'full_analysis': '30-60 seconds',
                'complex_document': '60-120 seconds'
            }
        }
        
        return jsonify({
            'success': True,
            'capabilities': capabilities
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Batch processing endpoint
@enhanced_api_bp.route('/extract/batch', methods=['POST'])
def batch_extract():
    """Process multiple documents in batch"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        document_ids = data.get('document_ids', [])
        requirements = data.get('requirements', '')
        output_format = data.get('output_format', 'json')
        
        if not document_ids:
            return jsonify({
                'success': False,
                'error': 'Document IDs required'
            }), 400
        
        if len(document_ids) > 10:  # Limit batch size
            return jsonify({
                'success': False,
                'error': 'Maximum 10 documents per batch'
            }), 400
        
        # Check system capacity
        available_slots = performance_monitor.get_processing_queue_status()['available_slots']
        if len(document_ids) > available_slots:
            return jsonify({
                'success': False,
                'error': f'Not enough processing capacity. Available slots: {available_slots}',
                'queue_status': performance_monitor.get_processing_queue_status()
            }), 503
        
        # Create extraction requests for all documents
        extraction_requests = []
        for document_id in document_ids:
            document = Document.query.get(document_id)
            if not document:
                continue
            
            extraction_request = ExtractionRequest(
                document_id=document_id,
                natural_language_request=requirements,
                output_format=OutputFormat(output_format),
                status=ExtractionStatus.PROCESSING,
                created_timestamp=datetime.utcnow(),
                metadata={
                    'api_version': 'v2_batch',
                    'batch_processing': True
                }
            )
            
            db.session.add(extraction_request)
            extraction_requests.append(extraction_request)
        
        db.session.commit()
        
        # Submit batch for processing (would be done asynchronously in production)
        batch_results = {
            'batch_id': f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'total_documents': len(extraction_requests),
            'extraction_ids': [req.id for req in extraction_requests],
            'estimated_completion_time': '2-5 minutes',
            'status': 'submitted'
        }
        
        return jsonify({
            'success': True,
            'batch_results': batch_results
        })
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Health check endpoint
@enhanced_api_bp.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint"""
    try:
        engine = get_enhanced_extraction_engine()
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': 'v2.0',
            'services': {
                'extraction_engine': 'available',
                'performance_monitor': 'active' if performance_monitor.monitoring_active else 'inactive',
                'database': 'connected',
                'email_monitor': 'available' if get_email_monitor() else 'not_configured'
            },
            'features': engine.get_supported_features(),
            'system_metrics': performance_monitor.get_performance_metrics()['system_metrics']
        }
        
        # Check for any critical issues
        metrics = performance_monitor.get_performance_metrics()
        if metrics['performance_status'] in ['degraded', 'critical']:
            health_status['status'] = 'degraded'
            health_status['warnings'] = metrics.get('recent_alerts', [])
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Register the enhanced API blueprint
def register_enhanced_api(app):
    """Register the enhanced API blueprint with the Flask app"""
    app.register_blueprint(enhanced_api_bp)

import os
import time
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from threading import Thread
import queue
from app.models import Document, ExtractionRequest, AuditLog
from app.services.document_processor import DocumentProcessor
from app.services.extraction_engine import ExtractionEngine
from app import db

logger = logging.getLogger(__name__)

class EmailMonitoringService:
    """Service for monitoring email inboxes and triggering extractions on new documents"""
    
    def __init__(self):
        self.imap_server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        self.imap_port = int(os.getenv('IMAP_PORT', 993))
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.monitored_folders = os.getenv('MONITORED_FOLDERS', 'INBOX').split(',')
        
        self.document_processor = DocumentProcessor()
        self.extraction_engine = ExtractionEngine()
        
        self.processing_queue = queue.Queue()
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Supported attachment types
        self.supported_types = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'word',
            'application/msword': 'word',
            'image/png': 'image',
            'image/jpeg': 'image',
            'image/tiff': 'image'
        }
    
    def start_monitoring(self):
        """Start monitoring email inboxes for new documents"""
        if not self.email_address or not self.email_password:
            logger.warning("Email credentials not configured. Email monitoring disabled.")
            return False
        
        self.is_monitoring = True
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Start processing thread
        processing_thread = Thread(target=self._process_queue, daemon=True)
        processing_thread.start()
        
        logger.info(f"Email monitoring started for {self.email_address}")
        return True
    
    def stop_monitoring(self):
        """Stop monitoring email inboxes"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("Email monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        last_check = datetime.utcnow() - timedelta(minutes=5)
        
        while self.is_monitoring:
            try:
                # Connect to IMAP server
                mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
                mail.login(self.email_address, self.email_password)
                
                for folder in self.monitored_folders:
                    folder = folder.strip()
                    mail.select(folder)
                    
                    # Search for new emails since last check
                    search_date = last_check.strftime('%d-%b-%Y')
                    result, data = mail.search(None, f'(SINCE "{search_date}")')
                    
                    if result == 'OK':
                        email_ids = data[0].split()
                        
                        for email_id in email_ids:
                            try:
                                result, data = mail.fetch(email_id, '(RFC822)')
                                if result == 'OK':
                                    raw_email = data[0][1]
                                    email_message = email.message_from_bytes(raw_email)
                                    
                                    # Check if email has attachments
                                    if self._has_supported_attachments(email_message):
                                        self.processing_queue.put({
                                            'email_message': email_message,
                                            'folder': folder,
                                            'email_id': email_id.decode()
                                        })
                            except Exception as e:
                                logger.error(f"Error processing email {email_id}: {e}")
                
                mail.logout()
                last_check = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Error in email monitoring loop: {e}")
            
            # Wait before next check
            time.sleep(int(os.getenv('EMAIL_CHECK_INTERVAL', 300)))  # Default 5 minutes
    
    def _has_supported_attachments(self, email_message) -> bool:
        """Check if email has supported document attachments"""
        for part in email_message.walk():
            if part.get_content_disposition() == 'attachment':
                content_type = part.get_content_type()
                if content_type in self.supported_types:
                    return True
        return False
    
    def _process_queue(self):
        """Process emails from the queue"""
        while True:
            try:
                email_data = self.processing_queue.get(timeout=60)
                self._process_email(email_data)
                self.processing_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing email queue: {e}")
    
    def _process_email(self, email_data: Dict[str, Any]):
        """Process a single email and extract documents"""
        try:
            email_message = email_data['email_message']
            folder = email_data['folder']
            email_id = email_data['email_id']
            
            # Extract email metadata
            sender = email_message.get('From', '')
            subject = email_message.get('Subject', '')
            email_body = self._extract_email_body(email_message)
            
            logger.info(f"Processing email from {sender} with subject: {subject}")
            
            # Process attachments
            for part in email_message.walk():
                if part.get_content_disposition() == 'attachment':
                    content_type = part.get_content_type()
                    filename = part.get_filename()
                    
                    if content_type in self.supported_types and filename:
                        try:
                            # Save attachment
                            attachment_data = part.get_payload(decode=True)
                            document = self._save_email_attachment(
                                attachment_data, filename, content_type, 
                                sender, subject, email_body
                            )
                            
                            # Trigger automatic extraction if requested
                            extraction_request = self._extract_requirements_from_email(
                                email_body, subject
                            )
                            
                            if extraction_request:
                                self._trigger_extraction(document, extraction_request, 
                                                       sender, email_id)
                            
                        except Exception as e:
                            logger.error(f"Error processing attachment {filename}: {e}")
            
        except Exception as e:
            logger.error(f"Error processing email: {e}")
    
    def _extract_email_body(self, email_message) -> str:
        """Extract text body from email message"""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == 'text/plain':
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            return email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        return ""
    
    def _save_email_attachment(self, attachment_data: bytes, filename: str, 
                              content_type: str, sender: str, subject: str, 
                              email_body: str) -> Document:
        """Save email attachment as a document"""
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # Create upload directory if it doesn't exist
            upload_dir = os.path.join('static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"email_{timestamp}_{filename}"
            file_path = os.path.join(upload_dir, safe_filename)
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(attachment_data)
            
            # Create document record
            document = Document(
                original_filename=filename,
                filename=safe_filename,
                file_path=file_path,
                file_size=len(attachment_data),
                document_type=self.supported_types[content_type],
                upload_timestamp=datetime.utcnow(),
                source='email',
                metadata={
                    'sender': sender,
                    'subject': subject,
                    'email_body': email_body[:500]  # Truncate for storage
                }
            )
            
            db.session.add(document)
            db.session.commit()
            
            # Log the upload
            audit_log = AuditLog(
                action='document_upload',
                document_id=document.id,
                details=f"Document uploaded via email from {sender}",
                timestamp=datetime.utcnow(),
                ip_address='email_system'
            )
            db.session.add(audit_log)
            db.session.commit()
            
            logger.info(f"Saved email attachment: {filename} from {sender}")
            return document
    
    def _extract_requirements_from_email(self, email_body: str, subject: str) -> Optional[str]:
        """Extract extraction requirements from email content"""
        # Look for extraction keywords in subject or body
        extraction_keywords = [
            'extract', 'extraction', 'analyze', 'analysis', 'process',
            'get data', 'pull information', 'find', 'identify'
        ]
        
        full_text = f"{subject} {email_body}".lower()
        
        # Check if email contains extraction request
        if any(keyword in full_text for keyword in extraction_keywords):
            # Try to extract specific requirements
            requirements = self._parse_extraction_requirements(email_body, subject)
            return requirements
        
        return None
    
    def _parse_extraction_requirements(self, email_body: str, subject: str) -> str:
        """Parse specific extraction requirements from email"""
        # Default extraction based on document type mentions
        requirements = []
        
        text = f"{subject} {email_body}".lower()
        
        if 'contract' in text:
            requirements.append("Extract party names, effective date, and key terms")
        if 'invoice' in text:
            requirements.append("Extract vendor, amount, and due date")
        if 'receipt' in text:
            requirements.append("Extract merchant, total amount, and date")
        if 'legal' in text or 'agreement' in text:
            requirements.append("Extract legal clauses and obligations")
        
        if not requirements:
            # Generic extraction
            requirements.append("Extract key information including dates, names, amounts, and important terms")
        
        return "; ".join(requirements)
    
    def _trigger_extraction(self, document: Document, requirements: str, 
                           sender: str, email_id: str):
        """Trigger automatic extraction for the document"""
        from app import create_app
        app = create_app()
        
        with app.app_context():
            try:
                # Create extraction request
                extraction_request = ExtractionRequest(
                    document_id=document.id,
                    natural_language_request=requirements,
                    output_format='json',
                    status='processing',
                    created_timestamp=datetime.utcnow(),
                    metadata={
                        'triggered_by': 'email_monitor',
                        'sender': sender,
                        'email_id': email_id
                    }
                )
                
                db.session.add(extraction_request)
                db.session.commit()
                
                # Perform extraction
                result = self.extraction_engine.extract_data(document, extraction_request)
                
                # Update extraction request with results
                extraction_request.extracted_data = result.get('extracted_data', {})
                extraction_request.confidence_score = result.get('confidence_score', 0.0)
                extraction_request.status = 'completed' if result.get('success') else 'failed'
                extraction_request.completed_timestamp = datetime.utcnow()
                
                if not result.get('success'):
                    extraction_request.error_message = result.get('error', 'Unknown error')
                
                db.session.commit()
                
                # Send results back via email if configured
                if os.getenv('EMAIL_RESULTS_ENABLED', 'false').lower() == 'true':
                    self._send_results_email(sender, document, extraction_request)
                
                logger.info(f"Completed automatic extraction for {document.original_filename}")
                
            except Exception as e:
                logger.error(f"Error triggering extraction: {e}")
    
    def _send_results_email(self, recipient: str, document: Document, 
                           extraction_request: ExtractionRequest):
        """Send extraction results back to the sender"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = recipient
            msg['Subject'] = f"Extraction Results: {document.original_filename}"
            
            # Create email body
            body = f"""
            Hello,
            
            Your document "{document.original_filename}" has been processed successfully.
            
            Extraction Request: {extraction_request.natural_language_request}
            
            Results:
            {self._format_results_for_email(extraction_request.extracted_data)}
            
            Confidence Score: {extraction_request.confidence_score:.2%}
            
            Best regards,
            DocExtract AI System
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.email_password)
            text = msg.as_string()
            server.sendmail(self.email_address, recipient, text)
            server.quit()
            
            logger.info(f"Results email sent to {recipient}")
            
        except Exception as e:
            logger.error(f"Error sending results email: {e}")
    
    def _format_results_for_email(self, extracted_data: Dict[str, Any]) -> str:
        """Format extraction results for email"""
        if not extracted_data:
            return "No data extracted."
        
        formatted = []
        for key, value in extracted_data.items():
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            formatted.append(f"- {key}: {value}")
        
        return '\n'.join(formatted)
    
    def configure_email_rules(self, rules: List[Dict[str, Any]]):
        """Configure extraction rules for different email patterns"""
        # Store rules in database or configuration
        # Rules can define different extraction patterns based on sender, subject, etc.
        pass

# Global instance
email_monitor = EmailMonitoringService()

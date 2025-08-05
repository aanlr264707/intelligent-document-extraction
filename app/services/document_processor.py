import os
import magic
from werkzeug.utils import secure_filename
from PIL import Image
import PyPDF2
from docx import Document as DocxDocument
import pytesseract
from app.models.document import Document, DocumentType
from app import db
import uuid

class DocumentProcessor:
    """Handles document upload, validation, and preprocessing"""
    
    ALLOWED_EXTENSIONS = {
        'pdf': DocumentType.PDF,
        'doc': DocumentType.WORD,
        'docx': DocumentType.WORD,
        'png': DocumentType.IMAGE,
        'jpg': DocumentType.IMAGE,
        'jpeg': DocumentType.IMAGE,
        'tiff': DocumentType.IMAGE,
        'bmp': DocumentType.IMAGE
    }
    
    def __init__(self, upload_folder='static/uploads'):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)
    
    def validate_document(self, file_info):
        """Validate document file information"""
        filename = file_info.get('filename', '')
        content_type = file_info.get('content_type', '')
        size = file_info.get('size', 0)
        
        # Basic validation
        if not filename:
            return {'valid': False, 'error': 'No filename provided'}
        
        if not self.is_allowed_file(filename):
            return {'valid': False, 'error': 'File type not allowed'}
        
        if size > 50 * 1024 * 1024:  # 50MB limit
            return {'valid': False, 'error': 'File too large'}
        
        return {'valid': True, 'message': 'File validation passed'}
    
    def is_allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def detect_document_type(self, file_path):
        """Detect document type using file magic"""
        mime_type = magic.from_file(file_path, mime=True)
        extension = file_path.rsplit('.', 1)[1].lower()
        
        if extension in self.ALLOWED_EXTENSIONS:
            return self.ALLOWED_EXTENSIONS[extension], mime_type
        
        if 'pdf' in mime_type:
            return DocumentType.PDF, mime_type
        elif 'word' in mime_type or 'officedocument' in mime_type:
            return DocumentType.WORD, mime_type
        elif 'image' in mime_type:
            return DocumentType.IMAGE, mime_type
        else:
            return DocumentType.OTHER, mime_type
    
    def save_uploaded_file(self, file):
        """Save uploaded file and return file info"""
        if not file or not self.is_allowed_file(file.filename):
            raise ValueError("Invalid file type")
        
        original_filename = file.filename
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        file_path = os.path.join(self.upload_folder, unique_filename)
        file.save(file_path)
        
        file_size = os.path.getsize(file_path)
        document_type, mime_type = self.detect_document_type(file_path)
        
        return {
            'filename': unique_filename,
            'original_filename': original_filename,
            'file_path': file_path,
            'file_size': file_size,
            'document_type': document_type,
            'mime_type': mime_type
        }
    
    def create_document_record(self, file_info):
        """Create database record for uploaded document"""
        document = Document(
            filename=file_info['filename'],
            original_filename=file_info['original_filename'],
            file_path=file_info['file_path'],
            file_size=file_info['file_size'],
            document_type=file_info['document_type'],
            mime_type=file_info['mime_type']
        )
        
        db.session.add(document)
        db.session.commit()
        
        return document
    
    def extract_text_content(self, document):
        """Extract raw text content from document"""
        try:
            if document.document_type == DocumentType.PDF:
                return self._extract_pdf_text(document.file_path)
            elif document.document_type == DocumentType.WORD:
                return self._extract_word_text(document.file_path)
            elif document.document_type == DocumentType.IMAGE:
                return self._extract_image_text(document.file_path)
            else:
                raise ValueError(f"Unsupported document type: {document.document_type}")
        except Exception as e:
            raise Exception(f"Failed to extract text from document: {str(e)}")
    
    def _extract_pdf_text(self, file_path):
        """Extract text from PDF file"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    def _extract_word_text(self, file_path):
        """Extract text from Word document"""
        doc = DocxDocument(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text += cell.text + "\t"
                text += "\n"
        
        return text
    
    def _extract_image_text(self, file_path):
        """Extract text from image using OCR"""
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text
    
    def is_handwritten_document(self, document):
        """Detect if document contains handwritten content"""
        if document.document_type == DocumentType.IMAGE:
            return True
        return False

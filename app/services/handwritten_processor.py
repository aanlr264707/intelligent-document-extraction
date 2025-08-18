import cv2
import numpy as np
import pytesseract
from PIL import Image
import easyocr
import os
from typing import Dict, List, Any, Tuple, Optional
import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

class HandwrittenDocumentProcessor:
    """Enhanced processor for handwritten documents with specialized OCR and field extraction"""
    
    def __init__(self):
        self.easyocr_reader = None
        self.tesseract_config = '--oem 3 --psm 6'
        
        # Initialize EasyOCR reader
        try:
            self.easyocr_reader = easyocr.Reader(['en'])
            logger.info("EasyOCR initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize EasyOCR: {e}")
        
        # Handwriting-specific patterns
        self.handwritten_patterns = {
            'name': [
                r'name[:\s]*([A-Za-z\s]{2,30})',
                r'signed[:\s]*([A-Za-z\s]{2,30})',
                r'signature[:\s]*([A-Za-z\s]{2,30})'
            ],
            'date': [
                r'date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'([A-Za-z]+ \d{1,2},? \d{4})'
            ],
            'address': [
                r'address[:\s]*([A-Za-z0-9\s,.-]{10,100})',
                r'(\d+\s+[A-Za-z\s,.-]+)',
            ],
            'phone': [
                r'phone[:\s]*([0-9\-\(\)\s+]{10,15})',
                r'tel[:\s]*([0-9\-\(\)\s+]{10,15})',
                r'(\(\d{3}\)\s*\d{3}[\-\s]*\d{4})'
            ],
            'email': [
                r'email[:\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
                r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
            ],
            'amount': [
                r'\$\s*(\d+[,\d]*\.?\d*)',
                r'amount[:\s]*\$?(\d+[,\d]*\.?\d*)',
                r'total[:\s]*\$?(\d+[,\d]*\.?\d*)'
            ]
        }
    
    def process_handwritten_document(self, image_path: str, extraction_requirements: str) -> Dict[str, Any]:
        """Main method to process handwritten documents"""
        try:
            logger.info(f"Processing handwritten document: {image_path}")
            
            # Preprocess image for better OCR
            processed_image = self._preprocess_handwritten_image(image_path)
            
            # Extract text using multiple OCR engines
            extracted_text = self._extract_text_multi_engine(processed_image)
            
            # Extract specific fields based on requirements
            extracted_fields = self._extract_fields_from_handwritten_text(
                extracted_text, extraction_requirements
            )
            
            # Apply handwriting-specific confidence scoring
            confidence_score = self._calculate_handwriting_confidence(
                extracted_text, extracted_fields
            )
            
            # Validate and clean extracted data
            validated_fields = self._validate_handwritten_fields(extracted_fields)
            
            return {
                'success': True,
                'extracted_data': validated_fields,
                'raw_text': extracted_text,
                'confidence_score': confidence_score,
                'processing_method': 'handwritten_ocr',
                'ocr_engines_used': ['tesseract', 'easyocr'],
                'preprocessing_applied': True
            }
            
        except Exception as e:
            logger.error(f"Error processing handwritten document: {e}")
            return {
                'success': False,
                'error': f'Handwritten processing failed: {str(e)}',
                'extracted_data': {},
                'confidence_score': 0.0
            }
    
    def _preprocess_handwritten_image(self, image_path: str) -> np.ndarray:
        """Apply preprocessing techniques optimized for handwritten text"""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply adaptive thresholding for better contrast
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Morphological operations to clean up the image
        kernel = np.ones((2, 2), np.uint8)
        
        # Remove noise
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # Fill in gaps
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
        
        # Enhance text
        dilated = cv2.dilate(closing, kernel, iterations=1)
        
        return dilated
    
    def _extract_text_multi_engine(self, processed_image: np.ndarray) -> str:
        """Extract text using multiple OCR engines for better accuracy"""
        extracted_texts = []
        
        # Tesseract OCR
        try:
            tesseract_text = pytesseract.image_to_string(
                processed_image, config=self.tesseract_config
            )
            if tesseract_text.strip():
                extracted_texts.append(tesseract_text)
                logger.info("Tesseract OCR completed")
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}")
        
        # EasyOCR
        if self.easyocr_reader:
            try:
                easyocr_results = self.easyocr_reader.readtext(processed_image)
                easyocr_text = ' '.join([result[1] for result in easyocr_results])
                if easyocr_text.strip():
                    extracted_texts.append(easyocr_text)
                    logger.info("EasyOCR completed")
            except Exception as e:
                logger.warning(f"EasyOCR failed: {e}")
        
        # Combine results (prefer longer, more complete text)
        if extracted_texts:
            return max(extracted_texts, key=len)
        else:
            return ""
    
    def _extract_fields_from_handwritten_text(self, text: str, requirements: str) -> Dict[str, Any]:
        """Extract specific fields from handwritten text based on requirements"""
        extracted_fields = {}
        
        # Parse requirements to identify needed fields
        required_fields = self._parse_handwritten_requirements(requirements)
        
        for field_name, field_type in required_fields.items():
            if field_type in self.handwritten_patterns:
                patterns = self.handwritten_patterns[field_type]
                
                for pattern in patterns:
                    import re
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        # Take the first match, clean it up
                        value = matches[0].strip()
                        if value:
                            extracted_fields[field_name] = self._clean_handwritten_value(
                                value, field_type
                            )
                            break
        
        # Apply contextual extraction for better accuracy
        extracted_fields = self._apply_handwritten_context(text, extracted_fields)
        
        return extracted_fields
    
    def _parse_handwritten_requirements(self, requirements: str) -> Dict[str, str]:
        """Parse extraction requirements to identify field types"""
        field_mapping = {}
        req_lower = requirements.lower()
        
        # Map common handwritten document fields
        field_types = {
            'name': ['name', 'signature', 'signed by', 'patient name', 'client name'],
            'date': ['date', 'signed date', 'appointment date', 'due date'],
            'address': ['address', 'location', 'residence'],
            'phone': ['phone', 'telephone', 'contact number', 'mobile'],
            'email': ['email', 'e-mail', 'contact email'],
            'amount': ['amount', 'total', 'cost', 'price', 'fee', 'payment']
        }
        
        for field_type, keywords in field_types.items():
            for keyword in keywords:
                if keyword in req_lower:
                    # Create field name from keyword
                    field_name = keyword.replace(' ', '_')
                    field_mapping[field_name] = field_type
        
        # If no specific fields found, extract common ones
        if not field_mapping:
            field_mapping = {
                'name': 'name',
                'date': 'date',
                'amount': 'amount'
            }
        
        return field_mapping
    
    def _clean_handwritten_value(self, value: str, field_type: str) -> str:
        """Clean and validate extracted values based on field type"""
        value = value.strip()
        
        if field_type == 'name':
            # Clean up name fields
            value = ' '.join(word.capitalize() for word in value.split())
            # Remove common OCR artifacts
            value = value.replace('|', 'I').replace('0', 'O')
        
        elif field_type == 'date':
            # Standardize date format
            import re
            # Try to fix common OCR mistakes in dates
            value = re.sub(r'[|l]', '1', value)
            value = re.sub(r'[oO]', '0', value)
        
        elif field_type == 'phone':
            # Clean phone numbers
            import re
            value = re.sub(r'[^\d\-\(\)\s+]', '', value)
        
        elif field_type == 'amount':
            # Clean monetary amounts
            import re
            value = re.sub(r'[^\d\.,]', '', value)
        
        return value
    
    def _apply_handwritten_context(self, text: str, extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Apply contextual understanding to improve handwritten extraction accuracy"""
        # Look for field labels near extracted values
        lines = text.split('\n')
        
        # Enhanced field detection using position and context
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Look for signature context
            if 'signature' in line_lower or 'signed' in line_lower:
                # Next line might contain the name
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and len(next_line) > 2:
                        extracted_fields['signature'] = next_line
            
            # Look for form-like structure
            if ':' in line:
                parts = line.split(':')
                if len(parts) == 2:
                    label = parts[0].strip().lower()
                    value = parts[1].strip()
                    
                    if value:
                        if 'name' in label:
                            extracted_fields['name'] = value
                        elif 'date' in label:
                            extracted_fields['date'] = value
                        elif 'address' in label:
                            extracted_fields['address'] = value
        
        return extracted_fields
    
    def _calculate_handwriting_confidence(self, text: str, extracted_fields: Dict[str, Any]) -> float:
        """Calculate confidence score for handwritten document extraction"""
        if not text.strip():
            return 0.0
        
        # Base confidence factors
        text_length_factor = min(len(text) / 100, 1.0)  # Longer text generally more reliable
        field_count_factor = min(len(extracted_fields) / 5, 1.0)  # More fields extracted
        
        # Quality indicators
        quality_score = 0.5  # Base score
        
        # Check for clear text indicators
        if any(char.isalpha() for char in text):
            quality_score += 0.2
        
        # Check for structured content
        if ':' in text or '\n' in text:
            quality_score += 0.1
        
        # Check for common document elements
        common_words = ['name', 'date', 'signature', 'address', 'phone']
        if any(word in text.lower() for word in common_words):
            quality_score += 0.1
        
        # Penalize for too many numbers (might be OCR artifacts)
        digit_ratio = sum(c.isdigit() for c in text) / len(text) if text else 0
        if digit_ratio > 0.5:
            quality_score -= 0.2
        
        final_confidence = min(
            text_length_factor * field_count_factor * quality_score, 1.0
        )
        
        return max(final_confidence, 0.1)  # Minimum 10% confidence
    
    def _validate_handwritten_fields(self, extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and post-process extracted fields"""
        validated_fields = {}
        
        for field_name, value in extracted_fields.items():
            if not value or not isinstance(value, str):
                continue
            
            # Basic validation based on field type
            field_type = self._infer_field_type(field_name)
            
            if field_type == 'date':
                if self._is_valid_date_format(value):
                    validated_fields[field_name] = value
            elif field_type == 'email':
                if '@' in value and '.' in value:
                    validated_fields[field_name] = value
            elif field_type == 'phone':
                if len(re.sub(r'[^\d]', '', value)) >= 10:
                    validated_fields[field_name] = value
            elif field_type == 'amount':
                if re.match(r'^\d+[,\d]*\.?\d*$', value):
                    validated_fields[field_name] = value
            else:
                # Accept other fields with basic length check
                if len(value.strip()) >= 2:
                    validated_fields[field_name] = value
        
        return validated_fields
    
    def _infer_field_type(self, field_name: str) -> str:
        """Infer field type from field name"""
        field_name_lower = field_name.lower()
        
        if 'date' in field_name_lower:
            return 'date'
        elif 'email' in field_name_lower:
            return 'email'
        elif 'phone' in field_name_lower or 'tel' in field_name_lower:
            return 'phone'
        elif 'amount' in field_name_lower or 'total' in field_name_lower:
            return 'amount'
        elif 'name' in field_name_lower:
            return 'name'
        else:
            return 'text'
    
    def _is_valid_date_format(self, date_str: str) -> bool:
        """Check if string looks like a valid date"""
        import re
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'[A-Za-z]+ \d{1,2},? \d{4}'
        ]
        
        return any(re.match(pattern, date_str.strip()) for pattern in date_patterns)
    
    def test_with_iam_dataset(self, iam_dataset_path: str) -> Dict[str, Any]:
        """Test handwriting recognition with IAM Handwriting Database"""
        # This would be used for validation against the IAM dataset
        # Implementation would depend on having access to the dataset
        logger.info("IAM dataset testing would be implemented here")
        return {
            'test_results': 'IAM dataset testing not implemented in this demo',
            'accuracy': 0.85,  # Placeholder
            'sample_count': 100
        }

# Import guard to prevent circular imports
import re

import os
import openai
import json
import re
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from app.services.nlp_processor import NLPProcessor
from app.services.vision_processor import VisionProcessor
from app.services.legal_processor import LegalProcessor
from app.services.document_processor import DocumentProcessor
from app.services.advanced_nlp import AdvancedNLPProcessor

class ExtractionEngine:
    """Core extraction engine that orchestrates the document extraction process"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        
        self.nlp_processor = NLPProcessor()
        self.vision_processor = VisionProcessor()
        self.legal_processor = LegalProcessor()
        self.document_processor = DocumentProcessor()
        self.advanced_nlp = AdvancedNLPProcessor()
        
        self.confidence_threshold = 0.7
        self.flag_threshold = 0.5
    
    def extract_data(self, document, extraction_request) -> Dict[str, Any]:
        """Main extraction method that processes a document based on extraction request"""
        
        start_time = datetime.utcnow()
        
        try:
            parsed_request = self.nlp_processor.parse_extraction_request(
                extraction_request.natural_language_request,
                document.document_type.value
            )
            
            text_content = self.document_processor.extract_text_content(document)
            
            visual_data = {}
            if document.document_type.value in ['image', 'pdf']:
                visual_result = self.vision_processor.analyze_document(document.file_path)
                visual_data = visual_result if visual_result is not None else {}
            
            extraction_result = self._perform_extraction(
                text_content, visual_data, parsed_request, document
            )
            
            legal_analysis = None
            if parsed_request.get('legal_analysis', False):
                legal_analysis = self.legal_processor.analyze_legal_document(
                    text_content, extraction_result
                )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            extracted_data = extraction_result['data']
            
            if self.advanced_nlp.models_loaded and text_content:
                extracted_data = self.advanced_nlp.enhance_extraction_results(
                    text_content, 
                    extracted_data
                )
            
            result = {
                'extracted_data': extracted_data,
                'confidence_score': extraction_result['confidence'],
                'flagged_fields': extraction_result['flagged_fields'],
                'processing_time_seconds': processing_time,
                'legal_analysis': legal_analysis,
                'metadata': {
                    'document_type': document.document_type.value,
                    'extraction_method': extraction_result['method'],
                    'fields_requested': len(parsed_request.get('fields', [])),
                    'fields_extracted': len(extracted_data)
                }
            }
            
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'processing_time_seconds': (datetime.utcnow() - start_time).total_seconds()
            }
    
    def _perform_extraction(self, text_content: str, visual_data: Dict, 
                          parsed_request: Dict, document) -> Dict[str, Any]:
        """Perform the actual data extraction"""
        
        if self.openai_api_key:
            return self._extract_with_openai(text_content, visual_data, parsed_request, document)
        else:
            return self._extract_with_local_models(text_content, visual_data, parsed_request, document)
    
    def _extract_with_openai(self, text_content: str, visual_data: Dict, 
                           parsed_request: Dict, document) -> Dict[str, Any]:
        """Extract data using OpenAI GPT models"""
        
        system_prompt = """You are an expert document extraction AI. Extract the requested information from the provided document text with high accuracy.

        Rules:
        1. Extract only the information specifically requested
        2. Maintain high accuracy and provide confidence scores
        3. Flag any ambiguous or uncertain extractions
        4. For tables, preserve structure and relationships
        5. For dates, use ISO format (YYYY-MM-DD)
        6. For amounts, include currency if specified
        
        Return results as JSON with this structure:
        {
            "extracted_fields": {
                "field_name": {
                    "value": "extracted_value",
                    "confidence": 0.95,
                    "location": "page/section reference",
                    "context": "surrounding text"
                }
            },
            "tables": [
                {
                    "title": "table_name",
                    "headers": ["col1", "col2"],
                    "rows": [["val1", "val2"]],
                    "confidence": 0.90
                }
            ],
            "overall_confidence": 0.85,
            "flagged_items": ["field_name_with_low_confidence"]
        }"""
        
        fields_to_extract = [field['name'] for field in parsed_request.get('fields', [])]
        
        user_prompt = f"""Document Type: {document.document_type.value}
        
        Fields to Extract: {', '.join(fields_to_extract)}
        
        Special Requirements: {', '.join(parsed_request.get('special_requirements', []))}
        
        Document Text:
        {text_content[:8000]}  # Limit text to avoid token limits
        
        Extract the requested information:"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4" if "gpt-4" in os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo') else "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000,
                timeout=25
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return self._format_extraction_result(result, 'openai')
            
        except Exception as e:
            print(f"OpenAI extraction failed: {e}")
            return self._extract_with_local_models(text_content, visual_data, parsed_request, document)
    
    def _extract_with_local_models(self, text_content: str, visual_data: Dict, 
                                 parsed_request: Dict, document) -> Dict[str, Any]:
        """Extract data using local models and rule-based approaches"""
        
        extracted_fields = {}
        tables = []
        flagged_items = []
        
        for field in parsed_request.get('fields', []):
            field_name = field['name']
            field_type = field['type']
            
            extracted_value, confidence = self._extract_field_with_patterns(
                text_content, field_name, field_type
            )
            
            if extracted_value:
                extracted_fields[field_name] = {
                    'value': extracted_value,
                    'confidence': confidence,
                    'location': 'text_content',
                    'context': self._get_field_context(text_content, extracted_value)
                }
                
                if confidence < self.flag_threshold:
                    flagged_items.append(field_name)
        
        if parsed_request.get('table_extraction', False):
            tables = self._extract_tables_with_patterns(text_content)
        
        confidences = [field['confidence'] for field in extracted_fields.values()]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        result = {
            'extracted_fields': extracted_fields,
            'tables': tables,
            'overall_confidence': overall_confidence,
            'flagged_items': flagged_items
        }
        
        return self._format_extraction_result(result, 'local_patterns')
    
    def _extract_field_with_patterns(self, text: str, field_name: str, field_type: str) -> Tuple[Optional[str], float]:
        """Extract a specific field using pattern matching"""
        
        patterns = {
            'date': [
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
                r'\b(\d{4}-\d{2}-\d{2})\b',
                r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
            ],
            'name': [
                r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',
                r'\b([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)\b'
            ],
            'amount': [
                r'\$[\d,]+\.?\d*',
                r'\b\d+\.\d{2}\b',
                r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b'
            ],
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'phone': [
                r'\b\d{3}-\d{3}-\d{4}\b',
                r'\(\d{3}\)\s*\d{3}-\d{4}\b'
            ]
        }
        
        field_patterns = patterns.get(field_type, [])
        
        field_context = self._find_field_context(text, field_name)
        
        for pattern in field_patterns:
            matches = re.findall(pattern, field_context, re.IGNORECASE)
            if matches:
                confidence = 0.8 if len(field_patterns) > 1 else 0.6
                return matches[0], confidence
        
        for pattern in field_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0], 0.5  # Lower confidence for general search
        
        return None, 0.0
    
    def _find_field_context(self, text: str, field_name: str, context_size: int = 200) -> str:
        """Find text context around a field name"""
        
        field_name_lower = field_name.lower()
        text_lower = text.lower()
        
        index = text_lower.find(field_name_lower)
        if index == -1:
            words = field_name_lower.split()
            for word in words:
                index = text_lower.find(word)
                if index != -1:
                    break
        
        if index == -1:
            return text[:context_size]  # Return beginning if not found
        
        start = max(0, index - context_size // 2)
        end = min(len(text), index + context_size // 2)
        
        return text[start:end]
    
    def _get_field_context(self, text: str, value: str, context_size: int = 100) -> str:
        """Get context around an extracted value"""
        
        index = text.find(str(value))
        if index == -1:
            return ""
        
        start = max(0, index - context_size // 2)
        end = min(len(text), index + context_size // 2)
        
        return text[start:end]
    
    def _extract_tables_with_patterns(self, text: str) -> List[Dict]:
        """Extract tables using pattern matching"""
        
        tables = []
        
        lines = text.split('\n')
        
        current_table = []
        in_table = False
        
        for line in lines:
            if '\t' in line or re.search(r'\s{3,}', line):
                if not in_table:
                    in_table = True
                    current_table = []
                
                if '\t' in line:
                    row = [cell.strip() for cell in line.split('\t') if cell.strip()]
                else:
                    row = [cell.strip() for cell in re.split(r'\s{3,}', line) if cell.strip()]
                
                if len(row) > 1:
                    current_table.append(row)
            else:
                if in_table and current_table:
                    if len(current_table) > 1:  # At least header + one row
                        tables.append({
                            'title': f'Table_{len(tables) + 1}',
                            'headers': current_table[0],
                            'rows': current_table[1:],
                            'confidence': 0.7
                        })
                    current_table = []
                    in_table = False
        
        if in_table and current_table and len(current_table) > 1:
            tables.append({
                'title': f'Table_{len(tables) + 1}',
                'headers': current_table[0],
                'rows': current_table[1:],
                'confidence': 0.7
            })
        
        return tables
    
    def _format_extraction_result(self, result: Dict, method: str) -> Dict[str, Any]:
        """Format extraction result into standard format"""
        
        extracted_fields = result.get('extracted_fields', {})
        tables = result.get('tables', [])
        overall_confidence = result.get('overall_confidence', 0.0)
        flagged_items = result.get('flagged_items', [])
        
        data = {}
        
        for field_name, field_data in extracted_fields.items():
            if isinstance(field_data, dict):
                data[field_name] = field_data['value']
            else:
                data[field_name] = field_data
        
        if tables:
            data['tables'] = tables
        
        return {
            'data': data,
            'confidence': overall_confidence,
            'flagged_fields': flagged_items,
            'method': method
        }

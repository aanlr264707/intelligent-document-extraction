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
from app.services.rag_processor import RAGProcessor

class ExtractionEngine:
    """Core extraction engine that orchestrates the document extraction process"""
    
    def __init__(self):
        self.openai_client = None
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if self.openai_api_key and self.openai_api_key.strip() and self.openai_api_key != 'your-openai-api-key':
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                print("OpenAI client initialized successfully")
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
                self.openai_client = None
        else:
            print("No valid OpenAI API key found, will use local models only")
        
        # Lazy loading - initialize processors only when needed
        self._nlp_processor = None
        self._vision_processor = None
        self._legal_processor = None
        self._document_processor = None
        self._advanced_nlp = None
        self._rag_processor = None
        
        self.confidence_threshold = 0.7
        self.flag_threshold = 0.5
    
    @property
    def nlp_processor(self):
        if self._nlp_processor is None:
            self._nlp_processor = NLPProcessor()
        return self._nlp_processor
    
    @property
    def vision_processor(self):
        if self._vision_processor is None:
            self._vision_processor = VisionProcessor()
        return self._vision_processor
    
    @property
    def legal_processor(self):
        if self._legal_processor is None:
            self._legal_processor = LegalProcessor()
        return self._legal_processor
    
    @property
    def document_processor(self):
        if self._document_processor is None:
            self._document_processor = DocumentProcessor()
        return self._document_processor
    
    @property
    def advanced_nlp(self):
        if self._advanced_nlp is None:
            self._advanced_nlp = AdvancedNLPProcessor()
        return self._advanced_nlp
    
    @property
    def rag_processor(self):
        if self._rag_processor is None:
            self._rag_processor = RAGProcessor()
        return self._rag_processor
    
    def extract_data(self, document, extraction_request) -> Dict[str, Any]:
        """Main extraction method that processes a document based on extraction request"""
        
        start_time = datetime.utcnow()
        
        try:
            print(f"Starting extraction for document: {document.original_filename}")
            
            if hasattr(extraction_request, 'natural_language_request'):
                requirements = extraction_request.natural_language_request
            else:
                requirements = extraction_request.get('requirements', '')
            
            print(f"Extraction requirements: {requirements}")
            
            if not requirements or requirements.strip() == '':
                return {
                    'error': 'No extraction requirements provided',
                    'extracted_data': {},
                    'confidence_score': 0.0,
                    'processing_time_seconds': (datetime.utcnow() - start_time).total_seconds()
                }
            
            try:
                parsed_request = self.nlp_processor.parse_extraction_request(
                    requirements,
                    document.document_type.value
                )
            except Exception as e:
                print(f"Failed to parse extraction request: {e}")
                parsed_request = {
                    'fields': [{'name': 'general_content', 'type': 'text'}],
                    'special_requirements': [],
                    'legal_analysis': False
                }
            
            try:
                text_content = self.document_processor.extract_text_content(document)
            except Exception as e:
                print(f"Failed to extract text content: {e}")
                return {
                    'error': f'Failed to extract text content: {str(e)}',
                    'extracted_data': {},
                    'confidence_score': 0.0,
                    'processing_time_seconds': (datetime.utcnow() - start_time).total_seconds()
                }
            
            if not text_content or len(text_content.strip()) < 10:
                return {
                    'error': 'Document appears to be empty or contains insufficient text',
                    'extracted_data': {},
                    'confidence_score': 0.0,
                    'processing_time_seconds': (datetime.utcnow() - start_time).total_seconds()
                }
            
            print(f"Extracted {len(text_content)} characters of text content")
            
            visual_data = {}
            if document.document_type.value in ['image', 'pdf']:
                try:
                    visual_result = self.vision_processor.analyze_document(document.file_path)
                    visual_data = visual_result if visual_result is not None else {}
                except Exception as e:
                    print(f"Vision processing failed: {e}")
                    visual_data = {}
            
            extraction_result = self._perform_extraction(
                text_content, visual_data, parsed_request, document
            )
            
            if not extraction_result:
                return {
                    'error': 'Extraction returned no result',
                    'extracted_data': {},
                    'confidence_score': 0.0,
                    'processing_time_seconds': (datetime.utcnow() - start_time).total_seconds()
                }
            
            legal_analysis = None
            if parsed_request.get('legal_analysis', False):
                try:
                    legal_analysis = self.legal_processor.analyze_legal_document(
                        text_content, extraction_result
                    )
                except Exception as e:
                    print(f"Legal analysis failed: {e}")
                    legal_analysis = {'error': str(e)}
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            extracted_data = extraction_result.get('data', {})
            
            if not extracted_data:
                extracted_data = {
                    'text_content': text_content[:1000] + '...' if len(text_content) > 1000 else text_content,
                    'requirements': requirements,
                    'extraction_method': 'fallback'
                }
            
            try:
                if self.advanced_nlp.models_loaded and text_content:
                    extracted_data = self.advanced_nlp.enhance_extraction_results(
                        text_content, 
                        extracted_data
                    )
            except Exception as e:
                print(f"Advanced NLP enhancement failed: {e}")
            
            result = {
                'extracted_data': extracted_data,
                'confidence_score': extraction_result.get('confidence', 0.0),
                'flagged_fields': extraction_result.get('flagged_fields', []),
                'processing_time_seconds': processing_time,
                'legal_analysis': legal_analysis,
                'metadata': {
                    'document_type': document.document_type.value,
                    'extraction_method': extraction_result.get('method', 'unknown'),
                    'fields_requested': len(parsed_request.get('fields', [])),
                    'fields_extracted': len(extracted_data)
                }
            }
            
            if hasattr(self, 'rag_processor') and self.rag_processor and result.get('confidence_score', 0) > 0.5:
                try:
                    document_id = str(document.id) if hasattr(document, 'id') else f"doc_{hash(text_content[:100])}"
                    self.rag_processor.add_document_to_knowledge_base(
                        document_text=text_content,
                        document_id=document_id,
                        extraction_data=result.get('extracted_data', {})
                    )
                    print(f"[RAG DEBUG] Added document {document_id} to knowledge base")
                except Exception as e:
                    print(f"[RAG DEBUG] Failed to add document to knowledge base: {e}")
            
            print(f"Extraction completed successfully with confidence: {result['confidence_score']}")
            return result
            
        except Exception as e:
            print(f"Error during extraction: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'error': f'Extraction failed: {str(e)}',
                'extracted_data': {},
                'confidence_score': 0.0,
                'processing_time_seconds': (datetime.utcnow() - start_time).total_seconds()
            }
    
    def _perform_extraction(self, text_content: str, visual_data: Dict, 
                          parsed_request: Dict, document) -> Dict[str, Any]:
        """Perform the actual data extraction"""
        
        print(f"Attempting data extraction...")
        
        if self.openai_client:
            print("Using OpenAI for extraction")
            try:
                result = self._extract_with_openai(text_content, visual_data, parsed_request, document)
                if result:
                    return result
                print("OpenAI extraction returned empty result, falling back to local models")
            except Exception as e:
                print(f"OpenAI extraction failed: {e}, falling back to local models")
        
        print("Using local models for extraction")
        try:
            result = self._extract_with_local_models(text_content, visual_data, parsed_request, document)
            if result:
                return result
            print("Local model extraction returned empty result, using basic fallback")
        except Exception as e:
            print(f"Local model extraction failed: {e}, using basic fallback")
        
        return self._basic_extraction_fallback(text_content, parsed_request)
    
    def _extract_with_openai(self, text_content: str, visual_data: Dict, 
                           parsed_request: Dict, document) -> Dict[str, Any]:
        """Extract data using OpenAI GPT models with RAG enhancement"""
        
        try:
            print(f"Making OpenAI API call...")
            
            rag_result = None
            if hasattr(self, 'rag_processor') and self.rag_processor and self.rag_processor.openai_client:
                print(f"[RAG DEBUG] Attempting RAG-enhanced extraction...")
                try:
                    fields_to_extract = [field['name'] for field in parsed_request.get('fields', [])]
                    requirements_text = f"Extract: {', '.join(fields_to_extract)}. Special requirements: {', '.join(parsed_request.get('special_requirements', []))}"
                    
                    rag_result = self.rag_processor.generate_rag_response(
                        query=requirements_text,
                        document_text=text_content,
                        extraction_requirements=requirements_text
                    )
                    if rag_result:
                        print(f"[RAG DEBUG] RAG extraction successful with {rag_result.get('context_documents', 0)} context documents")
                        return self._format_rag_result(rag_result)
                    else:
                        print(f"[RAG DEBUG] RAG extraction returned no result, falling back to regular OpenAI")
                except Exception as e:
                    print(f"[RAG DEBUG] RAG extraction failed: {e}, falling back to regular OpenAI")
            
            text_sample = text_content[:3000] if len(text_content) > 3000 else text_content
            fields_to_extract = [field['name'] for field in parsed_request.get('fields', [])]
            
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
            
            user_prompt = f"""Document Type: {document.document_type.value}
            
            Fields to Extract: {', '.join(fields_to_extract)}
            
            Special Requirements: {', '.join(parsed_request.get('special_requirements', []))}
            
            Document Text:
            {text_sample}
            
            Extract the requested information:"""
            
            import time
            start_time = time.time()
            
            if not self.openai_client:
                raise Exception("OpenAI client not initialized")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
                timeout=30
            )
            
            elapsed_time = time.time() - start_time
            print(f"OpenAI API call completed in {elapsed_time:.2f} seconds")
            
            result_text = response.choices[0].message.content
            print(f"OpenAI response length: {len(result_text)} characters")
            
            try:
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = result_text[start_idx:end_idx]
                    result = json.loads(json_str)
                    return self._format_extraction_result(result, 'openai')
                else:
                    result = {
                        'extracted_fields': {'content': {'value': result_text, 'confidence': 0.7}},
                        'overall_confidence': 0.7,
                        'flagged_items': []
                    }
                    return self._format_extraction_result(result, 'openai')
            except json.JSONDecodeError as je:
                print(f"JSON decode error: {je}")
                result = {
                    'extracted_fields': {'content': {'value': result_text, 'confidence': 0.6}},
                    'overall_confidence': 0.6,
                    'flagged_items': ['content']
                }
                return self._format_extraction_result(result, 'openai')
            
        except Exception as e:
            print(f"OpenAI extraction error: {e}")
            raise
    
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
    
    def _basic_extraction_fallback(self, text_content: str, parsed_request: Dict) -> Dict[str, Any]:
        """Basic extraction fallback when AI models fail"""
        print("Using basic extraction fallback")
        
        extracted_fields = {}
        
        import re
        
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text_content, re.IGNORECASE))
        
        if dates:
            extracted_fields['dates_found'] = {
                'value': list(set(dates))[:5],
                'confidence': 0.8,
                'location': 'text_content',
                'context': 'Pattern matching'
            }
        
        money_pattern = r'\$[\d,]+\.?\d*'
        amounts = re.findall(money_pattern, text_content)
        if amounts:
            extracted_fields['monetary_amounts'] = {
                'value': list(set(amounts))[:5],
                'confidence': 0.8,
                'location': 'text_content',
                'context': 'Pattern matching'
            }
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text_content)
        if emails:
            extracted_fields['email_addresses'] = {
                'value': list(set(emails))[:3],
                'confidence': 0.9,
                'location': 'text_content',
                'context': 'Pattern matching'
            }
        
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
        phones = re.findall(phone_pattern, text_content)
        if phones:
            extracted_fields['phone_numbers'] = {
                'value': list(set(phones))[:3],
                'confidence': 0.8,
                'location': 'text_content',
                'context': 'Pattern matching'
            }
        
        extracted_fields['text_sample'] = {
            'value': text_content[:1000] + '...' if len(text_content) > 1000 else text_content,
            'confidence': 1.0,
            'location': 'document',
            'context': 'Full text extraction'
        }
        
        confidences = [field['confidence'] for field in extracted_fields.values()]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        result = {
            'extracted_fields': extracted_fields,
            'tables': [],
            'overall_confidence': overall_confidence,
            'flagged_items': []
        }
        
        return self._format_extraction_result(result, 'basic_fallback')
    
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
    
    def _format_rag_result(self, rag_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format RAG extraction result into standard format"""
        
        extracted_fields = rag_result.get('extracted_fields', {})
        overall_confidence = rag_result.get('overall_confidence', 0.0)
        
        data = {}
        flagged_items = []
        
        for field_name, field_data in extracted_fields.items():
            if isinstance(field_data, dict):
                data[field_name] = field_data.get('value', field_data)
                if field_data.get('confidence', 1.0) < self.flag_threshold:
                    flagged_items.append(field_name)
            else:
                data[field_name] = field_data
        
        if rag_result.get('rag_insights'):
            data['rag_insights'] = rag_result['rag_insights']
        
        return {
            'data': data,
            'confidence': overall_confidence,
            'flagged_fields': flagged_items,
            'method': 'rag_enhanced',
            'context_documents': rag_result.get('context_documents', 0),
            'rag_used': True
        }

    def extract_with_open_source_models(self, document, extraction_request) -> Dict[str, Any]:
        """Enhanced extraction using open-source models (Tesseract, Hugging Face, CLIP)"""
        
        start_time = datetime.utcnow()
        
        try:
            print(f"Starting open-source extraction for document: {document.original_filename}")
            
            # Get the natural language request
            natural_language_request = getattr(extraction_request, 'natural_language_request', '')
            if not natural_language_request:
                natural_language_request = getattr(extraction_request, 'request_data', {}).get('natural_language_request', '')
            
            # Step 1: Analyze extraction intent using Hugging Face transformers
            intent_analysis = self.nlp_processor.analyze_extraction_intent(natural_language_request)
            
            # Step 2: Extract text content using enhanced Tesseract OCR
            text_content = self.document_processor.extract_text_content(document.file_path)
            
            # Step 3: Vision analysis with CLIP for document understanding
            vision_result = self.vision_processor.analyze_document(document.file_path)
            
            # Step 4: Extract semantic information using CLIP
            semantic_analysis = None
            if hasattr(self.vision_processor, 'extract_document_semantics'):
                semantic_analysis = self.vision_processor.extract_document_semantics(
                    self.vision_processor._load_image(document.file_path),
                    natural_language_request
                )
            
            # Step 5: Named Entity Recognition using Hugging Face
            entity_extraction = self.nlp_processor.extract_entities_from_text(text_content)
            
            # Step 6: Generate questions based on extraction requirements
            questions = self._generate_questions_from_requirements(intent_analysis, natural_language_request)
            qa_results = self.nlp_processor.answer_document_questions(text_content, questions)
            
            # Step 7: Combine all results
            extracted_data = self._combine_open_source_results(
                text_content, intent_analysis, vision_result, 
                semantic_analysis, entity_extraction, qa_results
            )
            
            # Step 8: Quality assessment
            quality_score = self._assess_extraction_quality(extracted_data, intent_analysis)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'extracted_data': extracted_data,
                'confidence_score': quality_score,
                'processing_time_seconds': processing_time,
                'extraction_method': 'open_source_models',
                'models_used': {
                    'ocr': 'tesseract_enhanced',
                    'nlp': 'huggingface_transformers',
                    'vision': 'clip',
                    'ner': 'bert_conll03'
                },
                'intent_analysis': intent_analysis,
                'semantic_analysis': semantic_analysis,
                'entity_extraction': entity_extraction,
                'qa_results': qa_results,
                'vision_analysis': vision_result
            }
            
        except Exception as e:
            print(f"Open-source extraction failed: {e}")
            return {
                'extracted_data': {'error': str(e)},
                'confidence_score': 0.0,
                'processing_time_seconds': (datetime.utcnow() - start_time).total_seconds(),
                'extraction_method': 'failed'
            }
    
    def _generate_questions_from_requirements(self, intent_analysis: Dict, natural_request: str) -> List[str]:
        """Generate questions for QA based on extraction requirements"""
        
        questions = []
        
        # Basic questions based on intent analysis
        if intent_analysis.get('suggested_fields'):
            for field in intent_analysis['suggested_fields']:
                field_name = field.get('name', '')
                if field_name:
                    questions.append(f"What is the {field_name}?")
                    questions.append(f"Where can I find the {field_name}?")
        
        # Questions based on categories
        categories = intent_analysis.get('categories', {})
        if categories.get('legal_document', 0) > 0:
            questions.extend([
                "Who are the parties involved in this agreement?",
                "What is the effective date?",
                "What are the key terms and conditions?",
                "Are there any penalties or risks mentioned?"
            ])
        
        if categories.get('financial_document', 0) > 0:
            questions.extend([
                "What is the total amount?",
                "When is the payment due?",
                "Who is the vendor or payer?",
                "What items or services are listed?"
            ])
        
        if categories.get('personal_document', 0) > 0:
            questions.extend([
                "What is the person's name?",
                "What is the address?",
                "What is the phone number?",
                "What is the email address?"
            ])
        
        # Add direct questions from natural language request
        if 'what' in natural_request.lower() or 'who' in natural_request.lower():
            questions.append(natural_request)
        
        return questions[:10]  # Limit to 10 questions to avoid overwhelming the QA model
    
    def _combine_open_source_results(self, text_content: str, intent_analysis: Dict, 
                                   vision_result: Dict, semantic_analysis: Dict,
                                   entity_extraction: Dict, qa_results: Dict) -> Dict[str, Any]:
        """Combine results from all open-source models"""
        
        combined_data = {
            'text_content': text_content,
            'document_length': len(text_content),
            'extraction_timestamp': datetime.utcnow().isoformat()
        }
        
        # Add entities as structured data
        if entity_extraction.get('entity_groups'):
            combined_data['entities'] = entity_extraction['entity_groups']
        
        # Add QA results as extracted fields
        if qa_results.get('answers'):
            combined_data['qa_extracted_fields'] = {}
            for question, answer_data in qa_results['answers'].items():
                if answer_data['confidence'] > 0.3:  # Only include confident answers
                    field_key = question.lower().replace('what is the ', '').replace('?', '').replace(' ', '_')
                    combined_data['qa_extracted_fields'][field_key] = {
                        'value': answer_data['answer'],
                        'confidence': answer_data['confidence'],
                        'source_question': question
                    }
        
        # Add vision analysis results
        if vision_result:
            combined_data['document_structure'] = vision_result.get('layout_analysis', {})
            combined_data['visual_elements'] = vision_result.get('visual_elements', {})
            combined_data['ocr_text'] = vision_result.get('text_content', '')
        
        # Add semantic understanding from CLIP
        if semantic_analysis:
            combined_data['document_type'] = semantic_analysis.get('document_type_prediction', 'unknown')
            combined_data['semantic_confidence'] = semantic_analysis.get('confidence', 0.0)
            combined_data['extraction_relevance'] = semantic_analysis.get('extraction_relevance', {})
        
        # Add suggested fields from intent analysis
        if intent_analysis.get('suggested_fields'):
            combined_data['suggested_extraction_fields'] = intent_analysis['suggested_fields']
        
        return combined_data
    
    def _assess_extraction_quality(self, extracted_data: Dict, intent_analysis: Dict) -> float:
        """Assess the quality of the extraction using multiple criteria"""
        
        quality_factors = []
        
        # Text content availability
        if extracted_data.get('text_content'):
            quality_factors.append(0.8 if len(extracted_data['text_content']) > 100 else 0.4)
        else:
            quality_factors.append(0.1)
        
        # Entity extraction success
        entities = extracted_data.get('entities', {})
        if entities:
            entity_score = min(0.9, len(entities) * 0.2)
            quality_factors.append(entity_score)
        else:
            quality_factors.append(0.2)
        
        # QA results confidence
        qa_fields = extracted_data.get('qa_extracted_fields', {})
        if qa_fields:
            avg_confidence = sum(field['confidence'] for field in qa_fields.values()) / len(qa_fields)
            quality_factors.append(avg_confidence)
        else:
            quality_factors.append(0.3)
        
        # Semantic analysis confidence
        semantic_confidence = extracted_data.get('semantic_confidence', 0.0)
        quality_factors.append(semantic_confidence)
        
        # Overall quality score
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.0

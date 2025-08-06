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
            document_filename = getattr(document, 'original_filename', getattr(document, 'filename', 'unknown_document'))
            print(f"Starting extraction for document: {document_filename}")
            
            if hasattr(extraction_request, 'natural_language_request'):
                requirements = extraction_request.natural_language_request
            elif hasattr(extraction_request, 'extraction_fields'):
                # Handle mock extraction request with fields
                fields = extraction_request.extraction_fields
                requirements = f"Extract the following fields: {', '.join([f.get('name', 'unknown') for f in fields])}"
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
                    self._get_document_type_value(document)
                )
            except Exception as e:
                print(f"Failed to parse extraction request: {e}")
                parsed_request = {
                    'fields': [{'name': 'general_content', 'type': 'text'}],
                    'special_requirements': [],
                    'legal_analysis': False
                }
            
            try:
                if hasattr(document, 'file_content'):
                    # Handle mock document or document with direct content
                    text_content = document.file_content
                else:
                    # Handle real document object
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
            if self._get_document_type_value(document) in ['image', 'pdf']:
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
                    'document_type': self._get_document_type_value(document),
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
            
            user_prompt = f"""Document Type: {self._get_document_type_value(document)}
            
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
        """Enhanced extraction using multiple local analysis techniques"""
        
        try:
            print("🔍 Starting enhanced local extraction...")
            
            # Initialize comprehensive result structure
            comprehensive_result = {
                'extracted_fields': {},
                'structured_entities': {},
                'document_analysis': {},
                'field_extractions': {},
                'confidence_metrics': {}
            }
            
            # 1. ENHANCED FIELD-SPECIFIC EXTRACTION
            requested_fields = parsed_request.get('fields', [])
            for field in requested_fields:
                field_name = field.get('name', '')
                field_type = field.get('type', 'text')
                
                field_result = self._enhanced_field_extraction(
                    text_content, field_name, field_type, visual_data
                )
                
                if field_result and field_result.get('value'):
                    comprehensive_result['field_extractions'][field_name] = field_result
            
            # 2. STRUCTURED ENTITY EXTRACTION
            structured_entities = self._extract_structured_entities(text_content)
            comprehensive_result['structured_entities'] = structured_entities
            
            # 3. DOCUMENT TYPE ANALYSIS
            doc_analysis = self._analyze_document_type_and_structure(text_content, document)
            comprehensive_result['document_analysis'] = doc_analysis
            
            # 4. LEGAL DOCUMENT PROCESSING (if applicable)
            if self._is_legal_document(text_content):
                legal_result = self.legal_processor.analyze_legal_document(text_content, {})
                comprehensive_result['legal_analysis'] = legal_result
            
            # 5. TABLE AND STRUCTURED DATA EXTRACTION
            tables = self._extract_enhanced_tables(text_content)
            if tables:
                comprehensive_result['tables'] = tables
            
            # 6. VISION-BASED EXTRACTION (if visual data available)
            if visual_data:
                visual_fields = self._extract_from_visual_data(visual_data, parsed_request)
                comprehensive_result['visual_extraction'] = visual_fields
            
            # 7. CALCULATE OVERALL CONFIDENCE
            confidence_score = self._calculate_comprehensive_confidence(comprehensive_result)
            comprehensive_result['confidence_metrics']['overall_confidence'] = confidence_score
            
            return self._format_comprehensive_local_result(comprehensive_result)
            
        except Exception as e:
            print(f"Enhanced local extraction error: {e}")
            # Fallback to basic extraction
            return self._basic_extraction_fallback(text_content, parsed_request)
    
    def _basic_extraction_fallback(self, text_content: str, parsed_request: Dict) -> Dict[str, Any]:
        """Enhanced basic extraction fallback with improved pattern matching"""
        print("Using enhanced basic extraction fallback")
        
        extracted_fields = {}
        
        # Enhanced pattern collection
        enhanced_patterns = {
            'dates': [
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
                r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
                r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b',
                r'(?:effective|start|begin|end|expire|due|deadline)[:\s]*([^.\n]{0,50}(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}))',
            ],
            'names': [
                r'\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
                r'(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?)\s+([A-Z][a-z]+(?:\s+[A-Z]\.)*\s+[A-Z][a-z]+)',
                r'(?:employee|contractor|client|party)[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.)*\s+[A-Z][a-z]+)',
            ],
            'amounts': [
                r'(\$[\d,]+\.?\d*)',
                r'(USD\s*[\d,]+\.?\d*)',
                r'(EUR\s*[\d,]+\.?\d*)',
                r'(?:amount|sum|total|cost|price|fee|salary|wage)[:\s]*(\$?[\d,]+\.?\d*)',
            ],
            'emails': [
                r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b',
                r'(?:email|e-mail|contact)[:\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
            ],
            'phones': [
                r'\b(\d{3}-\d{3}-\d{4})\b',
                r'(\(\d{3}\)\s*\d{3}-\d{4})\b',
                r'\b(\d{3}\.\d{3}\.\d{4})\b',
                r'(?:phone|tel|telephone)[:\s]*([+\d\s\(\)-]+)',
            ],
            'organizations': [
                r'\b([A-Z][A-Za-z\s]+(?:Inc\.?|LLC|Corporation|Corp\.?|Company|Co\.?|Ltd\.?))\b',
                r'\b([A-Z][A-Za-z\s]+ (?:University|College|School))\b',
            ],
            'addresses': [
                r'\b(\d+\s+[A-Z][A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln))\b',
                r'\b([A-Z][a-z]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)\b',
            ],
            'percentages': [
                r'\b(\d+(?:\.\d+)?%)\b',
                r'(?:rate|percentage)[:\s]*(\d+(?:\.\d+)?%?)',
            ]
        }
        
        # Extract each pattern type
        for pattern_type, patterns in enhanced_patterns.items():
            found_items = []
            for pattern in patterns:
                matches = re.finditer(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    value = match.group(1) if len(match.groups()) > 0 else match.group()
                    if value and value not in [item['value'] for item in found_items]:
                        found_items.append({
                            'value': value.strip(),
                            'position': match.start(),
                            'confidence': 0.8
                        })
            
            if found_items:
                extracted_fields[pattern_type] = {
                    'value': [item['value'] for item in found_items[:5]],  # Top 5
                    'confidence': 0.8,
                    'location': 'text_content',
                    'context': f'Enhanced pattern matching for {pattern_type}'
                }
        
        # Try to match requested fields to extracted patterns
        requested_fields = parsed_request.get('fields', [])
        for field in requested_fields:
            field_name = field.get('name', '').lower()
            field_type = field.get('type', 'text').lower()
            
            # Map field names/types to extracted patterns
            if 'date' in field_name or field_type == 'date':
                if 'dates' in extracted_fields:
                    extracted_fields[field['name']] = extracted_fields['dates']
            elif 'name' in field_name or field_type == 'name':
                if 'names' in extracted_fields:
                    extracted_fields[field['name']] = extracted_fields['names']
            elif any(term in field_name for term in ['amount', 'price', 'cost', 'salary', 'fee']) or field_type == 'amount':
                if 'amounts' in extracted_fields:
                    extracted_fields[field['name']] = extracted_fields['amounts']
            elif 'email' in field_name or field_type == 'email':
                if 'emails' in extracted_fields:
                    extracted_fields[field['name']] = extracted_fields['emails']
            elif 'phone' in field_name or field_type == 'phone':
                if 'phones' in extracted_fields:
                    extracted_fields[field['name']] = extracted_fields['phones']
        
        # Enhanced table extraction
        tables = self._extract_enhanced_tables(text_content)
        
        # Extract key-value pairs
        key_value_pairs = self._extract_key_value_pairs(text_content)
        if key_value_pairs:
            extracted_fields['key_value_pairs'] = {
                'value': key_value_pairs,
                'confidence': 0.7,
                'location': 'text_content',
                'context': 'Key-value pattern matching'
            }
        
        # Enhanced document analysis with legal clause identification
        document_analysis = self._perform_comprehensive_document_analysis(text_content)
        extracted_fields['document_summary'] = {
            'value': document_analysis,
            'confidence': 1.0,
            'location': 'document',
            'context': 'Comprehensive document analysis with legal clause identification'
        }
        
        # Calculate overall confidence
        confidences = [field['confidence'] for field in extracted_fields.values() if isinstance(field, dict) and 'confidence' in field]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Flag low-confidence fields
        flagged_items = []
        for field_name, field_data in extracted_fields.items():
            if isinstance(field_data, dict) and field_data.get('confidence', 0) < 0.6:
                flagged_items.append(field_name)
        
        result = {
            'extracted_fields': extracted_fields,
            'tables': tables,
            'overall_confidence': overall_confidence,
            'flagged_items': flagged_items
        }
        
        return self._format_extraction_result(result, 'enhanced_basic_fallback')
    
    def _extract_key_value_pairs(self, text_content: str) -> List[Dict[str, str]]:
        """Extract key-value pairs from text"""
        
        key_value_pairs = []
        
        # Common key-value patterns
        patterns = [
            r'([A-Za-z\s]+):\s*([^.\n]+)',
            r'([A-Za-z\s]+)\s*=\s*([^.\n]+)',
            r'([A-Za-z\s]+)\s*-\s*([^.\n]+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text_content)
            for match in matches:
                key = match.group(1).strip()
                value = match.group(2).strip()
                
                # Filter out very short or very long keys/values
                if 3 <= len(key) <= 50 and 1 <= len(value) <= 200:
                    key_value_pairs.append({
                        'key': key,
                        'value': value,
                        'confidence': 0.7
                    })
        
        return key_value_pairs[:20]  # Limit to top 20
    
    def _extract_enhanced_tables(self, text_content: str) -> List[Dict[str, Any]]:
        """Enhanced table extraction from text content"""
        
        tables = []
        
        # Look for table-like structures
        lines = text_content.split('\n')
        current_table = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                if current_table:
                    tables.append(current_table)
                    current_table = None
                continue
            
            # Check if line could be a table row (multiple columns separated by delimiters)
            delimiters = ['|', '\t', '  ', ',']
            for delimiter in delimiters:
                if delimiter in line:
                    parts = [p.strip() for p in line.split(delimiter) if p.strip()]
                    if len(parts) >= 2:  # At least 2 columns
                        if not current_table:
                            current_table = {
                                'headers': parts,
                                'rows': [],
                                'start_line': i,
                                'delimiter': delimiter,
                                'confidence': 0.7
                            }
                        else:
                            # Check if this row fits the current table structure
                            if (abs(len(parts) - len(current_table['headers'])) <= 1 and 
                                delimiter == current_table['delimiter']):
                                current_table['rows'].append(parts)
                            else:
                                # Different structure, save current table and start new one
                                if current_table and current_table['rows']:
                                    tables.append(current_table)
                                current_table = {
                                    'headers': parts,
                                    'rows': [],
                                    'start_line': i,
                                    'delimiter': delimiter,
                                    'confidence': 0.7
                                }
                        break
            else:
                # Line doesn't appear to be part of a table
                if current_table:
                    if current_table['rows']:  # Only save if it has data rows
                        tables.append(current_table)
                    current_table = None
        
        # Don't forget the last table
        if current_table and current_table['rows']:
            tables.append(current_table)
        
        # Filter out tables with very few rows or columns
        valid_tables = []
        for table in tables:
            if len(table['rows']) >= 1 and len(table['headers']) >= 2:
                # Calculate confidence based on consistency
                row_lengths = [len(row) for row in table['rows']]
                if row_lengths:
                    avg_length = sum(row_lengths) / len(row_lengths)
                    length_variance = sum((length - avg_length) ** 2 for length in row_lengths) / len(row_lengths)
                    
                    # Higher confidence for consistent row lengths
                    if length_variance < 2:
                        table['confidence'] = min(0.9, table['confidence'] + 0.2)
                    
                    valid_tables.append(table)
        
        return valid_tables[:10]  # Limit to top 10 tables
    
    def _perform_comprehensive_document_analysis(self, text_content: str) -> Dict[str, Any]:
        """Comprehensive analysis of document with legal clause identification and risk assessment"""
        
        analysis = {
            'basic_info': self._analyze_basic_document_info(text_content),
            'legal_clauses': self._identify_legal_clauses(text_content),
            'risk_assessment': self._assess_document_risks(text_content),
            'key_dates': self._extract_critical_dates(text_content),
            'parties_involved': self._identify_parties(text_content),
            'obligations': self._identify_obligations(text_content),
            'compliance_requirements': self._identify_compliance_requirements(text_content),
            'financial_terms': self._extract_financial_terms(text_content),
            'termination_conditions': self._identify_termination_conditions(text_content)
        }
        
        return analysis
    
    def _analyze_basic_document_info(self, text_content: str) -> Dict[str, Any]:
        """Analyze basic document information"""
        
        words = text_content.split()
        sentences = text_content.split('.')
        paragraphs = [p.strip() for p in text_content.split('\n\n') if p.strip()]
        
        # Document type detection
        doc_type = self._classify_document_type(text_content)
        
        # Language complexity analysis
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        avg_sentence_length = sum(len(sentence.split()) for sentence in sentences) / len(sentences) if sentences else 0
        
        return {
            'document_type': doc_type,
            'word_count': len(words),
            'sentence_count': len(sentences),
            'paragraph_count': len(paragraphs),
            'estimated_reading_time': f"{len(words) // 200 + 1} minutes",
            'complexity_score': self._calculate_complexity_score(avg_word_length, avg_sentence_length),
            'language_analysis': {
                'avg_word_length': round(avg_word_length, 2),
                'avg_sentence_length': round(avg_sentence_length, 2),
                'formality_score': self._assess_formality(text_content)
            }
        }
    
    def _classify_document_type(self, text_content: str) -> Dict[str, Any]:
        """Classify the type of document"""
        
        text_lower = text_content.lower()
        
        # Document type indicators
        type_indicators = {
            'contract': ['contract', 'agreement', 'party', 'hereby', 'whereas', 'covenant'],
            'employment_agreement': ['employment', 'employee', 'employer', 'salary', 'benefits', 'termination'],
            'lease_agreement': ['lease', 'tenant', 'landlord', 'rent', 'premises', 'property'],
            'nda': ['confidential', 'non-disclosure', 'proprietary', 'trade secret'],
            'service_agreement': ['services', 'provider', 'client', 'deliverables', 'scope of work'],
            'purchase_order': ['purchase', 'order', 'goods', 'delivery', 'payment terms'],
            'license_agreement': ['license', 'licensor', 'licensee', 'intellectual property'],
            'invoice': ['invoice', 'bill', 'amount due', 'payment', 'total'],
            'policy': ['policy', 'procedure', 'guidelines', 'rules', 'compliance'],
            'memo': ['memorandum', 'memo', 'to:', 'from:', 'subject:'],
            'legal_brief': ['court', 'case', 'plaintiff', 'defendant', 'jurisdiction'],
            'terms_of_service': ['terms', 'service', 'user', 'website', 'platform']
        }
        
        scores = {}
        for doc_type, keywords in type_indicators.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[doc_type] = score / len(keywords)  # Normalize by keyword count
        
        if scores:
            primary_type = max(scores, key=scores.get)
            confidence = scores[primary_type]
        else:
            primary_type = 'unknown'
            confidence = 0.0
        
        return {
            'primary_type': primary_type,
            'confidence': confidence,
            'all_scores': scores
        }
    
    def _identify_legal_clauses(self, text_content: str) -> List[Dict[str, Any]]:
        """Identify and classify legal clauses in the document"""
        
        clauses = []
        
        # Common legal clause patterns
        clause_patterns = {
            'termination_clause': {
                'keywords': ['terminate', 'termination', 'end', 'expire', 'dissolution', 'breach'],
                'patterns': [
                    r'(?:termination|terminate).*?(?:notice|days?|months?|immediately)',
                    r'(?:breach|violation).*?(?:terminate|end)',
                    r'(?:expire|expiration).*?(?:date|term)'
                ],
                'risk_level': 'high'
            },
            'payment_clause': {
                'keywords': ['payment', 'pay', 'compensation', 'fee', 'salary', 'remuneration'],
                'patterns': [
                    r'payment.*?(?:due|terms|schedule|amount)',
                    r'compensat.*?(?:\$|amount|sum)',
                    r'fee.*?(?:payable|due|amount)'
                ],
                'risk_level': 'medium'
            },
            'confidentiality_clause': {
                'keywords': ['confidential', 'proprietary', 'non-disclosure', 'trade secret'],
                'patterns': [
                    r'confidential.*?(?:information|data|material)',
                    r'non-disclosure.*?(?:agreement|obligation)',
                    r'proprietary.*?(?:information|rights)'
                ],
                'risk_level': 'high'
            },
            'liability_clause': {
                'keywords': ['liability', 'liable', 'damages', 'indemnify', 'limitation'],
                'patterns': [
                    r'liabilit.*?(?:limited|excluded|damages)',
                    r'indemnif.*?(?:against|from|for)',
                    r'damages.*?(?:consequential|incidental|punitive)'
                ],
                'risk_level': 'high'
            },
            'force_majeure': {
                'keywords': ['force majeure', 'act of god', 'unforeseeable', 'beyond control'],
                'patterns': [
                    r'force majeure.*?(?:event|circumstances)',
                    r'act of god.*?(?:prevent|hinder)',
                    r'unforeseeable.*?(?:event|circumstances)'
                ],
                'risk_level': 'medium'
            },
            'dispute_resolution': {
                'keywords': ['dispute', 'arbitration', 'mediation', 'jurisdiction', 'governing law'],
                'patterns': [
                    r'dispute.*?(?:resolution|arbitration|court)',
                    r'arbitration.*?(?:binding|rules|procedure)',
                    r'governing law.*?(?:jurisdiction|state|country)'
                ],
                'risk_level': 'medium'
            },
            'intellectual_property': {
                'keywords': ['intellectual property', 'copyright', 'trademark', 'patent', 'ownership'],
                'patterns': [
                    r'intellectual property.*?(?:rights|ownership)',
                    r'copyright.*?(?:ownership|license)',
                    r'trademark.*?(?:use|license|ownership)'
                ],
                'risk_level': 'high'
            },
            'non_compete': {
                'keywords': ['non-compete', 'competition', 'solicit', 'restraint of trade'],
                'patterns': [
                    r'non-compete.*?(?:period|restriction|covenant)',
                    r'solicit.*?(?:employees|customers|clients)',
                    r'restraint.*?(?:trade|competition)'
                ],
                'risk_level': 'high'
            },
            'warranty_clause': {
                'keywords': ['warranty', 'guarantee', 'representation', 'disclaim'],
                'patterns': [
                    r'warrant.*?(?:that|accuracy|performance)',
                    r'guarantee.*?(?:performance|quality)',
                    r'disclaim.*?(?:warranty|liability)'
                ],
                'risk_level': 'medium'
            }
        }
        
        paragraphs = [p.strip() for p in text_content.split('\n\n') if p.strip()]
        
        for i, paragraph in enumerate(paragraphs):
            paragraph_lower = paragraph.lower()
            
            for clause_type, clause_info in clause_patterns.items():
                # Check for keyword matches
                keyword_matches = sum(1 for keyword in clause_info['keywords'] if keyword in paragraph_lower)
                
                # Check for pattern matches
                pattern_matches = []
                for pattern in clause_info['patterns']:
                    matches = re.finditer(pattern, paragraph_lower, re.IGNORECASE | re.DOTALL)
                    pattern_matches.extend([match.group() for match in matches])
                
                if keyword_matches > 0 or pattern_matches:
                    # Extract associated dates
                    dates = self._extract_dates_from_text(paragraph)
                    
                    # Calculate confidence based on matches
                    confidence = min(0.9, (keyword_matches * 0.3 + len(pattern_matches) * 0.4) / len(clause_info['keywords']))
                    
                    clause = {
                        'type': clause_type,
                        'content': paragraph,
                        'paragraph_number': i + 1,
                        'confidence': confidence,
                        'risk_level': clause_info['risk_level'],
                        'keyword_matches': keyword_matches,
                        'pattern_matches': pattern_matches,
                        'associated_dates': dates,
                        'risk_explanation': self._explain_clause_risk(clause_type, paragraph)
                    }
                    
                    clauses.append(clause)
        
        return clauses
    
    def _assess_document_risks(self, text_content: str) -> Dict[str, Any]:
        """Assess potential risks in the document"""
        
        risks = {
            'high_risk_items': [],
            'medium_risk_items': [],
            'low_risk_items': [],
            'overall_risk_score': 0.0,
            'risk_categories': {}
        }
        
        text_lower = text_content.lower()
        
        # High-risk indicators
        high_risk_indicators = {
            'unlimited_liability': ['unlimited liability', 'unlimited damages', 'no limitation'],
            'automatic_renewal': ['automatic renewal', 'auto-renew', 'automatically renew'],
            'broad_indemnification': ['broadly indemnify', 'indemnify against all', 'unlimited indemnification'],
            'exclusive_dealing': ['exclusive', 'solely', 'exclusively deal'],
            'personal_guarantees': ['personal guarantee', 'personally liable', 'individual liability'],
            'liquidated_damages': ['liquidated damages', 'predetermined damages', 'fixed damages'],
            'broad_confidentiality': ['all information confidential', 'everything confidential'],
            'restrictive_non_compete': ['non-compete', 'restraint of trade', 'competition restriction'],
            'assignment_without_consent': ['assign without consent', 'transfer without approval'],
            'unilateral_modification': ['unilateral modification', 'change without consent']
        }
        
        # Medium-risk indicators
        medium_risk_indicators = {
            'short_notice_periods': ['immediate termination', 'without notice', '24 hours notice'],
            'penalty_clauses': ['penalty', 'fine', 'forfeit', 'liquidated damages'],
            'broad_warranties': ['all warranties', 'comprehensive warranty'],
            'jurisdiction_clauses': ['jurisdiction', 'governing law', 'venue'],
            'force_majeure_limitations': ['force majeure', 'act of god'],
            'intellectual_property_transfer': ['transfer ownership', 'assign rights'],
            'data_usage_rights': ['data usage', 'information rights', 'data ownership']
        }
        
        # Analyze high-risk items
        for risk_type, indicators in high_risk_indicators.items():
            matches = []
            for indicator in indicators:
                if indicator in text_lower:
                    # Find the sentence containing this indicator
                    sentences = text_content.split('.')
                    for sentence in sentences:
                        if indicator in sentence.lower():
                            matches.append(sentence.strip())
                            break
            
            if matches:
                risks['high_risk_items'].append({
                    'type': risk_type,
                    'description': self._get_risk_description(risk_type),
                    'impact': 'High',
                    'likelihood': 'Medium',
                    'mitigation': self._get_risk_mitigation(risk_type),
                    'found_text': matches
                })
        
        # Analyze medium-risk items
        for risk_type, indicators in medium_risk_indicators.items():
            matches = []
            for indicator in indicators:
                if indicator in text_lower:
                    sentences = text_content.split('.')
                    for sentence in sentences:
                        if indicator in sentence.lower():
                            matches.append(sentence.strip())
                            break
            
            if matches:
                risks['medium_risk_items'].append({
                    'type': risk_type,
                    'description': self._get_risk_description(risk_type),
                    'impact': 'Medium',
                    'likelihood': 'Medium',
                    'mitigation': self._get_risk_mitigation(risk_type),
                    'found_text': matches
                })
        
        # Calculate overall risk score
        high_risk_count = len(risks['high_risk_items'])
        medium_risk_count = len(risks['medium_risk_items'])
        
        risk_score = min(1.0, (high_risk_count * 0.3 + medium_risk_count * 0.15))
        risks['overall_risk_score'] = risk_score
        
        # Risk categories
        risks['risk_categories'] = {
            'financial': high_risk_count + medium_risk_count,
            'legal': len([r for r in risks['high_risk_items'] + risks['medium_risk_items'] 
                         if 'liability' in r['type'] or 'indemnif' in r['type']]),
            'operational': len([r for r in risks['high_risk_items'] + risks['medium_risk_items'] 
                               if 'termination' in r['type'] or 'renewal' in r['type']]),
            'compliance': len([r for r in risks['high_risk_items'] + risks['medium_risk_items'] 
                              if 'confidential' in r['type'] or 'data' in r['type']])
        }
        
        return risks
    
    def _explain_clause_risk(self, clause_type: str, content: str) -> str:
        """Explain why a specific clause might be risky"""
        
        risk_explanations = {
            'termination_clause': "Termination clauses can be risky if they allow for termination without sufficient notice or cause, potentially leaving parties vulnerable to sudden contract endings.",
            'payment_clause': "Payment clauses should be reviewed for clarity on amounts, timing, and consequences of late payment to avoid disputes.",
            'confidentiality_clause': "Broad confidentiality clauses may restrict future business activities or impose severe penalties for breaches.",
            'liability_clause': "Liability clauses that exclude or limit liability may leave one party exposed to significant financial risks.",
            'force_majeure': "Force majeure clauses may be too narrow or broad, potentially excusing performance inappropriately.",
            'dispute_resolution': "Dispute resolution clauses may favor one party through venue selection or arbitration requirements.",
            'intellectual_property': "IP clauses that broadly transfer rights may result in loss of valuable intellectual property.",
            'non_compete': "Non-compete clauses may be overly restrictive and could limit future employment opportunities.",
            'warranty_clause': "Warranty disclaimers may eliminate important protections, while broad warranties create liability exposure."
        }
        
        return risk_explanations.get(clause_type, "This clause type requires careful review for potential risks and obligations.")
    
    def _get_risk_description(self, risk_type: str) -> str:
        """Get description of specific risk type"""
        
        descriptions = {
            'unlimited_liability': "Unlimited liability exposure could result in catastrophic financial losses beyond the contract value.",
            'automatic_renewal': "Automatic renewal clauses may lock parties into unfavorable terms without opportunity to renegotiate.",
            'broad_indemnification': "Broad indemnification requirements could make you liable for the other party's actions or negligence.",
            'exclusive_dealing': "Exclusive dealing arrangements may limit business opportunities and growth potential.",
            'personal_guarantees': "Personal guarantees put individual assets at risk for business obligations.",
            'liquidated_damages': "Predetermined damage amounts may be disproportionate to actual losses incurred.",
            'broad_confidentiality': "Overly broad confidentiality terms may restrict normal business operations.",
            'restrictive_non_compete': "Restrictive non-compete clauses may severely limit future employment or business opportunities.",
            'assignment_without_consent': "Assignment clauses allowing transfer without consent may result in dealing with unknown parties.",
            'unilateral_modification': "Unilateral modification rights allow one party to change terms without negotiation.",
            'short_notice_periods': "Short notice periods may not provide adequate time to find alternatives or transition.",
            'penalty_clauses': "Penalty clauses may impose disproportionate financial consequences for minor breaches.",
            'jurisdiction_clauses': "Unfavorable jurisdiction or venue clauses may make legal proceedings expensive and inconvenient.",
            'intellectual_property_transfer': "IP transfer clauses may result in loss of valuable intellectual property rights."
        }
        
        return descriptions.get(risk_type, "This risk type requires careful legal review.")
    
    def _get_risk_mitigation(self, risk_type: str) -> str:
        """Get mitigation strategies for specific risk types"""
        
        mitigations = {
            'unlimited_liability': "Negotiate liability caps or limitations to protect against excessive financial exposure.",
            'automatic_renewal': "Add explicit notice requirements and renegotiation periods before renewal.",
            'broad_indemnification': "Limit indemnification to specific scenarios and exclude gross negligence or willful misconduct.",
            'exclusive_dealing': "Negotiate carve-outs for existing relationships or specific market segments.",
            'personal_guarantees': "Limit personal guarantees to specific amounts or time periods, or substitute corporate guarantees.",
            'liquidated_damages': "Ensure damage amounts are reasonable estimates of actual anticipated losses.",
            'broad_confidentiality': "Define confidentiality scope clearly and include standard exceptions.",
            'restrictive_non_compete': "Negotiate reasonable geographic and time limitations on non-compete restrictions.",
            'assignment_without_consent': "Require consent for assignments or limit assignments to affiliates only.",
            'unilateral_modification': "Require mutual consent for modifications or limit modification scope.",
            'short_notice_periods': "Negotiate reasonable notice periods that allow for adequate transition time.",
            'penalty_clauses': "Replace penalties with liquidated damages based on reasonable loss estimates.",
            'jurisdiction_clauses': "Negotiate neutral venue or mutual jurisdiction selection.",
            'intellectual_property_transfer': "Retain ownership or negotiate limited license grants instead of transfers."
        }
        
        return mitigations.get(risk_type, "Seek legal counsel to address this specific risk.")
    
    def _extract_critical_dates(self, text_content: str) -> List[Dict[str, Any]]:
        """Extract critical dates and their contexts"""
        
        critical_dates = []
        
        # Date patterns with context
        date_patterns = [
            r'(?:effective|start|begin|commence|commencement).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
            r'(?:expire|expiration|end|ending|termination|due).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
            r'(?:deadline|delivery|payment due|notice).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
            r'(?:renewal|review|renegotiat).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})'
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1)
                context = match.group(0)
                
                # Determine date type from context
                date_type = 'general'
                if any(word in context.lower() for word in ['effective', 'start', 'begin', 'commence']):
                    date_type = 'start_date'
                elif any(word in context.lower() for word in ['expire', 'end', 'termination']):
                    date_type = 'end_date'
                elif any(word in context.lower() for word in ['deadline', 'due']):
                    date_type = 'deadline'
                elif any(word in context.lower() for word in ['renewal', 'review']):
                    date_type = 'renewal_date'
                
                critical_dates.append({
                    'date': date_str,
                    'type': date_type,
                    'context': context.strip(),
                    'importance': self._assess_date_importance(date_type),
                    'days_from_now': self._calculate_days_from_now(date_str)
                })
        
        return critical_dates
    
    def _assess_date_importance(self, date_type: str) -> str:
        """Assess the importance level of a date"""
        
        importance_map = {
            'start_date': 'high',
            'end_date': 'high', 
            'deadline': 'high',
            'renewal_date': 'medium',
            'general': 'low'
        }
        
        return importance_map.get(date_type, 'low')
    
    def _calculate_days_from_now(self, date_str: str) -> Optional[int]:
        """Calculate days between now and the given date"""
        
        try:
            # Try different date formats
            formats = ['%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d', '%Y-%m-%d', '%B %d, %Y', '%B %d %Y']
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    today = datetime.now()
                    diff = (parsed_date - today).days
                    return diff
                except ValueError:
                    continue
            
            return None
        except:
            return None
    
    def _identify_parties(self, text_content: str) -> List[Dict[str, Any]]:
        """Identify parties involved in the document"""
        
        parties = []
        
        # Common party indicators
        party_patterns = [
            r'(?:party|parties).*?([A-Z][a-zA-Z\s,\.]+(?:Inc\.|LLC|Corporation|Corp\.|Company|Co\.|Ltd\.)?)',
            r'(?:between|among).*?([A-Z][a-zA-Z\s,\.]+(?:Inc\.|LLC|Corporation|Corp\.|Company|Co\.|Ltd\.)?).*?(?:and|&)',
            r'(?:client|customer|vendor|supplier|contractor|employee|employer).*?([A-Z][a-zA-Z\s,\.]+)',
            r'([A-Z][a-zA-Z\s]+(?:Inc\.|LLC|Corporation|Corp\.|Company|Co\.|Ltd\.)).*?(?:hereby|agrees|shall)'
        ]
        
        for pattern in party_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                party_name = match.group(1).strip()
                
                # Clean up the party name
                party_name = re.sub(r'[,\.]$', '', party_name)
                
                if len(party_name) > 2 and party_name not in [p['name'] for p in parties]:
                    parties.append({
                        'name': party_name,
                        'type': self._classify_party_type(party_name, text_content),
                        'context': match.group(0)
                    })
        
        return parties
    
    def _classify_party_type(self, party_name: str, text_content: str) -> str:
        """Classify the type of party (individual, corporation, etc.)"""
        
        if any(suffix in party_name for suffix in ['Inc.', 'LLC', 'Corporation', 'Corp.', 'Company', 'Co.', 'Ltd.']):
            return 'corporation'
        elif 'Mr.' in party_name or 'Mrs.' in party_name or 'Ms.' in party_name:
            return 'individual'
        elif any(word in text_content.lower() for word in ['employee', 'contractor']):
            return 'individual'
        else:
            return 'entity'
    
    def _identify_obligations(self, text_content: str) -> List[Dict[str, Any]]:
        """Identify obligations and duties in the document"""
        
        obligations = []
        
        # Obligation indicators
        obligation_patterns = [
            r'(?:shall|must|required to|obligated to|duty to)\s+([^.]{10,100})',
            r'(?:responsible for|liable for)\s+([^.]{10,100})',
            r'(?:agrees to|undertakes to|commits to)\s+([^.]{10,100})',
            r'(?:will|shall)\s+(?:provide|deliver|perform|pay|maintain)\s+([^.]{10,100})'
        ]
        
        for pattern in obligation_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                obligation_text = match.group(1).strip()
                
                obligations.append({
                    'description': obligation_text,
                    'type': self._classify_obligation_type(obligation_text),
                    'severity': self._assess_obligation_severity(obligation_text),
                    'full_context': match.group(0)
                })
        
        return obligations
    
    def _classify_obligation_type(self, obligation_text: str) -> str:
        """Classify the type of obligation"""
        
        text_lower = obligation_text.lower()
        
        if any(word in text_lower for word in ['pay', 'payment', 'remit', 'compensat']):
            return 'financial'
        elif any(word in text_lower for word in ['deliver', 'provide', 'supply', 'perform']):
            return 'performance'
        elif any(word in text_lower for word in ['maintain', 'keep', 'preserve', 'protect']):
            return 'maintenance'
        elif any(word in text_lower for word in ['confidential', 'disclose', 'proprietary']):
            return 'confidentiality'
        elif any(word in text_lower for word in ['comply', 'follow', 'adhere']):
            return 'compliance'
        else:
            return 'general'
    
    def _assess_obligation_severity(self, obligation_text: str) -> str:
        """Assess the severity/importance of an obligation"""
        
        text_lower = obligation_text.lower()
        
        high_severity_indicators = ['material', 'substantial', 'significant', 'critical', 'essential']
        medium_severity_indicators = ['reasonable', 'appropriate', 'timely', 'proper']
        
        if any(indicator in text_lower for indicator in high_severity_indicators):
            return 'high'
        elif any(indicator in text_lower for indicator in medium_severity_indicators):
            return 'medium'
        else:
            return 'low'
    
    def _identify_compliance_requirements(self, text_content: str) -> List[Dict[str, Any]]:
        """Identify compliance and regulatory requirements"""
        
        compliance_reqs = []
        
        # Compliance indicators
        compliance_patterns = [
            r'(?:comply with|compliance with|in accordance with)\s+([^.]{10,100})',
            r'(?:subject to|governed by)\s+([^.]{10,100})',
            r'(?:applicable|relevant)\s+(?:laws?|regulations?|rules?)\s+([^.]{10,100})',
            r'(?:regulatory|legal)\s+(?:requirements?|obligations?)\s+([^.]{10,100})'
        ]
        
        for pattern in compliance_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                requirement = match.group(1).strip()
                
                compliance_reqs.append({
                    'description': requirement,
                    'type': self._classify_compliance_type(requirement),
                    'jurisdiction': self._extract_jurisdiction(requirement),
                    'full_context': match.group(0)
                })
        
        return compliance_reqs
    
    def _classify_compliance_type(self, requirement: str) -> str:
        """Classify the type of compliance requirement"""
        
        req_lower = requirement.lower()
        
        if any(word in req_lower for word in ['data', 'privacy', 'gdpr', 'ccpa', 'hipaa']):
            return 'data_protection'
        elif any(word in req_lower for word in ['financial', 'securities', 'sox', 'accounting']):
            return 'financial'
        elif any(word in req_lower for word in ['environmental', 'epa', 'emission']):
            return 'environmental'
        elif any(word in req_lower for word in ['employment', 'labor', 'workplace', 'osha']):
            return 'employment'
        elif any(word in req_lower for word in ['tax', 'irs', 'taxation']):
            return 'tax'
        else:
            return 'general'
    
    def _extract_jurisdiction(self, requirement: str) -> Optional[str]:
        """Extract jurisdiction information from compliance requirement"""
        
        # Common jurisdiction patterns
        jurisdiction_patterns = [
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s+law',
            r'\bState\s+of\s+([A-Z][a-z]+)',
            r'\b(California|New York|Texas|Florida|Illinois)\b',
            r'\b(United States|US|USA)\b',
            r'\b(European Union|EU)\b'
        ]
        
        for pattern in jurisdiction_patterns:
            match = re.search(pattern, requirement, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_financial_terms(self, text_content: str) -> Dict[str, Any]:
        """Extract financial terms and conditions"""
        
        financial_terms = {
            'amounts': [],
            'payment_terms': [],
            'penalties': [],
            'interest_rates': [],
            'currencies': []
        }
        
        # Extract monetary amounts with context
        amount_pattern = r'(\$[\d,]+\.?\d*)\s*([^.]{0,50})'
        amount_matches = re.finditer(amount_pattern, text_content)
        
        for match in amount_matches:
            amount = match.group(1)
            context = match.group(2).strip()
            
            financial_terms['amounts'].append({
                'amount': amount,
                'context': context,
                'type': self._classify_financial_amount(context)
            })
        
        # Extract payment terms
        payment_patterns = [
            r'payment.*?(\d+)\s*days?',
            r'net\s*(\d+)',
            r'due.*?(\d+)\s*days?',
            r'payable.*?(immediately|upon|within.*?days?)'
        ]
        
        for pattern in payment_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                financial_terms['payment_terms'].append({
                    'term': match.group(0),
                    'period': match.group(1) if match.group(1) else 'immediate'
                })
        
        # Extract penalty information
        penalty_patterns = [
            r'penalty.*?(\$[\d,]+\.?\d*|\d+%)',
            r'late.*?fee.*?(\$[\d,]+\.?\d*)',
            r'interest.*?(\d+\.?\d*%)'
        ]
        
        for pattern in penalty_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                financial_terms['penalties'].append({
                    'description': match.group(0),
                    'amount': match.group(1)
                })
        
        return financial_terms
    
    def _classify_financial_amount(self, context: str) -> str:
        """Classify the type of financial amount based on context"""
        
        context_lower = context.lower()
        
        if any(word in context_lower for word in ['salary', 'wage', 'compensation']):
            return 'salary'
        elif any(word in context_lower for word in ['penalty', 'fine', 'damages']):
            return 'penalty'
        elif any(word in context_lower for word in ['fee', 'cost', 'charge']):
            return 'fee'
        elif any(word in context_lower for word in ['deposit', 'security']):
            return 'deposit'
        elif any(word in context_lower for word in ['total', 'sum', 'amount']):
            return 'total'
        else:
            return 'general'
    
    def _identify_termination_conditions(self, text_content: str) -> List[Dict[str, Any]]:
        """Identify conditions under which the agreement can be terminated"""
        
        termination_conditions = []
        
        # Termination patterns
        termination_patterns = [
            r'(?:terminate|termination).*?(?:for|upon|if|in the event).*?([^.]{10,150})',
            r'(?:breach|violation|default).*?(?:terminate|end).*?([^.]{10,150})',
            r'(?:notice).*?(?:terminate|termination).*?([^.]{10,150})',
            r'(?:expire|expiration).*?([^.]{10,150})'
        ]
        
        for pattern in termination_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                condition = match.group(1).strip()
                
                termination_conditions.append({
                    'condition': condition,
                    'type': self._classify_termination_type(condition),
                    'notice_required': self._extract_notice_period(match.group(0)),
                    'full_context': match.group(0)
                })
        
        return termination_conditions
    
    def _classify_termination_type(self, condition: str) -> str:
        """Classify the type of termination condition"""
        
        condition_lower = condition.lower()
        
        if any(word in condition_lower for word in ['breach', 'violation', 'default']):
            return 'for_cause'
        elif any(word in condition_lower for word in ['convenience', 'any reason', 'no reason']):
            return 'for_convenience'
        elif any(word in condition_lower for word in ['expire', 'expiration', 'end of term']):
            return 'expiration'
        elif any(word in condition_lower for word in ['bankruptcy', 'insolvency']):
            return 'insolvency'
        else:
            return 'other'
    
    def _extract_notice_period(self, termination_text: str) -> Optional[str]:
        """Extract notice period from termination clause"""
        
        notice_patterns = [
            r'(\d+)\s*days?\s*notice',
            r'(\d+)\s*months?\s*notice',
            r'(immediate|immediately)',
            r'(without notice)'
        ]
        
        for pattern in notice_patterns:
            match = re.search(pattern, termination_text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_dates_from_text(self, text: str) -> List[str]:
        """Extract all dates from a piece of text"""
        
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        return list(set(dates))  # Remove duplicates
    
    def _calculate_complexity_score(self, avg_word_length: float, avg_sentence_length: float) -> str:
        """Calculate document complexity score"""
        
        # Simple complexity scoring based on word and sentence length
        if avg_word_length > 6 and avg_sentence_length > 20:
            return 'high'
        elif avg_word_length > 5 or avg_sentence_length > 15:
            return 'medium'
        else:
            return 'low'
    
    def _assess_formality(self, text_content: str) -> float:
        """Assess the formality level of the document"""
        
        formal_indicators = ['hereby', 'whereas', 'pursuant', 'notwithstanding', 'aforementioned', 'heretofore']
        informal_indicators = ['you', 'we', 'I', 'can\'t', 'won\'t', 'don\'t']
        
        text_lower = text_content.lower()
        
        formal_count = sum(1 for indicator in formal_indicators if indicator in text_lower)
        informal_count = sum(1 for indicator in informal_indicators if indicator in text_lower)
        
        total_indicators = formal_count + informal_count
        if total_indicators == 0:
            return 0.5  # Neutral
        
        return formal_count / total_indicators
    
    def _get_document_type_value(self, document) -> str:
        """Safely get document type value from document object"""
        try:
            if hasattr(document, 'document_type'):
                doc_type = document.document_type
                # If it's an enum, get the value
                if hasattr(doc_type, 'value'):
                    return doc_type.value
                # If it's already a string
                elif isinstance(doc_type, str):
                    return doc_type
                # If it's a dict
                elif isinstance(doc_type, dict):
                    return doc_type.get('value', 'unknown')
                else:
                    return str(doc_type)
            else:
                return 'unknown'
        except Exception as e:
            print(f"Warning: Could not determine document type: {e}")
            return 'unknown'
    
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
                # For document_summary, preserve the entire structure
                if field_name == 'document_summary':
                    data[field_name] = field_data['value']
                else:
                    data[field_name] = field_data['value']
            else:
                data[field_name] = field_data
        
        if tables:
            data['tables'] = tables
        
        # Ensure all analysis data is preserved
        if 'document_summary' in extracted_fields:
            summary_data = extracted_fields['document_summary'].get('value', {})
            if isinstance(summary_data, dict):
                # Merge the comprehensive analysis into the main data
                data.update({
                    'legal_clauses': summary_data.get('legal_clauses', []),
                    'risk_assessment': summary_data.get('risk_assessment', {}),
                    'key_dates': summary_data.get('key_dates', []),
                    'parties_involved': summary_data.get('parties_involved', []),
                    'financial_terms': summary_data.get('financial_terms', {}),
                    'document_analysis': summary_data.get('basic_info', {}),
                    'comprehensive_analysis': summary_data
                })
        
        return {
            'data': data,
            'confidence': overall_confidence,
            'flagged_fields': flagged_items,
            'method': method,
            'extracted_fields': extracted_fields  # Preserve original structure too
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

    def _enhanced_field_extraction(self, text_content: str, field_name: str, field_type: str, visual_data: Dict) -> Dict[str, Any]:
        """Enhanced field extraction using multiple approaches"""
        
        field_result = {
            'value': None,
            'confidence': 0.0,
            'location': None,
            'context': None,
            'extraction_method': 'enhanced_patterns',
            'alternatives': []
        }
        
        # Method 1: Enhanced pattern matching with field-specific patterns
        pattern_result = self._extract_with_enhanced_patterns(text_content, field_name, field_type)
        if pattern_result:
            field_result = pattern_result
            field_result['extraction_method'] = 'enhanced_patterns'
        
        # Method 2: Context-aware extraction
        context_result = self._extract_with_context_analysis(text_content, field_name, field_type)
        if context_result and (not field_result['value'] or context_result['confidence'] > field_result['confidence']):
            if field_result['value']:
                field_result['alternatives'].append(field_result.copy())
            field_result.update(context_result)
            field_result['extraction_method'] = 'context_analysis'
        
        # Method 3: Semantic proximity extraction
        semantic_result = self._extract_with_semantic_proximity(text_content, field_name, field_type)
        if semantic_result and (not field_result['value'] or semantic_result['confidence'] > field_result['confidence']):
            if field_result['value']:
                field_result['alternatives'].append(field_result.copy())
            field_result.update(semantic_result)
            field_result['extraction_method'] = 'semantic_proximity'
        
        return field_result if field_result['value'] else None
    
    def _extract_with_enhanced_patterns(self, text: str, field_name: str, field_type: str) -> Dict[str, Any]:
        """Enhanced pattern matching with comprehensive field-specific patterns"""
        
        enhanced_patterns = {
            'date': [
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
                r'\b(\d{4}-\d{2}-\d{2})\b',
                r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b',
                r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b',
                r'(?:effective|start|begin|commence|end|expire|due|deadline)[:\s]*([^.\n]{0,50}(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}))',
            ],
            'name': [
                r'\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
                r'\b([A-Z][a-z]+(?:\s+[A-Z]\.)+\s+[A-Z][a-z]+)\b',
                r'(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?)\s+([A-Z][a-z]+(?:\s+[A-Z]\.)*\s+[A-Z][a-z]+)',
                r'(?:employee|contractor|client|party|person|individual)[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.)*\s+[A-Z][a-z]+)',
                r'(?:signed by|signature)[:\s]*([A-Z][a-z]+(?:\s+[A-Z]\.)*\s+[A-Z][a-z]+)',
            ],
            'amount': [
                r'\$[\d,]+\.?\d*',
                r'USD\s*[\d,]+\.?\d*',
                r'EUR\s*[\d,]+\.?\d*',
                r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD|EUR|GBP)\b',
                r'(?:amount|sum|total|cost|price|fee|salary|wage|payment|compensation)[:\s]*\$?[\d,]+\.?\d*',
                r'(?:\$|USD|EUR|GBP)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            ],
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                r'(?:email|e-mail|contact)[:\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
            ],
            'phone': [
                r'\b\d{3}-\d{3}-\d{4}\b',
                r'\(\d{3}\)\s*\d{3}-\d{4}\b',
                r'\b\d{3}\.\d{3}\.\d{4}\b',
                r'\+1\s*\d{3}\s*\d{3}\s*\d{4}',
                r'(?:phone|tel|telephone|mobile|cell)[:\s]*([+\d\s\(\)-]+)',
            ],
            'address': [
                r'\b\d+\s+[A-Z][A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl)\b',
                r'(?:address|location|premises)[:\s]*(.+?(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl)[^.]*)',
                r'\b([A-Z][a-z]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)\b',
            ],
            'contract_id': [
                r'(?:contract|agreement)\s*(?:number|no\.?|#|id)[:\s]*([A-Z0-9-]+)',
                r'\b(C\d{4,})\b',
                r'\b(CTR-[A-Z0-9-]+)\b',
                r'(?:reference|ref)[:\s]*([A-Z0-9-]+)',
            ],
            'percentage': [
                r'\b(\d+(?:\.\d+)?%)\b',
                r'(?:rate|percentage|percent)[:\s]*(\d+(?:\.\d+)?%?)',
                r'\b(\d+(?:\.\d+)?\s*percent)\b',
            ],
            'term': [
                r'(?:term|duration|period)[:\s]*([^.\n]+)',
                r'\b(\d+\s*(?:year|month|day|week)s?)\b',
                r'(?:for a period of|lasting|duration of)[:\s]*([^.\n]+)',
            ]
        }
        
        # Get patterns for field type and name
        field_patterns = enhanced_patterns.get(field_type, [])
        
        # Add field-name specific patterns
        field_name_lower = field_name.lower()
        if 'date' in field_name_lower:
            field_patterns.extend(enhanced_patterns['date'])
        elif any(term in field_name_lower for term in ['amount', 'price', 'cost', 'salary', 'fee', 'payment']):
            field_patterns.extend(enhanced_patterns['amount'])
        elif 'email' in field_name_lower:
            field_patterns.extend(enhanced_patterns['email'])
        elif 'phone' in field_name_lower:
            field_patterns.extend(enhanced_patterns['phone'])
        elif 'name' in field_name_lower:
            field_patterns.extend(enhanced_patterns['name'])
        elif 'address' in field_name_lower:
            field_patterns.extend(enhanced_patterns['address'])
        elif any(term in field_name_lower for term in ['contract', 'agreement', 'id']):
            field_patterns.extend(enhanced_patterns['contract_id'])
        
        # Search for patterns
        for i, pattern in enumerate(field_patterns):
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                value = match.group(1) if len(match.groups()) > 0 else match.group()
                if value and len(value.strip()) > 1:
                    confidence = 0.9 - (i * 0.05)  # Higher confidence for earlier patterns
                    location = self._find_value_location(text, value)
                    context = self._get_field_context(text, value, 200)
                    
                    return {
                        'value': value.strip(),
                        'confidence': max(0.1, confidence),
                        'location': location,
                        'context': context
                    }
        
        return None
    
    def _extract_with_context_analysis(self, text: str, field_name: str, field_type: str) -> Dict[str, Any]:
        """Extract using contextual clues and surrounding text analysis"""
        
        # Define context keywords for different field types
        context_keywords = {
            'date': ['effective', 'signed', 'executed', 'dated', 'expires', 'due', 'deadline', 'term', 'start', 'end'],
            'name': ['employee', 'contractor', 'client', 'party', 'person', 'individual', 'signatory', 'witness'],
            'amount': ['salary', 'wage', 'fee', 'cost', 'price', 'total', 'sum', 'payment', 'compensation', 'value'],
            'email': ['contact', 'reach', 'correspondence', 'communication', 'email', 'e-mail'],
            'phone': ['contact', 'call', 'telephone', 'mobile', 'cell', 'phone'],
            'address': ['located', 'situated', 'address', 'premises', 'facility', 'office', 'location']
        }
        
        field_keywords = context_keywords.get(field_type, [])
        
        # Search for field name variations
        field_variations = [
            field_name.lower(),
            field_name.replace('_', ' ').lower(),
            field_name.replace('-', ' ').lower()
        ]
        
        best_match = None
        best_confidence = 0.0
        
        for variation in field_variations:
            for keyword in field_keywords + [variation]:
                # Look for patterns like "keyword: value"
                pattern = rf'{re.escape(keyword)}[:\s]+([^.\n]+)'
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    potential_value = match.group(1).strip()
                    cleaned_value = self._clean_extracted_value(potential_value, field_type)
                    
                    if cleaned_value and self._validate_value_type(cleaned_value, field_type):
                        confidence = 0.8 if keyword == variation else 0.6
                        location = self._find_value_location(text, cleaned_value)
                        context = self._get_field_context(text, cleaned_value, 200)
                        
                        if confidence > best_confidence:
                            best_match = {
                                'value': cleaned_value,
                                'confidence': confidence,
                                'location': location,
                                'context': context
                            }
                            best_confidence = confidence
        
        return best_match
    
    def _extract_with_semantic_proximity(self, text: str, field_name: str, field_type: str) -> Dict[str, Any]:
        """Extract using semantic proximity and related terms"""
        
        # Find sentences containing the field name or related terms
        sentences = re.split(r'[.!?]\s+', text)
        
        field_terms = [
            field_name.lower(),
            field_name.replace('_', ' ').lower(),
            field_name.replace('-', ' ').lower()
        ]
        
        # Add semantic equivalents
        semantic_map = {
            'effective_date': ['start date', 'commencement', 'beginning', 'effective'],
            'expiration_date': ['end date', 'termination', 'expiry', 'conclusion'],
            'party_name': ['party', 'entity', 'organization', 'individual'],
            'contract_value': ['amount', 'sum', 'value', 'consideration', 'fee'],
            'payment_terms': ['payment', 'remuneration', 'compensation', 'fee structure'],
            'termination_clause': ['termination', 'end', 'conclude', 'cancel'],
            'penalty_clause': ['penalty', 'fine', 'damages', 'liquidated damages']
        }
        
        if field_name.lower() in semantic_map:
            field_terms.extend(semantic_map[field_name.lower()])
        
        relevant_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for term in field_terms:
                if term in sentence_lower:
                    relevant_sentences.append(sentence)
                    break
        
        # Extract from most relevant sentences
        for sentence in relevant_sentences:
            result = self._extract_with_enhanced_patterns(sentence, field_name, field_type)
            if result and result.get('value'):
                # Boost confidence for semantic proximity
                result['confidence'] = min(0.95, result['confidence'] + 0.1)
                return result
        
        return None
    
    def _extract_structured_entities(self, text_content: str) -> Dict[str, Any]:
        """Extract structured entities from the document"""
        
        entities = {
            'people': [],
            'organizations': [],
            'locations': [],
            'dates': [],
            'monetary_values': [],
            'email_addresses': [],
            'phone_numbers': [],
            'addresses': [],
            'percentages': [],
            'measurements': []
        }
        
        # Enhanced entity patterns
        entity_patterns = {
            'people': [
                r'\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
                r'(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?)\s+([A-Z][a-z]+(?:\s+[A-Z]\.)*\s+[A-Z][a-z]+)',
            ],
            'organizations': [
                r'\b([A-Z][A-Za-z\s]+(?:Inc\.?|LLC|Corporation|Corp\.?|Company|Co\.?|Ltd\.?|Limited))\b',
                r'\b([A-Z][A-Za-z\s]+ (?:University|College|School|Institute))\b',
            ],
            'dates': [
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
                r'\b(\d{4}-\d{2}-\d{2})\b',
                r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b',
            ],
            'monetary_values': [
                r'(\$[\d,]+\.?\d*)',
                r'(USD\s*[\d,]+\.?\d*)',
                r'(EUR\s*[\d,]+\.?\d*)',
            ],
            'email_addresses': [
                r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b',
            ],
            'phone_numbers': [
                r'\b(\d{3}-\d{3}-\d{4})\b',
                r'(\(\d{3}\)\s*\d{3}-\d{4})\b',
                r'\b(\d{3}\.\d{3}\.\d{4})\b',
            ],
            'percentages': [
                r'\b(\d+(?:\.\d+)?%)\b',
            ]
        }
        
        for entity_type, patterns in entity_patterns.items():
            found_entities = []
            for pattern in patterns:
                matches = re.finditer(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    entity_value = match.group(1)
                    if entity_value not in [e['value'] for e in found_entities]:
                        found_entities.append({
                            'value': entity_value,
                            'position': match.start(),
                            'confidence': 0.8
                        })
            
            entities[entity_type] = found_entities[:10]  # Limit to top 10 per type
        
        return entities
    
    def _analyze_document_type_and_structure(self, text_content: str, document) -> Dict[str, Any]:
        """Analyze document type and structure"""
        
        analysis = {
            'document_type_analysis': {},
            'structural_elements': {},
            'content_organization': {},
            'complexity_metrics': {}
        }
        
        # Document type indicators
        legal_indicators = ['agreement', 'contract', 'party', 'whereas', 'hereby', 'covenant']
        financial_indicators = ['payment', 'invoice', 'amount', 'fee', 'cost', 'billing']
        technical_indicators = ['specification', 'procedure', 'protocol', 'guidelines']
        
        text_lower = text_content.lower()
        
        type_scores = {
            'legal': sum(1 for indicator in legal_indicators if indicator in text_lower),
            'financial': sum(1 for indicator in financial_indicators if indicator in text_lower),
            'technical': sum(1 for indicator in technical_indicators if indicator in text_lower)
        }
        
        analysis['document_type_analysis'] = {
            'predicted_type': max(type_scores, key=type_scores.get),
            'type_confidence_scores': type_scores,
            'file_extension': getattr(document, 'original_filename', '').split('.')[-1] if hasattr(document, 'original_filename') else 'unknown'
        }
        
        # Structural analysis
        analysis['structural_elements'] = {
            'paragraph_count': len(text_content.split('\n\n')),
            'sentence_count': len(re.split(r'[.!?]+', text_content)),
            'word_count': len(text_content.split()),
            'has_numbered_sections': bool(re.search(r'^\d+\.', text_content, re.MULTILINE)),
            'has_bullet_points': bool(re.search(r'^\s*[•\-\*]', text_content, re.MULTILINE)),
        }
        
        return analysis
    
    def _extract_enhanced_tables(self, text_content: str) -> List[Dict[str, Any]]:
        """Extract tables with enhanced detection and processing"""
        
        tables = []
        
        # Method 1: Tab-separated tables
        lines = text_content.split('\n')
        current_table = []
        in_table = False
        
        for line_num, line in enumerate(lines):
            if '\t' in line or len(re.split(r'\s{3,}', line)) > 2:
                if not in_table:
                    in_table = True
                    current_table = []
                
                # Split by tabs or multiple spaces
                if '\t' in line:
                    row = [cell.strip() for cell in line.split('\t') if cell.strip()]
                else:
                    row = [cell.strip() for cell in re.split(r'\s{3,}', line) if cell.strip()]
                
                if len(row) > 1:
                    current_table.append(row)
            else:
                if in_table and current_table and len(current_table) > 1:
                    tables.append(self._create_table_structure(current_table, line_num))
                current_table = []
                in_table = False
        
        # Method 2: Pipe-separated tables
        pipe_table_pattern = r'\|([^|\n]+\|[^|\n]*)+\|'
        pipe_matches = re.finditer(pipe_table_pattern, text_content, re.MULTILINE)
        
        for match in pipe_matches:
            table_text = match.group()
            rows = []
            for line in table_text.split('\n'):
                if '|' in line:
                    row = [cell.strip() for cell in line.split('|') if cell.strip()]
                    if len(row) > 1:
                        rows.append(row)
            
            if len(rows) > 1:
                tables.append(self._create_table_structure(rows, text_content.find(table_text)))
        
        return tables
    
    def _create_table_structure(self, rows: List[List[str]], position: int) -> Dict[str, Any]:
        """Create structured table representation"""
        
        if not rows:
            return {}
        
        headers = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []
        
        return {
            'headers': headers,
            'rows': data_rows,
            'row_count': len(data_rows),
            'column_count': len(headers),
            'position': position,
            'confidence': 0.8 if len(data_rows) > 0 else 0.5
        }
    
    def _extract_from_visual_data(self, visual_data: Dict, parsed_request: Dict) -> Dict[str, Any]:
        """Extract data from visual elements if available"""
        
        visual_fields = {}
        
        if visual_data.get('text_content'):
            # Use OCR text for additional extraction
            ocr_text = visual_data['text_content']
            for field in parsed_request.get('fields', []):
                field_name = field.get('name', '')
                field_type = field.get('type', 'text')
                
                ocr_result = self._extract_with_enhanced_patterns(ocr_text, field_name, field_type)
                if ocr_result:
                    visual_fields[f"{field_name}_from_ocr"] = ocr_result
        
        if visual_data.get('layout_analysis'):
            visual_fields['layout_info'] = visual_data['layout_analysis']
        
        return visual_fields
    
    def _calculate_comprehensive_confidence(self, comprehensive_result: Dict) -> float:
        """Calculate overall confidence score for comprehensive extraction"""
        
        confidence_factors = []
        
        # Field extraction confidence
        field_extractions = comprehensive_result.get('field_extractions', {})
        if field_extractions:
            field_confidences = [field['confidence'] for field in field_extractions.values() if 'confidence' in field]
            if field_confidences:
                confidence_factors.append(sum(field_confidences) / len(field_confidences))
        
        # Entity extraction confidence
        structured_entities = comprehensive_result.get('structured_entities', {})
        entity_count = sum(len(entities) for entities in structured_entities.values() if isinstance(entities, list))
        if entity_count > 0:
            confidence_factors.append(min(0.9, entity_count / 20))  # Normalize to 0-1
        
        # Table extraction confidence
        tables = comprehensive_result.get('tables', [])
        if tables:
            table_confidences = [table.get('confidence', 0.5) for table in tables]
            confidence_factors.append(sum(table_confidences) / len(table_confidences))
        
        # Legal analysis confidence (if available)
        legal_analysis = comprehensive_result.get('legal_analysis', {})
        if legal_analysis and not legal_analysis.get('error'):
            confidence_factors.append(0.8)
        
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.3
    
    def _format_comprehensive_local_result(self, comprehensive_result: Dict) -> Dict[str, Any]:
        """Format comprehensive extraction result"""
        
        # Combine field extractions into main extracted_data
        extracted_data = {}
        field_extractions = comprehensive_result.get('field_extractions', {})
        
        for field_name, field_data in field_extractions.items():
            extracted_data[field_name] = field_data.get('value')
        
        # Add structured entities to extracted data
        structured_entities = comprehensive_result.get('structured_entities', {})
        for entity_type, entities in structured_entities.items():
            if entities:
                extracted_data[f'{entity_type}_found'] = [e['value'] for e in entities[:5]]  # Top 5
        
        # Add legal analysis if available
        legal_analysis = comprehensive_result.get('legal_analysis', {})
        if legal_analysis and not legal_analysis.get('error'):
            extracted_data['legal_analysis_summary'] = {
                'clauses_found': len(legal_analysis.get('identified_clauses', [])),
                'obligations_found': len(legal_analysis.get('obligations', [])),
                'risks_identified': len(legal_analysis.get('risk_flags', []))
            }
        
        overall_confidence = comprehensive_result.get('confidence_metrics', {}).get('overall_confidence', 0.3)
        
        # Flag low-confidence fields
        flagged_fields = []
        for field_name, field_data in field_extractions.items():
            if field_data.get('confidence', 0) < 0.5:
                flagged_fields.append(field_name)
        
        return {
            'data': extracted_data,
            'confidence': overall_confidence,
            'flagged_fields': flagged_fields,
            'method': 'enhanced_local_extraction',
            'tables': comprehensive_result.get('tables', []),
            'document_analysis': comprehensive_result.get('document_analysis', {}),
            'extraction_metadata': {
                'fields_extracted': len(field_extractions),
                'entities_found': sum(len(entities) for entities in structured_entities.values() if isinstance(entities, list)),
                'tables_found': len(comprehensive_result.get('tables', [])),
                'confidence_breakdown': comprehensive_result.get('confidence_metrics', {})
            }
        }
    
    def _clean_extracted_value(self, value: str, field_type: str) -> str:
        """Clean and normalize extracted values"""
        
        if not value:
            return value
        
        # General cleaning
        value = value.strip()
        value = re.sub(r'\s+', ' ', value)  # Normalize whitespace
        
        # Type-specific cleaning
        if field_type == 'amount':
            # Remove extra text, keep only amount
            amount_match = re.search(r'[\d,]+\.?\d*', value)
            if amount_match:
                value = amount_match.group()
        elif field_type == 'date':
            # Normalize date format
            date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}', value)
            if date_match:
                value = date_match.group()
        elif field_type == 'phone':
            # Clean phone number
            value = re.sub(r'[^\d\(\)\-\+\s]', '', value)
            value = re.sub(r'\s+', ' ', value).strip()
        
        return value
    
    def _validate_value_type(self, value: str, field_type: str) -> bool:
        """Validate if a value matches the expected type"""
        
        if not value:
            return False
        
        type_validators = {
            'date': lambda v: bool(re.search(r'\d{1,4}[/-]\d{1,2}[/-]\d{1,4}|\d{4}-\d{2}-\d{2}', v)),
            'email': lambda v: bool(re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', v)),
            'phone': lambda v: bool(re.search(r'\d{3,}', v)),
            'amount': lambda v: bool(re.search(r'[\d,]+\.?\d*', v)),
            'percentage': lambda v: bool(re.search(r'\d+(?:\.\d+)?%?', v)),
            'name': lambda v: len(v.split()) >= 2 and all(word.replace('.', '').isalpha() for word in v.split())
        }
        
        validator = type_validators.get(field_type)
        return validator(value) if validator else True
    
    def _find_value_location(self, text: str, value: str) -> Dict[str, Any]:
        """Find the location of a value in the text"""
        
        index = text.find(str(value))
        if index == -1:
            return {'page': 'unknown', 'position': 'unknown', 'line': 'unknown'}
        
        # Estimate page number (assuming ~2500 chars per page)
        page_num = (index // 2500) + 1
        
        # Find line number
        lines_before = text[:index].count('\n')
        line_num = lines_before + 1
        
        return {
            'page': page_num,
            'position': index,
            'line': line_num
        }

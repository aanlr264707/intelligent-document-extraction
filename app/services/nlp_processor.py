import os
import openai
import json
import re
from typing import Dict, List, Any, Optional

# Enable transformers for full NLP capabilities
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
    print("Transformers enabled - full NLP capabilities available")
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Transformers not available - falling back to basic NLP")

class NLPProcessor:
    """Processes natural language extraction requests and interprets user requirements"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        
        # Initialize Hugging Face models - will be loaded lazily
        self.intent_classifier = None
        self.ner_pipeline = None
        self.text_classifier = None
        self.question_answering = None
        self._models_initialized = False
        
        print("NLPProcessor initialized (models will load on demand)")
    
    def _initialize_transformers_models(self):
        """Initialize Hugging Face transformer models (lazy loading)"""
        if self._models_initialized or not TRANSFORMERS_AVAILABLE:
            if not TRANSFORMERS_AVAILABLE:
                print("Transformers not available - using rule-based NLP only")
            return
            
        self._models_initialized = True
        print("Loading Transformers models...")
        
        # Import transformers here only when needed
        try:
            from transformers import pipeline
        except ImportError:
            print("Transformers not available")
            return
        
        try:
            # Intent classification for understanding extraction requests
            self.intent_classifier = pipeline(
                "text-classification",
                model="microsoft/DialoGPT-medium",
                return_all_scores=True
            )
            print("Intent classifier initialized successfully")
        except Exception as e:
            print(f"Failed to initialize intent classifier: {e}")
        
        try:
            # Named Entity Recognition for extracting entities
            self.ner_pipeline = pipeline(
                "ner",
                model="dbmdz/bert-large-cased-finetuned-conll03-english",
                aggregation_strategy="simple"
            )
            print("NER pipeline initialized successfully")
        except Exception as e:
            print(f"Failed to initialize NER pipeline: {e}")
        
        try:
            # Document classification
            self.text_classifier = pipeline(
                "text-classification",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
            print("Text classifier initialized successfully")
        except Exception as e:
            print(f"Failed to initialize text classifier: {e}")
        
        try:
            # Question answering for document queries
            self.question_answering = pipeline(
                "question-answering",
                model="distilbert-base-cased-distilled-squad"
            )
            print("Question-answering pipeline initialized successfully")
        except Exception as e:
            print(f"Failed to initialize question-answering pipeline: {e}")
    
    def parse_extraction_request(self, natural_language_request: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """Parse natural language request into structured extraction requirements"""
        
        if self.openai_api_key:
            return self._parse_with_openai(natural_language_request, document_type)
        else:
            return self._parse_with_local_models(natural_language_request, document_type)
    
    def _parse_with_openai(self, request: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """Parse using OpenAI GPT models"""
        
        system_prompt = """You are an AI assistant that parses natural language extraction requests for document processing.
        
        Given a user's natural language request, extract the following information:
        1. Fields to extract (list of field names)
        2. Field types (text, date, number, table, etc.)
        3. Extraction context (any specific instructions)
        4. Output preferences
        5. Special requirements (legal clauses, risk analysis, etc.)
        
        Return the result as a JSON object with the following structure:
        {
            "fields": [{"name": "field_name", "type": "field_type", "description": "field_description"}],
            "context": "extraction_context",
            "special_requirements": ["requirement1", "requirement2"],
            "legal_analysis": true/false,
            "table_extraction": true/false,
            "risk_analysis": true/false
        }"""
        
        user_prompt = f"""Document type: {document_type or 'Unknown'}
        User request: {request}
        
        Parse this extraction request:"""
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai.api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"OpenAI parsing failed: {e}")
            return self._parse_with_local_models(request, document_type)
    
    def _parse_with_local_models(self, request: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """Parse using local models and rule-based approach"""
        
        field_patterns = {
            'date': r'\b(date|when|time|deadline|effective|expiry|expiration)\b',
            'name': r'\b(name|party|parties|person|entity|company|organization)\b',
            'amount': r'\b(amount|price|cost|fee|payment|salary|wage|penalty)\b',
            'address': r'\b(address|location|place|where)\b',
            'clause': r'\b(clause|term|condition|provision|section)\b',
            'obligation': r'\b(obligation|duty|responsibility|requirement|must|shall)\b',
            'risk': r'\b(risk|penalty|liability|consequence|breach|violation)\b'
        }
        
        fields = []
        special_requirements = []
        
        request_lower = request.lower()
        
        for field_type, pattern in field_patterns.items():
            if re.search(pattern, request_lower):
                field_matches = self._extract_field_names(request, field_type)
                fields.extend(field_matches)
        
        if re.search(r'\b(clause|legal|contract|agreement)\b', request_lower):
            special_requirements.append('legal_analysis')
        
        if re.search(r'\b(table|tabular|row|column|grid)\b', request_lower):
            special_requirements.append('table_extraction')
        
        if re.search(r'\b(risk|penalty|liability|flag|warning)\b', request_lower):
            special_requirements.append('risk_analysis')
        
        return {
            'fields': fields,
            'context': request,
            'special_requirements': special_requirements,
            'legal_analysis': 'legal_analysis' in special_requirements,
            'table_extraction': 'table_extraction' in special_requirements,
            'risk_analysis': 'risk_analysis' in special_requirements
        }
    
    def _extract_field_names(self, request: str, field_type: str) -> List[Dict[str, str]]:
        """Extract specific field names from request text"""
        
        field_name_patterns = {
            'date': ['effective date', 'start date', 'end date', 'expiry date', 'signing date', 'termination date'],
            'name': ['party name', 'company name', 'client name', 'contractor name', 'entity name'],
            'amount': ['contract value', 'payment amount', 'penalty amount', 'fee', 'cost'],
            'clause': ['termination clause', 'penalty clause', 'payment clause', 'liability clause'],
            'obligation': ['payment obligation', 'delivery obligation', 'performance obligation']
        }
        
        fields = []
        request_lower = request.lower()
        
        if field_type in field_name_patterns:
            for field_name in field_name_patterns[field_type]:
                if field_name in request_lower:
                    fields.append({
                        'name': field_name,
                        'type': field_type,
                        'description': f'Extract {field_name} from the document'
                    })
        
        if not fields:
            fields.append({
                'name': field_type,
                'type': field_type,
                'description': f'Extract {field_type} information from the document'
            })
        
        return fields
    
    def validate_extraction_request(self, parsed_request: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance the parsed extraction request"""
        
        if 'fields' not in parsed_request:
            parsed_request['fields'] = []
        
        if 'context' not in parsed_request:
            parsed_request['context'] = ''
        
        if 'special_requirements' not in parsed_request:
            parsed_request['special_requirements'] = []
        
        parsed_request.setdefault('legal_analysis', False)
        parsed_request.setdefault('table_extraction', False)
        parsed_request.setdefault('risk_analysis', False)
        
        return parsed_request
    
    def generate_field_mapping(self, extracted_fields: List[str], user_schema: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate dynamic field mapping between extracted fields and user schema"""
        
        if not user_schema:
            return {field: field for field in extracted_fields}
        
        mapping = {}
        
        for extracted_field in extracted_fields:
            best_match = self._find_best_field_match(extracted_field, list(user_schema.keys()))
            if best_match:
                mapping[extracted_field] = best_match
            else:
                mapping[extracted_field] = extracted_field
        
        return mapping
    
    def _find_best_field_match(self, field: str, schema_fields: List[str]) -> Optional[str]:
        """Find the best matching field in user schema"""
        
        field_lower = field.lower()
        
        for schema_field in schema_fields:
            if field_lower == schema_field.lower():
                return schema_field
        
        for schema_field in schema_fields:
            if field_lower in schema_field.lower() or schema_field.lower() in field_lower:
                return schema_field
        
        similarity_map = {
            'date': ['time', 'when', 'timestamp'],
            'name': ['title', 'label', 'identifier'],
            'amount': ['value', 'number', 'quantity'],
            'address': ['location', 'place', 'where']
        }
        
        for schema_field in schema_fields:
            schema_lower = schema_field.lower()
            for key, synonyms in similarity_map.items():
                if key in field_lower and any(syn in schema_lower for syn in synonyms):
                    return schema_field
        
        return None

    def analyze_extraction_intent(self, request: str) -> Dict[str, Any]:
        """Analyze the intent behind an extraction request using transformers"""
        
        # Lazy load models
        self._initialize_transformers_models()
        
        if not TRANSFORMERS_AVAILABLE or not self.ner_pipeline:
            return self._basic_intent_analysis(request)
        
        try:
            # Extract named entities
            entities = self.ner_pipeline(request)
            
            # Categorize the request
            categories = self._categorize_extraction_request(request)
            
            # Extract key information
            key_info = self._extract_key_information(request, entities)
            
            return {
                'entities': entities,
                'categories': categories,
                'key_information': key_info,
                'complexity': self._assess_complexity(request, entities),
                'suggested_fields': self._suggest_extraction_fields(entities, categories)
            }
            
        except Exception as e:
            return {'error': f'Intent analysis failed: {str(e)}'}
    
    def extract_entities_from_text(self, text: str) -> Dict[str, Any]:
        """Extract named entities from document text"""
        
        if not TRANSFORMERS_AVAILABLE or not self.ner_pipeline:
            return {'entities': [], 'error': 'NER pipeline not available'}
        
        try:
            entities = self.ner_pipeline(text)
            
            # Group entities by type
            entity_groups = {}
            for entity in entities:
                entity_type = entity['entity_group']
                if entity_type not in entity_groups:
                    entity_groups[entity_type] = []
                entity_groups[entity_type].append({
                    'text': entity['word'],
                    'confidence': entity['score'],
                    'start': entity['start'],
                    'end': entity['end']
                })
            
            return {
                'entities': entities,
                'entity_groups': entity_groups,
                'total_entities': len(entities),
                'entity_types': list(entity_groups.keys())
            }
            
        except Exception as e:
            return {'error': f'Entity extraction failed: {str(e)}'}
    
    def answer_document_questions(self, context: str, questions: List[str]) -> Dict[str, Any]:
        """Answer questions about document content using QA models"""
        
        if not TRANSFORMERS_AVAILABLE or not self.question_answering:
            return {'error': 'Question-answering pipeline not available'}
        
        try:
            answers = {}
            for question in questions:
                result = self.question_answering(question=question, context=context)
                answers[question] = {
                    'answer': result['answer'],
                    'confidence': result['score'],
                    'start': result['start'],
                    'end': result['end']
                }
            
            return {
                'answers': answers,
                'context_length': len(context),
                'questions_processed': len(questions)
            }
            
        except Exception as e:
            return {'error': f'Question answering failed: {str(e)}'}
    
    def _categorize_extraction_request(self, request: str) -> Dict[str, float]:
        """Categorize the type of extraction request"""
        
        categories = {
            'legal_document': ['contract', 'agreement', 'clause', 'legal', 'terms'],
            'financial_document': ['invoice', 'receipt', 'payment', 'amount', 'cost'],
            'personal_document': ['name', 'address', 'phone', 'email', 'personal'],
            'business_document': ['company', 'organization', 'business', 'corporate'],
            'form_extraction': ['form', 'field', 'input', 'checkbox', 'dropdown'],
            'table_extraction': ['table', 'row', 'column', 'data', 'spreadsheet']
        }
        
        request_lower = request.lower()
        scores = {}
        
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in request_lower)
            scores[category] = score / len(keywords) if keywords else 0
        
        return scores
    
    def _extract_key_information(self, request: str, entities: List[Dict]) -> Dict[str, Any]:
        """Extract key information from the request"""
        
        # Extract field mentions
        field_patterns = {
            'required_fields': r'extract\s+([^.]+?)(?:\s+from|\s+in|\.|$)',
            'document_type': r'from\s+(?:a\s+)?([^.]+?)(?:\s+document|\s+file|\.|$)',
            'output_format': r'(?:as|in|to)\s+(csv|json|xml|excel|pdf)',
            'conditions': r'(?:if|when|where)\s+([^.]+?)(?:\.|$)'
        }
        
        key_info = {}
        for info_type, pattern in field_patterns.items():
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                key_info[info_type] = matches
        
        return key_info
    
    def _assess_complexity(self, request: str, entities: List[Dict]) -> str:
        """Assess the complexity of the extraction request"""
        
        complexity_indicators = {
            'simple': ['extract', 'get', 'find'],
            'moderate': ['analyze', 'identify', 'determine', 'calculate'],
            'complex': ['compare', 'evaluate', 'assess', 'interpret', 'understand']
        }
        
        request_lower = request.lower()
        scores = {}
        
        for level, indicators in complexity_indicators.items():
            score = sum(1 for indicator in indicators if indicator in request_lower)
            scores[level] = score
        
        # Determine complexity based on scores and entity count
        entity_count = len(entities)
        
        if scores['complex'] > 0 or entity_count > 10:
            return 'complex'
        elif scores['moderate'] > 0 or entity_count > 5:
            return 'moderate'
        else:
            return 'simple'
    
    def _suggest_extraction_fields(self, entities: List[Dict], categories: Dict[str, float]) -> List[Dict[str, str]]:
        """Suggest fields to extract based on entities and categories"""
        
        suggested_fields = []
        
        # Based on entities
        entity_field_mapping = {
            'PER': {'name': 'person_name', 'type': 'text'},
            'ORG': {'name': 'organization', 'type': 'text'},
            'LOC': {'name': 'location', 'type': 'text'},
            'MISC': {'name': 'miscellaneous', 'type': 'text'}
        }
        
        for entity in entities:
            entity_type = entity.get('entity_group', 'MISC')
            if entity_type in entity_field_mapping:
                field_info = entity_field_mapping[entity_type].copy()
                field_info['description'] = f"Extracted {entity_type} entity: {entity.get('word', '')}"
                suggested_fields.append(field_info)
        
        # Based on categories
        category_field_mapping = {
            'legal_document': [
                {'name': 'contract_parties', 'type': 'text', 'description': 'Parties involved in the contract'},
                {'name': 'effective_date', 'type': 'date', 'description': 'Contract effective date'},
                {'name': 'terms_conditions', 'type': 'text', 'description': 'Key terms and conditions'}
            ],
            'financial_document': [
                {'name': 'amount', 'type': 'number', 'description': 'Financial amount'},
                {'name': 'date', 'type': 'date', 'description': 'Transaction date'},
                {'name': 'vendor', 'type': 'text', 'description': 'Vendor or payer information'}
            ]
        }
        
        # Find the highest scoring category
        if categories:
            top_category = max(categories, key=categories.get)
            if categories[top_category] > 0 and top_category in category_field_mapping:
                suggested_fields.extend(category_field_mapping[top_category])
        
        return suggested_fields
    
    def _basic_intent_analysis(self, request: str) -> Dict[str, Any]:
        """Basic intent analysis when transformers are not available"""
        
        return {
            'entities': [],
            'categories': self._categorize_extraction_request(request),
            'key_information': self._extract_key_information(request, []),
            'complexity': 'unknown',
            'suggested_fields': [],
            'note': 'Basic analysis - transformers not available'
        }

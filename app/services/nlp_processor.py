import os
import openai
import json
import re
from typing import Dict, List, Any, Optional

class NLPProcessor:
    """Processes natural language extraction requests and interprets user requirements"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        
        self.intent_classifier = None
    
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
            response = openai.ChatCompletion.create(
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

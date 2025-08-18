import os
import openai
import re
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime

class LegalProcessor:
    """Specialized processor for legal document analysis and extraction"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        
        self.clause_patterns = {
            'termination': [
                r'termination\s+clause',
                r'terminate\s+this\s+agreement',
                r'end\s+this\s+contract',
                r'expiry\s+of\s+this\s+agreement'
            ],
            'penalty': [
                r'penalty\s+clause',
                r'liquidated\s+damages',
                r'breach\s+penalty',
                r'default\s+penalty'
            ],
            'payment': [
                r'payment\s+terms',
                r'payment\s+schedule',
                r'payment\s+clause',
                r'compensation\s+terms'
            ],
            'liability': [
                r'liability\s+clause',
                r'limitation\s+of\s+liability',
                r'indemnification',
                r'hold\s+harmless'
            ],
            'confidentiality': [
                r'confidentiality\s+clause',
                r'non-disclosure',
                r'proprietary\s+information',
                r'confidential\s+information'
            ]
        }
        
        self.risk_indicators = {
            'high': [
                r'unlimited\s+liability',
                r'personal\s+guarantee',
                r'immediate\s+termination',
                r'no\s+cure\s+period'
            ],
            'medium': [
                r'liquidated\s+damages',
                r'specific\s+performance',
                r'injunctive\s+relief',
                r'attorney\s+fees'
            ],
            'ambiguous': [
                r'reasonable\s+efforts',
                r'best\s+efforts',
                r'commercially\s+reasonable',
                r'material\s+adverse\s+effect'
            ]
        }
    
    def analyze_legal_document(self, text_content: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive legal document analysis"""
        
        try:
            identified_clauses = self._identify_clauses(text_content)
            
            obligations = self._extract_obligations(text_content)
            
            risk_flags = self._flag_risks(text_content)
            
            document_summary = self._generate_summary(text_content, extracted_data)
            
            reference_materials = self._create_reference_materials(
                text_content, identified_clauses, obligations
            )
            
            return {
                'identified_clauses': identified_clauses,
                'obligations': obligations,
                'risk_flags': risk_flags,
                'document_summary': document_summary,
                'reference_materials': reference_materials,
                'legal_analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Legal analysis failed: {str(e)}',
                'legal_analysis_timestamp': datetime.utcnow().isoformat()
            }
    
    def _identify_clauses(self, text: str) -> List[Dict[str, Any]]:
        """Identify and extract legal clauses from the document"""
        
        clauses = []
        
        for clause_type, patterns in self.clause_patterns.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                
                for match in matches:
                    start_pos = max(0, match.start() - 200)
                    end_pos = min(len(text), match.end() + 500)
                    clause_text = text[start_pos:end_pos]
                    
                    page_ref = self._estimate_page_number(text, match.start())
                    
                    clauses.append({
                        'type': clause_type,
                        'text': clause_text.strip(),
                        'position': match.start(),
                        'page_reference': page_ref,
                        'confidence': 0.8,
                        'pattern_matched': pattern
                    })
        
        unique_clauses = []
        seen_positions = set()
        
        for clause in sorted(clauses, key=lambda x: x['position']):
            if not any(abs(clause['position'] - pos) < 100 for pos in seen_positions):
                unique_clauses.append(clause)
                seen_positions.add(clause['position'])
        
        return unique_clauses
    
    def _extract_obligations(self, text: str) -> List[Dict[str, Any]]:
        """Extract obligations and duties from the document"""
        
        obligations = []
        
        obligation_patterns = [
            r'shall\s+([^.]+)',
            r'must\s+([^.]+)',
            r'required\s+to\s+([^.]+)',
            r'obligated\s+to\s+([^.]+)',
            r'responsible\s+for\s+([^.]+)'
        ]
        
        for pattern in obligation_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            for match in matches:
                obligation_text = match.group(1).strip()
                
                if len(obligation_text) < 10 or len(obligation_text) > 200:
                    continue
                
                obligation_type = self._classify_obligation(obligation_text)
                
                start_pos = max(0, match.start() - 100)
                end_pos = min(len(text), match.end() + 100)
                context = text[start_pos:end_pos]
                
                obligations.append({
                    'text': obligation_text,
                    'type': obligation_type,
                    'context': context.strip(),
                    'position': match.start(),
                    'page_reference': self._estimate_page_number(text, match.start()),
                    'pattern_matched': pattern
                })
        
        return obligations
    
    def _classify_obligation(self, obligation_text: str) -> str:
        """Classify the type of obligation"""
        
        text_lower = obligation_text.lower()
        
        if any(word in text_lower for word in ['pay', 'payment', 'compensate', 'remit']):
            return 'payment'
        elif any(word in text_lower for word in ['deliver', 'provide', 'supply', 'furnish']):
            return 'delivery'
        elif any(word in text_lower for word in ['perform', 'execute', 'complete', 'fulfill']):
            return 'performance'
        elif any(word in text_lower for word in ['maintain', 'keep', 'preserve', 'retain']):
            return 'maintenance'
        elif any(word in text_lower for word in ['notify', 'inform', 'report', 'communicate']):
            return 'notification'
        else:
            return 'general'
    
    def _flag_risks(self, text: str) -> List[Dict[str, Any]]:
        """Flag potential risks in the document"""
        
        risks = []
        
        for risk_level, patterns in self.risk_indicators.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                
                for match in matches:
                    start_pos = max(0, match.start() - 150)
                    end_pos = min(len(text), match.end() + 150)
                    risk_context = text[start_pos:end_pos]
                    
                    risks.append({
                        'level': risk_level,
                        'text': match.group(0),
                        'context': risk_context.strip(),
                        'position': match.start(),
                        'page_reference': self._estimate_page_number(text, match.start()),
                        'description': self._get_risk_description(risk_level, match.group(0)),
                        'pattern_matched': pattern
                    })
        
        return sorted(risks, key=lambda x: x['position'])
    
    def _get_risk_description(self, risk_level: str, risk_text: str) -> str:
        """Get description for identified risk"""
        
        descriptions = {
            'high': f"High risk clause identified: '{risk_text}' - Review carefully for potential unlimited exposure",
            'medium': f"Medium risk clause identified: '{risk_text}' - Consider negotiating terms",
            'ambiguous': f"Ambiguous language detected: '{risk_text}' - May require clarification"
        }
        
        return descriptions.get(risk_level, f"Risk identified: {risk_text}")
    
    def _generate_summary(self, text: str, extracted_data: Dict[str, Any]) -> str:
        """Generate a concise summary of the legal document"""
        
        if self.openai_api_key:
            return self._generate_summary_with_ai(text, extracted_data)
        else:
            return self._generate_summary_rule_based(text, extracted_data)
    
    def _generate_summary_with_ai(self, text: str, extracted_data: Dict[str, Any]) -> str:
        """Generate summary using AI"""
        
        try:
            prompt = f"""Provide a concise legal document summary (max 200 words) covering:
            1. Document type and purpose
            2. Key parties involved
            3. Main obligations and terms
            4. Important dates and deadlines
            5. Notable risks or concerns
            
            Document text (first 2000 chars): {text[:2000]}
            
            Extracted data: {json.dumps(extracted_data, indent=2)[:500]}
            
            Summary:"""
            
            from openai import OpenAI
            client = OpenAI(api_key=openai.api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return self._generate_summary_rule_based(text, extracted_data)
    
    def _generate_summary_rule_based(self, text: str, extracted_data: Dict[str, Any]) -> str:
        """Generate summary using rule-based approach"""
        
        summary_parts = []
        
        if 'contract' in text.lower() or 'agreement' in text.lower():
            summary_parts.append("This appears to be a contractual agreement")
        
        if extracted_data:
            if 'effective_date' in extracted_data or 'date' in extracted_data:
                summary_parts.append("with specified effective dates")
            
            if any('party' in key.lower() or 'name' in key.lower() for key in extracted_data.keys()):
                summary_parts.append("between identified parties")
        
        clause_count = len(re.findall(r'clause|section|article', text, re.IGNORECASE))
        if clause_count > 0:
            summary_parts.append(f"containing {clause_count} clauses or sections")
        
        if summary_parts:
            summary = " ".join(summary_parts) + "."
        else:
            summary = "Legal document requiring detailed review for terms and obligations."
        
        return summary
    
    def _create_reference_materials(self, text: str, clauses: List[Dict], 
                                  obligations: List[Dict]) -> Dict[str, Any]:
        """Create reference materials for legal teams"""
        
        reference_materials = {
            'clause_index': [],
            'obligation_summary': [],
            'key_terms_glossary': [],
            'page_references': {}
        }
        
        for clause in clauses:
            reference_materials['clause_index'].append({
                'type': clause['type'],
                'page': clause['page_reference'],
                'summary': clause['text'][:100] + "..." if len(clause['text']) > 100 else clause['text']
            })
        
        obligation_types = {}
        for obligation in obligations:
            if obligation['type'] not in obligation_types:
                obligation_types[obligation['type']] = []
            obligation_types[obligation['type']].append(obligation)
        
        for obligation_type, obs in obligation_types.items():
            reference_materials['obligation_summary'].append({
                'type': obligation_type,
                'count': len(obs),
                'examples': [ob['text'][:50] + "..." for ob in obs[:3]]
            })
        
        key_terms = self._extract_key_terms(text)
        reference_materials['key_terms_glossary'] = key_terms
        
        return reference_materials
    
    def _extract_key_terms(self, text: str) -> List[Dict[str, str]]:
        """Extract key legal terms and their definitions"""
        
        legal_terms = [
            'force majeure', 'indemnification', 'liquidated damages',
            'material breach', 'specific performance', 'injunctive relief',
            'confidential information', 'intellectual property'
        ]
        
        key_terms = []
        
        for term in legal_terms:
            pattern = rf'\b{re.escape(term)}\b'
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            if matches:
                for match in matches[:1]:  # Only first occurrence
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(text), match.end() + 200)
                    context = text[start_pos:end_pos]
                    
                    key_terms.append({
                        'term': term,
                        'context': context.strip(),
                        'page_reference': self._estimate_page_number(text, match.start())
                    })
        
        return key_terms
    
    def _estimate_page_number(self, text: str, position: int) -> int:
        """Estimate page number based on text position"""
        
        chars_per_page = 500
        page_number = (position // chars_per_page) + 1
        
        return page_number

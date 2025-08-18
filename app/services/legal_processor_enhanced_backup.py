import re
import json
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import logging
import openai
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ExtractedClause:
    """Structured representation of an extracted legal clause"""
    clause_type: str
    content: str
    location: str
    confidence: float
    risk_level: str
    implications: List[str]

@dataclass
class FinancialTerm:
    """Structured representation of financial terms"""
    term_type: str
    amount: str
    currency: str
    frequency: str
    due_date: str
    conditions: List[str]

@dataclass
class KeyDate:
    """Structured representation of key dates"""
    date_type: str
    date_value: str
    description: str
    importance: str

class EnhancedLegalProcessor:
    """Advanced legal document processor with comprehensive AI-powered analysis"""
    
    def __init__(self):
        # Initialize OpenAI client
        try:
            import openai
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.openai_available = bool(openai.api_key)
        except ImportError:
            self.openai_available = False
            logger.warning("OpenAI not available - using pattern-based analysis only")
        
        # Advanced legal clause patterns with enhanced accuracy
        self.legal_patterns = {
            'termination_clauses': [
                r'(?i)(?:this\s+agreement\s+(?:may\s+be\s+)?(?:terminated|shall\s+terminate))',
                r'(?i)(?:termination\s+(?:of\s+this\s+)?(?:agreement|contract))',
                r'(?i)(?:either\s+party\s+may\s+terminate)',
                r'(?i)(?:automatic(?:ally)?\s+terminate|immediate\s+termination)',
                r'(?i)(?:upon\s+(?:\d+\s+)?(?:days?\s+)?notice.*?terminate)',
                r'(?i)(?:breach.*?(?:right\s+to\s+)?terminate|default.*?termination)',
                r'(?i)(?:terminate\s+for\s+(?:cause|convenience|any\s+reason))',
                r'(?i)(?:expiry|expiration)\s+(?:of\s+)?(?:this\s+)?(?:agreement|contract|term)'
            ],
            'penalty_clauses': [
                r'(?i)(?:liquidated\s+damages?\s+(?:of\s+|in\s+the\s+amount\s+of\s+)?\$[\d,]+)',
                r'(?i)(?:penalty\s+(?:of\s+|equal\s+to\s+)?\$[\d,]+)',
                r'(?i)(?:late\s+(?:payment\s+)?(?:fee|charge|penalty))',
                r'(?i)(?:interest\s+(?:at\s+(?:a\s+)?rate\s+of\s+)?\d+(?:\.\d+)?%)',
                r'(?i)(?:breach\s+penalty|default\s+(?:fee|penalty))',
                r'(?i)(?:per\s+day\s+penalty|daily\s+penalty)',
                r'(?i)(?:administrative\s+fee|processing\s+fee)',
                r'(?i)(?:compensatory\s+damages|consequential\s+damages)'
            ],
            'financial_terms': [
                r'(?i)(?:total\s+(?:contract\s+)?(?:value|amount|price|cost).*?\$[\d,]+)',
                r'(?i)(?:payment\s+(?:of\s+)?\$[\d,]+)',
                r'(?i)(?:monthly\s+(?:payment|fee|rent).*?\$[\d,]+)',
                r'(?i)(?:annual\s+(?:payment|fee|salary).*?\$[\d,]+)',
                r'(?i)(?:hourly\s+rate.*?\$[\d,]+)',
                r'(?i)(?:deposit.*?\$[\d,]+|down\s+payment.*?\$[\d,]+)',
                r'(?i)(?:commission.*?\d+(?:\.\d+)?%)',
                r'(?i)(?:bonus.*?\$[\d,]+)',
                r'(?i)(?:expense\s+reimbursement|expenses?\s+(?:up\s+to\s+)?\$[\d,]+)'
            ],
            'payment_terms': [
                r'(?i)(?:payment\s+(?:is\s+)?due\s+(?:within\s+)?\d+\s+days?)',
                r'(?i)(?:net\s+\d+\s+days?|payment\s+terms?\s+net\s+\d+)',
                r'(?i)(?:upon\s+(?:receipt\s+of\s+)?invoice)',
                r'(?i)(?:payable\s+(?:in\s+)?(?:advance|arrears))',
                r'(?i)(?:quarterly\s+payments?|monthly\s+payments?|annual\s+payments?)',
                r'(?i)(?:installment\s+payments?|payment\s+plan)',
                r'(?i)(?:wire\s+transfer|ach\s+transfer|check\s+payment)',
                r'(?i)(?:payment\s+method|acceptable\s+forms\s+of\s+payment)'
            ],
            'key_dates': [
                r'(?i)(?:effective\s+date.*?(?:\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}))',
                r'(?i)(?:commencement\s+date.*?(?:\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}))',
                r'(?i)(?:expiration\s+date.*?(?:\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}))',
                r'(?i)(?:renewal\s+date.*?(?:\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}))',
                r'(?i)(?:deadline.*?(?:\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}))',
                r'(?i)(?:delivery\s+date.*?(?:\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}))',
                r'(?i)(?:notice\s+period.*?\d+\s+days?)',
                r'(?i)(?:term\s+(?:of\s+)?\d+\s+(?:years?|months?))'
            ],
            'parties_identification': [
                r'(?i)(?:party\s+a|first\s+party|party\s+of\s+the\s+first\s+part)',
                r'(?i)(?:party\s+b|second\s+party|party\s+of\s+the\s+second\s+part)',
                r'(?i)(?:client|customer|buyer|purchaser)',
                r'(?i)(?:vendor|seller|supplier|contractor)',
                r'(?i)(?:employer|employee|independent\s+contractor)',
                r'(?i)(?:landlord|tenant|lessee|lessor)',
                r'(?i)(?:licensor|licensee)',
                r'(?i)(?:service\s+provider|consultant)'
            ]
        }
        
        # Enhanced risk assessment criteria
        self.risk_indicators = {
            'critical_risk': [
                r'(?i)(?:unlimited\s+liability|personal\s+guarantee)',
                r'(?i)(?:immediate\s+termination\s+without\s+(?:notice|cause))',
                r'(?i)(?:liquidated\s+damages.*?\$[\d,]{6,})',  # $100k+
                r'(?i)(?:non-compete.*?\d+\s+years?)',
                r'(?i)(?:sole\s+and\s+exclusive\s+remedy)'
            ],
            'high_risk': [
                r'(?i)(?:penalty.*?\$[\d,]{4,})',  # $1k+
                r'(?i)(?:indemnification|indemnify)',
                r'(?i)(?:waiver\s+of\s+(?:rights|claims))',
                r'(?i)(?:automatic\s+renewal)',
                r'(?i)(?:governing\s+law.*?(?!local|same|domestic))'
            ],
            'medium_risk': [
                r'(?i)(?:late\s+(?:fee|penalty).*?\d+%)',
                r'(?i)(?:confidentiality.*?\d+\s+years?)',
                r'(?i)(?:force\s+majeure)',
                r'(?i)(?:arbitration\s+(?:clause|requirement))',
                r'(?i)(?:limitation\s+of\s+liability)'
            ],
            'low_risk': [
                r'(?i)(?:standard\s+commercial\s+terms)',
                r'(?i)(?:mutual\s+agreement)',
                r'(?i)(?:good\s+faith\s+(?:effort|negotiation))',
                r'(?i)(?:reasonable\s+notice)',
                r'(?i)(?:market\s+rate|prevailing\s+rate)'
            ]
        }

    async def analyze_comprehensive_legal_document(self, text: str, document_type: str = None) -> Dict[str, Any]:
        """
        Comprehensive legal document analysis with AI enhancement
        """
        try:
            # Perform multiple analysis layers
            basic_analysis = self._extract_basic_legal_info(text)
            clause_analysis = await self._extract_legal_clauses(text)
            financial_analysis = self._extract_financial_terms(text)
            parties_analysis = self._extract_parties_info(text)
            dates_analysis = self._extract_key_dates(text)
            risk_analysis = self._assess_comprehensive_risk(text, clause_analysis)
            
            # Generate document overview with AI if available
            if self.openai_available:
                overview = await self._generate_ai_overview(text, document_type)
                summary = await self._generate_ai_summary(text, clause_analysis, financial_analysis)
            else:
                overview = self._generate_pattern_overview(text, basic_analysis)
                summary = self._generate_pattern_summary(basic_analysis, clause_analysis, financial_analysis)
            
            # Compile comprehensive analysis
            analysis_result = {
                'document_overview': overview,
                'contract_summary': summary,
                'main_parties': parties_analysis,
                'key_dates': dates_analysis,
                'financial_terms': financial_analysis,
                'legal_clauses': {
                    'termination_clauses': clause_analysis.get('termination_clauses', []),
                    'penalty_clauses': clause_analysis.get('penalty_clauses', []),
                    'payment_terms': clause_analysis.get('payment_terms', []),
                    'other_clauses': clause_analysis.get('other_clauses', [])
                },
                'risk_assessment': risk_analysis,
                'confidence_score': self._calculate_overall_confidence(clause_analysis, financial_analysis, parties_analysis)
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in comprehensive legal analysis: {e}")
            return {
                'error': f"Analysis failed: {str(e)}",
                'document_overview': {'type': 'unknown', 'description': 'Analysis failed'},
                'contract_summary': 'Unable to generate summary due to processing error',
                'main_parties': [],
                'key_dates': [],
                'financial_terms': [],
                'legal_clauses': {'termination_clauses': [], 'penalty_clauses': [], 'payment_terms': [], 'other_clauses': []},
                'risk_assessment': {'overall_risk': 'Unknown', 'risk_score': 0, 'risk_factors': []},
                'confidence_score': 0.0
            }

    async def _extract_legal_clauses(self, text: str) -> Dict[str, List[ExtractedClause]]:
        """Extract and categorize legal clauses with enhanced AI analysis"""
        clauses = {
            'termination_clauses': [],
            'penalty_clauses': [],
            'payment_terms': [],
            'other_clauses': []
        }
        
        try:
            # Extract termination clauses
            for pattern in self.legal_patterns['termination_clauses']:
                matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
                for match in matches:
                    clause = ExtractedClause(
                        clause_type='termination',
                        content=self._extract_clause_context(text, match.start(), match.end()),
                        location=f"Position {match.start()}-{match.end()}",
                        confidence=0.85,
                        risk_level=self._assess_clause_risk(match.group(), 'termination'),
                        implications=self._get_termination_implications(match.group())
                    )
                    clauses['termination_clauses'].append(clause)
            
            # Extract penalty clauses
            for pattern in self.legal_patterns['penalty_clauses']:
                matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
                for match in matches:
                    clause = ExtractedClause(
                        clause_type='penalty',
                        content=self._extract_clause_context(text, match.start(), match.end()),
                        location=f"Position {match.start()}-{match.end()}",
                        confidence=0.90,
                        risk_level=self._assess_clause_risk(match.group(), 'penalty'),
                        implications=self._get_penalty_implications(match.group())
                    )
                    clauses['penalty_clauses'].append(clause)
            
            # Extract payment terms
            for pattern in self.legal_patterns['payment_terms']:
                matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
                for match in matches:
                    clause = ExtractedClause(
                        clause_type='payment',
                        content=self._extract_clause_context(text, match.start(), match.end()),
                        location=f"Position {match.start()}-{match.end()}",
                        confidence=0.88,
                        risk_level='Medium',
                        implications=['Payment obligations defined', 'Timeline specified']
                    )
                    clauses['payment_terms'].append(clause)
            
            # If no clauses found, indicate this
            if not any(clauses.values()):
                logger.info("No specific legal clauses identified in document")
                
        except Exception as e:
            logger.error(f"Error extracting legal clauses: {e}")
            
        return clauses

    def _extract_financial_terms(self, text: str) -> List[FinancialTerm]:
        """Extract comprehensive financial terms and amounts"""
        financial_terms = []
        
        try:
            # Extract amounts with context
            amount_patterns = [
                r'(?i)(?:total\s+(?:amount|value|cost|price).*?\$[\d,]+(?:\.\d{2})?)',
                r'(?i)(?:payment\s+of\s+\$[\d,]+(?:\.\d{2})?)',
                r'(?i)(?:monthly\s+(?:payment|fee|rent).*?\$[\d,]+(?:\.\d{2})?)',
                r'(?i)(?:annual\s+(?:salary|fee|payment).*?\$[\d,]+(?:\.\d{2})?)',
                r'(?i)(?:hourly\s+rate.*?\$[\d,]+(?:\.\d{2})?)',
                r'(?i)(?:commission.*?\d+(?:\.\d+)?%)',
                r'(?i)(?:deposit.*?\$[\d,]+(?:\.\d{2})?)',
                r'(?i)(?:penalty.*?\$[\d,]+(?:\.\d{2})?)',
                r'(?i)(?:late\s+fee.*?\$[\d,]+(?:\.\d{2})?)'
            ]
            
            for pattern in amount_patterns:
                matches = re.finditer(pattern, text, re.MULTILINE)
                for match in matches:
                    # Extract amount and determine type
                    content = match.group()
                    amount_match = re.search(r'\$[\d,]+(?:\.\d{2})?', content)
                    percent_match = re.search(r'\d+(?:\.\d+)?%', content)
                    
                    if amount_match:
                        amount = amount_match.group()
                        currency = 'USD'
                    elif percent_match:
                        amount = percent_match.group()
                        currency = 'Percentage'
                    else:
                        continue
                    
                    # Determine term type and frequency
                    term_type = self._classify_financial_term(content)
                    frequency = self._extract_frequency(content)
                    due_date = self._extract_due_date(content)
                    conditions = self._extract_conditions(content)
                    
                    financial_term = FinancialTerm(
                        term_type=term_type,
                        amount=amount,
                        currency=currency,
                        frequency=frequency,
                        due_date=due_date,
                        conditions=conditions
                    )
                    financial_terms.append(financial_term)
            
            if not financial_terms:
                logger.info("No specific financial terms found in document")
                
        except Exception as e:
            logger.error(f"Error extracting financial terms: {e}")
            
        return financial_terms

    def _extract_parties_info(self, text: str) -> List[Dict[str, Any]]:
        """Extract information about the main parties to the contract"""
        parties = []
        
        try:
            # Look for party definitions in the beginning of the document
            intro_section = text[:2000]  # First 2000 characters
            
            # Common party patterns
            party_patterns = [
                r'(?i)(?:between|by\s+and\s+between)\s+([^,]+),?\s+(?:a\s+[^,]+,?)?\s*\([^)]*\)\s*(?:,\s*)?(?:and|&)\s+([^,]+)',
                r'(?i)(?:party\s+a|first\s+party|party\s+of\s+the\s+first\s+part)[:\s]*([^,\n]+)',
                r'(?i)(?:party\s+b|second\s+party|party\s+of\s+the\s+second\s+part)[:\s]*([^,\n]+)',
                r'(?i)(?:client|customer)[:\s]*([^,\n]+)',
                r'(?i)(?:contractor|vendor|supplier)[:\s]*([^,\n]+)',
                r'(?i)(?:employer)[:\s]*([^,\n]+)',
                r'(?i)(?:employee)[:\s]*([^,\n]+)'
            ]
            
            for pattern in party_patterns:
                matches = re.finditer(pattern, intro_section, re.MULTILINE)
                for match in matches:
                    if len(match.groups()) >= 2:
                        # Two party contract
                        party1 = match.group(1).strip()
                        party2 = match.group(2).strip()
                        
                        parties.extend([
                            {
                                'name': self._clean_party_name(party1),
                                'role': self._determine_party_role(party1, text),
                                'type': self._determine_entity_type(party1)
                            },
                            {
                                'name': self._clean_party_name(party2),
                                'role': self._determine_party_role(party2, text),
                                'type': self._determine_entity_type(party2)
                            }
                        ])
                    else:
                        # Single party mention
                        party = match.group(1).strip()
                        parties.append({
                            'name': self._clean_party_name(party),
                            'role': self._determine_party_role(party, text),
                            'type': self._determine_entity_type(party)
                        })
            
            # Remove duplicates
            unique_parties = []
            seen_names = set()
            for party in parties:
                if party['name'] not in seen_names:
                    unique_parties.append(party)
                    seen_names.add(party['name'])
            
            if not unique_parties:
                logger.info("No specific party information found in document")
                return [{'name': 'No party information found', 'role': 'Unknown', 'type': 'Unknown'}]
                
        except Exception as e:
            logger.error(f"Error extracting parties info: {e}")
            return [{'name': 'Error extracting party information', 'role': 'Unknown', 'type': 'Unknown'}]
            
        return unique_parties[:5]  # Limit to 5 parties

    def _extract_key_dates(self, text: str) -> List[KeyDate]:
        """Extract and categorize key dates from the document"""
        key_dates = []
        
        try:
            # Date patterns with context
            date_patterns = [
                (r'(?i)(?:effective\s+date|commencement\s+date)[:\s]*([^,\n.]+)', 'Effective Date'),
                (r'(?i)(?:expiration\s+date|termination\s+date|end\s+date)[:\s]*([^,\n.]+)', 'Expiration Date'),
                (r'(?i)(?:renewal\s+date|review\s+date)[:\s]*([^,\n.]+)', 'Renewal Date'),
                (r'(?i)(?:deadline|due\s+date|delivery\s+date)[:\s]*([^,\n.]+)', 'Deadline'),
                (r'(?i)(?:notice\s+period)[:\s]*(\d+\s+days?)', 'Notice Period'),
                (r'(?i)(?:term\s+of)[:\s]*(\d+\s+(?:years?|months?))', 'Contract Term')
            ]
            
            for pattern, date_type in date_patterns:
                matches = re.finditer(pattern, text, re.MULTILINE)
                for match in matches:
                    date_value = match.group(1).strip()
                    
                    # Determine importance
                    importance = 'High' if date_type in ['Effective Date', 'Expiration Date'] else 'Medium'
                    
                    key_date = KeyDate(
                        date_type=date_type,
                        date_value=date_value,
                        description=f"{date_type}: {date_value}",
                        importance=importance
                    )
                    key_dates.append(key_date)
            
            if not key_dates:
                logger.info("No specific key dates found in document")
                return [KeyDate('Not Found', 'No key dates identified', 'No specific dates found in document', 'Low')]
                
        except Exception as e:
            logger.error(f"Error extracting key dates: {e}")
            return [KeyDate('Error', 'Error extracting dates', 'Error occurred during date extraction', 'Low')]
            
        return key_dates

    def _assess_comprehensive_risk(self, text: str, clauses: Dict[str, List[ExtractedClause]]) -> Dict[str, Any]:
        """Perform comprehensive risk assessment of the document"""
        risk_factors = []
        risk_score = 0
        
        try:
            # Analyze clauses for risk
            for clause_type, clause_list in clauses.items():
                for clause in clause_list:
                    if clause.risk_level == 'High':
                        risk_score += 25
                        risk_factors.append(f"High-risk {clause.clause_type} clause identified")
                    elif clause.risk_level == 'Medium':
                        risk_score += 10
                        risk_factors.append(f"Medium-risk {clause.clause_type} clause present")
            
            # Check for specific risk indicators
            for risk_level, patterns in self.risk_indicators.items():
                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        if risk_level == 'critical_risk':
                            risk_score += 40
                            risk_factors.append("Critical risk indicator found")
                        elif risk_level == 'high_risk':
                            risk_score += 25
                            risk_factors.append("High risk indicator found")
                        elif risk_level == 'medium_risk':
                            risk_score += 15
                            risk_factors.append("Medium risk indicator found")
                        elif risk_level == 'low_risk':
                            risk_score += 5
                            risk_factors.append("Low risk indicator found")
            
            # Cap the risk score at 100
            risk_score = min(risk_score, 100)
            
            # Determine overall risk level
            if risk_score >= 70:
                overall_risk = 'Critical'
            elif risk_score >= 50:
                overall_risk = 'High'
            elif risk_score >= 25:
                overall_risk = 'Medium'
            elif risk_score >= 10:
                overall_risk = 'Low'
            else:
                overall_risk = 'Minimal'
            
            # Generate summary
            if not risk_factors:
                risk_factors = ['No significant risk factors identified']
                summary = "This document appears to contain standard commercial terms with minimal legal risk."
            else:
                summary = f"This document contains {len(risk_factors)} identified risk factors. {overall_risk} risk level requires careful review."
            
            return {
                'overall_risk': overall_risk,
                'risk_score': risk_score,
                'risk_factors': risk_factors[:10],  # Limit to 10 factors
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            return {
                'overall_risk': 'Unknown',
                'risk_score': 0,
                'risk_factors': ['Error occurred during risk assessment'],
                'summary': 'Unable to assess risk due to processing error'
            }

    # Helper methods for data extraction and analysis
    def _extract_basic_legal_info(self, text: str) -> Dict[str, Any]:
        """Extract basic legal information from document"""
        return {
            'document_length': len(text),
            'estimated_pages': len(text) // 3000 + 1,
            'contains_signatures': bool(re.search(r'(?i)(?:signature|signed|execute)', text)),
            'contains_dates': bool(re.search(r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}', text)),
            'contains_amounts': bool(re.search(r'\$[\d,]+', text))
        }

    async def _generate_ai_overview(self, text: str, document_type: str = None) -> Dict[str, Any]:
        """Generate AI-powered document overview"""
        if not self.openai_available:
            return self._generate_pattern_overview(text, {})
        
        try:
            import openai
            
            prompt = f"""
            Analyze this legal document and provide a structured overview:
            
            Document Text (first 2000 chars): {text[:2000]}
            
            Please provide:
            1. Document type classification
            2. Primary purpose
            3. Key obligations summary
            4. Notable provisions
            
            Format as JSON with keys: type, purpose, obligations, notable_provisions
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"AI overview generation failed: {e}")
            return self._generate_pattern_overview(text, {})

    async def _generate_ai_summary(self, text: str, clauses: Dict, financial_terms: List) -> str:
        """Generate AI-powered contract summary"""
        if not self.openai_available:
            return self._generate_pattern_summary({}, clauses, financial_terms)
        
        try:
            import openai
            
            clause_count = sum(len(v) for v in clauses.values() if isinstance(v, list))
            financial_count = len(financial_terms)
            
            prompt = f"""
            Create a concise contract summary (max 300 words) based on:
            - Document contains {clause_count} identified clauses
            - {financial_count} financial terms found
            - Key provisions extracted from legal analysis
            
            Focus on: main obligations, key terms, important dates, risk factors.
            Be professional and clear.
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"AI summary generation failed: {e}")
            return self._generate_pattern_summary({}, clauses, financial_terms)

    def _generate_pattern_overview(self, text: str, basic_info: Dict) -> Dict[str, Any]:
        """Generate document overview using pattern matching"""
        doc_type = self._classify_document_type(text)
        
        return {
            'type': doc_type,
            'purpose': f"This appears to be a {doc_type} document governing the relationship between parties",
            'obligations': "Document contains various obligations and terms that bind the parties",
            'notable_provisions': ["Standard commercial terms", "Party obligations defined", "Legal framework established"]
        }

    def _generate_pattern_summary(self, basic_info: Dict, clauses: Dict, financial_terms: List) -> str:
        """Generate contract summary using extracted patterns"""
        clause_count = sum(len(v) for v in clauses.values() if isinstance(v, list))
        financial_count = len(financial_terms)
        
        return f"""
        This contract establishes legal obligations between the parties. The document contains {clause_count} 
        identified legal clauses and {financial_count} financial terms. Key provisions include standard 
        commercial terms, party obligations, and contractual framework. The agreement defines rights, 
        responsibilities, and procedures governing the relationship between the contracting parties.
        """

    def _classify_document_type(self, text: str) -> str:
        """Classify the document type based on content"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['purchase', 'order', 'goods', 'products']):
            return 'Purchase Order'
        elif any(word in text_lower for word in ['employment', 'employee', 'employer', 'job']):
            return 'Employment Agreement'
        elif any(word in text_lower for word in ['lease', 'rent', 'tenant', 'landlord']):
            return 'Lease Agreement'
        elif any(word in text_lower for word in ['service', 'services', 'provider', 'client']):
            return 'Service Agreement'
        elif any(word in text_lower for word in ['non-disclosure', 'confidential', 'nda']):
            return 'Non-Disclosure Agreement'
        elif any(word in text_lower for word in ['loan', 'borrow', 'lender', 'credit']):
            return 'Loan Agreement'
        else:
            return 'General Contract'

    def _extract_clause_context(self, text: str, start: int, end: int, context_chars: int = 200) -> str:
        """Extract clause with surrounding context"""
        context_start = max(0, start - context_chars)
        context_end = min(len(text), end + context_chars)
        
        # Find sentence boundaries
        before_text = text[context_start:start]
        after_text = text[end:context_end]
        
        # Find last sentence start before match
        last_period = before_text.rfind('.')
        if last_period != -1:
            context_start = context_start + last_period + 1
        
        # Find first sentence end after match
        next_period = after_text.find('.')
        if next_period != -1:
            context_end = end + next_period + 1
        
        return text[context_start:context_end].strip()

    def _assess_clause_risk(self, clause_text: str, clause_type: str) -> str:
        """Assess risk level of a clause"""
        clause_lower = clause_text.lower()
        
        # High risk indicators
        if any(indicator in clause_lower for indicator in ['immediate', 'without notice', 'unlimited', 'personal guarantee']):
            return 'High'
        
        # Medium risk indicators
        elif any(indicator in clause_lower for indicator in ['penalty', 'liquidated damages', 'indemnify']):
            return 'Medium'
        
        # Low risk
        else:
            return 'Low'

    def _get_termination_implications(self, clause_text: str) -> List[str]:
        """Get implications of termination clauses"""
        implications = []
        clause_lower = clause_text.lower()
        
        if 'immediate' in clause_lower:
            implications.append('Immediate termination possible')
        if 'notice' in clause_lower:
            implications.append('Notice period required')
        if 'breach' in clause_lower:
            implications.append('Termination for breach allowed')
        if 'convenience' in clause_lower:
            implications.append('Termination for convenience permitted')
        
        return implications if implications else ['Standard termination provisions']

    def _get_penalty_implications(self, clause_text: str) -> List[str]:
        """Get implications of penalty clauses"""
        implications = []
        clause_lower = clause_text.lower()
        
        if 'liquidated' in clause_lower:
            implications.append('Predetermined damages specified')
        if 'late' in clause_lower:
            implications.append('Late payment penalties apply')
        if '$' in clause_text:
            implications.append('Specific monetary penalty defined')
        if '%' in clause_text:
            implications.append('Percentage-based penalty')
        
        return implications if implications else ['Financial penalties may apply']

    def _classify_financial_term(self, content: str) -> str:
        """Classify the type of financial term"""
        content_lower = content.lower()
        
        if 'total' in content_lower or 'contract value' in content_lower:
            return 'Contract Value'
        elif 'monthly' in content_lower:
            return 'Monthly Payment'
        elif 'annual' in content_lower or 'yearly' in content_lower:
            return 'Annual Payment'
        elif 'hourly' in content_lower:
            return 'Hourly Rate'
        elif 'deposit' in content_lower:
            return 'Deposit'
        elif 'penalty' in content_lower:
            return 'Penalty Amount'
        elif 'commission' in content_lower:
            return 'Commission'
        else:
            return 'Payment Amount'

    def _extract_frequency(self, content: str) -> str:
        """Extract payment frequency from content"""
        content_lower = content.lower()
        
        if 'monthly' in content_lower:
            return 'Monthly'
        elif 'quarterly' in content_lower:
            return 'Quarterly'
        elif 'annual' in content_lower or 'yearly' in content_lower:
            return 'Annually'
        elif 'weekly' in content_lower:
            return 'Weekly'
        elif 'hourly' in content_lower:
            return 'Hourly'
        else:
            return 'One-time'

    def _extract_due_date(self, content: str) -> str:
        """Extract due date information"""
        # Look for specific dates
        date_match = re.search(r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}', content)
        if date_match:
            return date_match.group()
        
        # Look for relative dates
        if 'upon receipt' in content.lower():
            return 'Upon receipt'
        elif 'net 30' in content.lower():
            return 'Net 30 days'
        elif 'net 15' in content.lower():
            return 'Net 15 days'
        else:
            return 'Not specified'

    def _extract_conditions(self, content: str) -> List[str]:
        """Extract conditions related to financial terms"""
        conditions = []
        content_lower = content.lower()
        
        if 'subject to' in content_lower:
            conditions.append('Subject to conditions')
        if 'plus tax' in content_lower:
            conditions.append('Plus applicable taxes')
        if 'reimbursable' in content_lower:
            conditions.append('Reimbursable expense')
        if 'advance' in content_lower:
            conditions.append('Advance payment')
        
        return conditions

    def _clean_party_name(self, name: str) -> str:
        """Clean and format party name"""
        # Remove common legal suffixes and prefixes
        name = re.sub(r'\([^)]*\)', '', name)  # Remove parenthetical content
        name = re.sub(r',?\s*a\s+\w+\s+corporation', '', name, flags=re.IGNORECASE)
        name = re.sub(r',?\s*llc', '', name, flags=re.IGNORECASE)
        name = re.sub(r',?\s*inc\.?', '', name, flags=re.IGNORECASE)
        name = name.strip(' ,')
        
        return name if name else 'Unnamed Party'

    def _determine_party_role(self, party_name: str, text: str) -> str:
        """Determine the role of a party in the contract"""
        party_lower = party_name.lower()
        text_lower = text.lower()
        
        # Look for role indicators near the party name
        party_context = ""
        party_pos = text_lower.find(party_lower)
        if party_pos != -1:
            start = max(0, party_pos - 100)
            end = min(len(text), party_pos + len(party_lower) + 100)
            party_context = text_lower[start:end]
        
        if any(role in party_context for role in ['client', 'customer', 'buyer']):
            return 'Client/Buyer'
        elif any(role in party_context for role in ['vendor', 'seller', 'supplier', 'contractor']):
            return 'Vendor/Seller'
        elif any(role in party_context for role in ['employer']):
            return 'Employer'
        elif any(role in party_context for role in ['employee']):
            return 'Employee'
        elif any(role in party_context for role in ['landlord']):
            return 'Landlord'
        elif any(role in party_context for role in ['tenant']):
            return 'Tenant'
        else:
            return 'Contracting Party'

    def _determine_entity_type(self, party_name: str) -> str:
        """Determine if party is individual or entity"""
        name_lower = party_name.lower()
        
        if any(indicator in name_lower for indicator in ['inc', 'corp', 'llc', 'ltd', 'company', 'corporation']):
            return 'Business Entity'
        elif any(indicator in name_lower for indicator in ['mr.', 'ms.', 'mrs.', 'dr.']):
            return 'Individual'
        else:
            # Check if it looks like a person's name (simple heuristic)
            words = party_name.split()
            if len(words) == 2 and all(word.istitle() for word in words):
                return 'Individual'
            else:
                return 'Entity'

    def _calculate_overall_confidence(self, *args) -> float:
        """Calculate overall confidence score based on extracted data"""
        total_items = 0
        for arg in args:
            if isinstance(arg, list):
                total_items += len(arg)
            elif isinstance(arg, dict):
                total_items += sum(len(v) if isinstance(v, list) else 1 for v in arg.values())
        
        # Base confidence on amount of data extracted
        if total_items >= 10:
            return 0.95
        elif total_items >= 5:
            return 0.85
        elif total_items >= 2:
            return 0.75
        elif total_items >= 1:
            return 0.65
        else:
            return 0.50

# Create global instance
enhanced_legal_processor = EnhancedLegalProcessor()
            analysis_parts.append("TERMINATION PROVISIONS: No specific termination clauses identified.")
            analysis_parts.append("")
        
        # Penalty clauses analysis
        if penalty_clauses:
            analysis_parts.append("PENALTY PROVISIONS:")
            for clause in penalty_clauses:
                amount_text = f" (Amount: {clause['amount']})" if clause.get('amount') else ""
                analysis_parts.append(f"• {clause['type']}: {self._summarize_clause(clause['text'])}{amount_text}")
            analysis_parts.append("")
        else:
            analysis_parts.append("PENALTY PROVISIONS: No specific penalty clauses identified.")
            analysis_parts.append("")
        
        # Key recommendations
        analysis_parts.append("KEY RECOMMENDATIONS:")
        recommendations = self._generate_recommendations(termination_clauses, penalty_clauses, risk_analysis)
        for rec in recommendations:
            analysis_parts.append(f"• {rec}")
        
        # Join and limit to ~800 words
        full_analysis = "\n".join(analysis_parts)
        
        # Truncate if too long (approximate word count)
        words = full_analysis.split()
        if len(words) > 800:
            full_analysis = " ".join(words[:800]) + "... [Analysis truncated for brevity]"
        
        return full_analysis
    
    def _classify_document_type(self, text: str) -> str:
        """Classify the type of legal document"""
        text_lower = text.lower()
        type_scores = {}
        
        for doc_type, keywords in self.document_type_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                type_scores[doc_type] = score
        
        if type_scores:
            return max(type_scores.keys(), key=lambda k: type_scores[k])
        
        return 'unknown'
    
    def _extract_all_legal_clauses(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract all types of legal clauses"""
        all_clauses = {}
        
        for clause_type, patterns in self.legal_patterns.items():
            clauses = []
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    # Get context around the match
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end].strip()
                    
                    # Find the page reference (approximate)
                    page_num = self._estimate_page_number(text, match.start())
                    
                    clause_info = {
                        'text': match.group(0),
                        'context': context,
                        'page_reference': page_num,
                        'position': match.start(),
                        'confidence': self._calculate_clause_confidence(match.group(0), pattern)
                    }
                    
                    clauses.append(clause_info)
            
            if clauses:
                # Remove duplicates and sort by position
                unique_clauses = self._remove_duplicate_clauses(clauses)
                all_clauses[clause_type] = sorted(unique_clauses, key=lambda x: x['position'])
        
        return all_clauses
    
    def _extract_comprehensive_obligations(self, text: str) -> List[Dict[str, Any]]:
        """Extract comprehensive obligations from the document"""
        all_obligations = []
        
        for obligation_type, patterns in self.obligation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    # Extract the full sentence containing the obligation
                    obligation_text = self._extract_full_sentence(text, match.start())
                    
                    if obligation_text and len(obligation_text) > 20:  # Filter out too short matches
                        obligation_info = {
                            'type': obligation_type,
                            'text': obligation_text,
                            'page_reference': self._estimate_page_number(text, match.start()),
                            'urgency': self._assess_obligation_urgency(obligation_text),
                            'responsible_party': self._identify_responsible_party(obligation_text),
                            'deadline': self._extract_deadline(obligation_text)
                        }
                        
                        all_obligations.append(obligation_info)
        
        # Remove duplicates and sort by urgency
        unique_obligations = self._remove_duplicate_obligations(all_obligations)
        return sorted(unique_obligations, key=lambda x: x['urgency'], reverse=True)
    
    def _perform_comprehensive_risk_assessment(self, text: str, 
                                             clauses: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Perform comprehensive risk assessment"""
        risk_factors = []
        risk_score = 0
        
        # Analyze each risk category
        for risk_level, patterns in self.risk_indicators.items():
            risk_count = 0
            found_risks = []
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    risk_count += len(matches)
                    found_risks.extend(matches)
            
            if risk_count > 0:
                risk_factor = {
                    'level': risk_level,
                    'count': risk_count,
                    'examples': found_risks[:3],  # Show up to 3 examples
                    'weight': {'high_risk': 3, 'medium_risk': 2, 'ambiguous_terms': 1}[risk_level]
                }
                risk_factors.append(risk_factor)
                risk_score += risk_count * risk_factor['weight']
        
        # Assess clause-specific risks
        clause_risks = self._assess_clause_risks(clauses)
        
        # Calculate overall risk level
        overall_risk = self._calculate_overall_risk_level(risk_score, clause_risks)
        
        # Generate risk mitigation recommendations
        recommendations = self._generate_risk_recommendations(risk_factors, clause_risks)
        
        return {
            'overall_risk': overall_risk,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'clause_risks': clause_risks,
            'recommendations': recommendations,
            'assessment_date': datetime.utcnow().isoformat()
        }
    
    def _generate_comprehensive_summary(self, text: str, clauses: Dict[str, List[Dict[str, Any]]], 
                                       obligations: List[Dict[str, Any]]) -> str:
        """Generate a comprehensive summary of the legal document"""
        summary_parts = []
        
        # Document overview
        document_type = self._classify_document_type(text)
        summary_parts.append(f"Document Type: {document_type.replace('_', ' ').title()}")
        
        # Key clause summary
        if clauses:
            clause_summary = []
            for clause_type, clause_list in clauses.items():
                if clause_list:
                    count = len(clause_list)
                    clause_name = clause_type.replace('_', ' ').title()
                    clause_summary.append(f"{clause_name}: {count} found")
            
            if clause_summary:
                summary_parts.append("Key Clauses Found:")
                summary_parts.extend([f"  - {item}" for item in clause_summary])
        
        # Obligations summary
        if obligations:
            obligation_types = {}
            for obligation in obligations:
                obj_type = obligation['type']
                obligation_types[obj_type] = obligation_types.get(obj_type, 0) + 1
            
            summary_parts.append("Obligations Summary:")
            for obj_type, count in obligation_types.items():
                type_name = obj_type.replace('_', ' ').title()
                summary_parts.append(f"  - {type_name}: {count}")
        
        # Key stakeholders
        stakeholders = self._identify_stakeholders(text)
        if stakeholders:
            summary_parts.append("Key Stakeholders:")
            for party, role in stakeholders.items():
                summary_parts.append(f"  - {party}: {role}")
        
        # Important dates
        key_dates = self._extract_key_dates(text)
        if key_dates:
            summary_parts.append("Important Dates:")
            for date_info in key_dates[:3]:  # Show top 3 dates
                summary_parts.append(f"  - {date_info['description']}: {date_info['date']}")
        
        return "\n".join(summary_parts)
    
    def _create_reference_materials(self, text: str, 
                                   clauses: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Create reference materials for legal teams"""
        reference_materials = {
            'clause_index': {},
            'page_references': {},
            'quick_reference': {},
            'citation_guide': []
        }
        
        # Create clause index with page references
        for clause_type, clause_list in clauses.items():
            if clause_list:
                clause_refs = []
                for clause in clause_list:
                    clause_refs.append({
                        'text_preview': clause['text'][:100] + '...' if len(clause['text']) > 100 else clause['text'],
                        'page': clause['page_reference'],
                        'context': clause['context'][:200] + '...' if len(clause['context']) > 200 else clause['context']
                    })
                
                reference_materials['clause_index'][clause_type] = clause_refs
        
        # Create page reference guide
        page_contents = {}
        lines = text.split('\n')
        current_page = 1
        
        for i, line in enumerate(lines):
            if 'page' in line.lower() and any(char.isdigit() for char in line):
                # Try to extract page number
                page_match = re.search(r'(\d+)', line)
                if page_match:
                    current_page = int(page_match.group(1))
            
            if current_page not in page_contents:
                page_contents[current_page] = []
            
            if len(line.strip()) > 10:  # Meaningful content
                page_contents[current_page].append(line.strip())
        
        reference_materials['page_references'] = page_contents
        
        # Create quick reference guide
        quick_ref = {}
        important_clauses = ['termination_clauses', 'penalty_clauses', 'payment_schedules']
        
        for clause_type in important_clauses:
            if clause_type in clauses and clauses[clause_type]:
                quick_ref[clause_type] = {
                    'count': len(clauses[clause_type]),
                    'first_occurrence_page': clauses[clause_type][0]['page_reference'],
                    'key_points': [clause['text'][:50] + '...' for clause in clauses[clause_type][:2]]
                }
        
        reference_materials['quick_reference'] = quick_ref
        
        # Create citation guide
        citations = []
        for clause_type, clause_list in clauses.items():
            for i, clause in enumerate(clause_list):
                citation = f"{clause_type.replace('_', ' ').title()} {i+1}, Page {clause['page_reference']}"
                citations.append(citation)
        
        reference_materials['citation_guide'] = citations
        
        return reference_materials
    
    def _extract_key_dates(self, text: str) -> List[Dict[str, str]]:
        """Extract key dates and deadlines from the document"""
        date_patterns = [
            r'(?i)(?:effective|start|commencement).*?(?:date|on)\s*:?\s*([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?i)(?:expir|end|terminat).*?(?:date|on)\s*:?\s*([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?i)(?:due|payment|deliver).*?(?:date|by|on)\s*:?\s*([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?i)(?:within|after|before)\s+(\d+)\s+(days?|weeks?|months?|years?)',
            r'(?i)(?:on|by)\s+([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        key_dates = []
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                # Extract context to understand what the date refers to
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                date_info = {
                    'date': match.group(1) if match.group(1) else match.group(0),
                    'description': self._describe_date_context(context),
                    'context': context,
                    'page_reference': self._estimate_page_number(text, match.start())
                }
                
                key_dates.append(date_info)
        
        # Remove duplicates and sort by importance
        unique_dates = self._remove_duplicate_dates(key_dates)
        return sorted(unique_dates, key=lambda x: self._date_importance_score(x['description']), reverse=True)
    
    def _identify_stakeholders(self, text: str) -> Dict[str, str]:
        """Identify key stakeholders in the document"""
        stakeholder_patterns = {
            'party': r'(?i)(?:party|parties).*?(?:"([^"]+)"|\'([^\']+)\'|([A-Z][a-z]+ [A-Z][a-z]+))',
            'company': r'(?i)(?:company|corporation|corp|inc|llc|ltd).*?(?:"([^"]+)"|\'([^\']+)\'|([A-Z][a-z]+ [A-Z][a-z]+))',
            'individual': r'(?i)(?:individual|person|mr\.|mrs\.|ms\.|dr\.)\s+([A-Z][a-z]+ [A-Z][a-z]+)',
            'client': r'(?i)(?:client|customer|buyer|purchaser).*?(?:"([^"]+)"|\'([^\']+)\'|([A-Z][a-z]+ [A-Z][a-z]+))',
            'vendor': r'(?i)(?:vendor|supplier|seller|provider).*?(?:"([^"]+)"|\'([^\']+)\'|([A-Z][a-z]+ [A-Z][a-z]+))',
            'tenant': r'(?i)(?:tenant|lessee|renter).*?(?:"([^"]+)"|\'([^\']+)\'|([A-Z][a-z]+ [A-Z][a-z]+))',
            'landlord': r'(?i)(?:landlord|lessor|owner).*?(?:"([^"]+)"|\'([^\']+)\'|([A-Z][a-z]+ [A-Z][a-z]+))'
        }
        
        stakeholders = {}
        
        for role, pattern in stakeholder_patterns.items():
            matches = re.finditer(pattern, text)
            
            for match in matches:
                # Extract the actual name from the match groups
                name = None
                for group in match.groups():
                    if group and len(group.strip()) > 2:
                        name = group.strip()
                        break
                
                if name and name not in stakeholders:
                    stakeholders[name] = role
        
        return stakeholders
    
    def _generate_compliance_checklist(self, document_type: str, 
                                     clauses: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Generate a compliance checklist based on document type and clauses"""
        checklist = []
        
        # General compliance items
        general_items = [
            {
                'item': 'Verify all parties have signed the document',
                'category': 'execution',
                'priority': 'high',
                'completed': False
            },
            {
                'item': 'Ensure all dates are properly filled in',
                'category': 'content',
                'priority': 'high',
                'completed': False
            },
            {
                'item': 'Confirm all monetary amounts are specified',
                'category': 'financial',
                'priority': 'medium',
                'completed': False
            }
        ]
        
        checklist.extend(general_items)
        
        # Document-type specific items
        if document_type == 'contract':
            contract_items = [
                {
                    'item': 'Review termination clauses for fairness',
                    'category': 'terms',
                    'priority': 'high',
                    'completed': False
                },
                {
                    'item': 'Validate payment terms and schedules',
                    'category': 'financial',
                    'priority': 'high',
                    'completed': False
                }
            ]
            checklist.extend(contract_items)
        
        elif document_type == 'employment':
            employment_items = [
                {
                    'item': 'Ensure compliance with labor laws',
                    'category': 'legal',
                    'priority': 'high',
                    'completed': False
                },
                {
                    'item': 'Review non-compete clauses for enforceability',
                    'category': 'terms',
                    'priority': 'medium',
                    'completed': False
                }
            ]
            checklist.extend(employment_items)
        
        # Clause-specific items
        if 'confidentiality' in clauses:
            checklist.append({
                'item': 'Review confidentiality terms for adequacy',
                'category': 'privacy',
                'priority': 'medium',
                'completed': False
            })
        
        if 'penalty_clauses' in clauses:
            checklist.append({
                'item': 'Assess penalty clauses for reasonableness',
                'category': 'risk',
                'priority': 'high',
                'completed': False
            })
        
        return checklist
    
    # Helper methods
    def _estimate_page_number(self, text: str, position: int) -> int:
        """Estimate page number based on text position"""
        # Simple estimation: assume ~500 characters per page
        estimated_page = (position // 500) + 1
        return max(1, estimated_page)
    
    def _calculate_clause_confidence(self, matched_text: str, pattern: str) -> float:
        """Calculate confidence score for a clause match"""
        # Base confidence
        confidence = 0.7
        
        # Longer matches are generally more reliable
        if len(matched_text) > 50:
            confidence += 0.1
        
        # Check for legal keywords
        legal_keywords = ['shall', 'must', 'required', 'obligation', 'duty']
        if any(keyword in matched_text.lower() for keyword in legal_keywords):
            confidence += 0.1
        
        # Check for specific legal formatting
        if re.search(r'\d+\.\d+|\([a-z]\)|\([0-9]+\)', matched_text):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _remove_duplicate_clauses(self, clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate clauses based on text similarity"""
        unique_clauses = []
        
        for clause in clauses:
            is_duplicate = False
            for existing in unique_clauses:
                # Check for text similarity
                if self._text_similarity(clause['text'], existing['text']) > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_clauses.append(clause)
        
        return unique_clauses
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity between two strings"""
        # Simple similarity based on common words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_full_sentence(self, text: str, position: int) -> str:
        """Extract the full sentence containing the given position"""
        # Find sentence boundaries
        start = position
        end = position
        
        # Go backwards to find sentence start
        while start > 0 and text[start] not in '.!?':
            start -= 1
        
        # Go forwards to find sentence end
        while end < len(text) and text[end] not in '.!?':
            end += 1
        
        if end < len(text):
            end += 1  # Include the punctuation
        
        return text[start:end].strip()
    
    def _assess_obligation_urgency(self, obligation_text: str) -> int:
        """Assess the urgency of an obligation (1-5 scale)"""
        text_lower = obligation_text.lower()
        
        # High urgency indicators
        if any(word in text_lower for word in ['immediate', 'urgent', 'asap', 'emergency']):
            return 5
        
        # Medium-high urgency
        if any(word in text_lower for word in ['within 24 hours', 'next day', 'tomorrow']):
            return 4
        
        # Medium urgency
        if any(word in text_lower for word in ['within', 'days', 'week']):
            return 3
        
        # Low-medium urgency
        if any(word in text_lower for word in ['month', 'quarterly']):
            return 2
        
        # Low urgency
        return 1
    
    def _identify_responsible_party(self, obligation_text: str) -> str:
        """Identify who is responsible for the obligation"""
        text_lower = obligation_text.lower()
        
        # Look for subject pronouns and party references
        if any(word in text_lower for word in ['client shall', 'buyer shall', 'purchaser shall']):
            return 'Client/Buyer'
        elif any(word in text_lower for word in ['vendor shall', 'seller shall', 'provider shall']):
            return 'Vendor/Seller'
        elif any(word in text_lower for word in ['tenant shall', 'lessee shall']):
            return 'Tenant'
        elif any(word in text_lower for word in ['landlord shall', 'lessor shall']):
            return 'Landlord'
        elif 'company shall' in text_lower:
            return 'Company'
        else:
            return 'Unspecified'
    
    def _extract_deadline(self, obligation_text: str) -> Optional[str]:
        """Extract deadline information from obligation text"""
        deadline_patterns = [
            r'(?i)(?:by|before|on|until)\s+([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?i)within\s+(\d+)\s+(days?|weeks?|months?|years?)',
            r'(?i)no later than\s+([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in deadline_patterns:
            match = re.search(pattern, obligation_text)
            if match:
                return match.group(1)
        
        return None
    
    def _remove_duplicate_obligations(self, obligations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate obligations"""
        unique_obligations = []
        
        for obligation in obligations:
            is_duplicate = False
            for existing in unique_obligations:
                if self._text_similarity(obligation['text'], existing['text']) > 0.7:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_obligations.append(obligation)
        
        return unique_obligations

    # New helper methods for readable legal analysis
    
    def _extract_clause_context(self, text: str, start: int, end: int) -> str:
        """Extract meaningful context around a clause"""
        # Find sentence boundaries
        context_start = max(0, start - 200)
        context_end = min(len(text), end + 200)
        
        context = text[context_start:context_end]
        
        # Try to find complete sentences
        sentences = re.split(r'(?<=[.!?])\s+', context)
        if len(sentences) > 1:
            # Return the middle sentences that likely contain the full clause
            middle = len(sentences) // 2
            if middle > 0 and middle < len(sentences) - 1:
                return sentences[middle-1] + " " + sentences[middle] + " " + sentences[middle+1]
        
        return context.strip()

    def _assess_clause_risk(self, clause_text: str, clause_type: str) -> str:
        """Assess risk level of a specific clause"""
        clause_lower = clause_text.lower()
        
        if clause_type == 'termination':
            high_risk_terms = ['immediate', 'without notice', 'sole discretion', 'any reason']
            medium_risk_terms = ['30 days', 'notice required', 'breach', 'default']
            
            if any(term in clause_lower for term in high_risk_terms):
                return "High"
            elif any(term in clause_lower for term in medium_risk_terms):
                return "Medium"
            else:
                return "Low"
        
        elif clause_type == 'penalty':
            # Look for monetary amounts
            amounts = re.findall(r'\$[\d,]+', clause_text)
            percentages = re.findall(r'\d+%', clause_text)
            
            if amounts or 'unlimited' in clause_lower or 'liquidated' in clause_lower:
                return "High"
            elif percentages or 'interest' in clause_lower:
                return "Medium"
            else:
                return "Low"
        
        return "Low"

    def _extract_penalty_amount(self, clause_text: str) -> str:
        """Extract penalty amount from clause text"""
        # Look for dollar amounts
        dollar_match = re.search(r'\$[\d,]+(?:\.\d{2})?', clause_text)
        if dollar_match:
            return dollar_match.group()
        
        # Look for percentages
        percent_match = re.search(r'\d+(?:\.\d+)?%', clause_text)
        if percent_match:
            return percent_match.group()
        
        # Look for interest rates
        interest_match = re.search(r'\d+(?:\.\d+)?\s*(?:percent|%)\s*(?:per|annually|monthly)', clause_text)
        if interest_match:
            return interest_match.group()
        
        return "Amount not specified"

    def _generate_risk_summary(self, risk_level: str, risk_factors: List[str]) -> str:
        """Generate a human-readable risk summary"""
        if risk_level == "High":
            base_msg = "This document contains significant legal risks that require immediate attention."
        elif risk_level == "Medium":
            base_msg = "This document contains moderate legal risks that should be reviewed carefully."
        elif risk_level == "Low":
            base_msg = "This document contains minor legal risks with standard commercial terms."
        else:
            base_msg = "This document appears to have minimal legal risks."
        
        if risk_factors:
            return f"{base_msg} Key concerns include: {', '.join(risk_factors[:3])}."
        else:
            return f"{base_msg} No major risk factors identified."

    def _summarize_clause(self, clause_text: str) -> str:
        """Create a brief summary of a clause"""
        # Limit to 2 sentences and 150 characters
        sentences = re.split(r'(?<=[.!?])\s+', clause_text.strip())
        
        if len(sentences) > 2:
            summary = ". ".join(sentences[:2]) + "."
        else:
            summary = clause_text.strip()
        
        if len(summary) > 150:
            summary = summary[:147] + "..."
        
        return summary

    def _generate_recommendations(self, termination_clauses: List, penalty_clauses: List, risk_analysis: Dict) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        # Termination-related recommendations
        if not termination_clauses:
            recommendations.append("Consider adding clear termination clauses to define exit procedures")
        else:
            high_risk_termination = [c for c in termination_clauses if c.get('risk_level') == 'High']
            if high_risk_termination:
                recommendations.append("Review termination clauses for potentially unfavorable terms")
        
        # Penalty-related recommendations
        high_penalty_risk = [c for c in penalty_clauses if c.get('risk_level') == 'High']
        if high_penalty_risk:
            recommendations.append("Negotiate penalty clauses to limit financial exposure")
        
        # Risk level recommendations
        if risk_analysis.get('risk_level') == 'High':
            recommendations.append("Seek legal counsel before signing due to high-risk provisions")
        elif risk_analysis.get('risk_level') == 'Medium':
            recommendations.append("Consider legal review to address moderate risk factors")
        
        # General recommendations
        if len(recommendations) == 0:
            recommendations.append("Standard commercial terms identified - proceed with normal review process")
        
        return recommendations[:4]  # Limit to 4 recommendations

    def _calculate_overall_confidence(self, termination_clauses: List, penalty_clauses: List) -> float:
        """Calculate confidence score for the analysis"""
        confidence = 0.6  # Base confidence
        
        if termination_clauses:
            confidence += 0.2
        if penalty_clauses:
            confidence += 0.15
        
        # Boost confidence if we found specific, well-structured clauses
        well_structured = len([c for c in (termination_clauses + penalty_clauses) 
                             if len(c.get('text', '')) > 50])
        confidence += min(well_structured * 0.05, 0.2)
        
        return min(confidence, 0.95)  # Cap at 95%
    
    def _assess_clause_risks(self, clauses: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
        """Assess risks associated with specific clauses"""
        clause_risks = {}
        
        # High-risk clause types
        high_risk_clauses = ['penalty_clauses', 'liability_clauses', 'termination_clauses']
        
        for clause_type, clause_list in clauses.items():
            if clause_list:
                if clause_type in high_risk_clauses:
                    clause_risks[clause_type] = 'high'
                elif clause_type in ['payment_schedules', 'confidentiality']:
                    clause_risks[clause_type] = 'medium'
                else:
                    clause_risks[clause_type] = 'low'
        
        return clause_risks
    
    def _calculate_overall_risk_level(self, risk_score: int, 
                                    clause_risks: Dict[str, str]) -> str:
        """Calculate overall risk level"""
        high_risk_count = sum(1 for risk in clause_risks.values() if risk == 'high')
        medium_risk_count = sum(1 for risk in clause_risks.values() if risk == 'medium')
        
        if risk_score > 10 or high_risk_count > 2:
            return 'high'
        elif risk_score > 5 or high_risk_count > 0 or medium_risk_count > 2:
            return 'medium'
        else:
            return 'low'
    
    def _generate_risk_recommendations(self, risk_factors: List[Dict[str, Any]], 
                                     clause_risks: Dict[str, str]) -> List[str]:
        """Generate risk mitigation recommendations"""
        recommendations = []
        
        # General recommendations based on risk factors
        for risk_factor in risk_factors:
            if risk_factor['level'] == 'high_risk':
                recommendations.append("Consider legal review of high-risk terms before signing")
            elif risk_factor['level'] == 'ambiguous_terms':
                recommendations.append("Clarify ambiguous terms to avoid future disputes")
        
        # Clause-specific recommendations
        if 'penalty_clauses' in clause_risks and clause_risks['penalty_clauses'] == 'high':
            recommendations.append("Review penalty clauses for reasonableness and enforceability")
        
        if 'termination_clauses' in clause_risks:
            recommendations.append("Ensure termination procedures are clearly defined")
        
        if not recommendations:
            recommendations.append("Document appears to have acceptable risk levels")
        
        return recommendations
    
    def _describe_date_context(self, context: str) -> str:
        """Describe what a date refers to based on context"""
        context_lower = context.lower()
        
        if any(word in context_lower for word in ['effective', 'start', 'commence']):
            return 'Effective/Start Date'
        elif any(word in context_lower for word in ['expir', 'end', 'terminat']):
            return 'Expiration/End Date'
        elif any(word in context_lower for word in ['due', 'payment']):
            return 'Payment Due Date'
        elif any(word in context_lower for word in ['deliver', 'completion']):
            return 'Delivery/Completion Date'
        else:
            return 'Important Date'
    
    def _remove_duplicate_dates(self, dates: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Remove duplicate dates"""
        unique_dates = []
        seen_dates = set()
        
        for date_info in dates:
            date_key = date_info['date'].strip()
            if date_key not in seen_dates:
                seen_dates.add(date_key)
                unique_dates.append(date_info)
        
        return unique_dates
    
    def _date_importance_score(self, description: str) -> int:
        """Score date importance for sorting"""
        importance_scores = {
            'Effective/Start Date': 5,
            'Expiration/End Date': 5,
            'Payment Due Date': 4,
            'Delivery/Completion Date': 3,
            'Important Date': 1
        }
        
        return importance_scores.get(description, 1)
    
    def _calculate_legal_confidence(self, clauses: Dict[str, List[Dict[str, Any]]], 
                                   obligations: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence score for legal analysis"""
        # Base confidence
        confidence = 0.5
        
        # Boost for finding clauses
        if clauses:
            clause_count = sum(len(clause_list) for clause_list in clauses.values())
            confidence += min(clause_count * 0.05, 0.3)
        
        # Boost for finding obligations
        if obligations:
            confidence += min(len(obligations) * 0.02, 0.1)
        
        # Boost for high-confidence clauses
        high_conf_clauses = 0
        for clause_list in clauses.values():
            for clause in clause_list:
                if clause.get('confidence', 0) > 0.8:
                    high_conf_clauses += 1
        
        confidence += min(high_conf_clauses * 0.02, 0.1)
        
        return min(confidence, 1.0)

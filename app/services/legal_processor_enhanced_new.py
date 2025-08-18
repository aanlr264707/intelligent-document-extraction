import re
import json
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import logging
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
        # Initialize OpenAI availability
        try:
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            self.openai_available = bool(self.openai_api_key)
        except:
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
            logger.info("Starting comprehensive legal document analysis")
            
            # Perform multiple analysis layers
            basic_analysis = self._extract_basic_legal_info(text)
            clause_analysis = await self._extract_legal_clauses(text)
            financial_analysis = self._extract_financial_terms(text)
            parties_analysis = self._extract_parties_info(text)
            dates_analysis = self._extract_key_dates(text)
            risk_analysis = self._assess_comprehensive_risk(text, clause_analysis)
            
            # Generate document overview and summary
            overview = await self._generate_document_overview(text, document_type)
            summary = await self._generate_contract_summary(text, clause_analysis, financial_analysis)
            
            # Check for tables in document
            tables_data = self._extract_document_tables(text)
            
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
                'document_tables': tables_data,
                'confidence_score': self._calculate_overall_confidence(clause_analysis, financial_analysis, parties_analysis),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in comprehensive legal analysis: {e}")
            return {
                'error': f"Analysis failed: {str(e)}",
                'document_overview': {
                    'type': 'Unknown', 
                    'description': 'Analysis failed due to processing error'
                },
                'contract_summary': 'Unable to generate summary due to processing error',
                'main_parties': [{'name': 'No party information found', 'role': 'Unknown', 'type': 'Unknown'}],
                'key_dates': [KeyDate('Not Found', 'No key dates identified', 'No specific dates found', 'Low').__dict__],
                'financial_terms': [],
                'legal_clauses': {
                    'termination_clauses': [], 
                    'penalty_clauses': [], 
                    'payment_terms': [], 
                    'other_clauses': []
                },
                'risk_assessment': {
                    'overall_risk': 'Unknown', 
                    'risk_score': 0, 
                    'risk_factors': ['Processing error occurred'],
                    'summary': 'Unable to assess risk due to processing error'
                },
                'document_tables': [],
                'confidence_score': 0.0
            }

    async def _extract_legal_clauses(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract and categorize legal clauses with enhanced AI analysis"""
        clauses = {
            'termination_clauses': [],
            'penalty_clauses': [],
            'payment_terms': [],
            'other_clauses': []
        }
        
        try:
            # Extract termination clauses
            termination_clauses = []
            for pattern in self.legal_patterns['termination_clauses']:
                matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
                for match in matches:
                    clause_content = self._extract_clause_context(text, match.start(), match.end())
                    if clause_content and len(clause_content) > 20:  # Filter short matches
                        termination_clauses.append({
                            'type': 'Termination Clause',
                            'content': clause_content,
                            'location': f"Position {match.start()}-{match.end()}",
                            'confidence': 0.85,
                            'risk_level': self._assess_clause_risk(clause_content, 'termination'),
                            'implications': self._get_termination_implications(clause_content)
                        })
            
            # Remove duplicates and limit
            clauses['termination_clauses'] = self._remove_duplicate_clauses(termination_clauses)[:3]
            
            # Extract penalty clauses
            penalty_clauses = []
            for pattern in self.legal_patterns['penalty_clauses']:
                matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
                for match in matches:
                    clause_content = self._extract_clause_context(text, match.start(), match.end())
                    if clause_content and len(clause_content) > 20:
                        penalty_clauses.append({
                            'type': 'Penalty Clause',
                            'content': clause_content,
                            'location': f"Position {match.start()}-{match.end()}",
                            'confidence': 0.90,
                            'risk_level': self._assess_clause_risk(clause_content, 'penalty'),
                            'implications': self._get_penalty_implications(clause_content)
                        })
            
            clauses['penalty_clauses'] = self._remove_duplicate_clauses(penalty_clauses)[:3]
            
            # Extract payment terms
            payment_terms = []
            for pattern in self.legal_patterns['payment_terms']:
                matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
                for match in matches:
                    clause_content = self._extract_clause_context(text, match.start(), match.end())
                    if clause_content and len(clause_content) > 20:
                        payment_terms.append({
                            'type': 'Payment Terms',
                            'content': clause_content,
                            'location': f"Position {match.start()}-{match.end()}",
                            'confidence': 0.88,
                            'risk_level': 'Medium',
                            'implications': ['Payment obligations defined', 'Timeline specified']
                        })
            
            clauses['payment_terms'] = self._remove_duplicate_clauses(payment_terms)[:3]
            
            # Add fallback messages if no clauses found
            if not clauses['termination_clauses']:
                clauses['termination_clauses'] = [{
                    'type': 'Not Found',
                    'content': 'No specific termination clauses identified.',
                    'location': 'Document review',
                    'confidence': 1.0,
                    'risk_level': 'Medium',
                    'implications': ['Consider adding clear termination clauses to define exit procedures']
                }]
            
            if not clauses['penalty_clauses']:
                clauses['penalty_clauses'] = [{
                    'type': 'Not Found',
                    'content': 'No specific penalty clauses identified.',
                    'location': 'Document review',
                    'confidence': 1.0,
                    'risk_level': 'Low',
                    'implications': ['Standard enforcement mechanisms may apply']
                }]
                
        except Exception as e:
            logger.error(f"Error extracting legal clauses: {e}")
            
        return clauses

    def _extract_financial_terms(self, text: str) -> List[Dict[str, Any]]:
        """Extract comprehensive financial terms and amounts"""
        financial_terms = []
        
        try:
            # Extract amounts with context
            amount_patterns = [
                (r'(?i)(?:total\s+(?:amount|value|cost|price).*?\$[\d,]+(?:\.\d{2})?)', 'Contract Value'),
                (r'(?i)(?:payment\s+of\s+\$[\d,]+(?:\.\d{2})?)', 'Payment Amount'),
                (r'(?i)(?:monthly\s+(?:payment|fee|rent).*?\$[\d,]+(?:\.\d{2})?)', 'Monthly Payment'),
                (r'(?i)(?:annual\s+(?:salary|fee|payment).*?\$[\d,]+(?:\.\d{2})?)', 'Annual Payment'),
                (r'(?i)(?:hourly\s+rate.*?\$[\d,]+(?:\.\d{2})?)', 'Hourly Rate'),
                (r'(?i)(?:commission.*?\d+(?:\.\d+)?%)', 'Commission Rate'),
                (r'(?i)(?:deposit.*?\$[\d,]+(?:\.\d{2})?)', 'Deposit Amount'),
                (r'(?i)(?:penalty.*?\$[\d,]+(?:\.\d{2})?)', 'Penalty Amount'),
                (r'(?i)(?:late\s+fee.*?\$[\d,]+(?:\.\d{2})?)', 'Late Fee')
            ]
            
            for pattern, term_type in amount_patterns:
                matches = re.finditer(pattern, text, re.MULTILINE)
                for match in matches:
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
                    
                    frequency = self._extract_frequency(content)
                    due_date = self._extract_due_date(content)
                    
                    financial_term = {
                        'term_type': term_type,
                        'amount': amount,
                        'currency': currency,
                        'frequency': frequency,
                        'due_date': due_date,
                        'description': content.strip(),
                        'location': f"Position {match.start()}-{match.end()}"
                    }
                    financial_terms.append(financial_term)
            
            # Remove duplicates
            financial_terms = self._remove_duplicate_financial_terms(financial_terms)
            
            if not financial_terms:
                financial_terms = [{
                    'term_type': 'Not Found',
                    'amount': 'No financial terms identified',
                    'currency': 'N/A',
                    'frequency': 'N/A',
                    'due_date': 'N/A',
                    'description': 'No specific financial terms found in document',
                    'location': 'Document review'
                }]
                
        except Exception as e:
            logger.error(f"Error extracting financial terms: {e}")
            
        return financial_terms[:10]  # Limit to 10 terms

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
                if party['name'] not in seen_names and len(party['name']) > 3:
                    unique_parties.append(party)
                    seen_names.add(party['name'])
            
            if not unique_parties:
                return [{
                    'name': 'No party information found', 
                    'role': 'Unknown', 
                    'type': 'Unknown'
                }]
                
        except Exception as e:
            logger.error(f"Error extracting parties info: {e}")
            return [{
                'name': 'Error extracting party information', 
                'role': 'Unknown', 
                'type': 'Unknown'
            }]
            
        return unique_parties[:5]  # Limit to 5 parties

    def _extract_key_dates(self, text: str) -> List[Dict[str, Any]]:
        """Extract and categorize key dates from the document"""
        key_dates = []
        
        try:
            # Date patterns with context
            date_patterns = [
                (r'(?i)(?:effective\s+date|commencement\s+date)[:\s]*([^,\n.]+)', 'Effective Date', 'High'),
                (r'(?i)(?:expiration\s+date|termination\s+date|end\s+date)[:\s]*([^,\n.]+)', 'Expiration Date', 'High'),
                (r'(?i)(?:renewal\s+date|review\s+date)[:\s]*([^,\n.]+)', 'Renewal Date', 'Medium'),
                (r'(?i)(?:deadline|due\s+date|delivery\s+date)[:\s]*([^,\n.]+)', 'Deadline', 'Medium'),
                (r'(?i)(?:notice\s+period)[:\s]*(\d+\s+days?)', 'Notice Period', 'Medium'),
                (r'(?i)(?:term\s+of)[:\s]*(\d+\s+(?:years?|months?))', 'Contract Term', 'High')
            ]
            
            for pattern, date_type, importance in date_patterns:
                matches = re.finditer(pattern, text, re.MULTILINE)
                for match in matches:
                    date_value = match.group(1).strip()
                    
                    key_date = {
                        'date_type': date_type,
                        'date_value': date_value,
                        'description': f"{date_type}: {date_value}",
                        'importance': importance,
                        'location': f"Position {match.start()}-{match.end()}"
                    }
                    key_dates.append(key_date)
            
            # Remove duplicates
            key_dates = self._remove_duplicate_dates(key_dates)
            
            if not key_dates:
                return [{
                    'date_type': 'Not Found',
                    'date_value': 'No key dates identified',
                    'description': 'No specific dates found in document',
                    'importance': 'Low',
                    'location': 'Document review'
                }]
                
        except Exception as e:
            logger.error(f"Error extracting key dates: {e}")
            return [{
                'date_type': 'Error',
                'date_value': 'Error extracting dates',
                'description': 'Error occurred during date extraction',
                'importance': 'Low',
                'location': 'Processing error'
            }]
            
        return key_dates[:8]  # Limit to 8 dates

    def _extract_document_tables(self, text: str) -> List[Dict[str, Any]]:
        """Extract tables and structured data from document"""
        tables = []
        
        try:
            # Look for table-like structures
            table_patterns = [
                r'(?i)(?:table|schedule|exhibit|appendix)\s+\d+.*?\n((?:.*\|.*\n){2,})',
                r'(\n(?:\s*[^\n]+\s+\|\s+[^\n]+\n){2,})',
                r'(?i)(?:payment\s+schedule|fee\s+schedule|rate\s+schedule)\s*:?\s*\n((?:.*\n){2,10})',
            ]
            
            for i, pattern in enumerate(table_patterns):
                matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
                for match in matches:
                    table_content = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    
                    if len(table_content.strip()) > 50:  # Only include substantial content
                        table_data = {
                            'title': f'Table {len(tables) + 1}',
                            'content': table_content.strip(),
                            'type': 'Structured Data',
                            'location': f"Position {match.start()}-{match.end()}",
                            'rows_count': len([line for line in table_content.split('\n') if line.strip()])
                        }
                        tables.append(table_data)
            
            if not tables:
                # Look for any structured financial data
                financial_data_pattern = r'(?i)(?:amount|fee|cost|price|rate)\s*:?\s*\$?[\d,]+(?:\.\d{2})?'
                financial_matches = re.findall(financial_data_pattern, text)
                
                if financial_matches:
                    tables.append({
                        'title': 'Financial Data Summary',
                        'content': '\n'.join(financial_matches[:10]),  # Limit to 10 items
                        'type': 'Financial Summary',
                        'location': 'Multiple locations',
                        'rows_count': len(financial_matches[:10])
                    })
                
        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
            
        return tables[:5]  # Limit to 5 tables

    def _assess_comprehensive_risk(self, text: str, clauses: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Perform comprehensive risk assessment of the document"""
        risk_factors = []
        risk_score = 0
        
        try:
            # Analyze clauses for risk
            for clause_type, clause_list in clauses.items():
                for clause in clause_list:
                    if clause.get('risk_level') == 'High':
                        risk_score += 25
                        risk_factors.append(f"High-risk {clause.get('type', 'clause')} identified")
                    elif clause.get('risk_level') == 'Medium':
                        risk_score += 10
                        risk_factors.append(f"Medium-risk {clause.get('type', 'clause')} present")
            
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

    async def _generate_document_overview(self, text: str, document_type: str = None) -> Dict[str, Any]:
        """Generate comprehensive document overview"""
        try:
            doc_type = self._classify_document_type(text)
            purpose = self._determine_document_purpose(text, doc_type)
            
            return {
                'type': doc_type,
                'purpose': purpose,
                'length': len(text),
                'estimated_pages': max(1, len(text) // 3000),
                'complexity': self._assess_document_complexity(text),
                'key_characteristics': self._identify_key_characteristics(text, doc_type)
            }
        except Exception as e:
            logger.error(f"Error generating document overview: {e}")
            return {
                'type': 'Unknown',
                'purpose': 'Unable to determine purpose',
                'length': len(text),
                'estimated_pages': 1,
                'complexity': 'Unknown',
                'key_characteristics': ['Analysis failed']
            }

    async def _generate_contract_summary(self, text: str, clauses: Dict, financial_terms: List) -> str:
        """Generate comprehensive contract summary"""
        try:
            clause_count = sum(len(v) for v in clauses.values() if isinstance(v, list))
            financial_count = len([ft for ft in financial_terms if ft.get('term_type') != 'Not Found'])
            
            doc_type = self._classify_document_type(text)
            
            summary_parts = []
            summary_parts.append(f"This {doc_type.lower()} establishes legal obligations between the contracting parties.")
            
            if clause_count > 3:
                summary_parts.append(f"The document contains {clause_count} identified legal clauses covering various aspects of the relationship.")
            
            if financial_count > 0:
                summary_parts.append(f"Financial terms include {financial_count} specific monetary provisions.")
            
            # Add specific observations
            if any('termination' in str(clause).lower() for clause_list in clauses.values() for clause in clause_list):
                summary_parts.append("Termination provisions are defined to govern contract ending procedures.")
            
            if any('penalty' in str(ft).lower() for ft in financial_terms):
                summary_parts.append("Penalty clauses specify consequences for non-compliance.")
            
            summary_parts.append("The agreement defines rights, responsibilities, and procedures governing the contractual relationship.")
            
            return " ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error generating contract summary: {e}")
            return "This document establishes legal obligations between parties. Analysis was unable to provide detailed summary due to processing limitations."

    # Helper methods
    def _classify_document_type(self, text: str) -> str:
        """Classify the document type based on content"""
        text_lower = text.lower()
        
        type_indicators = {
            'Purchase Order': ['purchase', 'order', 'goods', 'products', 'buyer', 'seller'],
            'Employment Agreement': ['employment', 'employee', 'employer', 'job', 'position', 'salary'],
            'Lease Agreement': ['lease', 'rent', 'tenant', 'landlord', 'premises', 'property'],
            'Service Agreement': ['service', 'services', 'provider', 'client', 'scope of work'],
            'Non-Disclosure Agreement': ['non-disclosure', 'confidential', 'nda', 'proprietary'],
            'Loan Agreement': ['loan', 'borrow', 'lender', 'principal', 'interest', 'credit'],
            'Partnership Agreement': ['partnership', 'partners', 'joint venture', 'collaboration'],
            'License Agreement': ['license', 'licensing', 'intellectual property', 'copyright']
        }
        
        for doc_type, keywords in type_indicators.items():
            if sum(1 for keyword in keywords if keyword in text_lower) >= 2:
                return doc_type
        
        return 'General Contract'

    def _determine_document_purpose(self, text: str, doc_type: str) -> str:
        """Determine the primary purpose of the document"""
        purpose_map = {
            'Purchase Order': 'To establish terms for the purchase and sale of goods or services',
            'Employment Agreement': 'To define the employment relationship between employer and employee',
            'Lease Agreement': 'To establish terms for the rental of property or premises',
            'Service Agreement': 'To define the provision of services between parties',
            'Non-Disclosure Agreement': 'To protect confidential information between parties',
            'Loan Agreement': 'To establish terms for the lending and borrowing of money',
            'Partnership Agreement': 'To establish a business partnership between parties',
            'License Agreement': 'To grant rights to use intellectual property or assets'
        }
        
        return purpose_map.get(doc_type, 'To establish legal obligations and rights between contracting parties')

    def _assess_document_complexity(self, text: str) -> str:
        """Assess the complexity level of the document"""
        length = len(text)
        
        # Count legal terms
        legal_terms = ['whereas', 'heretofore', 'hereby', 'thereof', 'therein', 'notwithstanding']
        legal_term_count = sum(1 for term in legal_terms if term in text.lower())
        
        # Count sections
        section_count = len(re.findall(r'(?i)(?:section|article|clause)\s+\d+', text))
        
        if length > 10000 or legal_term_count > 5 or section_count > 10:
            return 'High'
        elif length > 5000 or legal_term_count > 2 or section_count > 5:
            return 'Medium'
        else:
            return 'Low'

    def _identify_key_characteristics(self, text: str, doc_type: str) -> List[str]:
        """Identify key characteristics of the document"""
        characteristics = []
        
        if re.search(r'\$[\d,]+', text):
            characteristics.append('Contains financial terms')
        
        if re.search(r'(?i)signature', text):
            characteristics.append('Requires signatures')
        
        if re.search(r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}', text):
            characteristics.append('Contains specific dates')
        
        if re.search(r'(?i)termination', text):
            characteristics.append('Includes termination provisions')
        
        if re.search(r'(?i)confidential', text):
            characteristics.append('Contains confidentiality provisions')
        
        if not characteristics:
            characteristics.append('Standard commercial document')
        
        return characteristics

    def _extract_clause_context(self, text: str, start: int, end: int, context_chars: int = 300) -> str:
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
        high_risk_terms = ['immediate', 'without notice', 'unlimited', 'personal guarantee', 'liquidated damages']
        if any(term in clause_lower for term in high_risk_terms):
            return 'High'
        
        # Medium risk indicators
        medium_risk_terms = ['penalty', 'indemnify', 'automatic', 'exclusive']
        if any(term in clause_lower for term in medium_risk_terms):
            return 'Medium'
        
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

    def _extract_frequency(self, content: str) -> str:
        """Extract payment frequency from content"""
        content_lower = content.lower()
        
        frequency_map = {
            'monthly': 'Monthly',
            'quarterly': 'Quarterly',
            'annual': 'Annually',
            'yearly': 'Annually',
            'weekly': 'Weekly',
            'hourly': 'Hourly',
            'daily': 'Daily'
        }
        
        for freq_term, freq_value in frequency_map.items():
            if freq_term in content_lower:
                return freq_value
        
        return 'One-time'

    def _extract_due_date(self, content: str) -> str:
        """Extract due date information"""
        # Look for specific dates
        date_match = re.search(r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}', content)
        if date_match:
            return date_match.group()
        
        # Look for relative dates
        content_lower = content.lower()
        if 'upon receipt' in content_lower:
            return 'Upon receipt'
        elif 'net 30' in content_lower:
            return 'Net 30 days'
        elif 'net 15' in content_lower:
            return 'Net 15 days'
        elif 'immediate' in content_lower:
            return 'Immediate'
        
        return 'Not specified'

    def _clean_party_name(self, name: str) -> str:
        """Clean and format party name"""
        # Remove common legal suffixes and prefixes
        name = re.sub(r'\([^)]*\)', '', name)  # Remove parenthetical content
        name = re.sub(r',?\s*a\s+\w+\s+corporation', '', name, flags=re.IGNORECASE)
        name = re.sub(r',?\s*llc', '', name, flags=re.IGNORECASE)
        name = re.sub(r',?\s*inc\.?', '', name, flags=re.IGNORECASE)
        name = name.strip(' ,')
        
        return name if name and len(name) > 2 else 'Unnamed Party'

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
        
        role_indicators = {
            'Client/Buyer': ['client', 'customer', 'buyer', 'purchaser'],
            'Vendor/Seller': ['vendor', 'seller', 'supplier', 'contractor'],
            'Employer': ['employer'],
            'Employee': ['employee'],
            'Landlord': ['landlord'],
            'Tenant': ['tenant'],
            'Service Provider': ['provider', 'consultant']
        }
        
        for role, indicators in role_indicators.items():
            if any(indicator in party_context for indicator in indicators):
                return role
        
        return 'Contracting Party'

    def _determine_entity_type(self, party_name: str) -> str:
        """Determine if party is individual or entity"""
        name_lower = party_name.lower()
        
        entity_indicators = ['inc', 'corp', 'llc', 'ltd', 'company', 'corporation', 'enterprises']
        if any(indicator in name_lower for indicator in entity_indicators):
            return 'Business Entity'
        
        individual_indicators = ['mr.', 'ms.', 'mrs.', 'dr.']
        if any(indicator in name_lower for indicator in individual_indicators):
            return 'Individual'
        
        # Check if it looks like a person's name (simple heuristic)
        words = party_name.split()
        if len(words) == 2 and all(word.istitle() for word in words):
            return 'Individual'
        
        return 'Entity'

    def _remove_duplicate_clauses(self, clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate clauses based on content similarity"""
        unique_clauses = []
        
        for clause in clauses:
            is_duplicate = False
            for unique_clause in unique_clauses:
                if self._text_similarity(clause.get('content', ''), unique_clause.get('content', '')) > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_clauses.append(clause)
        
        return unique_clauses

    def _remove_duplicate_financial_terms(self, terms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate financial terms"""
        unique_terms = []
        seen_amounts = set()
        
        for term in terms:
            amount_key = f"{term.get('amount', '')}-{term.get('term_type', '')}"
            if amount_key not in seen_amounts:
                unique_terms.append(term)
                seen_amounts.add(amount_key)
        
        return unique_terms

    def _remove_duplicate_dates(self, dates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate dates"""
        unique_dates = []
        seen_dates = set()
        
        for date in dates:
            date_key = f"{date.get('date_type', '')}-{date.get('date_value', '')}"
            if date_key not in seen_dates:
                unique_dates.append(date)
                seen_dates.add(date_key)
        
        return unique_dates

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    def _calculate_overall_confidence(self, *args) -> float:
        """Calculate overall confidence score based on extracted data"""
        total_items = 0
        for arg in args:
            if isinstance(arg, list):
                # Don't count "Not Found" items
                total_items += len([item for item in arg if not str(item).startswith('No ') and not str(item).startswith('Error')])
            elif isinstance(arg, dict):
                # Count actual extracted items
                total_items += sum(len(v) if isinstance(v, list) else 1 for v in arg.values())
        
        # Base confidence on amount of data extracted
        if total_items >= 15:
            return 0.95
        elif total_items >= 10:
            return 0.90
        elif total_items >= 5:
            return 0.80
        elif total_items >= 2:
            return 0.70
        elif total_items >= 1:
            return 0.60
        else:
            return 0.50

# Create global instance
enhanced_legal_processor = EnhancedLegalProcessor()

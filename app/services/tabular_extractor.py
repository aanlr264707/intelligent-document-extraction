import re
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class TabularDataExtractor:
    """Enhanced service for extracting and reconstructing tabular data from documents"""
    
    def __init__(self):
        self.table_patterns = {
            'header_indicators': [
                r'^\s*[A-Z][a-z\s]+[A-Z][a-z\s]+',  # Title case headers
                r'^\s*[A-Z\s]+$',  # All caps headers
                r'.*\b(name|date|amount|total|quantity|description|price)\b.*'  # Common headers
            ],
            'row_separators': [
                r'[-]{3,}',  # Dashes
                r'[_]{3,}',  # Underscores
                r'[=]{3,}',  # Equals signs
                r'\+[-\+]+\+'  # ASCII table borders
            ],
            'column_separators': [
                r'\|',  # Pipe characters
                r'\t',  # Tabs
                r'\s{3,}',  # Multiple spaces
                r'(?<=\d)\s+(?=[A-Za-z])',  # Space between number and text
                r'(?<=[A-Za-z])\s+(?=\d)'   # Space between text and number
            ]
        }
        
        self.table_keywords = [
            'table', 'schedule', 'list', 'summary', 'breakdown', 'details',
            'items', 'services', 'products', 'charges', 'fees', 'rates'
        ]
        
        # Common table headers and their types
        self.header_types = {
            'date': ['date', 'time', 'when', 'period', 'due'],
            'amount': ['amount', 'total', 'cost', 'price', 'fee', 'charge', 'value'],
            'quantity': ['qty', 'quantity', 'count', 'number', 'units'],
            'description': ['description', 'item', 'service', 'product', 'details'],
            'name': ['name', 'title', 'label', 'person', 'entity'],
            'id': ['id', 'number', 'code', 'reference', 'ref']
        }
    
    def extract_tables_from_text(self, text: str, extraction_requirements: str = "") -> Dict[str, Any]:
        """Main method to extract tabular data from text"""
        try:
            logger.info("Starting tabular data extraction")
            
            # Identify potential table regions
            table_regions = self._identify_table_regions(text)
            
            if not table_regions:
                return {
                    'success': False,
                    'message': 'No tabular data detected',
                    'tables': [],
                    'confidence_score': 0.0
                }
            
            extracted_tables = []
            total_confidence = 0.0
            
            for i, region in enumerate(table_regions):
                logger.info(f"Processing table region {i+1}")
                
                # Extract table structure
                table_data = self._extract_table_structure(region)
                
                if table_data['success']:
                    # Reconstruct multi-page tables if needed
                    table_data = self._reconstruct_split_table(table_data, extracted_tables)
                    
                    # Apply data type inference
                    table_data = self._infer_column_types(table_data)
                    
                    # Validate and clean data
                    table_data = self._validate_table_data(table_data)
                    
                    # Calculate confidence
                    confidence = self._calculate_table_confidence(table_data)
                    table_data['confidence_score'] = confidence
                    total_confidence += confidence
                    
                    extracted_tables.append(table_data)
            
            # Apply extraction requirements filtering
            if extraction_requirements:
                extracted_tables = self._filter_tables_by_requirements(
                    extracted_tables, extraction_requirements
                )
            
            avg_confidence = total_confidence / len(extracted_tables) if extracted_tables else 0.0
            
            return {
                'success': True,
                'tables': extracted_tables,
                'table_count': len(extracted_tables),
                'confidence_score': avg_confidence,
                'processing_method': 'tabular_extraction'
            }
            
        except Exception as e:
            logger.error(f"Error in tabular data extraction: {e}")
            return {
                'success': False,
                'error': f'Tabular extraction failed: {str(e)}',
                'tables': [],
                'confidence_score': 0.0
            }
    
    def _identify_table_regions(self, text: str) -> List[str]:
        """Identify potential table regions in the text"""
        regions = []
        lines = text.split('\n')
        current_region = []
        in_table = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                if in_table and current_region:
                    # Empty line might end a table
                    regions.append('\n'.join(current_region))
                    current_region = []
                    in_table = False
                continue
            
            # Check if line looks like table content
            is_table_line = self._is_table_line(line)
            
            if is_table_line:
                if not in_table:
                    in_table = True
                current_region.append(line)
            else:
                if in_table and current_region:
                    # Non-table line might end the table
                    if len(current_region) >= 2:  # Minimum table size
                        regions.append('\n'.join(current_region))
                    current_region = []
                    in_table = False
        
        # Add final region if we're still in a table
        if in_table and current_region and len(current_region) >= 2:
            regions.append('\n'.join(current_region))
        
        return regions
    
    def _is_table_line(self, line: str) -> bool:
        """Determine if a line looks like it's part of a table"""
        line_stripped = line.strip()
        
        # Check for table separators
        for pattern in self.table_patterns['row_separators']:
            if re.match(pattern, line_stripped):
                return True
        
        # Check for column separators
        separator_count = 0
        for pattern in self.table_patterns['column_separators']:
            separator_count += len(re.findall(pattern, line))
        
        # If line has multiple separators, likely a table row
        if separator_count >= 2:
            return True
        
        # Check for structured content (mix of different data types)
        has_numbers = bool(re.search(r'\d+', line))
        has_letters = bool(re.search(r'[A-Za-z]', line))
        has_symbols = bool(re.search(r'[$%#@]', line))
        
        # Multiple data types suggest tabular content
        data_type_count = sum([has_numbers, has_letters, has_symbols])
        if data_type_count >= 2:
            return True
        
        # Check for common table headers
        for keyword in self.table_keywords:
            if keyword.lower() in line.lower():
                return True
        
        return False
    
    def _extract_table_structure(self, table_text: str) -> Dict[str, Any]:
        """Extract the structure of a table from text"""
        lines = [line.strip() for line in table_text.split('\n') if line.strip()]
        
        if len(lines) < 2:
            return {'success': False, 'error': 'Insufficient table data'}
        
        # Identify the most likely column separator
        separator = self._identify_column_separator(lines)
        
        # Split rows into columns
        parsed_rows = []
        headers = None
        
        for i, line in enumerate(lines):
            # Skip separator lines
            if any(re.match(pattern, line) for pattern in self.table_patterns['row_separators']):
                continue
            
            # Split by identified separator
            if separator:
                columns = [col.strip() for col in re.split(separator, line)]
            else:
                # Fall back to whitespace splitting
                columns = line.split()
            
            # Filter out empty columns
            columns = [col for col in columns if col]
            
            if columns:
                if i == 0 or headers is None:
                    # First non-separator line is likely headers
                    if self._looks_like_headers(columns):
                        headers = columns
                        continue
                
                parsed_rows.append(columns)
        
        # If no headers identified, create generic ones
        if headers is None and parsed_rows:
            max_cols = max(len(row) for row in parsed_rows)
            headers = [f'Column_{i+1}' for i in range(max_cols)]
        
        # Normalize row lengths
        if headers:
            target_length = len(headers)
            normalized_rows = []
            
            for row in parsed_rows:
                # Pad or truncate to match header length
                if len(row) < target_length:
                    row.extend([''] * (target_length - len(row)))
                elif len(row) > target_length:
                    row = row[:target_length]
                normalized_rows.append(row)
            
            return {
                'success': True,
                'headers': headers,
                'rows': normalized_rows,
                'row_count': len(normalized_rows),
                'column_count': len(headers),
                'raw_text': table_text
            }
        
        return {'success': False, 'error': 'Could not parse table structure'}
    
    def _identify_column_separator(self, lines: List[str]) -> Optional[str]:
        """Identify the most likely column separator"""
        separator_candidates = ['|', '\t', '  ', '   ', '    ']
        separator_scores = {}
        
        for separator in separator_candidates:
            score = 0
            consistent_count = 0
            
            for line in lines:
                if any(re.match(pattern, line) for pattern in self.table_patterns['row_separators']):
                    continue
                
                parts = line.split(separator)
                if len(parts) > 1:
                    score += len(parts)
                    consistent_count += 1
            
            if consistent_count > 0:
                # Favor separators that appear consistently
                separator_scores[separator] = score * (consistent_count / len(lines))
        
        if separator_scores:
            best_separator = max(separator_scores.keys(), key=lambda k: separator_scores[k])
            return best_separator
        
        return None
    
    def _looks_like_headers(self, columns: List[str]) -> bool:
        """Determine if columns look like table headers"""
        if not columns:
            return False
        
        # Check for header patterns
        header_score = 0
        
        for col in columns:
            col_lower = col.lower()
            
            # Check for common header words
            for header_type, keywords in self.header_types.items():
                if any(keyword in col_lower for keyword in keywords):
                    header_score += 1
                    break
            
            # Check for title case
            if col.istitle():
                header_score += 0.5
            
            # Check for all caps (common in headers)
            if col.isupper() and len(col) > 1:
                header_score += 0.5
        
        # If more than 50% of columns look like headers
        return header_score / len(columns) > 0.5
    
    def _reconstruct_split_table(self, table_data: Dict[str, Any], 
                                existing_tables: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Reconstruct tables that may be split across pages"""
        if not existing_tables or not table_data['success']:
            return table_data
        
        # Look for tables with similar headers
        for existing_table in existing_tables:
            if self._headers_match(table_data['headers'], existing_table['headers']):
                logger.info("Found matching table headers - merging tables")
                
                # Merge the tables
                merged_table = existing_table.copy()
                merged_table['rows'].extend(table_data['rows'])
                merged_table['row_count'] = len(merged_table['rows'])
                merged_table['raw_text'] += '\n\n' + table_data['raw_text']
                merged_table['is_reconstructed'] = True
                
                # Remove the existing table from the list (will be replaced with merged)
                existing_tables.remove(existing_table)
                
                return merged_table
        
        return table_data
    
    def _headers_match(self, headers1: List[str], headers2: List[str]) -> bool:
        """Check if two header lists are similar enough to be the same table"""
        if len(headers1) != len(headers2):
            return False
        
        matches = 0
        for h1, h2 in zip(headers1, headers2):
            # Normalize for comparison
            h1_norm = h1.lower().strip()
            h2_norm = h2.lower().strip()
            
            if h1_norm == h2_norm:
                matches += 1
            elif h1_norm in h2_norm or h2_norm in h1_norm:
                matches += 0.8
        
        # Consider it a match if 80% of headers are similar
        return (matches / len(headers1)) >= 0.8
    
    def _infer_column_types(self, table_data: Dict[str, Any]) -> Dict[str, Any]:
        """Infer data types for each column"""
        if not table_data['success']:
            return table_data
        
        headers = table_data['headers']
        rows = table_data['rows']
        column_types = {}
        
        for i, header in enumerate(headers):
            column_values = [row[i] if i < len(row) else '' for row in rows]
            column_type = self._infer_column_type(header, column_values)
            column_types[header] = column_type
        
        table_data['column_types'] = column_types
        return table_data
    
    def _infer_column_type(self, header: str, values: List[str]) -> str:
        """Infer the data type of a column"""
        header_lower = header.lower()
        
        # Check header name first
        for type_name, keywords in self.header_types.items():
            if any(keyword in header_lower for keyword in keywords):
                return type_name
        
        # Analyze values
        non_empty_values = [v for v in values if v.strip()]
        if not non_empty_values:
            return 'text'
        
        # Check for dates
        date_count = sum(1 for v in non_empty_values if self._looks_like_date(v))
        if date_count / len(non_empty_values) > 0.7:
            return 'date'
        
        # Check for amounts/numbers
        number_count = sum(1 for v in non_empty_values if self._looks_like_number(v))
        if number_count / len(non_empty_values) > 0.7:
            # Check if it's currency
            if any('$' in v or '€' in v or '£' in v for v in non_empty_values):
                return 'amount'
            return 'quantity'
        
        return 'text'
    
    def _looks_like_date(self, value: str) -> bool:
        """Check if a value looks like a date"""
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'[A-Za-z]+ \d{1,2},? \d{4}',
            r'\d{1,2} [A-Za-z]+ \d{4}'
        ]
        
        return any(re.match(pattern, value.strip()) for pattern in date_patterns)
    
    def _looks_like_number(self, value: str) -> bool:
        """Check if a value looks like a number"""
        # Remove common currency symbols and separators
        cleaned = re.sub(r'[$€£,\s]', '', value.strip())
        
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
    
    def _validate_table_data(self, table_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean table data"""
        if not table_data['success']:
            return table_data
        
        headers = table_data['headers']
        rows = table_data['rows']
        column_types = table_data.get('column_types', {})
        
        validated_rows = []
        
        for row in rows:
            validated_row = []
            
            for i, (header, value) in enumerate(zip(headers, row)):
                column_type = column_types.get(header, 'text')
                cleaned_value = self._clean_cell_value(value, column_type)
                validated_row.append(cleaned_value)
            
            # Only include rows with at least one non-empty value
            if any(cell.strip() for cell in validated_row):
                validated_rows.append(validated_row)
        
        table_data['rows'] = validated_rows
        table_data['row_count'] = len(validated_rows)
        
        return table_data
    
    def _clean_cell_value(self, value: str, column_type: str) -> str:
        """Clean individual cell values based on column type"""
        if not value or not value.strip():
            return ''
        
        value = value.strip()
        
        if column_type == 'amount':
            # Clean monetary values
            value = re.sub(r'[^\d\.,\-]', '', value)
        elif column_type == 'quantity':
            # Clean numeric values
            value = re.sub(r'[^\d\.,\-]', '', value)
        elif column_type == 'date':
            # Standardize date format (basic cleaning)
            value = re.sub(r'[|l]', '1', value)  # Common OCR mistakes
            value = re.sub(r'[oO](?=\d)', '0', value)
        
        return value
    
    def _calculate_table_confidence(self, table_data: Dict[str, Any]) -> float:
        """Calculate confidence score for extracted table"""
        if not table_data['success']:
            return 0.0
        
        headers = table_data['headers']
        rows = table_data['rows']
        
        # Base factors
        structure_score = 0.5  # Base score for having structure
        
        # Header quality
        if headers:
            header_score = sum(1 for h in headers if len(h.strip()) > 0) / len(headers)
            structure_score += header_score * 0.2
        
        # Data completeness
        if rows:
            total_cells = len(headers) * len(rows)
            filled_cells = sum(1 for row in rows for cell in row if cell.strip())
            completeness = filled_cells / total_cells if total_cells > 0 else 0
            structure_score += completeness * 0.2
        
        # Type consistency
        column_types = table_data.get('column_types', {})
        if column_types:
            type_confidence = 0.1  # Bonus for having type information
            structure_score += type_confidence
        
        return min(structure_score, 1.0)
    
    def _filter_tables_by_requirements(self, tables: List[Dict[str, Any]], 
                                     requirements: str) -> List[Dict[str, Any]]:
        """Filter and prioritize tables based on extraction requirements"""
        if not requirements:
            return tables
        
        req_lower = requirements.lower()
        scored_tables = []
        
        for table in tables:
            score = 0
            headers = table.get('headers', [])
            
            # Score based on header relevance
            for header in headers:
                header_lower = header.lower()
                
                # Check for specific field mentions in requirements
                for field_type, keywords in self.header_types.items():
                    if any(keyword in req_lower for keyword in keywords):
                        if any(keyword in header_lower for keyword in keywords):
                            score += 2
                
                # General relevance
                if any(word in header_lower for word in req_lower.split()):
                    score += 1
            
            scored_tables.append((score, table))
        
        # Sort by score and return tables
        scored_tables.sort(key=lambda x: x[0], reverse=True)
        return [table for score, table in scored_tables]
    
    def export_table_to_formats(self, table_data: Dict[str, Any], 
                               output_format: str = 'json') -> Dict[str, Any]:
        """Export table data to various formats"""
        if not table_data['success']:
            return {'success': False, 'error': 'No valid table data to export'}
        
        headers = table_data['headers']
        rows = table_data['rows']
        
        try:
            if output_format.lower() == 'json':
                # Convert to list of dictionaries
                data = []
                for row in rows:
                    row_dict = {}
                    for i, header in enumerate(headers):
                        value = row[i] if i < len(row) else ''
                        row_dict[header] = value
                    data.append(row_dict)
                
                return {
                    'success': True,
                    'format': 'json',
                    'data': data
                }
            
            elif output_format.lower() == 'csv':
                # Create CSV-like structure
                csv_lines = [','.join(f'"{header}"' for header in headers)]
                for row in rows:
                    csv_line = ','.join(f'"{cell}"' for cell in row)
                    csv_lines.append(csv_line)
                
                return {
                    'success': True,
                    'format': 'csv',
                    'data': '\n'.join(csv_lines)
                }
            
            elif output_format.lower() == 'xml':
                # Create simple XML structure
                xml_lines = ['<table>']
                xml_lines.append('  <headers>')
                for header in headers:
                    xml_lines.append(f'    <header>{header}</header>')
                xml_lines.append('  </headers>')
                xml_lines.append('  <rows>')
                
                for row in rows:
                    xml_lines.append('    <row>')
                    for i, cell in enumerate(row):
                        header = headers[i] if i < len(headers) else f'column_{i}'
                        xml_lines.append(f'      <{header}>{cell}</{header}>')
                    xml_lines.append('    </row>')
                
                xml_lines.append('  </rows>')
                xml_lines.append('</table>')
                
                return {
                    'success': True,
                    'format': 'xml',
                    'data': '\n'.join(xml_lines)
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Export failed: {str(e)}'
            }
        
        return {
            'success': False,
            'error': f'Unsupported format: {output_format}'
        }

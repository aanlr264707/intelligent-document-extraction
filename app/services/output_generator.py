import json
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pandas as pd
from io import StringIO, BytesIO
from typing import Dict, List, Any, Union
import os
from datetime import datetime

class OutputGenerator:
    """Generates structured output in various formats (JSON, CSV, XML)"""
    
    def __init__(self, output_dir='static/outputs'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_output(self, extracted_data: Dict[str, Any], 
                       output_format: str, filename_prefix: str = None) -> Dict[str, Any]:
        """Generate output in the specified format"""
        
        if filename_prefix is None:
            filename_prefix = f"extraction_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            if output_format.lower() == 'json':
                return self._generate_json_output(extracted_data, filename_prefix)
            elif output_format.lower() == 'csv':
                return self._generate_csv_output(extracted_data, filename_prefix)
            elif output_format.lower() == 'xml':
                return self._generate_xml_output(extracted_data, filename_prefix)
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Output generation failed: {str(e)}"
            }
    
    def _generate_json_output(self, data: Dict[str, Any], filename_prefix: str) -> Dict[str, Any]:
        """Generate JSON output"""
        
        structured_data = self._structure_data_for_json(data)
        
        filename = f"{filename_prefix}.json"
        file_path = os.path.join(self.output_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, indent=2, ensure_ascii=False, default=str)
        
        return {
            'success': True,
            'format': 'json',
            'filename': filename,
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'preview': json.dumps(structured_data, indent=2)[:500] + "..." if len(json.dumps(structured_data)) > 500 else json.dumps(structured_data, indent=2)
        }
    
    def _generate_csv_output(self, data: Dict[str, Any], filename_prefix: str) -> Dict[str, Any]:
        """Generate CSV output"""
        
        tabular_data = self._structure_data_for_csv(data)
        
        filename = f"{filename_prefix}.csv"
        file_path = os.path.join(self.output_dir, filename)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            if tabular_data:
                writer = csv.DictWriter(f, fieldnames=tabular_data[0].keys())
                writer.writeheader()
                writer.writerows(tabular_data)
        
        preview = self._generate_csv_preview(tabular_data)
        
        return {
            'success': True,
            'format': 'csv',
            'filename': filename,
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'row_count': len(tabular_data),
            'preview': preview
        }
    
    def _generate_xml_output(self, data: Dict[str, Any], filename_prefix: str) -> Dict[str, Any]:
        """Generate XML output"""
        
        xml_data = self._structure_data_for_xml(data)
        
        filename = f"{filename_prefix}.xml"
        file_path = os.path.join(self.output_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(xml_data)
        
        return {
            'success': True,
            'format': 'xml',
            'filename': filename,
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'preview': xml_data[:500] + "..." if len(xml_data) > 500 else xml_data
        }
    
    def _structure_data_for_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Structure data for JSON output"""
        
        structured = {
            'extraction_metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'format': 'json'
            },
            'extracted_fields': {},
            'tables': [],
            'legal_analysis': {},
            'confidence_metrics': {}
        }
        
        if 'extracted_data' in data:
            extracted_data = data['extracted_data']
            
            for key, value in extracted_data.items():
                if key == 'tables' and isinstance(value, list):
                    structured['tables'] = value
                else:
                    structured['extracted_fields'][key] = value
        
        if 'legal_analysis' in data and data['legal_analysis']:
            structured['legal_analysis'] = data['legal_analysis']
        
        if 'confidence_score' in data:
            structured['confidence_metrics']['overall_confidence'] = data['confidence_score']
        
        if 'flagged_fields' in data:
            structured['confidence_metrics']['flagged_fields'] = data['flagged_fields']
        
        if 'metadata' in data:
            structured['extraction_metadata'].update(data['metadata'])
        
        return structured
    
    def _structure_data_for_csv(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Structure data for CSV output"""
        
        rows = []
        
        extracted_data = data.get('extracted_data', {})
        
        tables = extracted_data.pop('tables', [])
        
        if extracted_data:
            main_row = {}
            for key, value in extracted_data.items():
                if isinstance(value, (dict, list)):
                    main_row[key] = json.dumps(value)
                else:
                    main_row[key] = str(value)
            
            main_row['confidence_score'] = data.get('confidence_score', '')
            main_row['processing_time'] = data.get('processing_time_seconds', '')
            
            rows.append(main_row)
        
        for i, table in enumerate(tables):
            if isinstance(table, dict) and 'rows' in table:
                headers = table.get('headers', [])
                table_rows = table.get('rows', [])
                
                for row_data in table_rows:
                    table_row = {}
                    
                    table_row['table_name'] = table.get('title', f'Table_{i+1}')
                    
                    for j, cell_value in enumerate(row_data):
                        column_name = headers[j] if j < len(headers) else f'Column_{j+1}'
                        table_row[column_name] = str(cell_value)
                    
                    rows.append(table_row)
        
        return rows
    
    def _structure_data_for_xml(self, data: Dict[str, Any]) -> str:
        """Structure data for XML output"""
        
        root = ET.Element('document_extraction')
        
        metadata = ET.SubElement(root, 'metadata')
        ET.SubElement(metadata, 'timestamp').text = datetime.utcnow().isoformat()
        ET.SubElement(metadata, 'format').text = 'xml'
        
        if 'confidence_score' in data:
            ET.SubElement(metadata, 'confidence_score').text = str(data['confidence_score'])
        
        if 'processing_time_seconds' in data:
            ET.SubElement(metadata, 'processing_time').text = str(data['processing_time_seconds'])
        
        extracted_data = data.get('extracted_data', {})
        if extracted_data:
            fields_element = ET.SubElement(root, 'extracted_fields')
            
            for key, value in extracted_data.items():
                if key != 'tables':  # Handle tables separately
                    field_element = ET.SubElement(fields_element, 'field')
                    field_element.set('name', str(key))
                    
                    if isinstance(value, (dict, list)):
                        field_element.text = json.dumps(value)
                    else:
                        field_element.text = str(value)
        
        tables = extracted_data.get('tables', [])
        if tables:
            tables_element = ET.SubElement(root, 'tables')
            
            for i, table in enumerate(tables):
                table_element = ET.SubElement(tables_element, 'table')
                table_element.set('id', str(i + 1))
                
                if isinstance(table, dict):
                    if 'title' in table:
                        ET.SubElement(table_element, 'title').text = table['title']
                    
                    if 'headers' in table:
                        headers_element = ET.SubElement(table_element, 'headers')
                        for header in table['headers']:
                            ET.SubElement(headers_element, 'header').text = str(header)
                    
                    if 'rows' in table:
                        rows_element = ET.SubElement(table_element, 'rows')
                        for row_data in table['rows']:
                            row_element = ET.SubElement(rows_element, 'row')
                            for j, cell_value in enumerate(row_data):
                                cell_element = ET.SubElement(row_element, 'cell')
                                cell_element.set('column', str(j + 1))
                                cell_element.text = str(cell_value)
        
        legal_analysis = data.get('legal_analysis')
        if legal_analysis:
            legal_element = ET.SubElement(root, 'legal_analysis')
            
            for key, value in legal_analysis.items():
                analysis_element = ET.SubElement(legal_element, key)
                if isinstance(value, (dict, list)):
                    analysis_element.text = json.dumps(value)
                else:
                    analysis_element.text = str(value)
        
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def _generate_csv_preview(self, tabular_data: List[Dict[str, Any]], max_rows: int = 5) -> str:
        """Generate a preview of CSV data"""
        
        if not tabular_data:
            return "No data to preview"
        
        preview_data = tabular_data[:max_rows]
        
        output = StringIO()
        if preview_data:
            writer = csv.DictWriter(output, fieldnames=preview_data[0].keys())
            writer.writeheader()
            writer.writerows(preview_data)
        
        preview = output.getvalue()
        output.close()
        
        if len(tabular_data) > max_rows:
            preview += f"\n... and {len(tabular_data) - max_rows} more rows"
        
        return preview
    
    def generate_enterprise_format(self, data: Dict[str, Any], 
                                 schema_mapping: Dict[str, str] = None) -> Dict[str, Any]:
        """Generate output formatted for enterprise system integration"""
        
        if schema_mapping:
            data = self._apply_schema_mapping(data, schema_mapping)
        
        enterprise_data = {
            'document_id': data.get('document_id'),
            'extraction_timestamp': datetime.utcnow().isoformat(),
            'status': 'completed' if not data.get('error') else 'failed',
            'confidence_score': data.get('confidence_score', 0.0),
            'extracted_fields': data.get('extracted_data', {}),
            'quality_metrics': {
                'processing_time_seconds': data.get('processing_time_seconds', 0),
                'flagged_fields_count': len(data.get('flagged_fields', [])),
                'extraction_method': data.get('metadata', {}).get('extraction_method', 'unknown')
            }
        }
        
        legal_analysis = data.get('legal_analysis')
        if legal_analysis:
            enterprise_data['legal_metadata'] = {
                'clauses_identified': len(legal_analysis.get('identified_clauses', [])),
                'obligations_count': len(legal_analysis.get('obligations', [])),
                'risk_flags_count': len(legal_analysis.get('risk_flags', [])),
                'has_summary': bool(legal_analysis.get('document_summary'))
            }
        
        return enterprise_data
    
    def _apply_schema_mapping(self, data: Dict[str, Any], 
                            schema_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Apply user-defined schema mapping to extracted data"""
        
        mapped_data = data.copy()
        extracted_data = mapped_data.get('extracted_data', {})
        
        mapped_fields = {}
        for original_field, mapped_field in schema_mapping.items():
            if original_field in extracted_data:
                mapped_fields[mapped_field] = extracted_data[original_field]
            else:
                if original_field in extracted_data:
                    mapped_fields[original_field] = extracted_data[original_field]
        
        for field, value in extracted_data.items():
            if field not in schema_mapping and field not in mapped_fields:
                mapped_fields[field] = value
        
        mapped_data['extracted_data'] = mapped_fields
        return mapped_data
    
    def create_audit_export(self, audit_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create exportable audit trail"""
        
        filename = f"audit_trail_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = os.path.join(self.output_dir, filename)
        
        if audit_logs:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = audit_logs[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(audit_logs)
        
        return {
            'success': True,
            'filename': filename,
            'file_path': file_path,
            'record_count': len(audit_logs),
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }

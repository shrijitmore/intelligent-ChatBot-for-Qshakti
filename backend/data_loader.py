import json
from typing import Dict, List, Any
import re


class DataLoader:
    """Load and structure the database schema data"""
    
    def __init__(self, schema_file_path: str):
        self.schema_file_path = schema_file_path
        self.structured_data = {}
    
    def load_and_structure(self) -> Dict[str, Any]:
        """Load the schema file and structure it"""
        with open(self.schema_file_path, 'r') as f:
            content = f.read()
        
        # Parse the schema content
        tables = self._parse_schema(content)
        
        self.structured_data = {
            "tables": tables,
            "total_tables": len(tables),
            "categories": self._categorize_tables(tables)
        }
        
        return self.structured_data
    
    def _parse_schema(self, content: str) -> Dict[str, Any]:
        """Parse schema content into structured format"""
        tables = {}
        
        # Split by table sections (looking for ### headers)
        table_sections = re.split(r'###\s+', content)
        
        for section in table_sections[1:]:  # Skip first empty split
            lines = section.strip().split('\n')
            if not lines:
                continue
            
            table_name = lines[0].strip()
            table_info = {
                "name": table_name,
                "columns": [],
                "records": 0,
                "references": [],
                "referenced_by": [],
                "description": ""
            }
            
            for line in lines[1:]:
                line = line.strip()
                if line.startswith('**Columns:**'):
                    columns_text = line.replace('**Columns:**', '').strip()
                    table_info['columns'] = [c.strip() for c in columns_text.split(',')]
                elif line.startswith('**Records:**'):
                    records_text = line.replace('**Records:**', '').strip()
                    try:
                        table_info['records'] = int(records_text.split()[0])
                    except:
                        table_info['records'] = 0
                elif line.startswith('**References:**'):
                    refs_text = line.replace('**References:**', '').strip()
                    # Parse references
                    refs = re.findall(r'(\w+)\s+\(via\s+(\w+)\)', refs_text)
                    table_info['references'] = [{'table': r[0], 'via': r[1]} for r in refs]
                elif line.startswith('**Referenced by:**'):
                    refs_text = line.replace('**Referenced by:**', '').strip()
                    refs = re.findall(r'(\w+)\s+\(via\s+(\w+)\)', refs_text)
                    table_info['referenced_by'] = [{'table': r[0], 'via': r[1]} for r in refs]
            
            tables[table_name] = table_info
        
        return tables
    
    def _categorize_tables(self, tables: Dict[str, Any]) -> Dict[str, List[str]]:
        """Categorize tables by their purpose"""
        categories = {
            "Inspection & Quality Control": [],
            "Master Data": [],
            "User Management": [],
            "System Tables": []
        }
        
        for table_name in tables.keys():
            if 'inspection' in table_name.lower():
                categories["Inspection & Quality Control"].append(table_name)
            elif table_name.startswith('auth_'):
                categories["User Management"].append(table_name)
            elif table_name.startswith('django_') or 'token' in table_name.lower():
                categories["System Tables"].append(table_name)
            elif table_name.startswith('master_') or 'rbac' in table_name.lower():
                categories["Master Data"].append(table_name)
        
        return categories
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a specific table"""
        return self.structured_data.get('tables', {}).get(table_name, {})
    
    def search_tables(self, keyword: str) -> List[str]:
        """Search for tables matching a keyword"""
        matching_tables = []
        for table_name, table_info in self.structured_data.get('tables', {}).items():
            if keyword.lower() in table_name.lower():
                matching_tables.append(table_name)
            elif any(keyword.lower() in col.lower() for col in table_info.get('columns', [])):
                matching_tables.append(table_name)
        return matching_tables

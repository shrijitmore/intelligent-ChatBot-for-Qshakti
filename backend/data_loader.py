import json
from typing import Dict, List, Any
from collections import defaultdict


class DataLoader:
    """Load and structure the inspection data hierarchically"""
    
    def __init__(self, data_file_path: str):
        self.data_file_path = data_file_path
        self.structured_data = {}
        self.raw_data = []
    
    def load_and_structure(self) -> Dict[str, Any]:
        """Load the JSON data file and structure it hierarchically"""
        with open(self.data_file_path, 'r') as f:
            self.raw_data = json.load(f)
        
        # Build hierarchical structure
        hierarchy = self._build_hierarchy()
        
        self.structured_data = {
            "hierarchy": hierarchy,
            "total_records": len(self.raw_data),
            "plants": list(hierarchy.keys()),
            "summary": self._generate_summary(hierarchy)
        }
        
        return self.structured_data
    
    def _build_hierarchy(self) -> Dict[str, Any]:
        """Build hierarchical structure: Plant -> Section -> Item -> Inspections"""
        hierarchy = {}
        
        for record in self.raw_data:
            # Extract plant info
            plant_data = record.get('created_by_id', {}).get('plant_id', {})
            plant_id = plant_data.get('plant_id')
            plant_name = plant_data.get('plant_name', 'Unknown Plant')
            
            if not plant_id:
                continue
            
            # Initialize plant
            if plant_id not in hierarchy:
                hierarchy[plant_id] = {
                    "id": plant_id,
                    "name": plant_name,
                    "sections": {}
                }
            
            # Extract section info
            section_data = record.get('insp_schedule_id_id', {}).get('building_id', {})
            section_id = section_data.get('building_id')
            section_name = section_data.get('building_name', 'Unknown Section')
            sub_section = section_data.get('sub_section', '')
            
            if section_id and section_id not in hierarchy[plant_id]['sections']:
                hierarchy[plant_id]['sections'][section_id] = {
                    "id": section_id,
                    "name": section_name,
                    "sub_section": sub_section,
                    "items": {}
                }
            
            # Extract item info
            item_data = record.get('insp_schedule_id_id', {}).get('item_code_id', {})
            item_code = item_data.get('item_code')
            item_desc = item_data.get('item_description', 'Unknown Item')
            item_type = item_data.get('item_type', '')
            item_unit = item_data.get('unit', '')
            
            if section_id and item_code:
                if item_code not in hierarchy[plant_id]['sections'][section_id]['items']:
                    hierarchy[plant_id]['sections'][section_id]['items'][item_code] = {
                        "code": item_code,
                        "description": item_desc,
                        "type": item_type,
                        "unit": item_unit,
                        "inspection_schedules": [],
                        "machines": {},
                        "operations": {},
                        "parameters": {},
                        "inspection_readings": []
                    }
                
                # Extract inspection schedule info
                insp_schedule = record.get('insp_schedule_id_id', {})
                schedule_id = insp_schedule.get('id')
                
                # Extract machine info
                machine_data = insp_schedule.get('qc_machine_id_id', {})
                if machine_data:
                    machine_id = machine_data.get('machine_id')
                    if machine_id:
                        hierarchy[plant_id]['sections'][section_id]['items'][item_code]['machines'][machine_id] = {
                            "id": machine_id,
                            "name": machine_data.get('machine_name', ''),
                            "make": machine_data.get('machine_make', ''),
                            "model": machine_data.get('machine_model', ''),
                            "is_digital": machine_data.get('is_digital', False),
                            "type": machine_data.get('machine_type', '')
                        }
                
                # Extract operation info
                operation_data = insp_schedule.get('operation_id', {})
                if operation_data:
                    operation_id = operation_data.get('operation_id')
                    if operation_id:
                        hierarchy[plant_id]['sections'][section_id]['items'][item_code]['operations'][operation_id] = {
                            "id": operation_id,
                            "name": operation_data.get('operation_name', ''),
                            "description": operation_data.get('operation_description', '')
                        }
                
                # Extract parameter info
                parameter_data = insp_schedule.get('inspection_parameter_id', {})
                if parameter_data:
                    param_id = parameter_data.get('inspection_parameter_id')
                    if param_id:
                        hierarchy[plant_id]['sections'][section_id]['items'][item_code]['parameters'][param_id] = {
                            "id": param_id,
                            "name": parameter_data.get('inspection_parameter', ''),
                            "description": parameter_data.get('parameter_description', '')
                        }
                
                # Add inspection reading
                reading = {
                    "id": record.get('id'),
                    "po_no": record.get('po_no'),
                    "actual_readings": record.get('actual_readings', []),
                    "created_at": record.get('created_at'),
                    "schedule": {
                        "id": schedule_id,
                        "LSL": insp_schedule.get('LSL'),
                        "target": insp_schedule.get('target_value'),
                        "USL": insp_schedule.get('USL'),
                        "sample_size": insp_schedule.get('sample_size'),
                        "frequency": insp_schedule.get('inspection_frequency'),
                        "method": insp_schedule.get('inspection_method'),
                        "recording_type": insp_schedule.get('recording_type'),
                        "defect_classification": insp_schedule.get('likely_defects_classification')
                    },
                    "machine": machine_data.get('machine_name') if machine_data else None,
                    "operation": operation_data.get('operation_name') if operation_data else None,
                    "parameter": parameter_data.get('inspection_parameter') if parameter_data else None
                }
                
                hierarchy[plant_id]['sections'][section_id]['items'][item_code]['inspection_readings'].append(reading)
        
        return hierarchy
    
    def _generate_summary(self, hierarchy: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics"""
        total_plants = len(hierarchy)
        total_sections = sum(len(plant['sections']) for plant in hierarchy.values())
        total_items = sum(
            len(section['items'])
            for plant in hierarchy.values()
            for section in plant['sections'].values()
        )
        total_inspections = sum(
            len(item['inspection_readings'])
            for plant in hierarchy.values()
            for section in plant['sections'].values()
            for item in section['items'].values()
        )
        
        return {
            "total_plants": total_plants,
            "total_sections": total_sections,
            "total_items": total_items,
            "total_inspection_readings": total_inspections
        }
    
    def get_plant_info(self, plant_id: str) -> Dict[str, Any]:
        """Get information about a specific plant"""
        return self.structured_data.get('hierarchy', {}).get(plant_id, {})
    
    def get_all_plants(self) -> List[Dict[str, Any]]:
        """Get all plants"""
        return [
            {"id": plant_id, "name": plant_data["name"]}
            for plant_id, plant_data in self.structured_data.get('hierarchy', {}).items()
        ]
    
    def get_sections_for_plant(self, plant_id: str) -> List[Dict[str, Any]]:
        """Get all sections for a plant"""
        plant = self.get_plant_info(plant_id)
        return [
            {"id": section_id, "name": section_data["name"], "sub_section": section_data.get("sub_section")}
            for section_id, section_data in plant.get('sections', {}).items()
        ]
    
    def get_items_for_section(self, plant_id: str, section_id: str) -> List[Dict[str, Any]]:
        """Get all items for a section"""
        plant = self.get_plant_info(plant_id)
        section = plant.get('sections', {}).get(section_id, {})
        return [
            {"code": item_code, "description": item_data["description"], "type": item_data["type"]}
            for item_code, item_data in section.get('items', {}).items()
        ]

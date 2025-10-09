import json
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime
import re


class StaticQAEngine:
    """Static Q&A engine for manufacturing inspection data with comprehensive information display"""
    
    def __init__(self, redis_client, structured_data: Dict[str, Any]):
        self.redis_client = redis_client
        self.structured_data = structured_data
        self.raw_records = structured_data.get('raw_records', [])
        
        # Build comprehensive indexes
        self.plant_index = {}
        self.building_index = {}
        self.item_index = {}
        self.po_index = {}
        self.operation_index = {}
        self.parameter_index = {}
        self.machine_index = {}
        
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize the QA engine and build all indexes"""
        self._build_indexes()
        self.logger.info("Static QA Engine initialized with comprehensive data indexing")
    
    def _build_indexes(self):
        """Build comprehensive indexes from raw data for fast lookup"""
        for record in self.raw_records:
            record_id = record.get('id')
            
            # Plant index
            plant_data = record.get('created_by_id', {}).get('plant_id', {})
            plant_id = plant_data.get('plant_id')
            if plant_id:
                if plant_id not in self.plant_index:
                    self.plant_index[plant_id] = {
                        'plant_id': plant_id,
                        'plant_name': plant_data.get('plant_name'),
                        'plant_location_1': plant_data.get('plant_location_1'),
                        'plant_location_2': plant_data.get('plant_location_2'),
                        'records': []
                    }
                self.plant_index[plant_id]['records'].append(record_id)
            
            # Building index
            building_data = record.get('insp_schedule_id_id', {}).get('building_id', {})
            building_id = building_data.get('building_id')
            if building_id:
                if building_id not in self.building_index:
                    self.building_index[building_id] = {
                        'building_id': building_id,
                        'building_name': building_data.get('building_name'),
                        'sub_section': building_data.get('sub_section'),
                        'plant_id': building_data.get('plant_id'),
                        'records': []
                    }
                self.building_index[building_id]['records'].append(record_id)
            
            # Item index
            item_data = record.get('insp_schedule_id_id', {}).get('item_code_id', {})
            item_code = item_data.get('item_code')
            if item_code:
                if item_code not in self.item_index:
                    self.item_index[item_code] = {
                        'item_code': item_code,
                        'item_description': item_data.get('item_description'),
                        'unit': item_data.get('unit'),
                        'item_type': item_data.get('item_type'),
                        'end_store': item_data.get('end_store'),
                        'records': []
                    }
                self.item_index[item_code]['records'].append(record_id)
            
            # PO index
            po_no = record.get('po_no')
            if po_no:
                if po_no not in self.po_index:
                    self.po_index[po_no] = {
                        'po_no': po_no,
                        'records': []
                    }
                self.po_index[po_no]['records'].append(record_id)
            
            # Operation index
            operation_data = record.get('insp_schedule_id_id', {}).get('operation_id', {})
            operation_id = operation_data.get('operation_id')
            if operation_id:
                if operation_id not in self.operation_index:
                    self.operation_index[operation_id] = {
                        'operation_id': operation_id,
                        'operation_name': operation_data.get('operation_name'),
                        'operation_description': operation_data.get('operation_description'),
                        'records': []
                    }
                self.operation_index[operation_id]['records'].append(record_id)
            
            # Parameter index
            param_data = record.get('insp_schedule_id_id', {}).get('inspection_parameter_id', {})
            param_id = param_data.get('inspection_parameter_id')
            if param_id:
                if param_id not in self.parameter_index:
                    self.parameter_index[param_id] = {
                        'inspection_parameter_id': param_id,
                        'inspection_parameter': param_data.get('inspection_parameter'),
                        'parameter_description': param_data.get('parameter_description'),
                        'records': []
                    }
                self.parameter_index[param_id]['records'].append(record_id)
            
            # Machine index
            machine_data = record.get('insp_schedule_id_id', {}).get('qc_machine_id_id', {})
            machine_id = machine_data.get('machine_id')
            if machine_id:
                if machine_id not in self.machine_index:
                    self.machine_index[machine_id] = {
                        'machine_id': machine_id,
                        'machine_name': machine_data.get('machine_name'),
                        'machine_make': machine_data.get('machine_make'),
                        'machine_model': machine_data.get('machine_model'),
                        'is_digital': machine_data.get('is_digital'),
                        'machine_type': machine_data.get('machine_type'),
                        'records': []
                    }
                self.machine_index[machine_id]['records'].append(record_id)
        
        self.logger.info(f"Built indexes: {len(self.plant_index)} plants, {len(self.building_index)} buildings, "
                        f"{len(self.item_index)} items, {len(self.po_index)} POs")
    
    async def generate_initial_suggestions(self, session_id: str) -> List[str]:
        """Generate initial suggestions based on available data"""
        suggestions = [
            "Show me PO number status",
            "View inward material quality inspection",
            "Check in-process inspection",
            "Show final inspection details",
            "Analyze inspection parameters",
            "View parameter distribution"
        ]
        
        # Store initial context
        await self._save_to_redis(session_id, 'context', {
            'level': 'START',
            'question_type': None
        })
        await self._save_to_redis(session_id, 'history', [])
        
        return suggestions[:5]
    
    async def process_message(self, session_id: str, message: str, is_suggestion: bool) -> Dict[str, Any]:
        """Process user message and return response with comprehensive data"""
        # Get current context
        context = await self._get_from_redis(session_id, 'context', {
            'level': 'START',
            'question_type': None
        })
        history = await self._get_from_redis(session_id, 'history', [])
        
        # Add message to history
        history.append({
            'role': 'user',
            'message': message,
            'is_suggestion': is_suggestion,
            'timestamp': datetime.now().isoformat()
        })
        
        # Detect question type and parse intent
        question_type, parsed_data = self._detect_question_type(message, context)
        
        # Update context
        new_context = {**context, 'question_type': question_type, **parsed_data}
        
        # Generate response based on question type
        response_data = await self._generate_response(message, new_context, history)
        
        # Add response to history
        history.append({
            'role': 'assistant',
            'message': response_data['response'],
            'suggestions': response_data['suggestions'],
            'chart_data': response_data.get('chart_data'),
            'table_data': response_data.get('table_data'),
            'timestamp': datetime.now().isoformat()
        })
        
        # Save updated context and history
        await self._save_to_redis(session_id, 'context', new_context)
        await self._save_to_redis(session_id, 'history', history)
        
        return {
            'response': response_data['response'],
            'suggestions': response_data['suggestions'],
            'context_path': [message],
            'chart_data': response_data.get('chart_data'),
            'table_data': response_data.get('table_data'),
            'metadata': {
                'question_type': question_type,
                'context': new_context
            }
        }
    
    def _detect_question_type(self, message: str, context: Dict) -> tuple:
        """Detect which of the 6 question types user is asking"""
        message_lower = message.lower()
        
        # Question 1: PO Status
        if any(keyword in message_lower for keyword in ['po', 'production order', 'order number', 'po status']):
            return 'po_status', self._parse_po_query(message)
        
        # Question 2: Inward Material Quality Inspection
        if any(keyword in message_lower for keyword in ['inward', 'material', 'mis', 'i/o']):
            return 'inward_quality', self._parse_inward_query(message)
        
        # Question 3: In-Process Inspection
        if any(keyword in message_lower for keyword in ['in-process', 'in process', 'process inspection']):
            return 'inprocess_inspection', self._parse_inprocess_query(message)
        
        # Question 4: Final Inspection / FAI
        if any(keyword in message_lower for keyword in ['final', 'fai', 'final inspection']):
            return 'final_inspection', self._parse_final_query(message)
        
        # Question 5: Parameter-wise Analysis
        if any(keyword in message_lower for keyword in ['parameter', 'analysis', 'trend', 'quality']):
            return 'parameter_analysis', self._parse_parameter_analysis(message)
        
        # Question 6: Parameter Distribution
        if any(keyword in message_lower for keyword in ['distribution', 'histogram', 'spread']):
            return 'parameter_distribution', self._parse_distribution_query(message)
        
        # Default: navigation
        return 'navigation', {}
    
    def _parse_po_query(self, message: str) -> Dict:
        """Parse PO number from message"""
        # Extract PO patterns like "1004", "D-2074", etc.
        po_pattern = r'[A-Z]?-?\d{4,}'
        match = re.search(po_pattern, message)
        if match:
            return {'po_no': match.group()}
        return {}
    
    def _parse_inward_query(self, message: str) -> Dict:
        """Parse inward material query"""
        return {}
    
    def _parse_inprocess_query(self, message: str) -> Dict:
        """Parse in-process inspection query"""
        return {}
    
    def _parse_final_query(self, message: str) -> Dict:
        """Parse final inspection query"""
        return {}
    
    def _parse_parameter_analysis(self, message: str) -> Dict:
        """Parse parameter analysis query"""
        return {}
    
    def _parse_distribution_query(self, message: str) -> Dict:
        """Parse distribution query"""
        return {}
    
    async def _generate_response(self, message: str, context: Dict, history: List) -> Dict[str, Any]:
        """Generate comprehensive response based on question type"""
        question_type = context.get('question_type')
        
        if question_type == 'po_status':
            return await self._generate_po_status_response(context)
        elif question_type == 'inward_quality':
            return await self._generate_inward_quality_response(context)
        elif question_type == 'inprocess_inspection':
            return await self._generate_inprocess_response(context)
        elif question_type == 'final_inspection':
            return await self._generate_final_inspection_response(context)
        elif question_type == 'parameter_analysis':
            return await self._generate_parameter_analysis_response(context)
        elif question_type == 'parameter_distribution':
            return await self._generate_distribution_response(context)
        else:
            return await self._generate_navigation_response(context)
    
    async def _generate_po_status_response(self, context: Dict) -> Dict[str, Any]:
        """Generate PO status response with ALL related information"""
        po_no = context.get('po_no')
        
        if not po_no:
            # Ask for factory selection first
            plants = list(self.plant_index.values())
            response = "To check PO status, please select the factory:\n\n"
            for plant in plants:
                response += f"• {plant['plant_name']} (ID: {plant['plant_id']})\n"
            
            suggestions = [f"Show PO for {p['plant_name']}" for p in plants[:3]]
            suggestions.append("Enter PO number")
            
            return {
                'response': response,
                'suggestions': suggestions
            }
        
        # Get PO details with comprehensive information
        if po_no in self.po_index:
            records = [r for r in self.raw_records if r.get('id') in self.po_index[po_no]['records']]
            
            if not records:
                return {
                    'response': f"PO Number: {po_no}\n\nNo inspection records found.",
                    'suggestions': ["Search another PO", "Go back"]
                }
            
            # Build comprehensive response
            response = f"📋 **Production Order Status**\n\n"
            response += f"**PO Number:** {po_no}\n"
            response += f"**Total Inspections:** {len(records)}\n\n"
            
            # Get unique plants, buildings, items
            plants = set()
            buildings = set()
            items = set()
            
            for record in records:
                plant_data = record.get('created_by_id', {}).get('plant_id', {})
                if plant_data.get('plant_id'):
                    plants.add((plant_data.get('plant_id'), plant_data.get('plant_name')))
                
                building_data = record.get('insp_schedule_id_id', {}).get('building_id', {})
                if building_data.get('building_id'):
                    buildings.add((building_data.get('building_id'), building_data.get('building_name')))
                
                item_data = record.get('insp_schedule_id_id', {}).get('item_code_id', {})
                if item_data.get('item_code'):
                    items.add((item_data.get('item_code'), item_data.get('item_description')))
            
            response += "**Factories Involved:**\n"
            for plant_id, plant_name in plants:
                response += f"  • {plant_name} (ID: {plant_id})\n"
            
            response += "\n**Buildings/Sections:**\n"
            for building_id, building_name in buildings:
                response += f"  • {building_name} (ID: {building_id})\n"
            
            response += "\n**Items:**\n"
            for item_code, item_desc in items:
                response += f"  • {item_desc} (Code: {item_code})\n"
            
            # Generate table with ALL inspection details
            table_data = self._generate_po_inspection_table(records)
            
            suggestions = [
                f"Show inspection trends for {po_no}",
                f"View parameter details for {po_no}",
                "Search another PO",
                "Go back to main menu"
            ]
            
            return {
                'response': response,
                'suggestions': suggestions,
                'table_data': table_data
            }
        else:
            available_pos = list(self.po_index.keys())[:10]
            response = f"PO Number '{po_no}' not found.\n\n"
            response += "Available PO Numbers:\n"
            for po in available_pos:
                response += f"• {po}\n"
            
            suggestions = [f"Show PO {po}" for po in available_pos[:3]]
            suggestions.append("Go back")
            
            return {
                'response': response,
                'suggestions': suggestions
            }
    
    def _generate_po_inspection_table(self, records: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive inspection table for PO with ALL details"""
        columns = [
            "Inspection ID",
            "Date",
            "Factory",
            "Building (ID)",
            "Item Code",
            "Item Description",
            "Operation",
            "Parameter",
            "LSL",
            "Target",
            "USL",
            "Actual Readings",
            "Status",
            "Machine",
            "Frequency",
            "Method",
            "Operator"
        ]
        
        rows = []
        for record in records:
            insp_schedule = record.get('insp_schedule_id_id', {})
            plant_data = record.get('created_by_id', {}).get('plant_id', {})
            building_data = insp_schedule.get('building_id', {})
            item_data = insp_schedule.get('item_code_id', {})
            operation_data = insp_schedule.get('operation_id', {})
            param_data = insp_schedule.get('inspection_parameter_id', {})
            machine_data = insp_schedule.get('qc_machine_id_id', {})
            operator_data = record.get('created_by_id', {})
            
            # Format actual readings
            actual_readings = record.get('actual_readings', [])
            if isinstance(actual_readings, list) and actual_readings:
                if isinstance(actual_readings[0], dict):
                    readings_str = f"Accepted: {actual_readings[0].get('accepted', 0)}, Rejected: {actual_readings[0].get('rejected', 0)}"
                else:
                    readings_str = ", ".join(map(str, actual_readings))
            else:
                readings_str = "N/A"
            
            # Determine status
            status = self._calculate_inspection_status(actual_readings, 
                                                      float(insp_schedule.get('LSL', 0) or 0),
                                                      float(insp_schedule.get('USL', 0) or 0))
            
            rows.append([
                str(record.get('id', 'N/A')),
                record.get('created_at', 'N/A')[:10],
                f"{plant_data.get('plant_name', 'N/A')}",
                f"{building_data.get('building_name', 'N/A')} ({building_data.get('building_id', 'N/A')})",
                item_data.get('item_code', 'N/A'),
                item_data.get('item_description', 'N/A'),
                operation_data.get('operation_name', 'N/A'),
                param_data.get('inspection_parameter', 'N/A'),
                insp_schedule.get('LSL', 'N/A'),
                insp_schedule.get('target_value', 'N/A'),
                insp_schedule.get('USL', 'N/A'),
                readings_str,
                status,
                f"{machine_data.get('machine_name', 'N/A')} ({machine_data.get('machine_id', 'N/A')})",
                insp_schedule.get('inspection_frequency', 'N/A'),
                insp_schedule.get('inspection_method', 'N/A'),
                f"{operator_data.get('first_name', '')} {operator_data.get('last_name', '')}"
            ])
        
        return {
            'title': f"Complete Inspection Records",
            'columns': columns,
            'rows': rows
        }
    
    def _calculate_inspection_status(self, readings, lsl, usl) -> str:
        """Calculate if readings are within specification"""
        if not readings:
            return "No Data"
        
        if isinstance(readings, list):
            if isinstance(readings[0], dict):
                rejected = int(readings[0].get('rejected', 0))
                return "❌ Failed" if rejected > 0 else "✅ Passed"
            else:
                numeric_readings = [float(r) for r in readings if str(r).replace('.', '').isdigit()]
                if not numeric_readings:
                    return "N/A"
                
                out_of_spec = [r for r in numeric_readings if r < lsl or r > usl]
                if out_of_spec:
                    return f"❌ Failed ({len(out_of_spec)} out of spec)"
                return "✅ Passed"
        
        return "N/A"
    
    async def _generate_inward_quality_response(self, context: Dict) -> Dict[str, Any]:
        """Generate inward material quality inspection response"""
        # Placeholder - will be implemented with similar comprehensive approach
        return {
            'response': "Inward Material Quality Inspection\n\nPlease provide:\n1. Factory name\n2. Item code or MIS/I/O number",
            'suggestions': ["View all items", "Select factory", "Go back"]
        }
    
    async def _generate_inprocess_response(self, context: Dict) -> Dict[str, Any]:
        """Generate in-process inspection response"""
        return {
            'response': "In-Process Inspection\n\nPlease provide:\n1. Factory\n2. Section/Building\n3. Item code\n4. PO number/Lot No",
            'suggestions': ["Select factory", "View all buildings", "Go back"]
        }
    
    async def _generate_final_inspection_response(self, context: Dict) -> Dict[str, Any]:
        """Generate final inspection response"""
        return {
            'response': "Final Inspection / FAI Details\n\nPlease provide:\n1. Factory\n2. Section/Building\n3. Item code\n4. PO number/Lot No",
            'suggestions': ["Select factory", "View all items", "Go back"]
        }
    
    async def _generate_parameter_analysis_response(self, context: Dict) -> Dict[str, Any]:
        """Generate parameter-wise analysis response"""
        return {
            'response': "Parameter-wise Analysis\n\nPlease select:\n1. Factory\n2. Section/Building\n3. Item code\n4. Operation\n5. Inspection parameter\n\nThen choose analysis type:\n• Duration-based analysis\n• Average readings\n• Min/Max readings\n• Out-of-spec readings\n• Operator performance",
            'suggestions': ["Select factory", "View parameters", "Go back"]
        }
    
    async def _generate_distribution_response(self, context: Dict) -> Dict[str, Any]:
        """Generate parameter distribution response"""
        return {
            'response': "Parameter Distribution Analysis\n\nPlease select:\n1. Factory\n2. Section/Building/Lab\n3. Inspection type (RM/In-process/Final)\n4. Item code\n5. Parameter",
            'suggestions': ["Select factory", "View all parameters", "Go back"]
        }
    
    async def _generate_navigation_response(self, context: Dict) -> Dict[str, Any]:
        """Generate navigation response for general queries"""
        response = "Welcome to Manufacturing Inspection Q&A System!\n\n"
        response += "I can help you with:\n\n"
        response += "1️⃣ PO Number Status - Track production order inspections\n"
        response += "2️⃣ Inward Material Quality - Check incoming material quality\n"
        response += "3️⃣ In-Process Inspection - Monitor production inspections\n"
        response += "4️⃣ Final Inspection - View FAI and final inspection details\n"
        response += "5️⃣ Parameter Analysis - Analyze quality parameters with trends\n"
        response += "6️⃣ Parameter Distribution - View distribution and histograms\n\n"
        response += "What would you like to explore?"
        
        suggestions = [
            "Show PO status",
            "View inward quality",
            "Check in-process inspection",
            "Show final inspection",
            "Analyze parameters"
        ]
        
        return {
            'response': response,
            'suggestions': suggestions
        }
    
    async def _save_to_redis(self, session_id: str, key: str, value: Any):
        """Save data to Redis/session store"""
        full_key = f"{session_id}:{key}"
        await self.redis_client.set(full_key, json.dumps(value))
    
    async def _get_from_redis(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get data from Redis/session store"""
        full_key = f"{session_id}:{key}"
        data = await self.redis_client.get(full_key)
        if data:
            return json.loads(data)
        return default

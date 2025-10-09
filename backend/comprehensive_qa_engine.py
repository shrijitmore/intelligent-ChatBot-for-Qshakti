import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import re
import statistics


class ComprehensiveQAEngine:
    """Comprehensive Q&A engine using ALL data fields from inspection records"""
    
    def __init__(self, redis_client, structured_data: Dict[str, Any]):
        self.redis_client = redis_client
        self.structured_data = structured_data
        self.raw_records = structured_data.get('raw_records', [])
        
        # Build comprehensive indexes using ALL data
        self.plant_index = {}
        self.building_index = {}
        self.item_index = {}
        self.po_index = {}
        self.operation_index = {}
        self.parameter_index = {}
        self.machine_index = {}
        self.operator_index = {}
        
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize and build comprehensive indexes"""
        self._build_comprehensive_indexes()
        self.logger.info(f"Comprehensive QA Engine initialized with ALL data fields")
    
    def _build_comprehensive_indexes(self):
        """Build indexes with EVERY field from data"""
        for record in self.raw_records:
            record_id = record.get('id')
            
            # Plant index - ALL plant data
            plant_data = record.get('created_by_id', {}).get('plant_id', {})
            plant_id = plant_data.get('plant_id')
            if plant_id and plant_id not in self.plant_index:
                self.plant_index[plant_id] = {
                    'plant_id': plant_id,
                    'plant_name': plant_data.get('plant_name'),
                    'plant_location_1': plant_data.get('plant_location_1'),
                    'plant_location_2': plant_data.get('plant_location_2'),
                    'buildings': set(),
                    'items': set(),
                    'pos': set(),
                    'records': []
                }
            if plant_id:
                self.plant_index[plant_id]['records'].append(record_id)
            
            # Building index - ALL building data
            building_data = record.get('insp_schedule_id_id', {}).get('building_id', {})
            building_id = building_data.get('building_id')
            if building_id and building_id not in self.building_index:
                self.building_index[building_id] = {
                    'id': building_data.get('id'),
                    'building_id': building_id,
                    'building_name': building_data.get('building_name'),
                    'sub_section': building_data.get('sub_section'),
                    'plant_id': building_data.get('plant_id'),
                    'is_active': building_data.get('is_active'),
                    'items': set(),
                    'operations': set(),
                    'records': []
                }
            if building_id:
                self.building_index[building_id]['records'].append(record_id)
                if plant_id:
                    self.plant_index[plant_id]['buildings'].add(building_id)
            
            # Item index - ALL item data
            item_data = record.get('insp_schedule_id_id', {}).get('item_code_id', {})
            item_code = item_data.get('item_code')
            if item_code and item_code not in self.item_index:
                self.item_index[item_code] = {
                    'id': item_data.get('id'),
                    'item_code': item_code,
                    'item_description': item_data.get('item_description'),
                    'unit': item_data.get('unit'),
                    'item_type': item_data.get('item_type'),
                    'end_store': item_data.get('end_store'),
                    'is_active': item_data.get('is_active'),
                    'buildings': set(),
                    'operations': set(),
                    'parameters': set(),
                    'machines': set(),
                    'pos': set(),
                    'records': []
                }
            if item_code:
                self.item_index[item_code]['records'].append(record_id)
                if plant_id:
                    self.plant_index[plant_id]['items'].add(item_code)
                if building_id:
                    self.building_index[building_id]['items'].add(item_code)
                    self.item_index[item_code]['buildings'].add(building_id)
            
            # PO index - ALL PO data
            po_no = record.get('po_no')
            if po_no and po_no not in self.po_index:
                self.po_index[po_no] = {
                    'po_no': po_no,
                    'plants': set(),
                    'buildings': set(),
                    'items': set(),
                    'operators': set(),
                    'total_inspections': 0,
                    'passed': 0,
                    'failed': 0,
                    'records': []
                }
            if po_no:
                self.po_index[po_no]['records'].append(record_id)
                self.po_index[po_no]['total_inspections'] += 1
                if plant_id:
                    self.po_index[po_no]['plants'].add(plant_id)
                    self.plant_index[plant_id]['pos'].add(po_no)
                if building_id:
                    self.po_index[po_no]['buildings'].add(building_id)
                if item_code:
                    self.po_index[po_no]['items'].add(item_code)
                    self.item_index[item_code]['pos'].add(po_no)
            
            # Operation index - ALL operation data
            operation_data = record.get('insp_schedule_id_id', {}).get('operation_id', {})
            operation_id = operation_data.get('operation_id')
            if operation_id and operation_id not in self.operation_index:
                self.operation_index[operation_id] = {
                    'id': operation_data.get('id'),
                    'operation_id': operation_id,
                    'operation_name': operation_data.get('operation_name'),
                    'operation_description': operation_data.get('operation_description'),
                    'is_active': operation_data.get('is_active'),
                    'items': set(),
                    'parameters': set(),
                    'records': []
                }
            if operation_id:
                self.operation_index[operation_id]['records'].append(record_id)
                if building_id:
                    self.building_index[building_id]['operations'].add(operation_id)
                if item_code:
                    self.item_index[item_code]['operations'].add(operation_id)
                    self.operation_index[operation_id]['items'].add(item_code)
            
            # Parameter index - ALL parameter data
            param_data = record.get('insp_schedule_id_id', {}).get('inspection_parameter_id', {})
            param_id = param_data.get('inspection_parameter_id')
            if param_id and param_id not in self.parameter_index:
                self.parameter_index[param_id] = {
                    'id': param_data.get('id'),
                    'inspection_parameter_id': param_id,
                    'inspection_parameter': param_data.get('inspection_parameter'),
                    'parameter_description': param_data.get('parameter_description'),
                    'is_active': param_data.get('is_active'),
                    'items': set(),
                    'operations': set(),
                    'records': []
                }
            if param_id:
                self.parameter_index[param_id]['records'].append(record_id)
                if item_code:
                    self.item_index[item_code]['parameters'].add(param_id)
                    self.parameter_index[param_id]['items'].add(item_code)
                if operation_id:
                    self.parameter_index[param_id]['operations'].add(operation_id)
                    self.operation_index[operation_id]['parameters'].add(param_id)
            
            # Machine index - ALL machine data
            machine_data = record.get('insp_schedule_id_id', {}).get('qc_machine_id_id', {})
            machine_id = machine_data.get('machine_id')
            if machine_id and machine_id not in self.machine_index:
                self.machine_index[machine_id] = {
                    'id': machine_data.get('id'),
                    'machine_id': machine_id,
                    'machine_name': machine_data.get('machine_name'),
                    'machine_make': machine_data.get('machine_make'),
                    'machine_model': machine_data.get('machine_model'),
                    'is_digital': machine_data.get('is_digital'),
                    'machine_type': machine_data.get('machine_type'),
                    'is_active': machine_data.get('is_active'),
                    'created_at': machine_data.get('created_at'),
                    'updated_at': machine_data.get('updated_at'),
                    'items': set(),
                    'records': []
                }
            if machine_id:
                self.machine_index[machine_id]['records'].append(record_id)
                if item_code:
                    self.item_index[item_code]['machines'].add(machine_id)
                    self.machine_index[machine_id]['items'].add(item_code)
            
            # Operator index - ALL operator data
            operator_data = record.get('created_by_id', {})
            operator_email = operator_data.get('email')
            if operator_email and operator_email not in self.operator_index:
                role_data = operator_data.get('role_id', {})
                self.operator_index[operator_email] = {
                    'first_name': operator_data.get('first_name'),
                    'middle_name': operator_data.get('middle_name'),
                    'last_name': operator_data.get('last_name'),
                    'email': operator_email,
                    'phone_number': operator_data.get('phone_number'),
                    'role_name': role_data.get('name'),
                    'role_description': role_data.get('description'),
                    'plant_id': plant_id,
                    'plant_name': plant_data.get('plant_name'),
                    'records': []
                }
            if operator_email:
                self.operator_index[operator_email]['records'].append(record_id)
                if po_no:
                    self.po_index[po_no]['operators'].add(operator_email)
        
        self.logger.info(f"Built comprehensive indexes: {len(self.plant_index)} plants, "
                        f"{len(self.building_index)} buildings, {len(self.item_index)} items, "
                        f"{len(self.po_index)} POs, {len(self.operation_index)} operations, "
                        f"{len(self.parameter_index)} parameters, {len(self.machine_index)} machines, "
                        f"{len(self.operator_index)} operators")
    
    async def generate_initial_suggestions(self, session_id: str) -> List[str]:
        """Generate initial suggestions"""
        suggestions = [
            "1️⃣ Show PO status",
            "2️⃣ Inward material quality",
            "3️⃣ In-process inspection",
            "4️⃣ Final inspection details",
            "5️⃣ Parameter analysis with charts",
            "6️⃣ Parameter distribution"
        ]
        
        await self._save_to_redis(session_id, 'context', {'level': 'START'})
        await self._save_to_redis(session_id, 'history', [])
        
        return suggestions
    
    async def process_message(self, session_id: str, message: str, is_suggestion: bool) -> Dict[str, Any]:
        """Process message with comprehensive data handling"""
        context = await self._get_from_redis(session_id, 'context', {'level': 'START'})
        history = await self._get_from_redis(session_id, 'history', [])
        
        history.append({
            'role': 'user',
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Detect question type and navigate
        response_data = await self._route_question(message, context, history)
        
        history.append({
            'role': 'assistant',
            'message': response_data['response'],
            'suggestions': response_data['suggestions'],
            'chart_data': response_data.get('chart_data'),
            'table_data': response_data.get('table_data'),
            'timestamp': datetime.now().isoformat()
        })
        
        await self._save_to_redis(session_id, 'context', response_data.get('new_context', context))
        await self._save_to_redis(session_id, 'history', history)
        
        return {
            'response': response_data['response'],
            'suggestions': response_data['suggestions'],
            'context_path': [message],
            'chart_data': response_data.get('chart_data'),
            'table_data': response_data.get('table_data'),
            'metadata': response_data.get('metadata', {})
        }
    
    async def _route_question(self, message: str, context: Dict, history: List) -> Dict[str, Any]:
        """Route to appropriate question handler"""
        msg_lower = message.lower()
        
        # Question type detection
        if any(kw in msg_lower for kw in ['po', 'production order', 'order status', '1']):
            return await self._handle_q1_po_status(message, context)
        elif any(kw in msg_lower for kw in ['inward', 'material', 'quality', '2']):
            return await self._handle_q2_inward_quality(message, context)
        elif any(kw in msg_lower for kw in ['in-process', 'in process', 'process', '3']):
            return await self._handle_q3_inprocess(message, context)
        elif any(kw in msg_lower for kw in ['final', 'fai', 'final inspection', '4']):
            return await self._handle_q4_final_inspection(message, context)
        elif any(kw in msg_lower for kw in ['parameter', 'analysis', 'chart', 'trend', '5']):
            return await self._handle_q5_parameter_analysis(message, context)
        elif any(kw in msg_lower for kw in ['distribution', 'histogram', '6']):
            return await self._handle_q6_distribution(message, context)
        else:
            return await self._handle_navigation(message, context)
    
    async def _handle_q1_po_status(self, message: str, context: Dict) -> Dict[str, Any]:
        """Question 1: PO Status - Show ALL data"""
        level = context.get('q1_level', 'start')
        
        if level == 'start':
            # Show all factories
            plants = list(self.plant_index.values())
            response = "📋 **QUESTION 1: Production Order Status**\n\n"
            response += "**Step 1: Select Factory**\n\n"
            
            for plant in plants:
                response += f"🏭 **{plant['plant_name']}**\n"
                response += f"   • Plant ID: {plant['plant_id']}\n"
                response += f"   • Location 1: {plant['plant_location_1']}\n"
                response += f"   • Location 2: {plant['plant_location_2']}\n"
                response += f"   • Total POs: {len(plant['pos'])}\n"
                response += f"   • Buildings: {len(plant['buildings'])}\n"
                response += f"   • Items: {len(plant['items'])}\n\n"
            
            suggestions = [f"Select {p['plant_name']}" for p in plants]
            suggestions.append("Go back")
            
            return {
                'response': response,
                'suggestions': suggestions,
                'new_context': {**context, 'q1_level': 'factory_selected'}
            }
        
        elif level == 'factory_selected':
            # Extract factory from message and show POs
            selected_plant = self._find_plant_in_message(message)
            
            if selected_plant:
                plant = self.plant_index[selected_plant]
                response = f"🏭 **Factory: {plant['plant_name']}**\n\n"
                response += f"**Plant Details:**\n"
                response += f"• Plant ID: {plant['plant_id']}\n"
                response += f"• Location 1: {plant['plant_location_1']}\n"
                response += f"• Location 2: {plant['plant_location_2']}\n\n"
                
                response += "**Available PO Numbers:**\n"
                pos_for_plant = [po for po, data in self.po_index.items() 
                                if selected_plant in data['plants']]
                
                for po in pos_for_plant:
                    po_data = self.po_index[po]
                    response += f"\n📦 **PO: {po}**\n"
                    response += f"   • Total Inspections: {po_data['total_inspections']}\n"
                    response += f"   • Buildings: {len(po_data['buildings'])}\n"
                    response += f"   • Items: {len(po_data['items'])}\n"
                    response += f"   • Operators: {len(po_data['operators'])}\n"
                
                suggestions = [f"Show details for PO {po}" for po in pos_for_plant[:3]]
                suggestions.append("Select another factory")
                
                return {
                    'response': response,
                    'suggestions': suggestions,
                    'new_context': {**context, 'q1_level': 'po_selected', 'selected_plant': selected_plant}
                }
        
        elif level == 'po_selected':
            # Extract PO and show COMPLETE details
            po_match = re.search(r'[A-Z]?-?\d{4,}', message)
            if po_match:
                po_no = po_match.group()
                if po_no in self.po_index:
                    return await self._generate_complete_po_details(po_no, context)
        
        # Default fallback
        return await self._handle_q1_po_status("start", {'q1_level': 'start'})
    
    async def _generate_complete_po_details(self, po_no: str, context: Dict) -> Dict[str, Any]:
        """Generate COMPLETE PO details with ALL fields"""
        records = [r for r in self.raw_records if r.get('po_no') == po_no]
        po_data = self.po_index[po_no]
        
        response = f"📦 **COMPLETE PO STATUS REPORT**\n\n"
        response += f"**PO Number:** {po_no}\n"
        response += f"**Total Inspection Records:** {len(records)}\n\n"
        
        # Show all factories involved
        response += "**🏭 Factories Involved:**\n"
        for plant_id in po_data['plants']:
            plant = self.plant_index.get(plant_id, {})
            response += f"• {plant.get('plant_name')} (ID: {plant_id})\n"
            response += f"  Location: {plant.get('plant_location_1')}, {plant.get('plant_location_2')}\n"
        
        # Show all buildings
        response += "\n**🏢 Buildings/Sections:**\n"
        for building_id in po_data['buildings']:
            building = self.building_index.get(building_id, {})
            response += f"• {building.get('building_name')} (ID: {building_id}, Sub-section: {building.get('sub_section')})\n"
        
        # Show all items
        response += "\n**📦 Items:**\n"
        for item_code in po_data['items']:
            item = self.item_index.get(item_code, {})
            response += f"• {item.get('item_description')}\n"
            response += f"  Code: {item_code}, Type: {item.get('item_type')}, Unit: {item.get('unit')}\n"
        
        # Show all operators
        response += "\n**👥 Operators:**\n"
        for email in po_data['operators']:
            operator = self.operator_index.get(email, {})
            response += f"• {operator.get('first_name')} {operator.get('last_name')} ({operator.get('role_name')})\n"
            response += f"  Email: {email}, Phone: {operator.get('phone_number')}\n"
        
        # Generate comprehensive table
        table_data = self._generate_ultra_comprehensive_table(records, "PO Inspection Details")
        
        # Generate charts
        chart_data = self._generate_po_charts(records)
        
        suggestions = [
            f"Show quality trends for {po_no}",
            f"Show parameter distribution for {po_no}",
            "Search another PO",
            "Go back to main menu"
        ]
        
        return {
            'response': response,
            'suggestions': suggestions,
            'table_data': table_data,
            'chart_data': chart_data,
            'new_context': context
        }
    
    def _generate_ultra_comprehensive_table(self, records: List[Dict], title: str) -> Dict[str, Any]:
        """Generate table with EVERY single field from records"""
        columns = [
            "ID", "Created Date", "Updated Date", "Active", "PO Number",
            "Plant ID", "Plant Name", "Plant Location 1", "Plant Location 2",
            "Building ID", "Building Name", "Sub-Section",
            "Item Code", "Item Description", "Item Type", "Unit",
            "Operation ID", "Operation Name", "Operation Description",
            "Parameter ID", "Parameter Name", "Parameter Description",
            "Machine ID", "Machine Name", "Make", "Model", "Is Digital",
            "LSL", "Target", "USL", "Actual Readings", "Status",
            "Sample Size", "Frequency", "Method", "Recording Type",
            "Defect Classification", "Remarks",
            "Operator Name", "Operator Email", "Operator Phone", "Operator Role"
        ]
        
        rows = []
        for record in records:
            insp_sched = record.get('insp_schedule_id_id', {})
            plant_data = record.get('created_by_id', {}).get('plant_id', {})
            building = insp_sched.get('building_id', {})
            item = insp_sched.get('item_code_id', {})
            operation = insp_sched.get('operation_id', {})
            param = insp_sched.get('inspection_parameter_id', {})
            machine = insp_sched.get('qc_machine_id_id', {})
            operator = record.get('created_by_id', {})
            role = operator.get('role_id', {})
            
            # Format readings
            readings = record.get('actual_readings', [])
            if isinstance(readings, list) and readings:
                if isinstance(readings[0], dict):
                    readings_str = f"Acc: {readings[0].get('accepted', 0)}, Rej: {readings[0].get('rejected', 0)}"
                else:
                    readings_str = ", ".join(map(str, readings))
            else:
                readings_str = "N/A"
            
            # Calculate status
            status = self._calculate_status(readings, 
                                           float(insp_sched.get('LSL', 0) or 0),
                                           float(insp_sched.get('USL', 0) or 0))
            
            rows.append([
                str(record.get('id', '')),
                record.get('created_at', '')[:19] if record.get('created_at') else '',
                record.get('updated_at', '')[:19] if record.get('updated_at') else '',
                str(record.get('is_active', '')),
                record.get('po_no', ''),
                plant_data.get('plant_id', ''),
                plant_data.get('plant_name', ''),
                plant_data.get('plant_location_1', ''),
                plant_data.get('plant_location_2', ''),
                building.get('building_id', ''),
                building.get('building_name', ''),
                building.get('sub_section', ''),
                item.get('item_code', ''),
                item.get('item_description', ''),
                item.get('item_type', ''),
                item.get('unit', ''),
                operation.get('operation_id', ''),
                operation.get('operation_name', ''),
                operation.get('operation_description', ''),
                param.get('inspection_parameter_id', ''),
                param.get('inspection_parameter', ''),
                param.get('parameter_description', ''),
                machine.get('machine_id', ''),
                machine.get('machine_name', ''),
                machine.get('machine_make', ''),
                machine.get('machine_model', ''),
                str(machine.get('is_digital', '')),
                insp_sched.get('LSL', ''),
                insp_sched.get('target_value', ''),
                insp_sched.get('USL', ''),
                readings_str,
                status,
                insp_sched.get('sample_size', ''),
                insp_sched.get('inspection_frequency', ''),
                insp_sched.get('inspection_method', ''),
                insp_sched.get('recording_type', ''),
                insp_sched.get('likely_defects_classification', ''),
                insp_sched.get('remarks', ''),
                f"{operator.get('first_name', '')} {operator.get('last_name', '')}",
                operator.get('email', ''),
                operator.get('phone_number', ''),
                role.get('name', '')
            ])
        
        return {
            'title': title,
            'columns': columns,
            'rows': rows
        }
    
    def _generate_po_charts(self, records: List[Dict]) -> Dict[str, Any]:
        """Generate charts for PO data"""
        # Extract numeric readings
        dates = []
        readings_data = []
        
        for record in records:
            date = record.get('created_at', '')[:10]
            readings = record.get('actual_readings', [])
            
            if isinstance(readings, list) and readings:
                if isinstance(readings[0], dict):
                    accepted = int(readings[0].get('accepted', 0))
                    readings_data.append(accepted)
                    dates.append(date)
                else:
                    for reading in readings:
                        if str(reading).replace('.', '').replace('-', '').isdigit():
                            readings_data.append(float(reading))
                            dates.append(date)
        
        if not readings_data:
            return None
        
        return {
            'type': 'line',
            'title': 'Inspection Readings Over Time',
            'data': {
                'labels': dates,
                'datasets': [{
                    'label': 'Readings',
                    'data': readings_data,
                    'borderColor': '#3b82f6',
                    'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                    'tension': 0.4
                }]
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'legend': {'display': True},
                    'title': {'display': True, 'text': 'Quality Readings Timeline'}
                }
            }
        }
    
    def _calculate_status(self, readings, lsl: float, usl: float) -> str:
        """Calculate pass/fail status"""
        if not readings:
            return "No Data"
        
        if isinstance(readings, list):
            if isinstance(readings[0], dict):
                rejected = int(readings[0].get('rejected', 0))
                return "❌ FAIL" if rejected > 0 else "✅ PASS"
            else:
                numeric = [float(r) for r in readings if str(r).replace('.', '').replace('-', '').isdigit()]
                if not numeric:
                    return "N/A"
                out_of_spec = [r for r in numeric if r < lsl or r > usl]
                return f"❌ FAIL ({len(out_of_spec)} OOS)" if out_of_spec else "✅ PASS"
        return "N/A"
    
    def _find_plant_in_message(self, message: str) -> Optional[str]:
        """Find plant ID from message"""
        msg_lower = message.lower()
        for plant_id, plant in self.plant_index.items():
            if plant['plant_name'].lower() in msg_lower or plant_id in message:
                return plant_id
        return None
    
    async def _handle_q2_inward_quality(self, message: str, context: Dict) -> Dict[str, Any]:
        """Question 2: Inward Material Quality Inspection"""
        level = context.get('q2_level', 'start')
        
        if level == 'start':
            plants = list(self.plant_index.values())
            response = "📥 **QUESTION 2: Inward Material Quality Inspection**\n\n"
            response += "**Step 1: Select Factory**\n\n"
            
            for plant in plants:
                response += f"🏭 {plant['plant_name']} (ID: {plant['plant_id']})\n"
                response += f"   Items tracked: {len(plant['items'])}\n\n"
            
            suggestions = [f"Select {p['plant_name']}" for p in plants]
            return {
                'response': response,
                'suggestions': suggestions,
                'new_context': {**context, 'q2_level': 'factory_selected'}
            }
        
        elif level == 'factory_selected':
            selected_plant = self._find_plant_in_message(message)
            if selected_plant:
                items = list(self.item_index.values())
                response = f"🏭 **Factory: {self.plant_index[selected_plant]['plant_name']}**\n\n"
                response += "**Step 2: Select Item Code or MIS/I/O Number**\n\n"
                
                for item in items[:10]:
                    response += f"📦 **{item['item_description']}**\n"
                    response += f"   Code: {item['item_code']}\n"
                    response += f"   Type: {item['item_type']}, Unit: {item['unit']}\n\n"
                
                suggestions = [f"Item {item['item_code']}" for item in items[:3]]
                return {
                    'response': response,
                    'suggestions': suggestions,
                    'new_context': {**context, 'q2_level': 'item_selected', 'selected_plant': selected_plant}
                }
        
        elif level == 'item_selected':
            item_match = re.search(r'\d{10,}', message)
            if item_match:
                item_code = item_match.group()
                if item_code in self.item_index:
                    records = [r for r in self.raw_records 
                             if r.get('insp_schedule_id_id', {}).get('item_code_id', {}).get('item_code') == item_code]
                    
                    item = self.item_index[item_code]
                    response = f"📦 **INWARD MATERIAL QUALITY INSPECTION**\n\n"
                    response += f"**Item Details:**\n"
                    response += f"• Item Code: {item['item_code']}\n"
                    response += f"• Description: {item['item_description']}\n"
                    response += f"• Type: {item['item_type']}\n"
                    response += f"• Unit: {item['unit']}\n"
                    response += f"• Total Inspections: {len(records)}\n\n"
                    
                    table_data = self._generate_ultra_comprehensive_table(records, f"Inward Quality - {item_code}")
                    
                    return {
                        'response': response,
                        'table_data': table_data,
                        'suggestions': ["Select another item", "Go back"],
                        'new_context': context
                    }
        
        return await self._handle_q2_inward_quality("start", {'q2_level': 'start'})
    
    async def _handle_q3_inprocess(self, message: str, context: Dict) -> Dict[str, Any]:
        """Question 3: In-Process Inspection"""
        level = context.get('q3_level', 'start')
        
        if level == 'start':
            plants = list(self.plant_index.values())
            response = "⚙️ **QUESTION 3: In-Process Inspection**\n\n"
            response += "**Step 1: Select Factory**\n\n"
            
            for plant in plants:
                response += f"🏭 {plant['plant_name']}\n"
            
            suggestions = [f"Factory {p['plant_name']}" for p in plants]
            return {
                'response': response,
                'suggestions': suggestions,
                'new_context': {**context, 'q3_level': 'building_selection'}
            }
        
        elif level == 'building_selection':
            selected_plant = self._find_plant_in_message(message)
            if selected_plant:
                buildings = [self.building_index[bid] for bid in self.plant_index[selected_plant]['buildings']]
                response = f"**Step 2: Select Section/Building**\n\n"
                
                for building in buildings:
                    response += f"🏢 {building['building_name']} (ID: {building['building_id']}, Sub: {building['sub_section']})\n"
                
                suggestions = [f"Building {b['building_name']}" for b in buildings]
                return {
                    'response': response,
                    'suggestions': suggestions,
                    'new_context': {**context, 'q3_level': 'item_selection', 'selected_plant': selected_plant}
                }
        
        elif level == 'item_selection':
            building_match = re.search(r'[A-Z0-9/-]+', message)
            if building_match:
                building_id = building_match.group()
                if building_id in self.building_index:
                    items = [self.item_index[iid] for iid in self.building_index[building_id]['items']]
                    response = f"**Step 3: Select Item**\n\n"
                    
                    for item in items:
                        response += f"📦 {item['item_description']} (Code: {item['item_code']})\n"
                    
                    suggestions = [f"Item {i['item_code']}" for i in items]
                    return {
                        'response': response,
                        'suggestions': suggestions,
                        'new_context': {**context, 'q3_level': 'po_selection', 'selected_building': building_id}
                    }
        
        elif level == 'po_selection':
            item_match = re.search(r'\d{10,}', message)
            if item_match:
                item_code = item_match.group()
                if item_code in self.item_index:
                    pos = list(self.item_index[item_code]['pos'])
                    response = f"**Step 4: Select PO Number/Lot No**\n\n"
                    
                    for po in pos:
                        response += f"📦 PO: {po}\n"
                    
                    suggestions = [f"PO {po}" for po in pos]
                    return {
                        'response': response,
                        'suggestions': suggestions,
                        'new_context': {**context, 'q3_level': 'show_data', 'selected_item': item_code}
                    }
        
        elif level == 'show_data':
            po_match = re.search(r'[A-Z]?-?\d{4,}', message)
            if po_match:
                po_no = po_match.group()
                item_code = context.get('selected_item')
                
                records = [r for r in self.raw_records 
                          if r.get('po_no') == po_no 
                          and r.get('insp_schedule_id_id', {}).get('item_code_id', {}).get('item_code') == item_code]
                
                response = f"⚙️ **IN-PROCESS INSPECTION DATA**\n\n"
                response += f"PO: {po_no}, Item: {item_code}\n\n"
                
                table_data = self._generate_ultra_comprehensive_table(records, "In-Process Inspection")
                
                return {
                    'response': response,
                    'table_data': table_data,
                    'suggestions': ["Search another", "Go back"],
                    'new_context': context
                }
        
        return await self._handle_q3_inprocess("start", {'q3_level': 'start'})
    
    async def _handle_q4_final_inspection(self, message: str, context: Dict) -> Dict[str, Any]:
        """Question 4: Final Inspection / FAI"""
        # Similar structure to Q3
        level = context.get('q4_level', 'start')
        
        if level == 'start':
            plants = list(self.plant_index.values())
            response = "🔍 **QUESTION 4: Final Inspection / FAI Details**\n\n"
            response += "**Step 1: Select Factory**\n\n"
            
            for plant in plants:
                response += f"🏭 {plant['plant_name']}\n"
            
            suggestions = [f"Factory {p['plant_name']}" for p in plants]
            return {
                'response': response,
                'suggestions': suggestions,
                'new_context': {**context, 'q4_level': 'complete'}
            }
        
        # Similar navigation flow as Q3
        return await self._handle_q4_final_inspection("start", {'q4_level': 'start'})
    
    async def _handle_q5_parameter_analysis(self, message: str, context: Dict) -> Dict[str, Any]:
        """Question 5: Parameter-wise Analysis with Charts"""
        level = context.get('q5_level', 'start')
        
        if level == 'start':
            plants = list(self.plant_index.values())
            response = "📊 **QUESTION 5: Inspection Parameter Analysis**\n\n"
            response += "**Step 1: Select Factory**\n\n"
            
            for plant in plants:
                response += f"🏭 {plant['plant_name']}\n"
            
            suggestions = [f"Factory {p['plant_name']}" for p in plants]
            return {
                'response': response,
                'suggestions': suggestions,
                'new_context': {**context, 'q5_level': 'select_building'}
            }
        
        elif level == 'select_building':
            selected_plant = self._find_plant_in_message(message)
            if selected_plant:
                buildings = [self.building_index[bid] for bid in self.plant_index[selected_plant]['buildings']]
                response = "**Step 2: Select Section/Building**\n\n"
                
                for building in buildings:
                    response += f"🏢 {building['building_name']}\n"
                
                suggestions = [f"Building {b['building_name']}" for b in buildings]
                return {
                    'response': response,
                    'suggestions': suggestions,
                    'new_context': {**context, 'q5_level': 'select_item'}
                }
        
        elif level == 'select_item':
            # Continue with item -> operation -> parameter -> analysis type selection
            response = "**Select analysis type:**\n\n"
            response += "• Duration-based analysis\n"
            response += "• Average readings chart\n"
            response += "• Min/Max readings\n"
            response += "• Out-of-spec readings\n"
            response += "• Operator performance\n"
            
            suggestions = ["Average readings", "Min/Max", "Out of spec", "Duration analysis"]
            
            # Generate sample chart
            chart_data = self._generate_parameter_analysis_chart()
            
            return {
                'response': response,
                'suggestions': suggestions,
                'chart_data': chart_data,
                'new_context': context
            }
        
        return await self._handle_q5_parameter_analysis("start", {'q5_level': 'start'})
    
    def _generate_parameter_analysis_chart(self) -> Dict[str, Any]:
        """Generate parameter analysis charts"""
        # Get all numeric readings
        all_readings = []
        labels = []
        
        for record in self.raw_records[:10]:
            readings = record.get('actual_readings', [])
            param = record.get('insp_schedule_id_id', {}).get('inspection_parameter_id', {}).get('inspection_parameter', '')
            
            if isinstance(readings, list) and readings:
                if not isinstance(readings[0], dict):
                    for r in readings:
                        if str(r).replace('.', '').replace('-', '').isdigit():
                            all_readings.append(float(r))
                            labels.append(param[:20])
        
        if not all_readings:
            return None
        
        return {
            'type': 'bar',
            'title': 'Parameter Readings Analysis',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': 'Readings',
                    'data': all_readings,
                    'backgroundColor': '#10b981'
                }]
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'title': {'display': True, 'text': 'Quality Parameter Analysis'}
                }
            }
        }
    
    async def _handle_q6_distribution(self, message: str, context: Dict) -> Dict[str, Any]:
        """Question 6: Parameter Distribution"""
        response = "📈 **QUESTION 6: Parameter Distribution Analysis**\n\n"
        response += "Showing distribution of captured inspection parameters\n\n"
        
        # Generate distribution chart
        chart_data = self._generate_distribution_chart()
        
        # Generate statistics table
        table_data = self._generate_distribution_table()
        
        suggestions = ["Show another distribution", "Go back"]
        
        return {
            'response': response,
            'chart_data': chart_data,
            'table_data': table_data,
            'suggestions': suggestions,
            'new_context': context
        }
    
    def _generate_distribution_chart(self) -> Dict[str, Any]:
        """Generate histogram for distribution"""
        all_readings = []
        
        for record in self.raw_records:
            readings = record.get('actual_readings', [])
            if isinstance(readings, list):
                for r in readings:
                    if not isinstance(r, dict) and str(r).replace('.', '').replace('-', '').isdigit():
                        all_readings.append(float(r))
        
        if not all_readings:
            return None
        
        # Create histogram bins
        min_val = min(all_readings)
        max_val = max(all_readings)
        bins = 10
        bin_width = (max_val - min_val) / bins
        
        bin_counts = [0] * bins
        bin_labels = []
        
        for i in range(bins):
            bin_start = min_val + i * bin_width
            bin_end = bin_start + bin_width
            bin_labels.append(f"{bin_start:.1f}-{bin_end:.1f}")
            bin_counts[i] = len([r for r in all_readings if bin_start <= r < bin_end])
        
        return {
            'type': 'bar',
            'title': 'Parameter Distribution',
            'data': {
                'labels': bin_labels,
                'datasets': [{
                    'label': 'Frequency',
                    'data': bin_counts,
                    'backgroundColor': '#8b5cf6'
                }]
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'title': {'display': True, 'text': 'Distribution Histogram'}
                }
            }
        }
    
    def _generate_distribution_table(self) -> Dict[str, Any]:
        """Generate statistics table for distribution"""
        all_readings = []
        
        for record in self.raw_records:
            readings = record.get('actual_readings', [])
            if isinstance(readings, list):
                for r in readings:
                    if not isinstance(r, dict) and str(r).replace('.', '').replace('-', '').isdigit():
                        all_readings.append(float(r))
        
        if not all_readings:
            return None
        
        columns = ["Statistic", "Value"]
        rows = [
            ["Count", str(len(all_readings))],
            ["Mean", f"{statistics.mean(all_readings):.2f}"],
            ["Median", f"{statistics.median(all_readings):.2f}"],
            ["Std Dev", f"{statistics.stdev(all_readings) if len(all_readings) > 1 else 0:.2f}"],
            ["Min", f"{min(all_readings):.2f}"],
            ["Max", f"{max(all_readings):.2f}"],
            ["Range", f"{max(all_readings) - min(all_readings):.2f}"]
        ]
        
        return {
            'title': 'Distribution Statistics',
            'columns': columns,
            'rows': rows
        }
    
    async def _handle_navigation(self, message: str, context: Dict) -> Dict[str, Any]:
        """Handle general navigation"""
        response = "🏭 **Manufacturing Inspection Q&A System**\n\n"
        response += "**Available Questions:**\n\n"
        response += "1️⃣ **PO Status** - Complete production order inspection details\n"
        response += "2️⃣ **Inward Material Quality** - Raw material inspection data\n"
        response += "3️⃣ **In-Process Inspection** - Production line quality checks\n"
        response += "4️⃣ **Final Inspection** - FAI and final quality verification\n"
        response += "5️⃣ **Parameter Analysis** - Trends, charts, min/max, out-of-spec\n"
        response += "6️⃣ **Parameter Distribution** - Statistical distribution analysis\n\n"
        response += f"**System Status:**\n"
        response += f"• Total Records: {len(self.raw_records)}\n"
        response += f"• Plants: {len(self.plant_index)}\n"
        response += f"• Buildings: {len(self.building_index)}\n"
        response += f"• Items: {len(self.item_index)}\n"
        response += f"• PO Numbers: {len(self.po_index)}\n"
        response += f"• Operations: {len(self.operation_index)}\n"
        response += f"• Parameters: {len(self.parameter_index)}\n"
        response += f"• Machines: {len(self.machine_index)}\n"
        response += f"• Operators: {len(self.operator_index)}\n"
        
        suggestions = [
            "1️⃣ Show PO status",
            "2️⃣ Inward quality",
            "3️⃣ In-process",
            "4️⃣ Final inspection",
            "5️⃣ Parameter analysis"
        ]
        
        return {
            'response': response,
            'suggestions': suggestions,
            'new_context': {'level': 'START'}
        }
    
    async def _save_to_redis(self, session_id: str, key: str, value: Any):
        """Save to session store"""
        full_key = f"{session_id}:{key}"
        await self.redis_client.set(full_key, json.dumps(value))
    
    async def _get_from_redis(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get from session store"""
        full_key = f"{session_id}:{key}"
        data = await self.redis_client.get(full_key)
        return json.loads(data) if data else default

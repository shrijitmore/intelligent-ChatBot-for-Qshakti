import json
import logging
from typing import Dict, List, Any, Optional
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
import hashlib
import asyncio


class ChatbotEngine:
    """Hierarchical chatbot engine with conversational navigation"""
    
    def __init__(self, gemini_api_key: str, redis_client, structured_data: Dict[str, Any]):
        self.gemini_api_key = gemini_api_key
        self.redis_client = redis_client
        self.structured_data = structured_data
        
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        # ChromaDB client (in-memory for now)
        self.chroma_client = None
        self.collection = None
        
        self.logger = logging.getLogger(__name__)
        
        # Hierarchy levels
        self.LEVELS = {
            "START": 0,
            "PLANT": 1,
            "SECTION": 2,
            "ITEM": 3,
            "DETAILS": 4
        }
    
    async def initialize(self):
        """Initialize the chatbot engine"""
        # Initialize ChromaDB
        self.chroma_client = chromadb.Client(Settings(
            allow_reset=True,
            is_persistent=False
        ))
        
        # Create or get collection
        try:
            self.collection = self.chroma_client.get_collection(name="hierarchy_embeddings")
        except Exception:
            self.collection = self.chroma_client.create_collection(name="hierarchy_embeddings")
        
        # Generate and store embeddings for hierarchy
        await self._generate_hierarchy_embeddings()
        
        self.logger.info("Chatbot engine initialized with hierarchical navigation")
    
    async def _generate_hierarchy_embeddings(self):
        """Generate embeddings for plants, sections, and items"""
        hierarchy = self.structured_data.get('hierarchy', {})
        
        documents = []
        metadatas = []
        ids = []
        
        # Generate embeddings for each level
        for plant_id, plant_data in hierarchy.items():
            # Plant level
            doc_text = f"Plant: {plant_data['name']} (ID: {plant_id})"
            documents.append(doc_text)
            metadatas.append({
                'level': 'plant',
                'plant_id': plant_id,
                'name': plant_data['name']
            })
            ids.append(f"plant_{plant_id}")
            
            # Section level
            for section_id, section_data in plant_data.get('sections', {}).items():
                doc_text = f"Section: {section_data['name']} in {plant_data['name']}"
                documents.append(doc_text)
                metadatas.append({
                    'level': 'section',
                    'plant_id': plant_id,
                    'section_id': section_id,
                    'name': section_data['name']
                })
                ids.append(f"section_{plant_id}_{section_id}")
                
                # Item level
                for item_code, item_data in section_data.get('items', {}).items():
                    doc_text = f"Item: {item_data['description']} ({item_data['type']}) in {section_data['name']}"
                    documents.append(doc_text)
                    metadatas.append({
                        'level': 'item',
                        'plant_id': plant_id,
                        'section_id': section_id,
                        'item_code': item_code,
                        'description': item_data['description']
                    })
                    ids.append(f"item_{plant_id}_{section_id}_{item_code}")
        
        # Generate embeddings using Gemini
        try:
            embeddings = []
            for doc in documents:
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=doc,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            
            # Store in ChromaDB
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(f"Generated embeddings for {len(documents)} hierarchy items")
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {str(e)}")
    
    async def generate_initial_suggestions(self, session_id: str) -> List[str]:
        """Generate initial suggestions showing all plants"""
        hierarchy = self.structured_data.get('hierarchy', {})
        
        # Get all plants
        plants = [(plant_id, plant_data['name']) for plant_id, plant_data in hierarchy.items()]
        
        # Create natural language suggestions for plants
        suggestions = []
        for plant_id, plant_name in plants:
            suggestions.append(f"Explore {plant_name}")
        
        # Add a visualization suggestion
        suggestions.append("Show me an overview of all facilities")
        
        # Store initial context
        await self._save_to_redis(session_id, 'context', {
            'level': 'START',
            'plant_id': None,
            'section_id': None,
            'item_code': None
        })
        await self._save_to_redis(session_id, 'tree_path', [])
        await self._save_to_redis(session_id, 'history', [])
        
        return suggestions[:5]
    
    async def process_message(self, session_id: str, message: str, is_suggestion: bool) -> Dict[str, Any]:
        """Process message with hierarchical navigation and intelligent context tracking"""
        # Get current context
        context = await self._get_from_redis(session_id, 'context', {
            'level': 'START',
            'plant_id': None,
            'section_id': None,
            'item_code': None,
            'selected_plant_name': None,
            'selected_section_name': None,
            'selected_item_desc': None
        })
        history = await self._get_from_redis(session_id, 'history', [])
        tree_path = await self._get_from_redis(session_id, 'tree_path', [])
        
        # Add message to history
        history.append({
            'role': 'user',
            'message': message,
            'is_suggestion': is_suggestion,
            'timestamp': str(asyncio.get_event_loop().time())
        })
        
        # Add to decision tree path
        tree_path.append(message)
        
        # Parse user intent and update context (with memory of selections)
        new_context = await self._parse_user_intent(message, context)
        
        # Generate response based on new context
        response_data = await self._generate_contextual_response(message, new_context, history, tree_path)
        
        # Add response to history
        history.append({
            'role': 'assistant',
            'message': response_data['response'],
            'suggestions': response_data['suggestions'],
            'chart_data': response_data.get('chart_data'),
            'table_data': response_data.get('table_data'),
            'timestamp': str(asyncio.get_event_loop().time())
        })
        
        # Save updated context and history
        await self._save_to_redis(session_id, 'context', new_context)
        await self._save_to_redis(session_id, 'history', history)
        await self._save_to_redis(session_id, 'tree_path', tree_path)
        
        return {
            'response': response_data['response'],
            'suggestions': response_data['suggestions'],
            'context_path': tree_path,
            'chart_data': response_data.get('chart_data'),
            'table_data': response_data.get('table_data'),
            'metadata': {
                'current_level': new_context['level'],
                'context': new_context,
                'selected_path': f"{new_context.get('selected_plant_name', '')} > {new_context.get('selected_section_name', '')} > {new_context.get('selected_item_desc', '')}"
            }
        }
    
    async def _parse_user_intent(self, message: str, current_context: Dict) -> Dict:
        """Parse user message to determine navigation intent with memory"""
        hierarchy = self.structured_data.get('hierarchy', {})
        
        # Try to find matching entities using embeddings
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=message,
                task_type="retrieval_query"
            )
            query_embedding = result['embedding']
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=3
            )
            
            if results and results['metadatas']:
                best_match = results['metadatas'][0][0]
                
                # Update context based on match
                new_context = current_context.copy()
                
                if best_match['level'] == 'plant':
                    plant_id = best_match['plant_id']
                    plant_data = hierarchy.get(plant_id, {})
                    new_context['level'] = 'PLANT'
                    new_context['plant_id'] = plant_id
                    new_context['selected_plant_name'] = plant_data.get('name', '')
                    new_context['section_id'] = None
                    new_context['selected_section_name'] = None
                    new_context['item_code'] = None
                    new_context['selected_item_desc'] = None
                    
                elif best_match['level'] == 'section':
                    plant_id = best_match['plant_id']
                    section_id = best_match['section_id']
                    plant_data = hierarchy.get(plant_id, {})
                    section_data = plant_data.get('sections', {}).get(section_id, {})
                    new_context['level'] = 'SECTION'
                    new_context['plant_id'] = plant_id
                    new_context['selected_plant_name'] = plant_data.get('name', '')
                    new_context['section_id'] = section_id
                    new_context['selected_section_name'] = section_data.get('name', '')
                    new_context['item_code'] = None
                    new_context['selected_item_desc'] = None
                    
                elif best_match['level'] == 'item':
                    plant_id = best_match['plant_id']
                    section_id = best_match['section_id']
                    item_code = best_match['item_code']
                    plant_data = hierarchy.get(plant_id, {})
                    section_data = plant_data.get('sections', {}).get(section_id, {})
                    item_data = section_data.get('items', {}).get(item_code, {})
                    new_context['level'] = 'ITEM'
                    new_context['plant_id'] = plant_id
                    new_context['selected_plant_name'] = plant_data.get('name', '')
                    new_context['section_id'] = section_id
                    new_context['selected_section_name'] = section_data.get('name', '')
                    new_context['item_code'] = item_code
                    new_context['selected_item_desc'] = item_data.get('description', '')
                
                return new_context
        except Exception as e:
            self.logger.error(f"Error parsing intent: {str(e)}")
        
        # If no clear match, stay at current level or move forward
        return current_context
    
    async def _generate_contextual_response(self, message: str, context: Dict, 
                                           history: List[Dict], tree_path: List[str]) -> Dict[str, Any]:
        """Generate response based on current hierarchical context with intelligent format detection"""
        hierarchy = self.structured_data.get('hierarchy', {})
        level = context.get('level', 'START')
        
        # Use LLM to intelligently detect output format
        output_format = await self._detect_output_format(message, context)
        
        # Generate chart/table based on intelligent detection
        chart_data = None
        table_data = None
        
        if output_format.get('needs_chart'):
            chart_data = await self._generate_chart_data_contextual(message, context)
        
        if output_format.get('needs_table'):
            table_data = await self._generate_table_data_contextual(message, context)
        
        # Generate response based on level
        if level == 'START':
            response_text = await self._generate_start_response(message)
            suggestions = await self._generate_plant_suggestions()
        
        elif level == 'PLANT':
            plant_id = context.get('plant_id')
            plant_data = hierarchy.get(plant_id, {})
            response_text = await self._generate_plant_response(message, plant_data, context)
            suggestions = await self._generate_section_suggestions(plant_id)
        
        elif level == 'SECTION':
            plant_id = context.get('plant_id')
            section_id = context.get('section_id')
            plant_data = hierarchy.get(plant_id, {})
            section_data = plant_data.get('sections', {}).get(section_id, {})
            response_text = await self._generate_section_response(message, plant_data, section_data, context)
            suggestions = await self._generate_item_suggestions(plant_id, section_id)
        
        elif level == 'ITEM':
            plant_id = context.get('plant_id')
            section_id = context.get('section_id')
            item_code = context.get('item_code')
            plant_data = hierarchy.get(plant_id, {})
            section_data = plant_data.get('sections', {}).get(section_id, {})
            item_data = section_data.get('items', {}).get(item_code, {})
            response_text = await self._generate_item_response(message, plant_data, section_data, item_data, context)
            suggestions = await self._generate_detail_suggestions(plant_id, section_id, item_code)
        
        else:
            response_text = "I'm here to help you explore the manufacturing and quality control data. What would you like to know?"
            suggestions = await self._generate_plant_suggestions()
        
        return {
            'response': response_text,
            'suggestions': suggestions,
            'chart_data': chart_data,
            'table_data': table_data
        }
    
    async def _generate_start_response(self, message: str) -> str:
        """Generate response for START level"""
        summary = self.structured_data.get('summary', {})
        
        prompt = f"""
You are a friendly manufacturing data assistant. A user just started a conversation.

User message: {message}

System overview:
- Total plants/facilities: {summary.get('total_plants', 0)}
- Total sections/labs: {summary.get('total_sections', 0)}
- Total items tracked: {summary.get('total_items', 0)}
- Total inspection readings: {summary.get('total_inspection_readings', 0)}

Generate a warm, welcoming response (max 100 words) that:
1. Greets the user naturally
2. Briefly explains what data is available
3. Encourages them to explore a specific facility
4. Is conversational and human-friendly (NO technical database terms)
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self.logger.error(f"Error generating start response: {str(e)}")
            return "Welcome! I can help you explore our manufacturing facilities and quality control data. We track several plants with numerous sections, items, and inspection processes. Which facility would you like to explore first?"
    
    async def _generate_plant_response(self, message: str, plant_data: Dict, context: Dict) -> str:
        """Generate response for PLANT level with context memory"""
        plant_name = plant_data.get('name', 'this facility')
        sections = plant_data.get('sections', {})
        section_names = [s['name'] for s in sections.values()]
        
        # Get total items in this plant
        total_items = sum(len(s.get('items', {})) for s in sections.values())
        
        prompt = f"""
You are a manufacturing data assistant. User selected: {context.get('selected_plant_name', plant_name)}

User message: {message}

Plant Details:
- Name: {plant_name}
- Sections/Buildings: {', '.join(section_names[:8])}
- Total sections: {len(sections)}
- Total items produced: {total_items}

Generate a conversational response (max 150 words) that:
1. Acknowledges their selection of {plant_name}
2. Describes what this facility manufactures
3. Lists key sections/buildings naturally
4. Mentions the scope (items, operations)
5. Encourages exploring specific sections
6. NO database jargon - speak naturally as a guide
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self.logger.error(f"Error generating plant response: {str(e)}")
            return f"You've selected {plant_name}, which has {len(sections)} sections/buildings including {', '.join(section_names[:3])}. We track {total_items} different items here. Which section would you like to explore?"
    
    async def _generate_section_response(self, message: str, plant_data: Dict, section_data: Dict, context: Dict) -> str:
        """Generate response for SECTION level with context memory"""
        plant_name = plant_data.get('name', 'the facility')
        section_name = section_data.get('name', 'this section')
        items = section_data.get('items', {})
        item_descs = [i['description'] for i in items.values()]
        
        # Get total inspection readings
        total_readings = sum(len(i.get('inspection_readings', [])) for i in items.values())
        
        prompt = f"""
You are a manufacturing data assistant. User navigated: {context.get('selected_plant_name')} → {context.get('selected_section_name')}

User message: {message}

Section Details:
- Plant: {plant_name}
- Section/Building: {section_name}
- Items/Products: {', '.join(item_descs[:5])}
- Total items: {len(items)}
- Inspection records: {total_readings}

Generate a natural response (max 150 words) that:
1. Acknowledges they're now viewing {section_name}
2. Describes what this section manufactures
3. Lists items/products clearly
4. Mentions quality control scope
5. Suggests they can view item details, parameters, or inspection data
6. NO technical jargon - friendly guide tone
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self.logger.error(f"Error generating section response: {str(e)}")
            return f"You're now viewing {section_name} at {plant_name}. This section handles {len(items)} items including {', '.join(item_descs[:2])}, with {total_readings} inspection records. Would you like to explore a specific item?"
    
    async def _generate_item_response(self, message: str, plant_data: Dict, section_data: Dict, item_data: Dict) -> str:
        """Generate response for ITEM level"""
        item_desc = item_data.get('description', 'this item')
        item_type = item_data.get('type', '')
        operations = list(item_data.get('operations', {}).values())
        machines = list(item_data.get('machines', {}).values())
        parameters = list(item_data.get('parameters', {}).values())
        inspections = item_data.get('inspection_readings', [])
        
        prompt = f"""
You are a manufacturing data assistant. User is exploring a specific item/product.

User message: {message}

Item: {item_desc} ({item_type})
Operations: {len(operations)} different operations
QC Machines: {len(machines)} machines used
Quality Parameters: {len(parameters)} parameters monitored
Inspection Records: {len(inspections)} readings available

Generate an informative response (max 150 words) that:
1. Describes what this item is
2. Explains the manufacturing/inspection process naturally
3. Mentions key quality checks
4. Offers to show specific data (charts, inspection details)
5. Be conversational - NO database jargon
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self.logger.error(f"Error generating item response: {str(e)}")
            return f"{item_desc} undergoes {len(operations)} operations with {len(parameters)} quality parameters monitored. We have {len(inspections)} inspection readings. Would you like to see quality trends or inspection details?"
    
    async def _generate_plant_suggestions(self) -> List[str]:
        """Generate suggestions for plant selection"""
        hierarchy = self.structured_data.get('hierarchy', {})
        plants = [(plant_id, plant_data['name']) for plant_id, plant_data in hierarchy.items()]
        
        suggestions = []
        for plant_id, plant_name in plants[:4]:
            suggestions.append(f"Explore {plant_name}")
        
        if len(suggestions) < 5:
            suggestions.append("Show me a comparison of all facilities")
        
        return suggestions[:5]
    
    async def _generate_section_suggestions(self, plant_id: str) -> List[str]:
        """Generate suggestions for section selection within a plant"""
        hierarchy = self.structured_data.get('hierarchy', {})
        plant_data = hierarchy.get(plant_id, {})
        sections = plant_data.get('sections', {})
        
        suggestions = []
        for section_id, section_data in list(sections.items())[:3]:
            suggestions.append(f"Show me {section_data['name']}")
        
        suggestions.append(f"What items are produced at {plant_data['name']}?")
        suggestions.append("Show me production overview")
        
        return suggestions[:5]
    
    async def _generate_item_suggestions(self, plant_id: str, section_id: str) -> List[str]:
        """Generate suggestions for item selection within a section"""
        hierarchy = self.structured_data.get('hierarchy', {})
        plant_data = hierarchy.get(plant_id, {})
        section_data = plant_data.get('sections', {}).get(section_id, {})
        items = section_data.get('items', {})
        
        suggestions = []
        for item_code, item_data in list(items.items())[:3]:
            desc = item_data['description']
            # Shorten if too long
            if len(desc) > 40:
                desc = desc[:37] + "..."
            suggestions.append(f"Tell me about {desc}")
        
        suggestions.append("Show quality control data")
        suggestions.append("What inspection parameters are tracked?")
        
        return suggestions[:5]
    
    async def _generate_detail_suggestions(self, plant_id: str, section_id: str, item_code: str) -> List[str]:
        """Generate suggestions for detailed exploration"""
        suggestions = [
            "Show me quality trends over time",
            "What machines are used for inspection?",
            "Display all inspection parameters",
            "Show me recent inspection results",
            "Compare actual vs target values"
        ]
        
        return suggestions[:5]
    
    async def _detect_output_format(self, message: str, context: Dict) -> Dict[str, bool]:
        """Use LLM to intelligently detect if user wants chart, table, or text"""
        level = context.get('level', 'START')
        
        prompt = f"""
You are a data visualization expert. Analyze this user request and determine the BEST output format.

User message: "{message}"
Current context level: {level}

Rules:
1. CHART: Use for trends, comparisons, quality data over time, distributions
2. TABLE: Use for listing multiple items, parameters, detailed records, specifications
3. TEXT: Use for navigation, explanations, descriptions, general questions

Return ONLY a JSON with three boolean flags:
{{"needs_chart": true/false, "needs_table": true/false, "needs_text_only": true/false}}

Examples:
- "Show quality trends" -> {{"needs_chart": true, "needs_table": false, "needs_text_only": false}}
- "List all parameters" -> {{"needs_chart": false, "needs_table": true, "needs_text_only": false}}
- "Tell me about CASE 4" -> {{"needs_chart": false, "needs_table": false, "needs_text_only": true}}
- "Show me section details" -> {{"needs_chart": false, "needs_table": false, "needs_text_only": true}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', result_text)
            if json_match:
                result = json.loads(json_match.group())
                return result
        except Exception as e:
            self.logger.error(f"Error detecting output format: {str(e)}")
        
        # Default: text only
        return {"needs_chart": False, "needs_table": False, "needs_text_only": True}
    
    async def _generate_chart_data_contextual(self, message: str, context: Dict) -> Optional[Dict]:
        """Generate chart based on current context"""
        hierarchy = self.structured_data.get('hierarchy', {})
        level = context.get('level', 'START')
        
        if level == 'ITEM':
            plant_id = context.get('plant_id')
            section_id = context.get('section_id')
            item_code = context.get('item_code')
            
            plant_data = hierarchy.get(plant_id, {})
            section_data = plant_data.get('sections', {}).get(section_id, {})
            item_data = section_data.get('items', {}).get(item_code, {})
            
            inspections = item_data.get('inspection_readings', [])
            
            if inspections:
                # Create quality trend chart
                labels = [f"Reading {i+1}" for i in range(min(10, len(inspections)))]
                actual_values = []
                
                for insp in inspections[:10]:
                    readings = insp.get('actual_readings', [])
                    if readings:
                        if isinstance(readings[0], dict):
                            actual_values.append(int(readings[0].get('accepted', 0)))
                        else:
                            actual_values.append(float(readings[0]) if readings[0] else 0)
                
                return {
                    "type": "line",
                    "title": f"Quality Trend for {item_data.get('description', 'Item')}",
                    "data": {
                        "labels": labels,
                        "datasets": [{
                            "label": "Inspection Values",
                            "data": actual_values,
                            "borderColor": "#36A2EB",
                            "backgroundColor": "rgba(54, 162, 235, 0.2)",
                            "tension": 0.4
                        }]
                    },
                    "options": {
                        "responsive": True,
                        "plugins": {
                            "legend": {"position": "top"},
                            "title": {"display": True, "text": f"Quality Trend"}
                        }
                    }
                }
        
        elif level == 'PLANT':
            plant_id = context.get('plant_id')
            plant_data = hierarchy.get(plant_id, {})
            sections = plant_data.get('sections', {})
            
            # Create section overview chart
            section_names = []
            item_counts = []
            
            for section_id, section_data in list(sections.items())[:8]:
                section_names.append(section_data['name'][:20])
                item_counts.append(len(section_data.get('items', {})))
            
            return {
                "type": "bar",
                "title": f"Sections at {plant_data.get('name', 'Plant')}",
                "data": {
                    "labels": section_names,
                    "datasets": [{
                        "label": "Items per Section",
                        "data": item_counts,
                        "backgroundColor": "#FF6384"
                    }]
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "legend": {"position": "top"},
                        "title": {"display": True, "text": "Items per Section"}
                    }
                }
            }
        
        return None
    
    async def _generate_table_data_contextual(self, message: str, context: Dict) -> Optional[Dict]:
        """Generate table based on current context"""
        hierarchy = self.structured_data.get('hierarchy', {})
        level = context.get('level', 'START')
        
        if level == 'ITEM':
            plant_id = context.get('plant_id')
            section_id = context.get('section_id')
            item_code = context.get('item_code')
            
            plant_data = hierarchy.get(plant_id, {})
            section_data = plant_data.get('sections', {}).get(section_id, {})
            item_data = section_data.get('items', {}).get(item_code, {})
            
            parameters = item_data.get('parameters', {})
            
            if parameters:
                rows = []
                for param_id, param_data in parameters.items():
                    rows.append([
                        param_data.get('name', ''),
                        param_data.get('description', '')
                    ])
                
                return {
                    "title": f"Quality Parameters for {item_data.get('description', 'Item')}",
                    "columns": ["Parameter", "Description"],
                    "rows": rows,
                    "description": "All quality control parameters monitored for this item"
                }
        
        elif level == 'SECTION':
            plant_id = context.get('plant_id')
            section_id = context.get('section_id')
            
            plant_data = hierarchy.get(plant_id, {})
            section_data = plant_data.get('sections', {}).get(section_id, {})
            items = section_data.get('items', {})
            
            rows = []
            for item_code, item_data in items.items():
                rows.append([
                    item_data.get('description', ''),
                    item_data.get('type', ''),
                    str(len(item_data.get('inspection_readings', [])))
                ])
            
            return {
                "title": f"Items in {section_data.get('name', 'Section')}",
                "columns": ["Item", "Type", "Inspection Records"],
                "rows": rows,
                "description": "All items produced in this section"
            }
        
        return None
    
    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history"""
        return await self._get_from_redis(session_id, 'history', [])
    
    async def get_decision_tree(self, session_id: str) -> List[str]:
        """Get decision tree path"""
        return await self._get_from_redis(session_id, 'tree_path', [])
    
    async def reset_session(self, session_id: str):
        """Reset session"""
        await self.redis_client.delete(f"{session_id}:history")
        await self.redis_client.delete(f"{session_id}:tree_path")
        await self.redis_client.delete(f"{session_id}:context")
    
    async def _save_to_redis(self, session_id: str, key: str, data: Any):
        """Save to Redis"""
        redis_key = f"{session_id}:{key}"
        await self.redis_client.set(redis_key, json.dumps(data))
        await self.redis_client.expire(redis_key, 86400)
    
    async def _get_from_redis(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get from Redis"""
        redis_key = f"{session_id}:{key}"
        data = await self.redis_client.get(redis_key)
        if data:
            return json.loads(data)
        return default

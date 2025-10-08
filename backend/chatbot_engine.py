import json
import logging
from typing import Dict, List, Any, Optional
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
import hashlib
import asyncio


class ChatbotEngine:
    """Main chatbot engine with LLM, embeddings, and memory"""
    
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
    
    async def initialize(self):
        """Initialize the chatbot engine"""
        # Initialize ChromaDB
        self.chroma_client = chromadb.Client(Settings(
            allow_reset=True,
            is_persistent=False
        ))
        
        # Create or get collection
        try:
            self.collection = self.chroma_client.get_collection(name="schema_embeddings")
        except:
            self.collection = self.chroma_client.create_collection(name="schema_embeddings")
        
        # Generate and store embeddings for schema
        await self._generate_schema_embeddings()
        
        self.logger.info("Chatbot engine initialized")
    
    async def _generate_schema_embeddings(self):
        """Generate embeddings for all tables and store in ChromaDB"""
        tables = self.structured_data.get('tables', {})
        
        documents = []
        metadatas = []
        ids = []
        
        for table_name, table_info in tables.items():
            # Create document text for embedding
            doc_text = f"Table: {table_name}\n"
            doc_text += f"Columns: {', '.join(table_info.get('columns', []))}\n"
            doc_text += f"Records: {table_info.get('records', 0)}\n"
            
            if table_info.get('references'):
                refs = ', '.join([f"{r['table']} via {r['via']}" for r in table_info['references']])
                doc_text += f"References: {refs}\n"
            
            if table_info.get('referenced_by'):
                refs = ', '.join([f"{r['table']} via {r['via']}" for r in table_info['referenced_by']])
                doc_text += f"Referenced by: {refs}\n"
            
            documents.append(doc_text)
            metadatas.append({
                'table_name': table_name,
                'type': 'table_schema'
            })
            ids.append(hashlib.md5(table_name.encode()).hexdigest())
        
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
            
            self.logger.info(f"Generated embeddings for {len(documents)} tables")
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {str(e)}")
    
    async def generate_initial_suggestions(self, session_id: str) -> List[str]:
        """Generate 5 initial suggestions based on the dataset"""
        categories = self.structured_data.get('categories', {})
        
        # Create prompt for LLM
        prompt = f"""
You are an intelligent data assistant helping users explore a Quality Control and Manufacturing Management database.

Database Overview:
{json.dumps(categories, indent=2)}

Total Tables: {self.structured_data.get('total_tables', 0)}

Generate 5 intelligent, diverse suggestions for what a user might want to explore or ask about this database.
These should be actionable questions or exploration paths that help users understand the data.

Format your response as a JSON array of exactly 5 strings.
Example: ["suggestion 1", "suggestion 2", "suggestion 3", "suggestion 4", "suggestion 5"]

Make suggestions specific, relevant, and varied. Cover different aspects of the database.
"""
        
        try:
            response = self.model.generate_content(prompt)
            suggestions_text = response.text.strip()
            
            # Parse JSON response
            suggestions_text = suggestions_text.replace('```json', '').replace('```', '').strip()
            suggestions = json.loads(suggestions_text)
            
            # Store initial state
            await self._save_to_redis(session_id, 'tree_path', [])
            await self._save_to_redis(session_id, 'history', [])
            
            return suggestions[:5]  # Ensure we return exactly 5
        except Exception as e:
            self.logger.error(f"Error generating initial suggestions: {str(e)}")
            # Fallback suggestions
            return [
                "Show me all inspection-related tables and their relationships",
                "What are the main quality control parameters being tracked?",
                "Explain the production planning workflow",
                "How is user access and permissions managed?",
                "What machine data is being tracked?"
            ]
    
    async def process_message(self, session_id: str, message: str, is_suggestion: bool) -> Dict[str, Any]:
        """Process user message and generate response with new suggestions"""
        # Get current context
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
        
        # Find relevant tables using embeddings
        relevant_tables = await self._find_relevant_tables(message)
        
        # Check if user wants a chart
        chart_data = None
        if self._is_chart_request(message):
            chart_data = await self._generate_chart_data(message, relevant_tables)
        
        # Generate response using LLM
        response_text = await self._generate_response(message, relevant_tables, history, tree_path, chart_data)
        
        # Generate next suggestions
        suggestions = await self._generate_next_suggestions(message, response_text, relevant_tables, tree_path)
        
        # Add response to history
        history.append({
            'role': 'assistant',
            'message': response_text,
            'suggestions': suggestions,
            'chart_data': chart_data,
            'timestamp': str(asyncio.get_event_loop().time())
        })
        
        # Save to Redis
        await self._save_to_redis(session_id, 'history', history)
        await self._save_to_redis(session_id, 'tree_path', tree_path)
        
        return {
            'response': response_text,
            'suggestions': suggestions,
            'context_path': tree_path,
            'chart_data': chart_data,
            'metadata': {
                'relevant_tables': relevant_tables
            }
        }
    
    async def _find_relevant_tables(self, query: str) -> List[str]:
        """Find relevant tables using embedding similarity search"""
        try:
            # Generate query embedding
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=query,
                task_type="retrieval_query"
            )
            query_embedding = result['embedding']
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=5
            )
            
            if results and results['metadatas']:
                return [meta['table_name'] for meta in results['metadatas'][0]]
            return []
        except Exception as e:
            self.logger.error(f"Error finding relevant tables: {str(e)}")
            return []
    
    async def _generate_response(self, query: str, relevant_tables: List[str], 
                                  history: List[Dict], tree_path: List[str], chart_data: Optional[Dict] = None) -> str:
        """Generate response using LLM"""
        # Build context about relevant tables
        tables_context = ""
        for table_name in relevant_tables:
            table_info = self.structured_data['tables'].get(table_name, {})
            tables_context += f"\nTable: {table_name}\n"
            tables_context += f"Columns: {', '.join(table_info.get('columns', []))}\n"
            if table_info.get('references'):
                tables_context += f"References: {json.dumps(table_info['references'])}\n"
        
        prompt = f"""
You are an intelligent data assistant helping users explore a Quality Control and Manufacturing Management database.

Conversation History:
{json.dumps(tree_path[-3:], indent=2) if len(tree_path) > 0 else 'New conversation'}

Relevant Database Tables:
{tables_context}

User Query: {query}

Provide a helpful, informative response that:
1. Directly answers the user's question
2. References specific tables and data when relevant
3. Explains relationships between tables if applicable
4. Is conversational and easy to understand
5. Highlights insights or patterns in the data structure

Keep your response focused and under 150 words.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I encountered an error processing your question. Could you please rephrase it?"
    
    async def _generate_next_suggestions(self, query: str, response: str, 
                                          relevant_tables: List[str], tree_path: List[str]) -> List[str]:
        """Generate 5 next suggestions based on conversation context"""
        prompt = f"""
You are an intelligent data assistant. Based on the current conversation, generate 5 smart follow-up suggestions.

Conversation Path: {' -> '.join(tree_path[-3:]) if tree_path else 'Starting'}
Last Question: {query}
Last Response: {response}
Relevant Tables: {', '.join(relevant_tables)}

Generate 5 diverse, actionable follow-up questions or exploration paths that:
1. Build on the current context
2. Explore deeper into the current topic
3. Connect to related areas
4. Help users discover new insights
5. Are specific and clear

Format your response as a JSON array of exactly 5 strings.
Example: ["suggestion 1", "suggestion 2", "suggestion 3", "suggestion 4", "suggestion 5"]
"""
        
        try:
            response_obj = self.model.generate_content(prompt)
            suggestions_text = response_obj.text.strip()
            
            # Parse JSON response
            suggestions_text = suggestions_text.replace('```json', '').replace('```', '').strip()
            suggestions = json.loads(suggestions_text)
            
            return suggestions[:5]
        except Exception as e:
            self.logger.error(f"Error generating suggestions: {str(e)}")
            # Fallback suggestions based on relevant tables
            if relevant_tables:
                return [
                    f"Tell me more about {relevant_tables[0]}",
                    f"How does {relevant_tables[0]} relate to other tables?",
                    "What are the key metrics I can track?",
                    "Show me data quality insights",
                    "Start a different exploration"
                ]
            return [
                "Explore inspection data",
                "Look at production planning",
                "Check user management",
                "Review machine operations",
                "Start over"
            ]
    
    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session"""
        return await self._get_from_redis(session_id, 'history', [])
    
    async def get_decision_tree(self, session_id: str) -> List[str]:
        """Get decision tree path for a session"""
        return await self._get_from_redis(session_id, 'tree_path', [])
    
    async def reset_session(self, session_id: str):
        """Reset a chat session"""
        await self.redis_client.delete(f"{session_id}:history")
        await self.redis_client.delete(f"{session_id}:tree_path")
    
    async def _save_to_redis(self, session_id: str, key: str, data: Any):
        """Save data to Redis"""
        redis_key = f"{session_id}:{key}"
        await self.redis_client.set(redis_key, json.dumps(data))
        # Set expiration to 24 hours
        await self.redis_client.expire(redis_key, 86400)
    
    async def _get_from_redis(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get data from Redis"""
        redis_key = f"{session_id}:{key}"
        data = await self.redis_client.get(redis_key)
        if data:
            return json.loads(data)
        return default

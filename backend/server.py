from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import json
import redis.asyncio as aioredis

from chatbot_engine import ChatbotEngine
from data_loader import DataLoader

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Redis connection
redis_client = None

# Initialize chatbot engine
chatbot_engine = None

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class ChatMessage(BaseModel):
    session_id: str
    message: str
    is_suggestion: bool = False

class ChatResponse(BaseModel):
    session_id: str
    response: str
    suggestions: List[str]
    context_path: List[str]
    chart_data: Optional[Dict[str, Any]] = None
    table_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class InitializeRequest(BaseModel):
    session_id: Optional[str] = None

class InitializeResponse(BaseModel):
    session_id: str
    suggestions: List[str]
    message: str

class HistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]]

class TreeResponse(BaseModel):
    session_id: str
    tree_path: List[str]


@app.on_event("startup")
async def startup_event():
    global redis_client, chatbot_engine
    
    # Initialize Redis
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    redis_client = await aioredis.from_url(redis_url, decode_responses=True)
    
    # Load the database schema
    schema_path = ROOT_DIR / 'database_schema.txt'
    data_loader = DataLoader(str(schema_path))
    structured_data = data_loader.load_and_structure()
    
    # Initialize chatbot engine
    gemini_api_key = os.environ['GEMINI_API_KEY']
    chatbot_engine = ChatbotEngine(gemini_api_key, redis_client, structured_data)
    await chatbot_engine.initialize()
    
    logging.info("Chatbot engine initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    global redis_client
    if redis_client:
        await redis_client.close()
    client.close()


# Routes
@api_router.get("/")
async def root():
    return {"message": "Intelligent Chatbot API is running"}


@api_router.post("/chat/initialize", response_model=InitializeResponse)
async def initialize_chat(request: InitializeRequest):
    """
    Initialize a new chat session and get initial suggestions
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        # Generate initial suggestions
        suggestions = await chatbot_engine.generate_initial_suggestions(session_id)
        
        return InitializeResponse(
            session_id=session_id,
            suggestions=suggestions,
            message="Chat session initialized. Here are some suggestions to get started."
        )
    except Exception as e:
        logging.error(f"Error initializing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/chat/message", response_model=ChatResponse)
async def send_message(message_data: ChatMessage):
    """
    Send a message and get response with new suggestions
    """
    try:
        response = await chatbot_engine.process_message(
            message_data.session_id,
            message_data.message,
            message_data.is_suggestion
        )
        
        return ChatResponse(
            session_id=message_data.session_id,
            response=response['response'],
            suggestions=response['suggestions'],
            context_path=response['context_path'],
            chart_data=response.get('chart_data'),
            table_data=response.get('table_data'),
            metadata=response.get('metadata')
        )
    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/chat/history/{session_id}", response_model=HistoryResponse)
async def get_chat_history(session_id: str):
    """
    Get chat history for a session
    """
    try:
        messages = await chatbot_engine.get_history(session_id)
        return HistoryResponse(
            session_id=session_id,
            messages=messages
        )
    except Exception as e:
        logging.error(f"Error getting history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/chat/tree/{session_id}", response_model=TreeResponse)
async def get_decision_tree(session_id: str):
    """
    Get the decision tree path for a session
    """
    try:
        tree_path = await chatbot_engine.get_decision_tree(session_id)
        return TreeResponse(
            session_id=session_id,
            tree_path=tree_path
        )
    except Exception as e:
        logging.error(f"Error getting decision tree: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/chat/reset/{session_id}")
async def reset_chat(session_id: str):
    """
    Reset a chat session
    """
    try:
        await chatbot_engine.reset_session(session_id)
        return {"message": "Session reset successfully"}
    except Exception as e:
        logging.error(f"Error resetting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

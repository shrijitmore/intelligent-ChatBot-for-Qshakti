"""
In-memory session store as Redis alternative
"""
import json
from typing import Any, Optional
from datetime import datetime, timedelta
import asyncio


class InMemorySessionStore:
    """Simple in-memory session store with TTL support"""
    
    def __init__(self):
        self.data = {}
        self.expiry = {}
    
    async def set(self, key: str, value: str):
        """Set a key-value pair"""
        self.data[key] = value
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value by key"""
        # Check if expired
        if key in self.expiry and datetime.now() > self.expiry[key]:
            await self.delete(key)
            return None
        return self.data.get(key)
    
    async def delete(self, key: str):
        """Delete a key"""
        if key in self.data:
            del self.data[key]
        if key in self.expiry:
            del self.expiry[key]
    
    async def expire(self, key: str, seconds: int):
        """Set expiry time for a key"""
        self.expiry[key] = datetime.now() + timedelta(seconds=seconds)
    
    async def close(self):
        """Close connection (no-op for in-memory)"""
        pass
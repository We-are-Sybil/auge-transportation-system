"""Redis manager for caching and sessions"""
import json
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from ..config import db_config

class RedisManager:
    def __init__(self):
        self.redis = None

    async def connect(self):
        """Connect to Redis"""
        self.redis = redis.from_url(
            db_config.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20
        )

    async def ping(self) -> str:
        """Test Redis connection"""
        if not self.redis:
            await self.connect()
        return await self.redis.ping()

    async def set_with_ttl(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set key with TTL (default 5 minutes)"""
        if not self.redis:
            await self.connect()
        
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        return await self.redis.setex(key, ttl_seconds, value)

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self.redis:
            await self.connect()
        return await self.redis.get(key)

    async def get_json(self, key: str) -> Optional[Dict]:
        """Get JSON value by key"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def save_session(self, user_id: str, session_data: Dict[str, Any], ttl_hours: int = 24):
        """Save conversation session"""
        key = f"session:{user_id}"
        session_data["last_updated"] = datetime.now().isoformat()
        ttl_seconds = ttl_hours * 3600
        return await self.set_with_ttl(key, session_data, ttl_seconds)

    async def get_session(self, user_id: str) -> Optional[Dict]:
        """Get conversation session"""
        key = f"session:{user_id}"
        return await self.get_json(key)

    async def delete(self, key: str) -> bool:
        """Delete key"""
        if not self.redis:
            await self.connect()
        return bool(await self.redis.delete(key))

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.aclose()

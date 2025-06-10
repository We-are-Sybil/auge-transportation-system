import logging
import sys
import os
import json
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.database.manager import DatabaseManager
from src.database.redis_manager import RedisManager
from src.database.models import MessageRole, ConversationStep
from src.webhook_service.whatsapp_models import (
    WhatsAppWebhook, ProcessedWhatsAppMessage, WhatsAppMessage, WhatsAppMessageType
)
from src.webhook_service.session_models import ConversationState, ConversationStage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Transportation Webhook Service", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    db = DatabaseManager()
    await db.init_tables()
    await db.close()
    logger.info("✅ Database tables initialized")

# Database dependency
async def get_db():
    db = DatabaseManager()
    try:
        yield db
    finally:
        await db.close()

# Redis dependency
async def get_redis():
    redis_mgr = RedisManager()
    try:
        yield redis_mgr
    finally:
        await redis_mgr.close()

class WebhookResponse(BaseModel):
    status: str
    timestamp: str
    message: str

class ConversationCreate(BaseModel):
    user_id: str
    session_id: str

class MessageCreate(BaseModel):
    session_id: int
    role: str
    content: str

class SessionData(BaseModel):
    user_id: str
    data: Dict[str, Any]

class SessionCreate(BaseModel):
    user_id: str
    session_data: Dict[str, Any]

@app.get("/webhook")
async def webhook_verification(
    request: Request,
    hub_mode: str = None,
    hub_verify_token: str = None, 
    hub_challenge: str = None
):
    """WhatsApp webhook verification (GET)"""
    # Get query parameters (FastAPI style and fallback)
    mode = hub_mode or request.query_params.get('hub.mode')
    token = hub_verify_token or request.query_params.get('hub.verify_token') 
    challenge = hub_challenge or request.query_params.get('hub.challenge')
    
    logger.info(f"🔍 Webhook verification - Mode: {mode}")
    
    VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        logger.info("✅ WEBHOOK_VERIFIED")
        return PlainTextResponse(content=challenge, status_code=200)
    else:
        logger.warning("❌ VERIFICATION_FAILED")
        raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook", response_model=WebhookResponse)
async def webhook_endpoint(
    request: Request, 
    db: DatabaseManager = Depends(get_db),
    redis: RedisManager = Depends(get_redis)
):
    """WhatsApp webhook endpoint with proper parsing"""
    try:
        body = await request.body()
        logger.info(f"Webhook received: {len(body)} bytes")
        
        # Parse WhatsApp webhook
        if body:
            webhook_data = await request.json()
            try:
                whatsapp_webhook = WhatsAppWebhook(**webhook_data)
                processed_messages = process_whatsapp_webhook(whatsapp_webhook)
                
                logger.info(f"Processed {len(processed_messages)} WhatsApp messages")
                
                # Store messages with enhanced session state
                for msg in processed_messages:
                    # Get or create conversation state
                    existing_state = await redis.get_session(msg.sender)
                    
                    if existing_state:
                        conv_state = ConversationState(**existing_state)
                    else:
                        conv_state = ConversationState(user_id=msg.sender)
                    
                    # Update state with new message
                    conv_state.update_message(msg.content)
                    
                    # Basic intent detection for stage progression
                    if any(word in msg.content.lower() for word in ["hola", "hi", "hello"]):
                        conv_state.set_stage(ConversationStage.GREETING)
                    elif any(word in msg.content.lower() for word in ["transporte", "taxi", "servicio"]):
                        conv_state.set_stage(ConversationStage.COLLECTING_INFO)
                    
                    # Save updated state to Redis
                    await redis.save_session(msg.sender, conv_state.model_dump(), 24)
                    
                    # Save to database
                    conv_id = await db.get_or_create_conversation(msg.sender)
                    message_id = await db.add_message(
                        conv_id, 
                        MessageRole.USER, 
                        msg.content,
                        json.dumps({
                            "whatsapp_message_id": msg.message_id, 
                            "sender_name": msg.sender_name,
                            "conversation_stage": conv_state.stage.value
                        })
                    )
                    
                    logger.info(f"Message from {msg.sender_name or msg.sender}: {msg.content}")
                    logger.info(f"State: {conv_state.stage.value}, Messages: {conv_state.message_count}")
                
                return WebhookResponse(
                    status="success",
                    timestamp=datetime.now().isoformat(),
                    message=f"Processed {len(processed_messages)} WhatsApp messages"
                )
                
            except Exception as e:
                logger.error(f"WhatsApp parsing error: {e}")
                # Fall back to basic logging
                logger.info(f"Raw webhook data: {webhook_data}")
        
        return WebhookResponse(
            status="success",
            timestamp=datetime.now().isoformat(),
            message="Webhook received"
        )
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return WebhookResponse(
            status="error",
            timestamp=datetime.now().isoformat(),
            message=f"Error: {str(e)}"
        )

def process_whatsapp_webhook(webhook: WhatsAppWebhook) -> List[ProcessedWhatsAppMessage]:
    """Process WhatsApp webhook and extract messages"""
    processed_messages = []
    
    for entry in webhook.entry:
        for change in entry.changes:
            if change.field == "messages":
                # Extract contacts for name mapping
                contacts = {c.wa_id: c.profile.name for c in change.value.contacts}
                
                # Process messages
                for message in change.value.messages:
                    if message.text:  # Only handle text messages for now
                        processed_msg = ProcessedWhatsAppMessage(
                            message_id=message.id,
                            sender=message.from_,  # Fix: use from_ field
                            content=message.text.body,
                            sender_name=contacts.get(message.from_),  # Fix: use from_ field  
                            timestamp=message.timestamp,
                            message_type=message.type
                        )
                        processed_messages.append(processed_msg)
    
    return processed_messages

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"service": "Transportation Webhook", "status": "running"}

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/db/test")
async def test_database(db: DatabaseManager = Depends(get_db)):
    """Test database connection"""
    try:
        version = await db.test_connection()
        records = await db.get_test_records()
        return {
            "database": version.split(',')[0],
            "test_records": len(records),
            "status": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/redis/test")
async def test_redis(redis: RedisManager = Depends(get_redis)):
    """Test Redis connection"""
    try:
        ping_result = await redis.ping()
        await redis.set_with_ttl("test_key", "test_value", 60)
        value = await redis.get("test_key")
        return {
            "redis": "connected",
            "ping": ping_result,
            "test_value": value,
            "status": "working"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversations")
async def create_conversation(conv: ConversationCreate, db: DatabaseManager = Depends(get_db)):
    """Create new conversation session"""
    try:
        session_id = await db.create_conversation_session(conv.user_id, conv.session_id)
        return {"session_id": session_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/messages")
async def add_message(msg: MessageCreate, db: DatabaseManager = Depends(get_db)):
    """Add message to conversation"""
    try:
        # Convert string role to enum
        role = MessageRole(msg.role)
        message_id = await db.add_message(msg.session_id, role, msg.content)
        return {"message_id": message_id, "status": "created"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role. Use: user, assistant, system")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions")
async def create_session(session: SessionCreate, redis: RedisManager = Depends(get_redis)):
    """Create/update session in Redis"""
    try:
        success = await redis.save_session(session.user_id, session.session_data)
        return {"user_id": session.user_id, "status": "saved", "success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{user_id}")
async def get_session(user_id: str, redis: RedisManager = Depends(get_redis)):
    """Get session from Redis"""
    try:
        session_data = await redis.get_session(user_id)
        if session_data:
            return {"user_id": user_id, "data": session_data, "status": "found"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

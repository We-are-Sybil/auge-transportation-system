import logging
import sys
import os
import json
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.database.manager import DatabaseManager
from src.database.redis_manager import RedisManager
from src.kafka_service import KafkaProducerService
from src.webhook_service.whatsapp_models import (
    WhatsAppWebhook, ProcessedWhatsAppMessage, WhatsAppMessage, WhatsAppMessageType
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Transportation Webhook Service", version="1.0.0")

# Global Kafka producer
kafka_producer = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global kafka_producer
    
    # Initialize database (for health checks and legacy API endpoints)
    db = DatabaseManager()
    await db.init_tables()
    await db.close()
    logger.info("✅ Database tables initialized")
    
    # Initialize Kafka producer
    kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_producer = KafkaProducerService(kafka_bootstrap)
    await kafka_producer.start()
    logger.info("✅ Kafka producer initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global kafka_producer
    if kafka_producer:
        await kafka_producer.stop()
        logger.info("✅ Kafka producer stopped")

# Database dependency (for legacy API endpoints)
async def get_db():
    db = DatabaseManager()
    try:
        yield db
    finally:
        await db.close()

# Redis dependency (for legacy API endpoints)
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
    kafka_sent: bool = False

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
async def webhook_endpoint(request: Request):
    """WhatsApp webhook endpoint - simplified to just parse and send to Kafka"""
    global kafka_producer
    
    try:
        body = await request.body()
        logger.info(f"Webhook received: {len(body)} bytes")
        
        kafka_sent = False
        processed_count = 0
        
        # Parse WhatsApp webhook
        if body:
            webhook_data = await request.json()
            try:
                whatsapp_webhook = WhatsAppWebhook(**webhook_data)
                processed_messages = process_whatsapp_webhook(whatsapp_webhook)
                processed_count = len(processed_messages)
                
                logger.info(f"Parsed {processed_count} WhatsApp messages")
                
                # Send each message to Kafka - consumer will handle processing
                for msg in processed_messages:
                    # Prepare message data for Kafka
                    message_data = {
                        "message_id": msg.message_id,
                        "sender": msg.sender,
                        "content": msg.content,
                        "sender_name": msg.sender_name,
                        "timestamp": msg.timestamp,
                        "message_type": msg.message_type.value
                    }
                    
                    # Send to Kafka
                    if kafka_producer:
                        success = await kafka_producer.send_webhook_message(message_data)
                        if success:
                            kafka_sent = True
                            logger.info(f"📤 Message sent to Kafka: {msg.sender} -> {msg.content[:50]}...")
                        else:
                            logger.error(f"❌ Failed to send message to Kafka: {msg.message_id}")
                
                return WebhookResponse(
                    status="success",
                    timestamp=datetime.now().isoformat(),
                    message=f"Processed {processed_count} messages, sent to Kafka for processing",
                    kafka_sent=kafka_sent
                )
                
            except Exception as e:
                logger.error(f"WhatsApp parsing error: {e}")
                return WebhookResponse(
                    status="error",
                    timestamp=datetime.now().isoformat(),
                    message=f"Parse error: {str(e)}",
                    kafka_sent=False
                )
        
        return WebhookResponse(
            status="success",
            timestamp=datetime.now().isoformat(),
            message="Webhook received - no messages",
            kafka_sent=False
        )
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return WebhookResponse(
            status="error",
            timestamp=datetime.now().isoformat(),
            message=f"Error: {str(e)}",
            kafka_sent=False
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
                            sender=message.from_,
                            content=message.text.body,
                            sender_name=contacts.get(message.from_),
                            timestamp=message.timestamp,
                            message_type=message.type
                        )
                        processed_messages.append(processed_msg)
    
    return processed_messages

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"service": "Transportation Webhook", "status": "running", "role": "webhook_receiver"}

@app.get("/health")
async def health():
    """Health check with Kafka status"""
    global kafka_producer
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "role": "webhook_receiver",
        "services": {}
    }
    
    # Check Kafka
    if kafka_producer:
        kafka_health = await kafka_producer.health_check()
        health_status["services"]["kafka"] = kafka_health
    else:
        health_status["services"]["kafka"] = {"status": "not_initialized"}
    
    return health_status

@app.get("/kafka/test")
async def test_kafka():
    """Test Kafka producer"""
    global kafka_producer
    
    if not kafka_producer:
        raise HTTPException(status_code=503, detail="Kafka producer not initialized")
    
    try:
        # Send test message
        test_data = {
            "test_id": "webhook_test",
            "content": "Webhook Kafka test message",
            "timestamp": datetime.now().isoformat(),
            "sender": "webhook_service",
            "message_type": "text"
        }
        
        success = await kafka_producer.send_webhook_message(test_data)
        
        if success:
            return {"kafka": "working", "test_sent": True, "status": "healthy"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send test message")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API models
class ConversationCreate(BaseModel):
    user_id: str
    session_id: str

class MessageCreate(BaseModel):
    session_id: int
    role: str
    content: str

class SessionCreate(BaseModel):
    user_id: str
    session_data: Dict[str, Any]

# Quotation API models
class QuotationRequestCreate(BaseModel):
    client_cc_nit: str
    nombre_solicitante: str
    celular_contacto: str
    quien_solicita: str
    fecha_inicio_servicio: str  # ISO format
    hora_inicio_servicio: str
    direccion_inicio: str
    direccion_terminacion: Optional[str] = None
    caracteristicas_servicio: str
    cantidad_pasajeros: int
    equipaje_carga: bool = False
    user_id: Optional[str] = None

class QuotationResponseCreate(BaseModel):
    request_id: int
    precio_base: float
    precio_total: float
    condiciones_servicio: str
    condiciones_pago: str

# Quotation endpoints
@app.post("/api/quotations/requests")
async def create_quotation_request(
    quotation: QuotationRequestCreate, 
    db: DatabaseManager = Depends(get_db)
):
    """Create quotation request and send to Kafka"""
    global kafka_producer
    
    try:
        from datetime import datetime
        import uuid
        
        # Create client if doesn't exist
        existing_client = await db.get_client_by_cc_nit(quotation.client_cc_nit)
        if not existing_client:
            client_id = await db.create_client(
                quotation.client_cc_nit,
                quotation.nombre_solicitante,
                quotation.celular_contacto
            )
        else:
            # Get existing client ID
            from src.database.models import Client
            async with db.get_session() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(Client).where(Client.cc_nit == quotation.client_cc_nit)
                )
                client = result.scalar_one()
                client_id = client.id

        # Generate form number
        form_number = f"FORM-{int(datetime.now().timestamp())}"
        
        # Parse service date
        service_date = datetime.fromisoformat(quotation.fecha_inicio_servicio.replace('Z', '+00:00'))
        
        # Create quotation request in database
        request_id = await db.create_quotation_request(
            form_number=form_number,
            client_id=client_id,
            quien_solicita=quotation.quien_solicita,
            fecha_inicio_servicio=service_date,
            hora_inicio_servicio=quotation.hora_inicio_servicio,
            direccion_inicio=quotation.direccion_inicio,
            direccion_terminacion=quotation.direccion_terminacion,
            caracteristicas_servicio=quotation.caracteristicas_servicio,
            cantidad_pasajeros=quotation.cantidad_pasajeros,
            equipaje_carga=quotation.equipaje_carga
        )
        
        logger.info(f"✅ Quotation request created in DB: {request_id}")
        
        # Send to Kafka
        if kafka_producer:
            event_data = {
                "request_id": request_id,
                "form_number": form_number,
                "client_id": client_id,
                "quien_solicita": quotation.quien_solicita,
                "fecha_inicio_servicio": service_date.isoformat(),
                "hora_inicio_servicio": quotation.hora_inicio_servicio,
                "direccion_inicio": quotation.direccion_inicio,
                "direccion_terminacion": quotation.direccion_terminacion,
                "caracteristicas_servicio": quotation.caracteristicas_servicio,
                "cantidad_pasajeros": quotation.cantidad_pasajeros,
                "equipaje_carga": quotation.equipaje_carga,
                "user_id": quotation.user_id
            }
            
            kafka_sent = await kafka_producer.send_quotation_request_event(event_data)
            logger.info(f"📤 Quotation request sent to Kafka: {kafka_sent}")
        else:
            kafka_sent = False
        
        return {
            "request_id": request_id,
            "form_number": form_number,
            "status": "created",
            "kafka_sent": kafka_sent
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating quotation request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/quotations/responses")
async def create_quotation_response(response: QuotationResponseCreate):
    """Generate quotation response and send to Kafka"""
    global kafka_producer
    
    try:
        import uuid
        
        # Generate quotation ID (in real app, this would be from database)
        quotation_id = int(datetime.now().timestamp())
        
        logger.info(f"✅ Quotation response generated: {quotation_id}")
        
        # Send to Kafka
        if kafka_producer:
            event_data = {
                "request_id": response.request_id,
                "quotation_id": quotation_id,
                "version": 1,
                "precio_base": str(response.precio_base),
                "precio_total": str(response.precio_total),
                "condiciones_servicio": response.condiciones_servicio,
                "condiciones_pago": response.condiciones_pago,
                "sent_to": "api_user",
                "delivery_method": "api"
            }
            
            kafka_sent = await kafka_producer.send_quotation_response_event(event_data)
            logger.info(f"📤 Quotation response sent to Kafka: {kafka_sent}")
        else:
            kafka_sent = False
        
        return {
            "quotation_id": quotation_id,
            "request_id": response.request_id,
            "precio_total": response.precio_total,
            "status": "sent",
            "kafka_sent": kafka_sent
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating quotation response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/quotations/{quotation_id}/accept")
async def accept_quotation(quotation_id: int, billing_data: Dict[str, Any] = None):
    """Accept quotation and send confirmation to Kafka"""
    global kafka_producer
    
    try:
        logger.info(f"✅ Quotation accepted: {quotation_id}")
        
        # Send to Kafka
        if kafka_producer:
            event_data = {
                "quotation_id": quotation_id,
                "request_id": quotation_id - 1000,  # Mock relationship
                "decision": "accepted",
                "confirmed_by": "API User",
                "billing_data": billing_data or {
                    "facturar_a_nombre": "Test Company",
                    "nit_facturacion": "123456789-0",
                    "email_facturacion": "test@company.com"
                },
                "service_order_id": f"SO-{quotation_id}"
            }
            
            kafka_sent = await kafka_producer.send_quotation_confirmation_event(event_data)
            logger.info(f"📤 Quotation confirmation sent to Kafka: {kafka_sent}")
        else:
            kafka_sent = False
        
        return {
            "quotation_id": quotation_id,
            "status": "accepted",
            "service_order_id": f"SO-{quotation_id}",
            "kafka_sent": kafka_sent
        }
        
    except Exception as e:
        logger.error(f"❌ Error accepting quotation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Legacy API endpoints (keep for backward compatibility and testing)
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
        from src.database.models import MessageRole
        session_id = await db.create_conversation_session(conv.user_id, conv.session_id)
        return {"session_id": session_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/messages")
async def add_message(msg: MessageCreate, db: DatabaseManager = Depends(get_db)):
    """Add message to conversation"""
    try:
        from src.database.models import MessageRole
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

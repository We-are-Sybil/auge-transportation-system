import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

# Import database and Redis managers
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.manager import DatabaseManager
from src.database.redis_manager import RedisManager
from src.database.models import MessageRole, ConversationStep
from src.webhook_service.session_models import ConversationState, ConversationStage

logger = logging.getLogger(__name__)

class KafkaConsumerService:
    """Async Kafka consumer for transportation events with database integration"""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092", group_id: str = "transportation_processors"):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False
        self.message_handlers = {}
        
        # Database and Redis managers
        self.db_manager = DatabaseManager()
        self.redis_manager = RedisManager()
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register message handler for specific event type"""
        self.message_handlers[event_type] = handler
        logger.info(f"📝 Registered handler for: {event_type}")
    
    async def start(self, topics: list):
        """Start Kafka consumer"""
        if self.running:
            return
        
        self.consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset='earliest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            enable_auto_commit=True,
            auto_commit_interval_ms=1000
        )
        
        try:
            await self.consumer.start()
            
            # Initialize database
            await self.db_manager.init_tables()
            
            self.running = True
            logger.info(f"✅ Kafka consumer started: {topics}")
            logger.info("✅ Database initialized for consumer")
        except Exception as e:
            logger.error(f"❌ Failed to start Kafka consumer: {e}")
            raise
    
    async def stop(self):
        """Stop Kafka consumer"""
        if self.consumer and self.running:
            await self.consumer.stop()
            await self.db_manager.close()
            await self.redis_manager.close()
            self.running = False
            logger.info("🛑 Kafka consumer stopped")
    
    async def consume_messages(self):
        """Main consumption loop"""
        if not self.running:
            logger.error("Consumer not started")
            return
        
        logger.info("🔄 Starting message consumption loop...")
        
        try:
            async for message in self.consumer:
                await self.process_message(message)
        except Exception as e:
            logger.error(f"❌ Error in consumption loop: {e}")
            raise
    
    async def process_message(self, message):
        """Process individual message"""
        try:
            message_data = message.value
            event_type = message_data.get("event_type", "unknown")
            
            logger.info(f"📥 Processing message: {event_type} from topic {message.topic}")
            
            # Find and execute handler
            handler = self.message_handlers.get(event_type)
            if handler:
                await handler(message_data, message, self.db_manager, self.redis_manager)
            else:
                logger.warning(f"⚠️ No handler for event type: {event_type}")
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            logger.error(f"Message data: {message.value}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check consumer health"""
        return {
            "kafka_consumer": {
                "running": self.running,
                "bootstrap_servers": self.bootstrap_servers,
                "group_id": self.group_id,
                "registered_handlers": list(self.message_handlers.keys()),
                "status": "healthy" if self.running else "stopped"
            }
        }

# Enhanced message processing handlers with database integration
async def handle_whatsapp_webhook(message_data: Dict[str, Any], kafka_message, db_manager: DatabaseManager, redis_manager: RedisManager):
    """Handle WhatsApp webhook messages with full conversation persistence"""
    try:
        msg_data = message_data.get("message_data", {})
        sender = msg_data.get("sender", "unknown")
        content = msg_data.get("content", "")
        message_id = msg_data.get("message_id", "")
        sender_name = msg_data.get("sender_name")
        
        logger.info(f"💬 Processing WhatsApp message from {sender}: {content[:100]}...")
        
        # 1. Get or create conversation session in database
        session_id = await db_manager.get_or_create_conversation(sender)
        logger.info(f"📋 Using conversation session: {session_id}")
        
        # 2. Add message to database
        message_db_id = await db_manager.add_message(session_id, MessageRole.USER, content)
        logger.info(f"💾 Message saved to database: {message_db_id}")
        
        # 3. Handle session state in Redis
        existing_state = await redis_manager.get_session(sender)
        if existing_state:
            conv_state = ConversationState(**existing_state)
        else:
            conv_state = ConversationState(
                user_id=sender,
                session_id=f"wa_{sender}_{int(datetime.now().timestamp())}"
            )
        
        # 4. Update conversation state
        conv_state.update_message(content, "user")
        
        # 5. Basic intent detection for stage management
        content_lower = content.lower()
        if any(word in content_lower for word in ["hola", "hi", "hello", "buenos", "buenas"]):
            conv_state.set_stage(ConversationStage.GREETING)
            await db_manager.update_session_step(session_id, ConversationStep.COLLECTING_INFO)
        elif any(word in content_lower for word in ["transporte", "taxi", "servicio", "viaje", "aeropuerto"]):
            conv_state.set_stage(ConversationStage.COLLECTING_INFO)
            await db_manager.update_session_step(session_id, ConversationStep.COLLECTING_INFO)
        
        # 6. Save updated state to Redis
        await redis_manager.save_session(sender, conv_state.model_dump(), 24)
        logger.info(f"🔄 Session state updated: {sender} - Stage: {conv_state.stage.value}")
        
        # 7. Store conversation context for potential CrewAI processing later
        conversation_context = {
            "session_id": session_id,
            "user_id": sender,
            "user_name": sender_name,
            "current_stage": conv_state.stage.value,
            "message_count": conv_state.message_count,
            "last_message": content,
            "collected_data": conv_state.collected_data
        }
        
        logger.info(f"✅ WhatsApp message fully processed: {sender} -> Database: {message_db_id}, Redis: updated")
        
        # TODO: Future step - Send to CrewAI for AI processing
        # This is where we'll integrate CrewAI agents for intelligent responses
        
    except Exception as e:
        logger.error(f"❌ Error processing WhatsApp webhook: {e}")
        raise

async def handle_conversation_event(message_data: Dict[str, Any], kafka_message, db_manager: DatabaseManager, redis_manager: RedisManager):
    """Handle conversation state changes"""
    try:
        user_id = message_data.get("user_id", "unknown")
        event_type = message_data.get("event_type", "unknown")
        event_data = message_data.get("data", {})
        
        logger.info(f"🔄 Processing conversation event: {event_type} for {user_id}")
        
        # Update conversation session based on event
        session_id = await db_manager.get_or_create_conversation(user_id)
        
        # Handle different event types
        if event_type == "stage_change":
            new_stage = event_data.get("new_stage")
            if new_stage:
                # Map conversation stages to database steps
                stage_mapping = {
                    "collecting_info": ConversationStep.COLLECTING_INFO,
                    "generating_quote": ConversationStep.GENERATING_QUOTE,
                    "awaiting_response": ConversationStep.COLLECTING_INFO,
                    "completed": ConversationStep.COLLECTING_INFO
                }
                db_step = stage_mapping.get(new_stage, ConversationStep.COLLECTING_INFO)
                await db_manager.update_session_step(session_id, db_step)
        
        # Update Redis session
        existing_state = await redis_manager.get_session(user_id)
        if existing_state:
            conv_state = ConversationState(**existing_state)
            # Apply event data updates
            for key, value in event_data.items():
                if hasattr(conv_state, key):
                    setattr(conv_state, key, value)
            
            await redis_manager.save_session(user_id, conv_state.model_dump(), 24)
        
        logger.info(f"✅ Conversation event processed: {event_type} for {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error processing conversation event: {e}")
        raise

async def handle_quotation_request(message_data: Dict[str, Any], kafka_message, db_manager: DatabaseManager, redis_manager: RedisManager):
    """Handle quotation processing requests"""
    try:
        request_data = message_data.get("request_data", {})
        client_id = request_data.get("client_id", "unknown")
        
        logger.info(f"💰 Processing quotation request for client: {client_id}")
        
        # TODO: Future step - integrate with quotation generation logic
        # This is where we'll add:
        # 1. Service data extraction
        # 2. Provider availability checking  
        # 3. Price calculation
        # 4. Quotation document generation
        
        logger.info(f"✅ Quotation request processed for client: {client_id}")
        
    except Exception as e:
        logger.error(f"❌ Error processing quotation request: {e}")
        raise

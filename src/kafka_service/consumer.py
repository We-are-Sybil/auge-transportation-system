import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

logger = logging.getLogger(__name__)

class KafkaConsumerService:
    """Async Kafka consumer for transportation events"""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092", group_id: str = "transportation_processors"):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False
        self.message_handlers = {}
    
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
            self.running = True
            logger.info(f"✅ Kafka consumer started: {topics}")
        except Exception as e:
            logger.error(f"❌ Failed to start Kafka consumer: {e}")
            raise
    
    async def stop(self):
        """Stop Kafka consumer"""
        if self.consumer and self.running:
            await self.consumer.stop()
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
                await handler(message_data, message)
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

# Message processing handlers
async def handle_whatsapp_webhook(message_data: Dict[str, Any], kafka_message):
    """Handle WhatsApp webhook messages"""
    msg_data = message_data.get("message_data", {})
    sender = msg_data.get("sender", "unknown")
    content = msg_data.get("content", "")
    
    logger.info(f"💬 WhatsApp message from {sender}: {content[:100]}...")
    
    # TODO: Add actual processing logic here
    # - Update conversation state in database
    # - Send to CrewAI for processing
    # - Generate responses
    
    print(f"[{datetime.now()}] Message: {sender} -> {content}")

async def handle_conversation_event(message_data: Dict[str, Any], kafka_message):
    """Handle conversation state changes"""
    user_id = message_data.get("user_id", "unknown")
    event_type = message_data.get("event_type", "unknown")
    
    logger.info(f"🔄 Conversation event: {event_type} for {user_id}")
    
    # TODO: Add conversation state processing
    print(f"[{datetime.now()}] Conversation: {user_id} -> {event_type}")

async def handle_quotation_request(message_data: Dict[str, Any], kafka_message):
    """Handle quotation processing"""
    request_data = message_data.get("request_data", {})
    client_id = request_data.get("client_id", "unknown")
    
    logger.info(f"💰 Quotation request for client: {client_id}")
    
    # TODO: Add quotation processing logic
    print(f"[{datetime.now()}] Quotation: client {client_id}")

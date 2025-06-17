import json
import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError
from enum import Enum
import traceback

# Import database and Redis managers
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.manager import DatabaseManager
from src.database.redis_manager import RedisManager
from src.database.models import MessageRole, ConversationStep
from src.webhook_service.session_models import ConversationState, ConversationStage

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Types of processing errors"""
    TRANSIENT = "transient"  # Temporary errors (DB connection, etc.)
    PERMANENT = "permanent"  # Data validation, parsing errors
    TIMEOUT = "timeout"      # Processing timeout
    DEPENDENCY = "dependency"  # External service failures

class RetryConfig:
    """Retry configuration"""
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    MAX_DELAY = 30.0  # seconds
    EXPONENTIAL_BASE = 2.0

class ErrorMetrics:
    """Simple in-memory error tracking"""
    def __init__(self):
        self.error_counts = {}
        self.circuit_breakers = {}
        self.last_reset = datetime.now()

    def record_error(self, error_type: str, handler_name: str):
        key = f"{handler_name}:{error_type}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Check circuit breaker
        total_errors = sum(count for k, count in self.error_counts.items() if k.startswith(handler_name))
        if total_errors >= 10:  # Circuit breaker threshold
            self.circuit_breakers[handler_name] = datetime.now() + timedelta(minutes=5)
            logger.warning(f"🔴 Circuit breaker OPEN for {handler_name} - too many errors")

    def is_circuit_open(self, handler_name: str) -> bool:
        if handler_name in self.circuit_breakers:
            if datetime.now() < self.circuit_breakers[handler_name]:
                return True
            else:
                # Reset circuit breaker
                del self.circuit_breakers[handler_name]
                logger.info(f"🟢 Circuit breaker CLOSED for {handler_name}")
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "error_counts": self.error_counts,
            "active_circuit_breakers": len(self.circuit_breakers),
            "last_reset": self.last_reset.isoformat()
        }

class MessageContext:
    """Context for message processing with retry information"""
    def __init__(self, original_message: Dict[str, Any], kafka_message=None):
        self.original_message = original_message
        self.kafka_message = kafka_message
        self.attempt_count = original_message.get("_retry_count", 0)
        self.first_attempt_time = original_message.get("_first_attempt", datetime.now().isoformat())
        self.last_error = original_message.get("_last_error")
        self.handler_name = None

class KafkaConsumerService:
    """Enhanced Kafka consumer with error handling and DLQ support"""

    def __init__(self, bootstrap_servers: str = "localhost:9092", group_id: str = "transportation_processors"):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.dlq_producer: Optional[AIOKafkaProducer] = None
        self.retry_producer: Optional[AIOKafkaProducer] = None
        self.running = False
        self.message_handlers = {}
        
        # Error handling
        self.error_metrics = ErrorMetrics()
        
        # Database and Redis managers
        self.db_manager = DatabaseManager()
        self.redis_manager = RedisManager()

    def register_handler(self, event_type: str, handler: Callable):
        """Register message handler for specific event type"""
        self.message_handlers[event_type] = handler
        logger.info(f"📝 Registered handler for: {event_type}")

    async def start(self, topics: list):
        """Start Kafka consumer with DLQ producer"""
        if self.running:
            return
        
        # Main consumer
        self.consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset='earliest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000
        )
        
        # DLQ Producer
        self.dlq_producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
            key_serializer=lambda x: x.encode('utf-8') if x else None
        )
        
        # Retry Producer
        self.retry_producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
            key_serializer=lambda x: x.encode('utf-8') if x else None
        )
        
        try:
            await self.consumer.start()
            await self.dlq_producer.start()
            await self.retry_producer.start()
            
            # Initialize database
            await self.db_manager.init_tables()
            
            self.running = True
            logger.info(f"✅ Enhanced Kafka consumer started: {topics}")
            logger.info("✅ DLQ and retry producers initialized")
        except Exception as e:
            logger.error(f"❌ Failed to start enhanced consumer: {e}")
            raise

    async def stop(self):
        """Stop all Kafka connections"""
        if self.running:
            tasks = []
            if self.consumer:
                tasks.append(self.consumer.stop())
            if self.dlq_producer:
                tasks.append(self.dlq_producer.stop())
            if self.retry_producer:
                tasks.append(self.retry_producer.stop())
            
            await asyncio.gather(*tasks, return_exceptions=True)
            await self.db_manager.close()
            await self.redis_manager.close()
            
            self.running = False
            logger.info("🛑 Enhanced Kafka consumer stopped")

    async def consume_messages(self):
        """Main consumption loop with error handling"""
        if not self.running:
            logger.error("Consumer not started")
            return
        
        logger.info("🔄 Starting enhanced message consumption loop...")
        
        try:
            async for message in self.consumer:
                await self.process_message_with_error_handling(message)
        except Exception as e:
            logger.error(f"❌ Critical error in consumption loop: {e}")
            raise

    async def process_message_with_error_handling(self, kafka_message):
        """Process message with comprehensive error handling"""
        context = None
        try:
            message_data = kafka_message.value
            context = MessageContext(message_data, kafka_message)
            event_type = message_data.get("event_type", "unknown")
            
            # Check circuit breaker
            if self.error_metrics.is_circuit_open(event_type):
                logger.warning(f"⚡ Circuit breaker OPEN - skipping {event_type}")
                await self.send_to_dlq(context, "circuit_breaker_open", ErrorType.DEPENDENCY)
                return
            
            logger.info(f"📥 Processing message: {event_type} (attempt {context.attempt_count + 1})")
            
            # Find and execute handler with timeout
            handler = self.message_handlers.get(event_type)
            if not handler:
                logger.warning(f"⚠️ No handler for event type: {event_type}")
                await self.send_to_dlq(context, f"no_handler_for_{event_type}", ErrorType.PERMANENT)
                return
            
            context.handler_name = event_type
            
            # Execute with timeout
            try:
                await asyncio.wait_for(
                    handler(message_data, kafka_message, self.db_manager, self.redis_manager),
                    timeout=30.0  # 30 second timeout
                )
                logger.info(f"✅ Message processed successfully: {event_type}")
                
            except asyncio.TimeoutError:
                raise Exception(f"Handler timeout after 30 seconds")
            
        except Exception as e:
            await self.handle_processing_error(context, e)

    async def handle_processing_error(self, context: MessageContext, error: Exception):
        """Handle processing errors with retry logic"""
        error_msg = str(error)
        error_type = self.classify_error(error)
        
        logger.error(f"❌ Processing error: {error_msg}")
        logger.error(f"📋 Error type: {error_type.value}")
        
        # Record error metrics
        if context.handler_name:
            self.error_metrics.record_error(error_type.value, context.handler_name)
        
        # Determine if we should retry
        should_retry = (
            error_type in [ErrorType.TRANSIENT, ErrorType.TIMEOUT, ErrorType.DEPENDENCY] and
            context.attempt_count < RetryConfig.MAX_RETRIES
        )
        
        if should_retry:
            await self.schedule_retry(context, error_msg, error_type)
        else:
            await self.send_to_dlq(context, error_msg, error_type)

    def classify_error(self, error: Exception) -> ErrorType:
        """Classify error type for retry decisions"""
        error_msg = str(error).lower()
        
        # Database connection errors
        if any(keyword in error_msg for keyword in ["connection", "timeout", "network", "unavailable"]):
            return ErrorType.TRANSIENT
        
        # Validation/parsing errors
        if any(keyword in error_msg for keyword in ["validation", "parse", "invalid", "format"]):
            return ErrorType.PERMANENT
        
        # Timeout errors
        if "timeout" in error_msg:
            return ErrorType.TIMEOUT
        
        # External service errors
        if any(keyword in error_msg for keyword in ["redis", "kafka", "service"]):
            return ErrorType.DEPENDENCY
        
        # Default to transient for unknown errors (safer)
        return ErrorType.TRANSIENT

    async def schedule_retry(self, context: MessageContext, error_msg: str, error_type: ErrorType):
        """Schedule message for retry with exponential backoff"""
        retry_count = context.attempt_count + 1
        delay = min(
            RetryConfig.BASE_DELAY * (RetryConfig.EXPONENTIAL_BASE ** retry_count),
            RetryConfig.MAX_DELAY
        )
        
        # Prepare retry message
        retry_message = context.original_message.copy()
        retry_message.update({
            "_retry_count": retry_count,
            "_first_attempt": context.first_attempt_time,
            "_last_error": error_msg,
            "_error_type": error_type.value,
            "_scheduled_for": (datetime.now() + timedelta(seconds=delay)).isoformat(),
            "_retry_delay": delay
        })
        
        # Determine retry topic
        original_topic = context.kafka_message.topic if context.kafka_message else "unknown"
        retry_topic = f"{original_topic}.retry"
        
        try:
            # Send to retry topic
            await self.retry_producer.send_and_wait(
                retry_topic,
                retry_message,
                key=context.original_message.get("event_type", "unknown")
            )
            
            logger.info(f"🔄 Scheduled retry {retry_count}/{RetryConfig.MAX_RETRIES} in {delay:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ Failed to schedule retry: {e}")
            await self.send_to_dlq(context, f"retry_scheduling_failed: {e}", ErrorType.DEPENDENCY)

    async def send_to_dlq(self, context: MessageContext, error_msg: str, error_type: ErrorType):
        """Send failed message to Dead Letter Queue"""
        try:
            # Prepare DLQ message with full context
            dlq_message = {
                "original_message": context.original_message,
                "error_details": {
                    "error_message": error_msg,
                    "error_type": error_type.value,
                    "handler_name": context.handler_name,
                    "attempt_count": context.attempt_count,
                    "first_attempt": context.first_attempt_time,
                    "final_attempt": datetime.now().isoformat(),
                    "stack_trace": traceback.format_exc()
                },
                "kafka_metadata": {
                    "topic": context.kafka_message.topic if context.kafka_message else "unknown",
                    "partition": context.kafka_message.partition if context.kafka_message else -1,
                    "offset": context.kafka_message.offset if context.kafka_message else -1
                },
                "dlq_timestamp": datetime.now().isoformat()
            }
            
            # Determine DLQ topic
            original_topic = context.kafka_message.topic if context.kafka_message else "unknown"
            dlq_topic = f"{original_topic}.dlq"
            
            # Send to DLQ
            await self.dlq_producer.send_and_wait(
                dlq_topic,
                dlq_message,
                key=f"error_{context.original_message.get('event_type', 'unknown')}"
            )
            
            logger.error(f"💀 Message sent to DLQ: {dlq_topic}")
            logger.error(f"📋 Error: {error_msg}")
            
        except Exception as e:
            logger.critical(f"💥 CRITICAL: Failed to send to DLQ: {e}")
            logger.critical(f"📋 Original message: {context.original_message}")

    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check with error metrics"""
        health = {
            "kafka_consumer": {
                "running": self.running,
                "bootstrap_servers": self.bootstrap_servers,
                "group_id": self.group_id,
                "registered_handlers": list(self.message_handlers.keys()),
                "status": "healthy" if self.running else "stopped"
            },
            "error_handling": {
                "dlq_producer_started": bool(self.dlq_producer and hasattr(self.dlq_producer, '_closed') and not self.dlq_producer._closed),
                "retry_producer_started": bool(self.retry_producer and hasattr(self.retry_producer, '_closed') and not self.retry_producer._closed),
                "error_metrics": self.error_metrics.get_stats()
            }
        }
        
        return health

# Enhanced message processing handlers with better error handling
async def handle_whatsapp_webhook(message_data: Dict[str, Any], kafka_message, db_manager: DatabaseManager, redis_manager: RedisManager):
    """Enhanced WhatsApp webhook handler with validation and error handling"""
    try:
        # Input validation
        msg_data = message_data.get("message_data", {})
        if not msg_data:
            raise ValueError("Missing message_data in webhook payload")
        
        sender = msg_data.get("sender")
        content = msg_data.get("content")
        message_id = msg_data.get("message_id")
        
        if not sender or not content or not message_id:
            raise ValueError(f"Missing required fields: sender={bool(sender)}, content={bool(content)}, message_id={bool(message_id)}")
        
        sender_name = msg_data.get("sender_name")
        
        logger.info(f"💬 Processing WhatsApp message from {sender}: {content[:100]}...")
        
        # 1. Database operations with error handling
        try:
            session_id = await db_manager.get_or_create_conversation(sender)
            logger.info(f"📋 Using conversation session: {session_id}")
        except Exception as e:
            raise Exception(f"Database session creation failed: {e}")
        
        try:
            message_db_id = await db_manager.add_message(session_id, MessageRole.USER, content)
            logger.info(f"💾 Message saved to database: {message_db_id}")
        except Exception as e:
            raise Exception(f"Database message save failed: {e}")
        
        # 2. Redis operations with error handling
        try:
            existing_state = await redis_manager.get_session(sender)
            if existing_state:
                conv_state = ConversationState(**existing_state)
            else:
                conv_state = ConversationState(
                    user_id=sender,
                    session_id=f"wa_{sender}_{int(datetime.now().timestamp())}"
                )
        except Exception as e:
            raise Exception(f"Redis session retrieval failed: {e}")
        
        # 3. State updates
        try:
            conv_state.update_message(content, "user")
            
            # Basic intent detection
            content_lower = content.lower()
            if any(word in content_lower for word in ["hola", "hi", "hello", "buenos", "buenas"]):
                conv_state.set_stage(ConversationStage.GREETING)
                await db_manager.update_session_step(session_id, ConversationStep.COLLECTING_INFO)
            elif any(word in content_lower for word in ["transporte", "taxi", "servicio", "viaje", "aeropuerto"]):
                conv_state.set_stage(ConversationStage.COLLECTING_INFO)
                await db_manager.update_session_step(session_id, ConversationStep.COLLECTING_INFO)
            
            # Save to Redis
            await redis_manager.save_session(sender, conv_state.model_dump(), 24)
            logger.info(f"🔄 Session state updated: {sender} - Stage: {conv_state.stage.value}")
            
        except Exception as e:
            raise Exception(f"State update failed: {e}")
        
        logger.info(f"✅ WhatsApp message fully processed: {sender} -> Database: {message_db_id}, Redis: updated")
        
    except ValueError as e:
        # Re-raise validation errors as permanent
        raise e
    except Exception as e:
        # Wrap other errors for better context
        logger.error(f"❌ WhatsApp webhook processing error: {e}")
        raise Exception(f"WhatsApp webhook processing failed: {e}")

async def handle_conversation_event(message_data: Dict[str, Any], kafka_message, db_manager: DatabaseManager, redis_manager: RedisManager):
    """Enhanced conversation event handler"""
    try:
        user_id = message_data.get("user_id")
        event_type = message_data.get("event_type")
        event_data = message_data.get("data", {})
        
        if not user_id or not event_type:
            raise ValueError(f"Missing required fields: user_id={bool(user_id)}, event_type={bool(event_type)}")
        
        logger.info(f"🔄 Processing conversation event: {event_type} for {user_id}")
        
        # Database operations
        try:
            session_id = await db_manager.get_or_create_conversation(user_id)
            
            if event_type == "stage_change":
                new_stage = event_data.get("new_stage")
                if new_stage:
                    stage_mapping = {
                        "collecting_info": ConversationStep.COLLECTING_INFO,
                        "generating_quote": ConversationStep.GENERATING_QUOTE,
                        "awaiting_response": ConversationStep.COLLECTING_INFO,
                        "completed": ConversationStep.COLLECTING_INFO
                    }
                    db_step = stage_mapping.get(new_stage, ConversationStep.COLLECTING_INFO)
                    await db_manager.update_session_step(session_id, db_step)
        except Exception as e:
            raise Exception(f"Database conversation update failed: {e}")
        
        # Redis operations
        try:
            existing_state = await redis_manager.get_session(user_id)
            if existing_state:
                conv_state = ConversationState(**existing_state)
                for key, value in event_data.items():
                    if hasattr(conv_state, key):
                        setattr(conv_state, key, value)
                await redis_manager.save_session(user_id, conv_state.model_dump(), 24)
        except Exception as e:
            raise Exception(f"Redis conversation update failed: {e}")
        
        logger.info(f"✅ Conversation event processed: {event_type} for {user_id}")
        
    except ValueError as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Conversation event processing error: {e}")
        raise Exception(f"Conversation event processing failed: {e}")

async def handle_quotation_request(message_data: Dict[str, Any], kafka_message, db_manager: DatabaseManager, redis_manager: RedisManager):
    """Enhanced quotation request handler"""
    try:
        request_data = message_data.get("request_data", {})
        if not request_data:
            raise ValueError("Missing request_data in quotation payload")
        
        client_id = request_data.get("client_id")
        if not client_id:
            raise ValueError("Missing client_id in request_data")
        
        logger.info(f"💰 Processing quotation request for client: {client_id}")
        
        # TODO: Future implementation for quotation processing
        # For now, just log successful processing
        
        logger.info(f"✅ Quotation request processed for client: {client_id}")
        
    except ValueError as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Quotation request processing error: {e}")
        raise Exception(f"Quotation request processing failed: {e}")

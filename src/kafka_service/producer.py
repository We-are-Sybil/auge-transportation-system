import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

logger = logging.getLogger(__name__)

class KafkaProducerService:
    """Async Kafka producer for transportation events"""

    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer: Optional[AIOKafkaProducer] = None
        self._started = False

    async def start(self):
        """Start Kafka producer"""
        if self._started:
            return
        
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=self._serialize_json,
            key_serializer=lambda x: x.encode('utf-8') if x else None,
            max_batch_size=16384,
            linger_ms=10,
            compression_type="gzip"
        )
        
        try:
            await self.producer.start()
            self._started = True
            logger.info(f"✅ Kafka producer started: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"❌ Failed to start Kafka producer: {e}")
            raise

    async def stop(self):
        """Stop Kafka producer"""
        if self.producer and self._started:
            await self.producer.stop()
            self._started = False
            logger.info("🛑 Kafka producer stopped")

    def _serialize_json(self, value: Any) -> bytes:
        """Serialize value to JSON bytes"""
        return json.dumps(value, default=str).encode('utf-8')

    async def send_webhook_message(self, message_data: Dict[str, Any]) -> bool:
        """Send WhatsApp webhook message to conversation.messages topic"""
        if not self._started:
            logger.error("Producer not started")
            return False
        
        try:
            # Prepare message with metadata
            message = {
                "event_type": "whatsapp_webhook",
                "timestamp": datetime.now().isoformat(),
                "message_data": message_data,
                "source": "webhook_service"
            }
            
            # Use sender as key for partitioning
            key = message_data.get("sender", "unknown")
            
            # Send to conversation.messages topic
            record_metadata = await self.producer.send_and_wait(
                "conversation.messages", 
                message, 
                key=key
            )
            
            logger.info(f"📤 Webhook message sent: topic={record_metadata.topic}, "
                       f"partition={record_metadata.partition}, offset={record_metadata.offset}")
            return True
            
        except KafkaError as e:
            logger.error(f"❌ Kafka send failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending to Kafka: {e}")
            return False

    async def send_conversation_event(self, event_type: str, user_id: str, data: Dict[str, Any]) -> bool:
        """Send conversation state change event"""
        if not self._started:
            return False
        
        try:
            event = {
                "event_type": event_type,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            
            await self.producer.send_and_wait(
                "conversation.state_changes",
                event,
                key=user_id
            )
            
            logger.info(f"📤 Conversation event sent: {event_type} for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send conversation event: {e}")
            return False

    async def send_quotation_request(self, request_data: Dict[str, Any]) -> bool:
        """Send quotation request to processing queue"""
        if not self._started:
            return False
        
        try:
            message = {
                "event_type": "quotation_request",
                "timestamp": datetime.now().isoformat(),
                "request_data": request_data
            }
            
            # Use client ID as key for quotation processing order
            key = request_data.get("client_id", "unknown")
            
            await self.producer.send_and_wait(
                "quotation.requests",
                message,
                key=str(key)
            )
            
            logger.info(f"📤 Quotation request sent for client: {key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send quotation request: {e}")
            return False

    async def send_quotation_request_event(self, event_data: Dict[str, Any]) -> bool:
        """Send quotation request event to quotation.requests topic"""
        if not self._started:
            return False
        
        try:
            message = {
                "event_type": "quotation_request",
                "timestamp": datetime.now().isoformat(),
                "event_data": event_data,
                "source": "quotation_service"
            }
            
            # Use request_id as key for ordering
            key = str(event_data.get("request_id", "unknown"))
            
            await self.producer.send_and_wait(
                "quotation.requests",
                message,
                key=key
            )
            
            logger.info(f"📤 Quotation request event sent: {event_data.get('form_number', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send quotation request event: {e}")
            return False

    async def send_quotation_processing_event(self, event_data: Dict[str, Any]) -> bool:
        """Send quotation processing event to quotation.processing topic"""
        if not self._started:
            return False
        
        try:
            message = {
                "event_type": "quotation_processing",
                "timestamp": datetime.now().isoformat(),
                "event_data": event_data,
                "source": "quotation_service"
            }
            
            # Use request_id as key
            key = str(event_data.get("request_id", "unknown"))
            
            await self.producer.send_and_wait(
                "quotation.processing",
                message,
                key=key
            )
            
            logger.info(f"📤 Quotation processing event sent: {event_data.get('processing_stage', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send quotation processing event: {e}")
            return False

    async def send_quotation_response_event(self, event_data: Dict[str, Any]) -> bool:
        """Send quotation response event to quotation.responses topic"""
        if not self._started:
            return False
        
        try:
            message = {
                "event_type": "quotation_response",
                "timestamp": datetime.now().isoformat(),
                "event_data": event_data,
                "source": "quotation_service"
            }
            
            # Use quotation_id as key
            key = str(event_data.get("quotation_id", "unknown"))
            
            await self.producer.send_and_wait(
                "quotation.responses",
                message,
                key=key
            )
            
            logger.info(f"📤 Quotation response event sent: quote_id={event_data.get('quotation_id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send quotation response event: {e}")
            return False

    async def send_quotation_modification_event(self, event_data: Dict[str, Any]) -> bool:
        """Send quotation modification event to quotation.modifications topic"""
        if not self._started:
            return False
        
        try:
            message = {
                "event_type": "quotation_modification",
                "timestamp": datetime.now().isoformat(),
                "event_data": event_data,
                "source": "quotation_service"
            }
            
            # Use original quotation_id as key
            key = str(event_data.get("original_quotation_id", "unknown"))
            
            await self.producer.send_and_wait(
                "quotation.modifications",
                message,
                key=key
            )
            
            logger.info(f"📤 Quotation modification event sent: {event_data.get('change_type', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send quotation modification event: {e}")
            return False

    async def send_quotation_confirmation_event(self, event_data: Dict[str, Any]) -> bool:
        """Send quotation confirmation event to quotation.confirmations topic"""
        if not self._started:
            return False
        
        try:
            message = {
                "event_type": "quotation_confirmation",
                "timestamp": datetime.now().isoformat(),
                "event_data": event_data,
                "source": "quotation_service"
            }
            
            # Use quotation_id as key
            key = str(event_data.get("quotation_id", "unknown"))
            
            await self.producer.send_and_wait(
                "quotation.confirmations",
                message,
                key=key
            )
            
            logger.info(f"📤 Quotation confirmation event sent: {event_data.get('decision', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send quotation confirmation event: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check producer health"""
        return {
            "producer": {
                "started": self._started,
                "bootstrap_servers": self.bootstrap_servers,
                "status": "healthy" if self._started else "stopped"
            }
        }

#!/usr/bin/env python3
"""Standalone Kafka consumer service for transportation system"""
import asyncio
import logging
import signal
import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.kafka_service.consumer import (
    KafkaConsumerService, 
    handle_whatsapp_webhook,
    handle_conversation_event,
    handle_quotation_request
)

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TransportationConsumerService:
    """Main consumer service for transportation system"""
    
    def __init__(self):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.consumer = KafkaConsumerService(
            bootstrap_servers=self.bootstrap_servers,
            group_id="transportation_processors"
        )
        self.shutdown_event = asyncio.Event()
    
    async def setup_handlers(self):
        """Register message handlers"""
        self.consumer.register_handler("whatsapp_webhook", handle_whatsapp_webhook)
        self.consumer.register_handler("conversation_state_change", handle_conversation_event) 
        self.consumer.register_handler("quotation_request", handle_quotation_request)
    
    async def start(self):
        """Start the consumer service"""
        logger.info("🚀 Starting Transportation Consumer Service")
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in [signal.SIGTERM, signal.SIGINT]:
            loop.add_signal_handler(sig, self.shutdown_event.set)
        
        try:
            # Setup message handlers
            await self.setup_handlers()
            
            # Start consumer
            topics = [
                "conversation.messages",
                "conversation.state_changes", 
                "quotation.requests"
            ]
            
            await self.consumer.start(topics)
            logger.info(f"✅ Consumer started, subscribed to: {topics}")
            
            # Start consumption loop
            consumption_task = asyncio.create_task(self.consumer.consume_messages())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            logger.info("🛑 Shutdown signal received")
            
            # Cancel consumption
            consumption_task.cancel()
            
            try:
                await consumption_task
            except asyncio.CancelledError:
                pass
            
        except Exception as e:
            logger.error(f"❌ Consumer service error: {e}")
            raise
        finally:
            await self.consumer.stop()
            logger.info("✅ Consumer service stopped")

async def main():
    """Main entry point"""
    service = TransportationConsumerService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

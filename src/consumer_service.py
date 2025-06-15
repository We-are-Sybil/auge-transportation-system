#!/usr/bin/env python3
"""Enhanced Kafka consumer service with error handling and monitoring"""
import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
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

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/consumer.log', mode='a') if os.access('/tmp', os.W_OK) else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

class TransportationConsumerService:
    """Enhanced consumer service with error handling and monitoring"""
    
    def __init__(self):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.consumer = KafkaConsumerService(
            bootstrap_servers=self.bootstrap_servers,
            group_id="transportation_processors"
        )
        self.shutdown_event = asyncio.Event()
        self.start_time = datetime.now()
        self.processed_messages = 0
        self.health_check_interval = 60  # seconds
    
    async def setup_handlers(self):
        """Register message handlers with error handling"""
        try:
            self.consumer.register_handler("whatsapp_webhook", handle_whatsapp_webhook)
            self.consumer.register_handler("conversation_state_change", handle_conversation_event) 
            self.consumer.register_handler("quotation_request", handle_quotation_request)
            logger.info("✅ All message handlers registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register handlers: {e}")
            raise
    
    async def start(self):
        """Start the enhanced consumer service"""
        logger.info("🚀 Starting Enhanced Transportation Consumer Service")
        logger.info(f"📋 Bootstrap servers: {self.bootstrap_servers}")
        logger.info(f"📋 Group ID: transportation_processors")
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in [signal.SIGTERM, signal.SIGINT]:
            loop.add_signal_handler(sig, self.shutdown_event.set)
        
        try:
            # Setup message handlers
            await self.setup_handlers()
            
            # Define topics including retry topics
            topics = [
                "conversation.messages",
                "conversation.messages.retry",
                "conversation.state_changes", 
                "quotation.requests",
                "quotation.requests.retry"
            ]
            
            await self.consumer.start(topics)
            logger.info(f"✅ Enhanced consumer started, subscribed to: {topics}")
            
            # Start background tasks
            consumption_task = asyncio.create_task(self.consumer.consume_messages())
            health_check_task = asyncio.create_task(self.periodic_health_check())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            logger.info("🛑 Shutdown signal received")
            
            # Cancel background tasks
            consumption_task.cancel()
            health_check_task.cancel()
            
            # Wait for tasks to complete
            try:
                await asyncio.gather(consumption_task, health_check_task, return_exceptions=True)
            except Exception as e:
                logger.warning(f"⚠️ Task cancellation error: {e}")
            
        except Exception as e:
            logger.error(f"❌ Consumer service error: {e}")
            raise
        finally:
            await self.consumer.stop()
            uptime = datetime.now() - self.start_time
            logger.info(f"✅ Consumer service stopped - Uptime: {uptime}, Messages processed: {self.processed_messages}")
    
    async def periodic_health_check(self):
        """Periodic health check and metrics logging"""
        while not self.shutdown_event.is_set():
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if self.shutdown_event.is_set():
                    break
                
                # Get health status
                health = await self.consumer.health_check()
                
                # Log basic metrics
                uptime = datetime.now() - self.start_time
                logger.info(f"📊 Health Check - Uptime: {uptime}")
                logger.info(f"📊 Consumer Status: {health['kafka_consumer']['status']}")
                
                # Log error metrics if available
                error_metrics = health.get('error_handling', {}).get('error_metrics', {})
                if error_metrics.get('error_counts'):
                    logger.info(f"📊 Error Counts: {error_metrics['error_counts']}")
                
                circuit_breakers = error_metrics.get('active_circuit_breakers', 0)
                if circuit_breakers > 0:
                    logger.warning(f"⚡ Active Circuit Breakers: {circuit_breakers}")
                
            except Exception as e:
                logger.error(f"❌ Health check error: {e}")
    
    def get_service_status(self):
        """Get current service status"""
        uptime = datetime.now() - self.start_time
        return {
            "service": "transportation_consumer",
            "status": "running" if not self.shutdown_event.is_set() else "shutting_down",
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "processed_messages": self.processed_messages,
            "bootstrap_servers": self.bootstrap_servers
        }

async def main():
    """Main entry point with enhanced error handling"""
    service = TransportationConsumerService()
    
    try:
        logger.info("🔧 Initializing Enhanced Transportation Consumer...")
        await service.start()
    except KeyboardInterrupt:
        logger.info("⌨️ Interrupted by user")
    except Exception as e:
        logger.error(f"💥 Service failed: {e}")
        logger.exception("Full error traceback:")
        sys.exit(1)
    finally:
        logger.info("🔚 Service shutdown complete")

if __name__ == "__main__":
    # Log startup
    logger.info("=" * 60)
    logger.info("🚀 Transportation Consumer Service Starting")
    logger.info(f"📅 Start Time: {datetime.now()}")
    logger.info(f"🐍 Python: {sys.version}")
    logger.info("=" * 60)
    
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"💥 Critical startup error: {e}")
        sys.exit(1)

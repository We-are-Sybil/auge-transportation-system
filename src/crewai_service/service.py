import asyncio
import logging
import signal
import sys
from typing import Dict, Any
from .kafka_consumer import CrewAIKafkaConsumer
from .config import config

logger = logging.getLogger(__name__)


class CrewAIService:
    """Main CrewAI service orchestrator"""

    def __init__(self):
        self.kafka_consumer = CrewAIKafkaConsumer()
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def start(self):
        """Start the service"""
        logger.info("🚀 Starting CrewAI Transportation Service")
        logger.info(f"📡 Kafka servers: {config.kafka_bootstrap_servers}")
        logger.info(f"🤖 Ollama model: {config.ollama_model} @ {config.ollama_base_url}")
        logger.info(f"📝 Topics: {config.kafka_consumer_topics}")
        
        try:
            await self.kafka_consumer.start()
            self.running = True
            
            # Main service loop
            while self.running:
                try:
                    await self.kafka_consumer.consume_messages()
                except Exception as e:
                    logger.error(f"Service error: {e}")
                    await asyncio.sleep(5)  # Brief pause before retry
            
        except Exception as e:
            logger.error(f"Fatal service error: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the service"""
        logger.info("⏹️ Stopping CrewAI Service...")
        self.running = False
        await self.kafka_consumer.stop()
        logger.info("✅ CrewAI Service stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "service_running": self.running,
            "config": {
                "ollama_model": config.ollama_model,
                "kafka_topics": config.kafka_consumer_topics,
                "consumer_group": config.kafka_consumer_group
            },
            "kafka_consumer": self.kafka_consumer.get_stats()
        }


async def main():
    """Run the CrewAI service"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    service = CrewAIService()

    try:
        await service.start()
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

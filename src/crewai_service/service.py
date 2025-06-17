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
        self._shutdown_event = asyncio.Event()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.running = False
            # Set the shutdown event in a thread-safe way
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(self._shutdown_event.set)
            except RuntimeError:
                # If no loop is running, just set the flag
                pass
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def start(self):
        """Start the service"""
        logger.info("🚀 Starting CrewAI Transportation Service")
        logger.info(f"📡 Kafka servers: {config.kafka_bootstrap_servers}")
        logger.info(f"🤖 LLM: {config.llm_provider}/{config.llm_model}")
        logger.info(f"📝 Topics: {config.kafka_consumer_topics}")
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        try:
            await self.kafka_consumer.start()
            self.running = True
            
            # Create consumption task
            consumption_task = asyncio.create_task(self.kafka_consumer.consume_messages())
            
            # Wait for either shutdown signal or consumption to complete
            done, pending = await asyncio.wait(
                [consumption_task, asyncio.create_task(self._shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
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
                "llm_provider": config.llm_provider,
                "llm_model": config.llm_model,
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
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)
    finally:
        logger.info("Service shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 CrewAI Service stopped")
        sys.exit(0)

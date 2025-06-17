import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaConsumer
from .config import config
from .crews.echo_crew import EchoCrew

logger = logging.getLogger(__name__)


class CrewAIKafkaConsumer:
    """Kafka consumer for CrewAI message processing"""

    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.echo_crew = EchoCrew()
        self.running = False
        self.processed_count = 0
        self.error_count = 0

    async def start(self):
        """Start the Kafka consumer"""
        logger.info("Starting CrewAI Kafka Consumer...")
        
        self.consumer = AIOKafkaConsumer(
            *config.kafka_consumer_topics,
            bootstrap_servers=config.kafka_bootstrap_servers,
            group_id=config.kafka_consumer_group,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
            consumer_timeout_ms=config.kafka_consumer_timeout * 1000
        )
        
        await self.consumer.start()
        self.running = True
        logger.info(f"✅ CrewAI Consumer started on topics: {config.kafka_consumer_topics}")

    async def stop(self):
        """Stop the Kafka consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
        logger.info("✅ CrewAI Consumer stopped")

    async def consume_messages(self):
        """Main consumption loop"""
        if not self.consumer:
            raise RuntimeError("Consumer not started")
        
        try:
            async for message in self.consumer:
                if not self.running:
                    break
                
                await self._process_message(message)
                
        except Exception as e:
            logger.error(f"❌ Consumption error: {e}")
            self.error_count += 1
            raise

    async def _process_message(self, message):
        """Process individual message"""
        try:
            # Extract message data
            kafka_data = {
                "topic": message.topic,
                "partition": message.partition,
                "offset": message.offset,
                "timestamp": message.timestamp,
                "key": message.key.decode('utf-8') if message.key else None,
                "value": message.value,
                "received_at": datetime.now().isoformat()
            }
            
            logger.info(f"📨 Processing message from {message.topic}")
            
            # Process with CrewAI
            result = self.echo_crew.process_message(kafka_data)
            
            if result["success"]:
                self.processed_count += 1
                logger.info(f"✅ Message processed successfully (#{self.processed_count})")
                logger.debug(f"Agent response: {result['agent_response']}")
            else:
                self.error_count += 1
                logger.error(f"❌ Processing failed: {result['error']}")
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ Message processing error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        return {
            "running": self.running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "topics": config.kafka_consumer_topics,
            "consumer_group": config.kafka_consumer_group
        }


async def main():
    """Run the CrewAI Kafka consumer"""
    consumer = CrewAIKafkaConsumer()

    try:
        await consumer.start()
        await consumer.consume_messages()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())

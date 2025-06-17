import os
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from aiokafka import AIOKafkaProducer

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Test configuration
KAFKA_SERVERS = "localhost:9092"
TEST_TOPICS = ["conversation.messages", "quotation.requests"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_test_message(topic: str, message: dict):
    """Send test message to Kafka topic"""
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_SERVERS,
        value_serializer=lambda x: json.dumps(x).encode('utf-8'),
        key_serializer=lambda x: x.encode('utf-8') if x else None
    )
    
    try:
        await producer.start()
        
        key = f"test-{int(time.time())}"
        await producer.send(topic, message, key=key)
        await producer.flush()
        
        logger.info(f"✅ Sent test message to {topic}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send message: {e}")
        return False
    finally:
        await producer.stop()


async def run_tests():
    """Run comprehensive CrewAI service tests"""
    logger.info("🧪 Starting CrewAI Service Tests")
    logger.info("=" * 40)
    
    # Test messages for different topics
    test_messages = {
        "conversation.messages": {
            "message_id": "test_001",
            "from_phone": "+1234567890",
            "message_type": "text",
            "content": "Hello, I need a quote for transportation",
            "timestamp": datetime.now().isoformat(),
            "webhook_id": "test_webhook"
        },
        "quotation.requests": {
            "request_id": "quote_001",
            "customer_phone": "+1234567890",
            "service_type": "passenger_transport",
            "pickup_location": "Airport Terminal A",
            "destination": "Downtown Hotel",
            "requested_date": "2025-06-20",
            "passenger_count": 2,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    success_count = 0
    total_tests = len(test_messages)
    
    # Send test messages
    for topic, message in test_messages.items():
        logger.info(f"📨 Testing {topic}")
        
        if await send_test_message(topic, message):
            success_count += 1
            # Wait between messages
            await asyncio.sleep(2)
        else:
            logger.error(f"❌ Test failed for {topic}")
    
    # Results
    logger.info("\n" + "=" * 40)
    logger.info(f"🏁 Test Results: {success_count}/{total_tests} passed")
    
    if success_count == total_tests:
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("✅ CrewAI service should now process these messages")
        logger.info("📝 Check CrewAI service logs for agent responses")
        logger.info("🤖 Test will work with any LLM provider configured")
    else:
        logger.error("❌ Some tests failed")
        return False
    
    return True


def print_usage():
    """Print test script usage"""
    print("CrewAI Service Test Script")
    print("=" * 30)
    print("Usage: uv run tests/test_crewai_service.py")
    print()
    print("Prerequisites:")
    print("1. Kafka running on localhost:9092")
    print("2. CrewAI service running")
    print("3. LLM provider configured (Ollama/OpenAI/Anthropic/etc.)")
    print()
    print("Environment Variables:")
    print("CREWAI_LLM_PROVIDER=ollama|openai|anthropic|google")
    print("CREWAI_LLM_MODEL=llama3.2|gpt-4|claude-3-sonnet|gemini-pro")
    print("CREWAI_LLM_BASE_URL=http://localhost:11434 (for Ollama)")
    print("CREWAI_LLM_API_KEY=your-api-key (for cloud providers)")
    print()
    print("This script sends test messages to Kafka topics.")
    print("Monitor CrewAI service logs to see agent responses.")


async def main():
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print_usage()
        return
    
    try:
        success = await run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

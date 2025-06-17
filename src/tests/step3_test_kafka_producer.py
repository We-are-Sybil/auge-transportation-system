import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from aiokafka import AIOKafkaProducer

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.kafka_service.producer import KafkaProducerService

async def test_producer_creation():
    """Test 1: Producer creation without errors"""
    print("🔍 Test 1: Producer creation...")
    try:
        producer = KafkaProducerService(KAFKA_BOOTSTRAP_SERVERS)
        await producer.start()
        print("✅ Producer started successfully")
        await producer.stop()
        print("✅ Producer stopped successfully")
        return True
    except Exception as e:
        print(f"❌ Producer creation failed: {e}")
        return False

async def test_producer_health():
    """Test 2: Producer health check"""
    print("\n🔍 Test 2: Producer health check...")
    try:
        producer = KafkaProducerService("localhost:9092")
        health = await producer.health_check()
        print(f"✅ Health check: {health}")
        return health["kafka_producer"]["started"] == False  # Should be false before start
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

async def main():
    print("🚀 Kafka Producer Fix Test")
    print("=" * 30)

    tests = [
        ("Producer Creation", test_producer_creation),
        ("Health Check", test_producer_health)
    ]

    results = []
    for name, test_func in tests:
        success = await test_func()
        results.append((name, success))

    print("\n" + "=" * 30)
    print("📊 RESULTS")
    print("=" * 30)

    all_passed = all(success for _, success in results)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")

    if all_passed:
        print("\n🎉 PRODUCER FIX WORKING!")
        print("FastAPI should start now")
    else:
        print("\n❌ Fix failed")

if __name__ == "__main__":
    asyncio.run(main())

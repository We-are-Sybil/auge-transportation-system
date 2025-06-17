import asyncio
import sys
import os
import json
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.kafka_service.consumer import KafkaConsumerService
from src.kafka_service.producer import KafkaProducerService

async def test_consumer_creation():
    """Test 1: Consumer creation"""
    print("🔍 Test 1: Consumer creation...")
    try:
        consumer = KafkaConsumerService("localhost:9092", "test_group")
        health = await consumer.health_check()
        print(f"✅ Consumer created: {health['kafka_consumer']['status']}")
        return True
    except Exception as e:
        print(f"❌ Consumer creation failed: {e}")
        return False

async def test_consumer_start_stop():
    """Test 2: Consumer start/stop"""
    print("\n🔍 Test 2: Consumer start/stop...")
    consumer = KafkaConsumerService("localhost:9092", "test_group_2")

    try:
        await consumer.start(["conversation.messages"])
        print("✅ Consumer started")
        
        health = await consumer.health_check()
        running = health['kafka_consumer']['running']
        print(f"✅ Consumer running: {running}")
        
        await consumer.stop()
        print("✅ Consumer stopped")
        return True
    except Exception as e:
        print(f"❌ Start/stop failed: {e}")
        return False

async def test_message_consumption():
    """Test 3: Actual message consumption"""
    print("\n🔍 Test 3: Message consumption...")

    # Create producer and consumer
    producer = KafkaProducerService("localhost:9092")
    consumer = KafkaConsumerService("localhost:9092", "test_consumption")

    # Track received messages
    received_messages = []

    # Updated handler signature to match new consumer interface
    async def test_handler(message_data, kafka_message, db_manager, redis_manager):
        received_messages.append(message_data)
        print(f"✅ Received: {message_data.get('message_data', {}).get('test_id', 'unknown')}")

    try:
        # Start services
        await producer.start()
        consumer.register_handler("whatsapp_webhook", test_handler)
        await consumer.start(["conversation.messages"])
        
        # Send test message
        test_data = {
            "test_id": "consumption_test",
            "content": "Test message for consumption",
            "timestamp": datetime.now().isoformat(),
            "sender": "test_consumer",
            "message_type": "text"
        }
        
        success = await producer.send_webhook_message(test_data)
        if not success:
            print("❌ Failed to send test message")
            return False
        
        print("✅ Test message sent")
        
        # Consume for 5 seconds
        consumption_task = asyncio.create_task(consumer.consume_messages())
        await asyncio.sleep(5)
        consumption_task.cancel()
        
        try:
            await consumption_task
        except asyncio.CancelledError:
            pass
        
        # Check results
        if received_messages:
            print(f"✅ Consumed {len(received_messages)} messages")
            return True
        else:
            print("❌ No messages received")
            return False
            
    except Exception as e:
        print(f"❌ Consumption test failed: {e}")
        return False
    finally:
        await producer.stop()
        await consumer.stop()

async def main():
    print("🚀 Kafka Consumer Tests")
    print("=" * 30)
    print("Prerequisites: podman-compose up -d")
    print("=" * 30)

    tests = [
        ("Consumer Creation", test_consumer_creation),
        ("Start/Stop", test_consumer_start_stop),
        ("Message Consumption", test_message_consumption)
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
        print("\n🎉 CONSUMER SERVICE READY!")
        print("Step 3.5 complete")
    else:
        print("\n❌ Some tests failed")

if __name__ == "__main__":
    asyncio.run(main())

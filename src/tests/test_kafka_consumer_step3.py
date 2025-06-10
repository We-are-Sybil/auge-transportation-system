import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

async def test_simple_consumer():
    """Test 1: Basic message consumption"""
    print("🔍 Test 1: Simple consumer...")
    
    # Send a test message first
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )
    
    consumer = AIOKafkaConsumer(
        'test-consumer-topic',
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        consumer_timeout_ms=5000
    )
    
    try:
        await producer.start()
        await consumer.start()
        
        # Send message
        test_message = {
            "test_id": "consumer_test_1",
            "content": "Hello consumer!",
            "timestamp": datetime.now().isoformat()
        }
        
        await producer.send_and_wait("test-consumer-topic", test_message)
        print("✅ Test message sent")
        
        # Consume message
        async for msg in consumer:
            if msg.value.get("test_id") == "consumer_test_1":
                print(f"✅ Message consumed: {msg.value['content']}")
                return True
            break
        
        print("❌ Message not found")
        return False
        
    except Exception as e:
        print(f"❌ Consumer failed: {e}")
        return False
    finally:
        await producer.stop()
        await consumer.stop()

async def test_group_consumer():
    """Test 2: Consumer group"""
    print("\n🔍 Test 2: Consumer group...")
    
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )
    
    consumer = AIOKafkaConsumer(
        'test-group-topic',
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id='transportation_group',
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        consumer_timeout_ms=5000
    )
    
    try:
        await producer.start()
        await consumer.start()
        
        # Send message
        group_message = {
            "group_test_id": "group_test_1",
            "content": "Group consumer test",
            "timestamp": datetime.now().isoformat()
        }
        
        await producer.send_and_wait("test-group-topic", group_message)
        print("✅ Group message sent")
        
        # Consume message
        async for msg in consumer:
            if msg.value.get("group_test_id") == "group_test_1":
                print(f"✅ Group message consumed: partition={msg.partition}, offset={msg.offset}")
                return True
            break
        
        print("❌ Group message not found")
        return False
        
    except Exception as e:
        print(f"❌ Group consumer failed: {e}")
        return False
    finally:
        await producer.stop()
        await consumer.stop()

async def test_webhook_message_consumption():
    """Test 3: Transportation webhook message consumption"""
    print("\n🔍 Test 3: Webhook message consumption...")
    
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )
    
    consumer = AIOKafkaConsumer(
        'transportation_webhooks',
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id='webhook_processors',
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        consumer_timeout_ms=5000
    )
    
    try:
        await producer.start()
        await consumer.start()
        
        # Send webhook-style message
        webhook_message = {
            "event_type": "whatsapp_message",
            "message_id": "wamid.webhook123",
            "sender": "+573001234567",
            "content": "Quiero un taxi para el aeropuerto",
            "conversation_stage": "collecting_info",
            "timestamp": datetime.now().isoformat()
        }
        
        await producer.send_and_wait("transportation_webhooks", webhook_message)
        print("✅ Webhook message sent")
        
        # Consume and process
        async for msg in consumer:
            data = msg.value
            if data.get("message_id") == "wamid.webhook123":
                print(f"✅ Webhook consumed: {data['sender']} -> {data['content']}")
                print(f"   Stage: {data['conversation_stage']}")
                return True
            break
        
        print("❌ Webhook message not found")
        return False
        
    except Exception as e:
        print(f"❌ Webhook consumer failed: {e}")
        return False
    finally:
        await producer.stop()
        await consumer.stop()

async def main():
    print("🚀 Kafka Consumer Tests")
    print("=" * 30)
    
    tests = [
        ("Simple Consumer", test_simple_consumer),
        ("Group Consumer", test_group_consumer),
        ("Webhook Consumer", test_webhook_message_consumption)
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
        print("\n🎉 CONSUMER READY!")
        print("Step 3.2 complete")
    else:
        print("\n❌ Some tests failed")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from aiokafka import AIOKafkaProducer

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

async def test_simple_producer():
    """Test 1: Basic message production"""
    print("🔍 Test 1: Simple producer...")
    
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )
    
    try:
        await producer.start()
        
        # Send test message
        message = {
            "test_id": "producer_test_1",
            "content": "Hello from aiokafka producer!",
            "timestamp": datetime.now().isoformat()
        }
        
        await producer.send_and_wait("test-topic", message)
        print("✅ Message sent successfully")
        return True
        
    except Exception as e:
        print(f"❌ Producer failed: {e}")
        return False
    finally:
        await producer.stop()

async def test_batch_producer():
    """Test 2: Batch message production"""
    print("\n🔍 Test 2: Batch producer...")
    
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda x: json.dumps(x).encode('utf-8'),
        max_batch_size=16384,
        linger_ms=10
    )
    
    try:
        await producer.start()
        
        # Send multiple messages
        messages = []
        for i in range(5):
            message = {
                "batch_id": f"batch_test_{i}",
                "content": f"Batch message {i}",
                "timestamp": datetime.now().isoformat()
            }
            
            # Send without waiting
            future = await producer.send("test-topic", message)
            messages.append(future)
        
        # Wait for all messages
        for future in messages:
            record_metadata = await future
            print(f"✅ Message sent to partition {record_metadata.partition}")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch producer failed: {e}")
        return False
    finally:
        await producer.stop()

async def test_webhook_message_format():
    """Test 3: Transportation webhook message format"""
    print("\n🔍 Test 3: Webhook message format...")
    
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )
    
    try:
        await producer.start()
        
        # Simulate WhatsApp webhook message
        webhook_message = {
            "event_type": "whatsapp_message",
            "message_id": "wamid.test123",
            "sender": "+573001234567",
            "content": "Necesito transporte al aeropuerto mañana",
            "timestamp": datetime.now().isoformat(),
            "conversation_stage": "collecting_info"
        }
        
        await producer.send_and_wait("transportation_requests", webhook_message)
        print("✅ Webhook message format sent")
        return True
        
    except Exception as e:
        print(f"❌ Webhook format test failed: {e}")
        return False
    finally:
        await producer.stop()

async def main():
    print("🚀 Kafka Producer Tests")
    print("=" * 30)
    
    tests = [
        ("Simple Producer", test_simple_producer),
        ("Batch Producer", test_batch_producer),
        ("Webhook Format", test_webhook_message_format)
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
        print("\n🎉 PRODUCER READY!")
    else:
        print("\n❌ Some tests failed")

if __name__ == "__main__":
    asyncio.run(main())

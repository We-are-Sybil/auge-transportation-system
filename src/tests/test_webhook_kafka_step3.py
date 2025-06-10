import os
import requests
import asyncio
import json
import time
from datetime import datetime
from aiokafka import AIOKafkaConsumer

BASE_URL = "http://localhost:8000"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
TEST_SENDER_ID = os.getenv("WHATSAPP_TESTING_PHONE_NUMBER", f"test_{int(time.time())}")


def create_whatsapp_payload(sender_id, message_text, sender_name="Test User"):
    """Create WhatsApp webhook payload"""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "123", "phone_number_id": "456"},
                    "contacts": [{"profile": {"name": sender_name}, "wa_id": sender_id}],
                    "messages": [{
                        "from": sender_id,
                        "id": f"msg_{int(time.time())}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": message_text},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

def test_fastapi_kafka_health():
    """Test 1: FastAPI Kafka health check"""
    print("🔍 Test 1: FastAPI Kafka health...")
    try:
        response = requests.get(f"{BASE_URL}/kafka/test")
        result = response.json()
        
        success = response.status_code == 200 and result.get("test_sent") == True
        print(f"✅ Kafka health: {result.get('status')}")
        return success
    except Exception as e:
        print(f"❌ Kafka health test failed: {e}")
        return False

def test_webhook_to_kafka():
    """Test 2: Webhook sends to Kafka"""
    print("\n🔍 Test 2: Webhook → Kafka...")
    try:
        user_id = TEST_SENDER_ID
        payload = create_whatsapp_payload(user_id, "Necesito transporte al aeropuerto")
        
        response = requests.post(f"{BASE_URL}/webhook", json=payload)
        result = response.json()
        
        success = (response.status_code == 200 and 
                  result.get("status") == "success" and 
                  result.get("kafka_sent") == True)
        
        print(f"✅ Webhook response: {result.get('message')}")
        print(f"✅ Kafka sent: {result.get('kafka_sent')}")
        return success, user_id
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return False, None

async def test_consume_from_kafka(expected_sender):
    """Test 3: Consume message from Kafka"""
    print("\n🔍 Test 3: Consume from Kafka...")
    
    consumer = AIOKafkaConsumer(
        'conversation.messages',
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='latest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        consumer_timeout_ms=10000
    )
    
    try:
        await consumer.start()
        print("✅ Kafka consumer started")
        
        found_message = False
        start_time = time.time()
        
        async for msg in consumer:
            message_data = msg.value
            print(f"{message_data.get("message_data", {}).get("sender")} == {expected_sender}")
            
            # Check if this is our test message
            if (message_data.get("event_type") == "whatsapp_webhook" and
                message_data.get("message_data", {}).get("sender") == expected_sender):
                
                print(f"✅ Found message: {message_data['message_data']['content']}")
                print(f"   Sender: {message_data['message_data']['sender']}")
                print(f"   Partition: {msg.partition}, Offset: {msg.offset}")
                found_message = True
                break
            
            # Timeout after 10 seconds
            if time.time() - start_time > 10:
                break
        
        return found_message
        
    except Exception as e:
        print(f"❌ Kafka consumer failed: {e}")
        return False
    finally:
        await consumer.stop()

def test_multiple_messages():
    """Test 4: Multiple messages in sequence"""
    print("\n🔍 Test 4: Multiple messages...")
    try:
        base_user = f"multi_{int(time.time())}"
        messages = [
            "Hola, necesito un taxi",
            "Para mañana a las 8am",
            "Al aeropuerto El Dorado"
        ]
        
        success_count = 0
        for i, msg in enumerate(messages):
            user_id = f"{base_user}_{i}"
            payload = create_whatsapp_payload(user_id, msg)
            
            response = requests.post(f"{BASE_URL}/webhook", json=payload)
            result = response.json()
            
            if (response.status_code == 200 and 
                result.get("kafka_sent") == True):
                success_count += 1
        
        print(f"✅ Sent {success_count}/{len(messages)} messages to Kafka")
        return success_count == len(messages)
        
    except Exception as e:
        print(f"❌ Multiple messages test failed: {e}")
        return False

async def test_kafka_message_structure():
    """Test 5: Verify Kafka message structure"""
    print("\n🔍 Test 5: Kafka message structure...")
    
    # Send test message
    user_id = TEST_SENDER_ID
    payload = create_whatsapp_payload(user_id, "Test message structure", "Structure Tester")
    
    response = requests.post(f"{BASE_URL}/webhook", json=payload)
    if response.status_code != 200:
        print("❌ Failed to send webhook")
        return False
    
    # Consume and verify structure
    consumer = AIOKafkaConsumer(
        'conversation.messages',
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='latest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        consumer_timeout_ms=8000
    )
    
    try:
        await consumer.start()
        
        async for msg in consumer:
            message_data = msg.value
            
            if (message_data.get("message_data", {}).get("sender") == user_id):
                # Verify expected structure
                required_fields = [
                    "event_type", "timestamp", "message_data", "source"
                ]
                
                message_required = [
                    "message_id", "sender", "content", "timestamp", "message_type"
                ]
                
                # Check top level
                for field in required_fields:
                    if field not in message_data:
                        print(f"❌ Missing field: {field}")
                        return False
                
                # Check message data
                msg_data = message_data.get("message_data", {})
                for field in message_required:
                    if field not in msg_data:
                        print(f"❌ Missing message field: {field}")
                        return False
                
                print("✅ Message structure valid")
                print(f"   Event type: {message_data['event_type']}")
                print(f"   Source: {message_data['source']}")
                print(f"   Content: {msg_data['content']}")
                print(f"   Sender name: {msg_data.get('sender_name')}")
                return True
        
        print("❌ Test message not found")
        return False
        
    except Exception as e:
        print(f"❌ Structure test failed: {e}")
        return False
    finally:
        await consumer.stop()

async def main():
    print("🚀 Webhook → Kafka Integration Test")
    print("=" * 45)
    print("Prerequisites:")
    print("- podman-compose up -d")
    print("- uv run uvicorn src.webhook_service.main:app --reload")
    print("=" * 45)
    
    # Test 1: Health check
    if not test_fastapi_kafka_health():
        print("\n❌ Kafka not ready. Check FastAPI logs.")
        return
    
    # Test 2: Webhook to Kafka
    webhook_success, test_user = test_webhook_to_kafka()
    if not webhook_success:
        print("\n❌ Webhook → Kafka failed")
        return
    
    # Wait a moment for message to be available
    await asyncio.sleep(2)
    
    # Test 3: Consume from Kafka
    if test_user and not await test_consume_from_kafka(test_user):
        print("\n❌ Kafka consumption failed")
        return
    
    # Test 4: Multiple messages
    if not test_multiple_messages():
        print("\n❌ Multiple messages test failed")
        return
    
    # Test 5: Message structure
    if not await test_kafka_message_structure():
        print("\n❌ Message structure test failed")
        return
    
    print("\n" + "=" * 45)
    print("📊 RESULTS")
    print("=" * 45)
    
    tests = [
        ("Kafka Health", True),
        ("Webhook → Kafka", True),
        ("Kafka Consumption", True),
        ("Multiple Messages", True),
        ("Message Structure", True)
    ]
    
    for name, success in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
    
    print("\n🎉 WEBHOOK → KAFKA INTEGRATION READY!")
    print("Step 3.4 complete")

if __name__ == "__main__":
    asyncio.run(main())

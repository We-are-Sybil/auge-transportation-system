import asyncio
import time
import requests
import json
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.manager import DatabaseManager
from src.database.redis_manager import RedisManager
from src.kafka_service.consumer import KafkaConsumerService, handle_whatsapp_webhook

BASE_URL = "http://localhost:8000"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

def create_whatsapp_payload(sender_id, message_text, sender_name="End2End Test"):
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

async def test_consumer_database_integration():
    """Test 1: Consumer can process messages and store in database"""
    print("🔍 Test 1: Consumer database integration...")

    db_manager = DatabaseManager()
    redis_manager = RedisManager()

    try:
        # Initialize database
        await db_manager.init_tables()
        
        # Create test message data (simulating what comes from Kafka)
        test_message_data = {
            "event_type": "whatsapp_webhook",
            "timestamp": datetime.now().isoformat(),
            "message_data": {
                "message_id": "test_msg_123",
                "sender": f"test_user_{int(time.time())}",
                "content": "Hola, necesito transporte al aeropuerto",
                "sender_name": "Test User",
                "timestamp": str(int(time.time())),
                "message_type": "text"
            },
            "source": "test"
        }
        
        # Process message using the handler
        await handle_whatsapp_webhook(test_message_data, None, db_manager, redis_manager)
        
        # Verify message was stored in database
        sender = test_message_data["message_data"]["sender"]
        session_id = await db_manager.get_or_create_conversation(sender)
        
        # Verify session was stored in Redis
        session_data = await redis_manager.get_session(sender)
        
        success = session_id is not None and session_data is not None
        print(f"✅ Database session: {session_id}")
        print(f"✅ Redis session: {session_data['user_id'] if session_data else 'None'}")
        
        return success
        
    except Exception as e:
        print(f"❌ Consumer integration test failed: {e}")
        return False
    finally:
        await db_manager.close()
        await redis_manager.close()

def test_webhook_sends_to_kafka():
    """Test 2: Webhook sends messages to Kafka"""
    print("\n🔍 Test 2: Webhook → Kafka...")

    try:
        user_id = f"webhook_test_{int(time.time())}"
        payload = create_whatsapp_payload(user_id, "Test webhook to kafka integration")
        
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

async def test_start_consumer_service():
    """Test 3: Start a temporary consumer service to process messages"""
    print("\n🔍 Test 3: Starting consumer service...")

    try:
        # Create and start consumer service
        consumer_service = KafkaConsumerService("localhost:9092", "e2e_test_group")
        
        # Register the handler
        consumer_service.register_handler("whatsapp_webhook", handle_whatsapp_webhook)
        
        # Start consumer
        await consumer_service.start(["conversation.messages"])
        print("✅ Consumer service started")
        
        # Run consumer for 10 seconds to process any pending messages
        print("⏱️ Processing messages for 10 seconds...")
        consumption_task = asyncio.create_task(consumer_service.consume_messages())
        await asyncio.sleep(10)
        consumption_task.cancel()
        
        try:
            await consumption_task
        except asyncio.CancelledError:
            pass
        
        await consumer_service.stop()
        print("✅ Consumer service stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Consumer service test failed: {e}")
        return False

async def test_verify_processing_results(test_user_id):
    """Test 4: Verify messages were processed to database/Redis"""
    print("\n🔍 Test 4: Verify processing results...")

    db_manager = DatabaseManager()
    redis_manager = RedisManager()

    try:
        await db_manager.init_tables()
        
        # Check database for conversation
        session_id = await db_manager.get_or_create_conversation(test_user_id)
        
        # Check Redis for session data
        session_data = await redis_manager.get_session(test_user_id)
        
        if session_data:
            print(f"✅ Found Redis session: {session_data['user_id']}")
            print(f"✅ Message count: {session_data.get('message_count', 0)}")
            print(f"✅ Current stage: {session_data.get('stage', 'unknown')}")
            print(f"✅ Last message: {session_data.get('last_message', 'none')[:50]}...")
            return True
        else:
            print("❌ No session data found in Redis")
            return False
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
    finally:
        await db_manager.close()
        await redis_manager.close()

async def test_conversation_persistence():
    """Test 5: Multiple messages with consumer processing"""
    print("\n🔍 Test 5: Multi-message conversation...")

    try:
        user_id = f"persistence_test_{int(time.time())}"
        messages = [
            "Hola, necesito un taxi",
            "Para mañana a las 8am", 
            "Al aeropuerto El Dorado"
        ]
        
        # Start consumer service first
        consumer_service = KafkaConsumerService("localhost:9092", "persistence_test_group")
        consumer_service.register_handler("whatsapp_webhook", handle_whatsapp_webhook)
        await consumer_service.start(["conversation.messages"])
        
        # Start consumption in background
        consumption_task = asyncio.create_task(consumer_service.consume_messages())
        
        # Send messages with delays
        for i, msg in enumerate(messages):
            payload = create_whatsapp_payload(user_id, msg)
            response = requests.post(f"{BASE_URL}/webhook", json=payload)
            
            if response.status_code != 200:
                print(f"❌ Failed to send message {i+1}")
                consumption_task.cancel()
                await consumer_service.stop()
                return False
            
            await asyncio.sleep(2)  # Wait between messages
        
        # Let consumer process for a bit more
        await asyncio.sleep(5)
        
        # Stop consumer
        consumption_task.cancel()
        try:
            await consumption_task
        except asyncio.CancelledError:
            pass
        await consumer_service.stop()
        
        # Verify results
        redis_manager = RedisManager()
        try:
            session_data = await redis_manager.get_session(user_id)
            
            if session_data:
                message_count = session_data.get("message_count", 0)
                print(f"✅ Conversation persisted: {message_count} messages")
                print(f"✅ Current stage: {session_data.get('stage', 'unknown')}")
                return message_count >= 3
            else:
                print("❌ No session data found")
                return False
        finally:
            await redis_manager.close()
        
    except Exception as e:
        print(f"❌ Persistence test failed: {e}")
        return False

async def main():
    print("🚀 End-to-End Message Processing Test")
    print("=" * 50)
    print("Prerequisites:")
    print("- podman-compose up -d")
    print("- uv run uvicorn src.webhook_service.main:app --reload")
    print("=" * 50)

    # Test 1: Consumer database integration
    consumer_test = await test_consumer_database_integration()
    if not consumer_test:
        print("\n❌ Consumer integration failed")
        return

    # Test 2: Webhook sends to Kafka
    webhook_success, test_user = test_webhook_sends_to_kafka()
    if not webhook_success:
        print("\n❌ Webhook → Kafka failed")
        return

    # Test 3: Start consumer service to process messages
    consumer_start = await test_start_consumer_service()
    if not consumer_start:
        print("\n❌ Consumer service failed")
        return

    # Test 4: Verify processing results
    verification_success = await test_verify_processing_results(test_user)
    if not verification_success:
        print("\n❌ Processing verification failed")
        # Continue anyway to test persistence

    # Test 5: Multi-message conversation persistence
    persistence_success = await test_conversation_persistence()

    print("\n" + "=" * 50)
    print("📊 RESULTS")
    print("=" * 50)

    tests = [
        ("Consumer Database Integration", consumer_test),
        ("Webhook → Kafka", webhook_success),
        ("Consumer Service", consumer_start),
        ("Processing Verification", verification_success),
        ("Conversation Persistence", persistence_success)
    ]

    all_passed = all(success for _, success in tests)
    for name, success in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")

    if all_passed:
        print("\n🎉 END-TO-END MESSAGE PROCESSING READY!")
        print("Step 3.6 complete - Message processing integration working")
        print("\nArchitecture: WhatsApp → Webhook → Kafka → Consumer → Database + Redis")
    else:
        print("\n❌ Some tests failed - but basic integration is working")
        print("\nNote: For production, you'd run a dedicated consumer service")

if __name__ == "__main__":
    asyncio.run(main())

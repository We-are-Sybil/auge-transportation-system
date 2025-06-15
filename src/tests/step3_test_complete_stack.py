import requests
import subprocess
import time
import asyncio
import json
import sys
import os 
from datetime import datetime

BASE_URL = "http://localhost:8000"

def check_container_status():
    """Test 1: Check all containers are running."""
    print("🔍 Test 1: Container status...")

    required_containers = [
            "transportation_postgres",
            "transportation_redis",
            "transportation_zookeeper",
            "transportation_kafka",
            "transportation_fastapi",
            "transportation_consumer",
            ]
    try:
        result = subprocess.run(
            ["podman", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )

        running_containers = result.stdout.strip().split("\n")
        missing = [container for container in required_containers if container not in running_containers]

        if missing:
            print(f"❌ Missing containers: {', '.join(missing)}")
            return False

        print(f"✅ All {len(required_containers)} containers are running.")
        return True
    except Exception as e:
        print(f"❌ Error checking containers: {e}")
        return False

def test_services_health():
    """Test 2: Check services are healthy"""
    print("\n🔍 Test 2: Services health...")
    
    try:
        # Test FastAPI health
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code != 200:
            print(f"❌ FastAPI unhealthy: {response.status_code}")
            return False
        print("✅ FastAPI healthy")

        health_data = response.json()
        kafka_status = health_data.get("services", {}).get("kafka", {}).get("kafka_producer", {}).get("status")
        
        if kafka_status != "healthy":
            print(f"❌ Kafka unhealthy: {kafka_status}")
            return False
        print("✅ Kafka healthy")
        
        # Test database
        response = requests.get(f"{BASE_URL}/db/test", timeout=5)
        if response.status_code == 200:
            print("✅ Database healthy")
        else:
            print("❌ Database unhealthy")
            return False
        
        # Test Redis
        response = requests.get(f"{BASE_URL}/redis/test", timeout=5)
        if response.status_code == 200:
            print("✅ Redis healthy")
        else:
            print("❌ Redis unhealthy")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_webhook_to_consumer_flow():
    """Test 3: Complete webhook -> consumer flow"""
    print("\n🔍 Test 3: Webhook -> Consumer flow...")
    
    try:
        # Generate unique test data
        test_user = f"stack_test_{int(time.time())}"
        test_message = "Necesito transporte al aeropuerto desde el hotel"
        
        # Create WhatsApp webhook payload
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "123", "phone_number_id": "456"},
                        "contacts": [{"profile": {"name": "Stack Test User"}, "wa_id": test_user}],
                        "messages": [{
                            "from": test_user,
                            "id": f"msg_{int(time.time())}",
                            "timestamp": str(int(time.time())),
                            "text": {"body": test_message},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        print(f"📤 Sending webhook for user: {test_user}")
        
        # Send webhook
        response = requests.post(f"{BASE_URL}/webhook", json=payload, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Webhook failed: {response.status_code}")
            return False, None
        
        result = response.json()
        kafka_sent = result.get("kafka_sent", False)
        
        if not kafka_sent:
            print("❌ Message not sent to Kafka")
            return False, None
        
        print("✅ Webhook received and sent to Kafka")
        
        return True, test_user
        
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return False, None

def test_consumer_processing(test_user):
    """Test 4: Verify consumer processed the message"""
    print("\n🔍 Test 4: Consumer processing verification...")
    
    if not test_user:
        print("❌ No test user to verify")
        return False
    
    try:
        # Wait for consumer to process (give it some time)
        print("⏱️ Waiting 10 seconds for consumer processing...")
        time.sleep(10)
        
        # Check if session was created in Redis
        response = requests.get(f"{BASE_URL}/api/sessions/{test_user}", timeout=5)
        
        if response.status_code == 200:
            session_data = response.json()["data"]
            
            print(f"✅ Session found in Redis")
            print(f"   User: {session_data.get('user_id', 'unknown')}")
            print(f"   Messages: {session_data.get('message_count', 0)}")
            print(f"   Stage: {session_data.get('stage', 'unknown')}")
            print(f"   Last message: {session_data.get('last_message', 'none')[:50]}...")
            
            # Verify message content
            if session_data.get("message_count", 0) > 0:
                print("✅ Consumer processed message to Redis")
                return True
            else:
                print("❌ No messages found in session")
                return False
        else:
            print(f"❌ Session not found in Redis: {response.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ Consumer verification failed: {e}")
        return False

def test_multiple_message_flow():
    """Test 5: Multiple messages through complete stack"""
    print("\n🔍 Test 5: Multiple message flow...")
    
    try:
        test_user = f"multi_stack_{int(time.time())}"
        messages = [
            "Hola, necesito un servicio de transporte",
            "Para mañana a las 9:00 AM",
            "Desde el hotel hasta el aeropuerto"
        ]
        
        # Send multiple messages
        for i, msg in enumerate(messages):
            payload = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "id": "123",
                    "changes": [{
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "123", "phone_number_id": "456"},
                            "contacts": [{"profile": {"name": "Multi Test"}, "wa_id": test_user}],
                            "messages": [{
                                "from": test_user,
                                "id": f"msg_{int(time.time())}_{i}",
                                "timestamp": str(int(time.time())),
                                "text": {"body": msg},
                                "type": "text"
                            }]
                        },
                        "field": "messages"
                    }]
                }]
            }
            
            response = requests.post(f"{BASE_URL}/webhook", json=payload, timeout=5)
            if response.status_code != 200:
                print(f"❌ Message {i+1} failed")
                return False
            
            time.sleep(2)  # Small delay between messages
        
        print(f"✅ Sent {len(messages)} messages")
        
        # Wait for processing
        time.sleep(8)
        
        # Check results
        response = requests.get(f"{BASE_URL}/api/sessions/{test_user}", timeout=5)
        if response.status_code == 200:
            session_data = response.json()["data"]
            message_count = session_data.get("message_count", 0)
            
            if message_count >= len(messages):
                print(f"✅ All {message_count} messages processed")
                return True
            else:
                print(f"❌ Only {message_count}/{len(messages)} messages processed")
                return False
        else:
            print("❌ Session not found")
            return False
        
    except Exception as e:
        print(f"❌ Multiple message test failed: {e}")
        return False

def check_consumer_logs():
    """Test 6: Check consumer container logs"""
    print("\n🔍 Test 6: Consumer logs...")
    
    try:
        result = subprocess.run(
            ["podman", "logs", "transportation_consumer"],
            capture_output=True, text=True, timeout=10
        )
        logs = result.stdout + result.stderr
        if "Kafka consumer started" in logs:
            print("✅ Consumer started successfully")
        else:
            print("❌ Consumer start not found in logs")
            return False
        
        if "Processing WhatsApp message" in logs:
            print("✅ Consumer processed messages")
        else:
            print("⚠️ No message processing in recent logs")
        
        return True
        
    except Exception as e:
        print(f"❌ Log check failed: {e}")
        return False

def main():
    print("🚀 Complete Containerized Stack Test - Step 3.8")
    print("=" * 60)
    print("Prerequisites:")
    print("- podman-compose up -d")
    print("- Wait 2-3 minutes for all services to start")
    print("=" * 60)
    
    tests = [
        ("Container Status", check_container_status),
        ("Services Health", test_services_health),
        ("Webhook Flow", lambda: test_webhook_to_consumer_flow()[0]),
        ("Consumer Logs", check_consumer_logs)
    ]
    
    results = []
    test_user = None
    
    # Run initial tests
    for name, test_func in tests:
        if name == "Webhook Flow":
            success, test_user = test_webhook_to_consumer_flow()
        else:
            success = test_func()
        results.append((name, success))
        
        if not success and name in ["Container Status", "Services Health"]:
            print(f"\n❌ Critical test failed: {name}")
            break
    
    # If webhook test passed, run verification tests
    if test_user:
        consumer_success = test_consumer_processing(test_user)
        results.append(("Consumer Processing", consumer_success))
        
        multi_success = test_multiple_message_flow()
        results.append(("Multiple Messages", multi_success))
    
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    
    all_passed = all(success for _, success in results)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
    
    if all_passed:
        print("\n🎉 COMPLETE CONTAINERIZED STACK WORKING!")
        print("Architecture verified:")
        print("- ✅ WhatsApp Webhook → FastAPI")
        print("- ✅ FastAPI → Kafka Producer")
        print("- ✅ Kafka → Consumer Service")
        print("- ✅ Consumer → Database + Redis")
        print("- ✅ All services containerized and healthy")
        print("\nStep 3.8 complete - Ready for CrewAI integration!")
    else:
        print("\n❌ Some tests failed")
        print("\nDebugging commands:")
        print("- podman logs transportation_consumer")
        print("- podman logs transportation_fastapi")
        print("- podman logs transportation_kafka")

if __name__ == "__main__":
    main()

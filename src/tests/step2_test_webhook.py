import requests
import time

BASE_URL = "http://localhost:8000"

def test_database_connection():
    """Test database connection endpoint"""
    print("🔍 Testing database connection...")
    try:
        response = requests.get(f"{BASE_URL}/db/test")
        result = response.json()
        print(f"✅ Database: {result}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_create_conversation():
    """Test conversation creation"""
    print("\n🔍 Testing conversation creation...")
    try:
        data = {
            "user_id": f"test_user_{int(time.time())}",
            "session_id": f"session_{int(time.time())}"
        }
        
        response = requests.post(f"{BASE_URL}/api/conversations", json=data)
        result = response.json()
        print(f"✅ Conversation: {result}")
        
        return response.status_code == 200, result.get("session_id")
    except Exception as e:
        print(f"❌ Conversation creation failed: {e}")
        return False, None

def test_add_message(session_id):
    """Test adding message"""
    print("\n🔍 Testing message creation...")
    try:
        data = {
            "session_id": session_id,
            "role": "user",
            "content": "Test message from API"
        }
        
        response = requests.post(f"{BASE_URL}/api/messages", json=data)
        result = response.json()
        print(f"✅ Message: {result}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Message creation failed: {e}")
        return False

def test_webhook_with_db():
    """Test webhook with database integration"""
    print("\n🔍 Testing webhook with database...")
    fake_whatsapp_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "TEST_ACCOUNT_ID",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "contacts": [ {"wa_id":"123","profile":{"name":"Alice"}} ],
                                "messages": [
                                    { "id":"msg-1","from":"123","timestamp": "1650000000",
                                     "text": {"body":"Hello"}, "type":"text" }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }

    try:
        response = requests.post(f"{BASE_URL}/webhook", json=fake_whatsapp_payload)
        result = response.json()
        print(f"✅ Webhook: {result}")
        return response.status_code == 200 and "database connected" in result["message"]
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return False

def main():
    print("🚀 FastAPI Database Integration Tests")
    print("=" * 45)
    print("Make sure services are running:")
    print("- podman-compose up -d")
    print("- uv run uvicorn src.webhook_service.main:app --reload")
    print("=" * 45)

    # Test database connection first
    if not test_database_connection():
        print("\n❌ Database connection failed. Check containers.")
        return

    # Test conversation workflow
    success, session_id = test_create_conversation()
    if not success or not session_id:
        print("\n❌ Conversation creation failed.")
        return

    # Test message creation
    if not test_add_message(session_id):
        print("\n❌ Message creation failed.")
        return

    # Test webhook integration
    webhook_success = test_webhook_with_db()

    print("\n" + "=" * 45)
    print("📊 RESULTS")
    print("=" * 45)

    results = [
        ("Database Connection", True),
        ("Conversation Creation", True),
        ("Message Creation", True),
        ("Webhook Integration", webhook_success)
    ]

    all_passed = True
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
        if not success:
            all_passed = False

    if all_passed:
        print("\n🎉 DATABASE INTEGRATION READY!")
        print("Step 2.2 complete")
    else:
        print("\n❌ Some tests failed")

if __name__ == "__main__":
    main()

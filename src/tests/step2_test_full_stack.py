import requests
import time

BASE_URL = "http://localhost:8000"

def test_fastapi_health():
    """Test FastAPI is running"""
    print("🔍 Testing FastAPI health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        result = response.json()
        print(f"✅ FastAPI: {result['status']}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ FastAPI failed: {e}")
        return False

def test_database_connection():
    """Test database connection through FastAPI"""
    print("\n🔍 Testing database connection...")
    try:
        response = requests.get(f"{BASE_URL}/db/test")
        result = response.json()
        print(f"✅ Database: {result['status']}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_redis_connection():
    """Test Redis connection through FastAPI"""
    print("\n🔍 Testing Redis connection...")
    try:
        response = requests.get(f"{BASE_URL}/redis/test")
        result = response.json()
        print(f"✅ Redis: {result['status']}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False

def test_whatsapp_webhook():
    """Test WhatsApp webhook"""
    print("\n🔍 Testing WhatsApp webhook...")
    try:
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "123", "phone_number_id": "456"},
                        "contacts": [{"profile": {"name": "Test User"}, "wa_id": "789"}],
                        "messages": [{
                            "from": "789",
                            "id": "msg123", 
                            "timestamp": "1234567890",
                            "text": {"body": "Test message"},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        response = requests.post(f"{BASE_URL}/webhook", json=payload)
        result = response.json()
        print(f"✅ Webhook: {result['status']}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return False

def main():
    print("🚀 Full Stack Integration Test")
    print("=" * 40)
    print("Run: podman-compose up -d")
    print("Wait 60 seconds for all services to start")
    print("=" * 40)

    tests = [
        ("FastAPI Health", test_fastapi_health),
        ("Database", test_database_connection), 
        ("Redis", test_redis_connection),
        ("WhatsApp Webhook", test_whatsapp_webhook)
    ]

    results = []
    for name, test_func in tests:
        success = test_func()
        results.append((name, success))
        time.sleep(1)

    print("\n" + "=" * 40)
    print("📊 RESULTS")
    print("=" * 40)

    all_passed = all(success for _, success in results)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")

    if all_passed:
        print("\n🎉 FULL STACK READY!")
        print("Phase 2 complete")
    else:
        print("\n❌ Some tests failed")

if __name__ == "__main__":
    main()

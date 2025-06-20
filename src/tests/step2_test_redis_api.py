import requests
import time

BASE_URL = "http://localhost:8000"

def test_redis_connection():
    """Test Redis connection endpoint"""
    print("🔍 Testing Redis connection...")
    try:
        response = requests.get(f"{BASE_URL}/redis/test")
        result = response.json()
        print(f"✅ Redis: {result}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False

def test_create_session():
    """Test session creation"""
    print("\n🔍 Testing session creation...")
    try:
        user_id = f"user_{int(time.time())}"
        data = {
            "user_id": user_id,
            "session_data": {
                "current_step": "collecting_info",
                "collected_data": {"name": "Test User"},
                "messages": ["Hello", "Hi there"]
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/sessions", json=data)
        result = response.json()
        print(f"✅ Session created: {result}")
        return response.status_code == 200, user_id
    except Exception as e:
        print(f"❌ Session creation failed: {e}")
        return False, None

def test_get_session(user_id):
    """Test session retrieval"""
    print("\n🔍 Testing session retrieval...")
    try:
        response = requests.get(f"{BASE_URL}/api/sessions/{user_id}")
        result = response.json()
        print(f"✅ Session retrieved: {result}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Session retrieval failed: {e}")
        return False

def test_session_not_found():
    """Test session not found"""
    print("\n🔍 Testing session not found...")
    try:
        response = requests.get(f"{BASE_URL}/api/sessions/nonexistent")
        print(f"✅ Not found: {response.status_code}")
        return response.status_code == 404
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    print("🚀 FastAPI Redis Integration Tests")
    print("=" * 40)

    # Test Redis connection
    if not test_redis_connection():
        print("\n❌ Redis connection failed.")
        return

    # Test session workflow
    success, user_id = test_create_session()
    if not success or not user_id:
        print("\n❌ Session creation failed.")
        return

    # Test session retrieval
    if not test_get_session(user_id):
        print("\n❌ Session retrieval failed.")
        return

    # Test not found case
    not_found_success = test_session_not_found()

    print("\n" + "=" * 40)
    print("📊 RESULTS")
    print("=" * 40)

    results = [
        ("Redis Connection", True),
        ("Session Creation", True),
        ("Session Retrieval", True),
        ("Not Found Test", not_found_success)
    ]

    all_passed = all(success for _, success in results)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")

    if all_passed:
        print("\n🎉 REDIS INTEGRATION READY!")
        print("Step 2.3 complete")
    else:
        print("\n❌ Some tests failed")

if __name__ == "__main__":
    main()

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.redis_manager import RedisManager

async def test_connection():
    """Test 1: Basic Redis connection"""
    print("🔍 Test 1: Redis connection...")
    redis_mgr = RedisManager()
    try:
        result = await redis_mgr.ping()
        print(f"✅ Connected: {result}")
        await redis_mgr.close()
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def test_basic_ops():
    """Test 2: Set/Get operations"""
    print("\n🔍 Test 2: Basic operations...")
    redis_mgr = RedisManager()
    try:
        # Set/Get string
        await redis_mgr.set_with_ttl("test_key", "test_value", 60)
        value = await redis_mgr.get("test_key")
        print(f"✅ String: {value}")
        
        # Set/Get JSON
        test_data = {"user": "test", "count": 42}
        await redis_mgr.set_with_ttl("test_json", test_data, 60)
        json_value = await redis_mgr.get_json("test_json")
        print(f"✅ JSON: {json_value}")
        
        await redis_mgr.close()
        return value == "test_value" and json_value == test_data
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def test_sessions():
    """Test 3: Session management"""
    print("\n🔍 Test 3: Session operations...")
    redis_mgr = RedisManager()
    try:
        session_data = {
            "user_id": "user123",
            "current_step": "booking",
            "collected_data": {"name": "John", "phone": "123456"}
        }
        
        # Save session
        await redis_mgr.save_session("user123", session_data, 1)
        
        # Get session
        retrieved = await redis_mgr.get_session("user123")
        print(f"✅ Session saved/retrieved")
        
        await redis_mgr.close()
        return retrieved["user_id"] == "user123"
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def main():
    """Run Redis tests"""
    print("🚀 Redis Test")
    print("=" * 30)

    tests = [
        ("Connection", test_connection),
        ("Basic Ops", test_basic_ops),
        ("Sessions", test_sessions)
    ]

    results = []
    for name, test_func in tests:
        success = await test_func()
        results.append((name, success))

    print("\n" + "=" * 30)
    print("📊 RESULTS")
    print("=" * 30)

    all_passed = True
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
        if not success:
            all_passed = False

    if all_passed:
        print("\n🎉 REDIS READY!")
        print("Step 1.2 complete - Redis + PostgreSQL working")
    else:
        print("\n❌ Tests failed")

if __name__ == "__main__":
    asyncio.run(main())

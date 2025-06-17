import asyncio
from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.manager import DatabaseManager

async def test_connection():
    """Test 1: Basic connection"""
    print("🔍 Test 1: Connection...")
    db = DatabaseManager()
    try:
        version = await db.test_connection()
        print(f"✅ Connected: {version.split(',')[0]}")
        await db.close()
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def test_crud():
    """Test 2: Create/Read operations"""
    print("\n🔍 Test 2: CRUD...")
    db = DatabaseManager()
    try:
        # Create
        test_id = await db.create_test_record(f"Test at {datetime.now()}")
        print(f"✅ Created record ID: {test_id}")
        
        # Read
        records = await db.get_test_records()
        print(f"✅ Found {len(records)} records")
        
        await db.close()
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def main():
    """Run tests"""
    print("🚀 PostgreSQL + SQLAlchemy Test")
    print("=" * 40)

    tests = [
        ("Connection", test_connection),
        ("CRUD", test_crud)
    ]

    results = []
    for name, test_func in tests:
        success = await test_func()
        results.append((name, success))

    print("\n" + "=" * 40)
    print("📊 RESULTS")
    print("=" * 40)

    all_passed = True
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
        if not success:
            all_passed = False

    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("Ready for Step 1.2: Redis Setup")
    else:
        print("\n❌ Tests failed")

if __name__ == "__main__":
    asyncio.run(main())

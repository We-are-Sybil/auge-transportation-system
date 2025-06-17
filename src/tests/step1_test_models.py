import asyncio
import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.manager import DatabaseManager
from src.database.models import MessageRole, ConversationStep, SessionStatus
from datetime import datetime

async def test_database_init():
    """Test 1: Initialize all tables"""
    print("🔍 Test 1: Database initialization...")
    db = DatabaseManager()
    try:
        await db.init_tables()
        print("✅ All tables created")
        await db.close()
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def test_conversation_flow():
    """Test 2: Complete conversation workflow"""
    print("\n🔍 Test 2: Conversation workflow...")
    db = DatabaseManager()
    try:
        # Use unique session ID
        session_id = f"session_{int(time.time())}"
        user_id = f"user_{int(time.time())}"
        
        # Create session
        session_id_db = await db.create_conversation_session(user_id, session_id)
        print(f"✅ Session created: {session_id_db}")
        
        # Add messages with ENUMs
        msg1_id = await db.add_message(session_id_db, MessageRole.USER, "Necesito transporte")
        msg2_id = await db.add_message(session_id_db, MessageRole.ASSISTANT, "¿Para cuándo?")
        print(f"✅ Messages added: {msg1_id}, {msg2_id}")
        
        # Update session step
        await db.update_session_step(session_id_db, ConversationStep.GENERATING_QUOTE)
        print("✅ Session step updated")
        
        await db.close()
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def test_business_workflow():
    """Test 3: Business workflow integration"""
    print("\n🔍 Test 3: Business workflow...")
    db = DatabaseManager()
    try:
        # Use unique CC/NIT
        cc_nit = f"CC{int(time.time())}"
        form_number = f"FORM-{int(time.time())}"
        
        # Create client
        client_id = await db.create_client(cc_nit, "Juan Pérez", "3001234567")
        print(f"✅ Client created: {client_id}")
        
        # Create quotation request
        request_id = await db.create_quotation_request(
            form_number=form_number,
            client_id=client_id,
            quien_solicita="Juan Pérez",
            fecha_inicio_servicio=datetime(2024, 12, 25, 15, 0),
            hora_inicio_servicio="15:00",
            direccion_inicio="Calle 123, Bogotá",
            caracteristicas_servicio="Transporte aeropuerto",
            cantidad_pasajeros=2
        )
        print(f"✅ Request created: {request_id}")
        
        # Test client lookup
        found_name = await db.get_client_by_cc_nit(cc_nit)
        print(f"✅ Client found: {found_name}")
        
        await db.close()
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def test_enum_values():
    """Test 4: ENUM values work correctly"""
    print("\n🔍 Test 4: ENUM validation...")
    try:
        # Test enum values
        assert MessageRole.USER.value == "user"
        assert ConversationStep.COLLECTING_INFO.value == "collecting_info"
        assert SessionStatus.ACTIVE.value == "active"
        print("✅ ENUMs working correctly")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

async def main():
    """Run all model tests"""
    print("🚀 Complete Models Test")
    print("=" * 40)

    tests = [
        ("Database Init", test_database_init),
        ("Conversation Flow", test_conversation_flow),
        ("Business Workflow", test_business_workflow),
        ("ENUM Values", test_enum_values)
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
        print("\n🎉 MODELS READY!")
        print("Phase 1 complete - Database infrastructure working")
    else:
        print("\n❌ Tests failed")

if __name__ == "__main__":
    asyncio.run(main())

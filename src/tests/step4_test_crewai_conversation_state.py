import asyncio
import json
import sys
import os
import time
import uuid
from datetime import datetime
from sqlalchemy import select

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.crewai_extensions import ExtendedDatabaseManager
from src.database.models import MessageRole, ConversationStep, ConversationSession
from src.crewai_service.tools.conversation_tools import (
    ConversationContextTool, UpdateContextTool, SaveCollectedDataTool
)
from typing import Optional



async def test_database_extensions():
    """Test 1: Extended database manager"""
    print("🔍 Test 1: Database extensions...")
    db = ExtendedDatabaseManager()
    try:
        # Create test session
        user_id = f"crewai_test_{int(time.time())}"
        session_id = f"session_{int(time.time())}"
        
        db_session_id = await db.create_conversation_session(user_id, session_id)
        print(f"✅ Session created: {db_session_id}")
        
        # Test context retrieval
        context = await db.get_conversation_context(session_id)
        if context:
            print(f"✅ Context retrieved for user: {context['user_id']}")
            return session_id
        else:
            print("❌ Context not found")
            return None
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None
    finally:
        await db.close()


async def test_context_updates(session_id: str):
    """Test 2: Context updates"""
    print("\n🔍 Test 2: Context updates...")
    db = ExtendedDatabaseManager()
    try:
        # Update context
        updates = {
            "collected_data": {
                "client_info": {"name": "Test User", "phone": "123456789"},
                "service_request": {"origin": "Medellín", "destination": "Bogotá"}
            },
            "current_step": "collecting_info"
        }
        
        success = await db.update_conversation_context(
            session_id, updates, ConversationStep.COLLECTING_INFO
        )
        
        if success:
            print("✅ Context updated")
            
            # Verify update
            context = await db.get_conversation_context(session_id)
            collected_data = context["context"].get("collected_data", {})
            print(f"✅ Verified: {len(collected_data)} data categories saved")
            return True
        else:
            print("❌ Update failed")
            return False
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    finally:
        await db.close()


async def test_message_handling(session_id: str):
    """Test 3: Message handling"""
    print("\n🔍 Test 3: Message handling...")
    db = ExtendedDatabaseManager()
    try:
        # Get session ID (int) for adding messages
        context = await db.get_conversation_context(session_id)
        if not context:
            print("❌ Session not found")
            return False
        
        # Add messages using existing method
        conv_result = await db._get_session_internal_id(session_id)
        if not conv_result:
            print("❌ Could not get internal session ID")
            return False
            
        internal_session_id = conv_result
        print(f"{internal_session_id=}")
       
        # Add test messages
        msg1_id = await db.add_message(
            internal_session_id, 
            MessageRole.USER, 
            "Necesito transporte de Medellín a Bogotá"
        )
        
        msg2_id = await db.add_message(
            internal_session_id,
            MessageRole.ASSISTANT, 
            "Perfecto, ¿para qué fecha necesitas el servicio?"
        )
        
        print(f"✅ Messages added: {msg1_id}, {msg2_id}")
        
        # Get message history
        messages = await db.get_conversation_messages(session_id, limit=5)
        print(f"✅ Retrieved {len(messages)} messages")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    finally:
        await db.close()


async def test_crewai_tools():
    """Test 4: CrewAI tools"""
    print("\n🔍 Test 4: CrewAI tools...")
    
    try:
        # Create test session for tools
        db = ExtendedDatabaseManager()
        unique_id = str(uuid.uuid4())[:8]
        user_id = f"tool_test_{unique_id}"
        session_id = f"session_{unique_id}"
        
        await db.create_conversation_session(user_id, session_id)
        await db.close()
        
        # Test ConversationContextTool - call _async_run directly
        context_tool = ConversationContextTool()
        context_result = await context_tool._async_run(session_id, include_messages=False)
        context_data = json.loads(context_result)
        
        if "error" not in context_data:
            print("✅ ConversationContextTool working")
            print(f"   User: {context_data.get('customer_name', 'N/A')}")
        else:
            print(f"❌ ConversationContextTool error: {context_data['error']}")
            return False
        
        # Test SaveCollectedDataTool - call _async_run directly
        save_tool = SaveCollectedDataTool()
        save_result = await save_tool._async_run(
            session_id=session_id,
            data_category="client_info",
            data={"name": "Juan Pérez", "phone": "+57 300 123 4567"},
            mark_step_complete=True
        )
        save_data = json.loads(save_result)
        
        if save_data.get("success"):
            print("✅ SaveCollectedDataTool working")
        else:
            print(f"❌ SaveCollectedDataTool error: {save_data.get('error')}")
            return False
        
        # Test UpdateContextTool - call _async_run directly
        update_tool = UpdateContextTool()
        update_result = await update_tool._async_run(
            session_id=session_id,
            context_updates={"test_tool": "working"},
            current_step="collecting_info"
        )
        update_data = json.loads(update_result)
        
        if update_data.get("success"):
            print("✅ UpdateContextTool working")
        else:
            print(f"❌ UpdateContextTool error: {update_data.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Tools test failed: {e}")
        return False


async def test_service_request_creation(session_id: str):
    """Test 5: Service request creation"""
    print("\n🔍 Test 5: Service request creation...")
    db = ExtendedDatabaseManager()
    try:
        # First populate with enough data
        context_updates = {
            "collected_data": {
                "client_info": {
                    "name": "Test Client",
                    "phone": "3001234567",
                    "cc_nit": f"CC{int(time.time())}"
                },
                "service_request": {
                    "direccion_inicio": "Calle 123, Medellín",
                    "direccion_terminacion": "Calle 456, Bogotá",
                    "travel_date": "2025-07-15T08:00:00",
                    "cantidad_pasajeros": 2,
                    "caracteristicas_servicio": "Transporte aeropuerto"
                }
            }
        }
        
        await db.update_conversation_context(session_id, context_updates)
        
        # Create service request
        request_id = await db.create_service_request_from_context(session_id)
        
        if request_id:
            print(f"✅ Service request created: {request_id}")
            return True
        else:
            missing = await db.get_missing_information(session_id)
            print(f"❌ Service request failed. Missing: {missing}")
            return False
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    finally:
        await db.close()


async def run_integration_tests():
    """Run all integration tests"""
    print("🚀 CrewAI Conversation State Integration Tests")
    print("=" * 50)
    
    # Test database extensions
    session_id = await test_database_extensions()
    if not session_id:
        print("\n❌ Database extensions failed - stopping tests")
        return False
    
    # Test context updates
    if not await test_context_updates(session_id):
        print("\n❌ Context updates failed")
        return False
    
    # Test message handling
    if not await test_message_handling(session_id):
        print("\n❌ Message handling failed")
        return False
    
    # Test CrewAI tools
    if not await test_crewai_tools():
        print("\n❌ CrewAI tools failed")
        return False
    
    # Test service request creation
    if not await test_service_request_creation(session_id):
        print("\n❌ Service request creation failed")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    print(f"📊 Test session: {session_id}")
    
    return True


# Helper method for database extensions
async def _get_session_internal_id_patch():
    """Add helper method to database extensions"""
    async def _get_session_internal_id(self, session_id: str) -> Optional[int]:
        async with self.get_session() as session:
            result = await session.execute(
                select(ConversationSession).where(ConversationSession.session_id == session_id)
            )
            conv_session = result.scalar_one_or_none()
            return conv_session.id if conv_session else None
    
    # Monkey patch the method
    ExtendedDatabaseManager._get_session_internal_id = _get_session_internal_id


async def main():
    """Main test function"""
    # Add helper method
    await _get_session_internal_id_patch()
    
    success = await run_integration_tests()
    
    if success:
        print("\n🎉 CrewAI conversation state integration working!")
        print("\nNext: Test with actual CrewAI agents")
    else:
        print("\n❌ Tests failed - check error messages above")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

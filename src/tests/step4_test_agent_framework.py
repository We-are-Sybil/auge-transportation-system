import os
import sys
import asyncio
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.crewai_service.config import CrewAIConfig


def test_ollama_connection():
    """Test connection to Ollama"""
    print("🔧 Testing Ollama connection...")
    config = CrewAIConfig()

    try:
        import requests
        response = requests.get(f"{config.llm_base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Ollama connected. Available models: {len(models)}")
            
            # Check if configured model exists
            model_names = [m['name'] for m in models]
            if config.llm_model in model_names:
                print(f"✅ Model '{config.llm_model}' available")
                return True
            else:
                print(f"⚠️  Model '{config.llm_model}' not found. Available: {model_names}")
                return False
        else:
            print(f"❌ Ollama connection failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama connection error: {e}")
        print("💡 Make sure Ollama is running: `ollama serve`")
        return False


def test_crew_creation():
    """Test creating crews without executing tasks"""
    print("\n🏗️  Testing crew creation...")

    try:
        # Test conversation crew creation
        print("   Creating conversation crew...")
        from src.crewai_service.crews.conversation_crew.conversation_crew import ConversationCrew
        conv_crew = ConversationCrew()
        print("   ✅ Conversation crew created")
        
        # Test quotation crew creation  
        print("   Creating quotation crew...")
        from src.crewai_service.crews.quotation_crew.quotation_crew import QuotationCrew
        quot_crew = QuotationCrew()
        print("   ✅ Quotation crew created")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Crew creation failed: {e}")
        return False


def test_agent_coordination():
    """Test basic agent coordination with simple task"""
    print("\n🤝 Testing agent coordination...")

    if not test_ollama_connection():
        print("   ⏭️  Skipping coordination test - Ollama not available")
        return False

    try:
        from src.crewai_service.crews.coordination_test import AgentCoordinator
        coordinator = AgentCoordinator()
        
        # Simple test message
        test_message = "Hello, I need transportation services"
        print(f"   Processing: '{test_message}'")
        
        result = coordinator.process_message(test_message)
        
        if result.get('success'):
            print("   ✅ Agent coordination successful")
            return True
        else:
            print(f"   ❌ Coordination failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Coordination test failed: {e}")
        return False


def main():
    """Run all tests for Step 4.2"""
    print("🚀 Step 4.2: Agent Framework Setup Tests")
    print("=" * 50)

    tests = [
        ("Configuration", test_ollama_connection),
        ("Crew Creation", test_crew_creation), 
        ("Agent Coordination", test_agent_coordination)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")

    print(f"\n🏁 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("✅ Step 4.2 implementation ready!")
    else:
        print("⚠️  Some tests failed - check configuration and dependencies")

    return passed == total


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 STEP 4.2 AGENT FRAMEWORK READY!")
        print("Conversation and quotation agents working with coordination")
    sys.exit(0 if success else 1)

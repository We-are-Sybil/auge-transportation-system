import sys
import os
import json
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.crewai_service.crews.conversation_crew.conversation_crew import ConversationCrew
from src.crewai_service.crews.quotation_crew.quotation_crew import QuotationCrew


class AgentCoordinator:
    """Coordinates handoff between conversation and quotation crews"""
    
    def __init__(self):
        self.conversation_crew = ConversationCrew()
        self.quotation_crew = QuotationCrew()
    
    def process_message(self, message: str, user_id: str = "test_user") -> Dict[str, Any]:
        """
        Process incoming message with crew coordination
        
        Args:
            message: User message to process
            user_id: User identifier
            
        Returns:
            Coordinated response from appropriate crews
        """
        # Format message for conversation crew
        message_data = {
            "content": message,
            "user_id": user_id,
            "timestamp": "2025-06-17T10:00:00Z",
            "message_type": "text"
        }
        
        print(f"\n🎯 Processing message: '{message}'")
        print("📋 Step 1: Conversation crew analyzing message...")
        
        # Process with conversation crew first
        conversation_result = self.conversation_crew.process_conversation_message(message_data)
        
        if not conversation_result.get('success'):
            return {
                'success': False,
                'error': 'Conversation processing failed',
                'details': conversation_result
            }
        
        print("✅ Conversation analysis complete")
        
        # Check if delegation to quotation crew is needed
        response_data = conversation_result.get('response', {})
        next_action = response_data.get('next_action', '')
        
        if 'delegate_quotation' in next_action or 'quotation' in message.lower():
            print("🔄 Step 2: Delegating to quotation crew...")
            
            # Extract any transportation requirements from conversation
            request_data = {
                "origin": "Sample Origin",  # Would be extracted from conversation
                "destination": "Sample Destination",
                "cargo_type": "general",
                "weight": "1000kg",
                "service_level": "standard",
                "requested_by": user_id,
                "conversation_context": conversation_result
            }
            
            quotation_result = self.quotation_crew.create_quotation(request_data)
            
            if quotation_result.get('success'):
                print("✅ Quotation generated successfully")
                return {
                    'success': True,
                    'conversation_response': conversation_result,
                    'quotation_response': quotation_result,
                    'coordination_status': 'completed_with_quotation'
                }
            else:
                print("❌ Quotation generation failed")
                return {
                    'success': False,
                    'conversation_response': conversation_result,
                    'quotation_error': quotation_result,
                    'coordination_status': 'quotation_failed'
                }
        
        print("✅ Conversation complete - no quotation needed")
        return {
            'success': True,
            'conversation_response': conversation_result,
            'coordination_status': 'conversation_only'
        }


def run_coordination_tests():
    """Run basic coordination tests"""
    coordinator = AgentCoordinator()
    
    test_messages = [
        "Hello, I need help with transportation",
        "I need a quote for shipping from New York to Los Angeles",
        "What are your transportation services?",
        "Can you provide pricing for freight delivery?"
    ]
    
    print("🚀 Starting Agent Framework Coordination Tests")
    print("=" * 60)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n🧪 Test {i}/{len(test_messages)}")
        try:
            result = coordinator.process_message(message)
            
            print(f"\n📊 Test {i} Results:")
            print(f"   Success: {result.get('success', False)}")
            print(f"   Status: {result.get('coordination_status', 'unknown')}")
            
            if result.get('success'):
                print("   ✅ Test passed")
            else:
                print("   ❌ Test failed")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Test {i} failed with exception: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🏁 Coordination tests complete")


if __name__ == "__main__":
    run_coordination_tests()

import requests
import time

BASE_URL = "http://localhost:8000"

def create_whatsapp_payload(sender_id, message_text, sender_name="Test User"):
    """Create WhatsApp webhook payload"""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "123", "phone_number_id": "456"},
                    "contacts": [{"profile": {"name": sender_name}, "wa_id": sender_id}],
                    "messages": [{
                        "from": sender_id,
                        "id": f"msg_{int(time.time())}",
                        "timestamp": str(int(time.time())),
                        "text": {"body": message_text},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

def test_conversation_creation():
    """Test creating new conversation"""
    print("🔍 Testing conversation creation...")

    user_id = f"test_{int(time.time())}"
    payload = create_whatsapp_payload(user_id, "Hola, necesito transporte")

    response = requests.post(f"{BASE_URL}/webhook", json=payload)
    result = response.json()

    success = response.status_code == 200 and "Processed 1 WhatsApp messages" in result["message"]
    print(f"✅ New conversation: {success}")
    return success, user_id

def test_conversation_continuation(user_id):
    """Test adding messages to existing conversation"""
    print("🔍 Testing conversation continuation...")

    payload = create_whatsapp_payload(user_id, "¿Cuánto cuesta al aeropuerto?")

    response = requests.post(f"{BASE_URL}/webhook", json=payload)
    result = response.json()

    success = response.status_code == 200 and "Processed 1 WhatsApp messages" in result["message"]
    print(f"✅ Continued conversation: {success}")
    return success

def test_session_retrieval(user_id):
    """Test session data retrieval"""
    print("🔍 Testing session retrieval...")

    response = requests.get(f"{BASE_URL}/api/sessions/{user_id}")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Session found: {result['data']['last_message']}")
        return True
    else:
        print(f"❌ Session not found: {response.status_code}")
        return False

def main():
    print("🚀 Conversation Persistence Test")
    print("=" * 35)

    # Test new conversation
    success, user_id = test_conversation_creation()
    if not success:
        print("❌ Conversation creation failed")
        return

    time.sleep(1)

    # Test conversation continuation
    if not test_conversation_continuation(user_id):
        print("❌ Conversation continuation failed")
        return

    time.sleep(1)

    # Test session retrieval
    if not test_session_retrieval(user_id):
        print("❌ Session retrieval failed")
        return

    print("\n🎉 CONVERSATION PERSISTENCE WORKING!")
    print("Step 2.7 complete")

if __name__ == "__main__":
    main()

import requests
import json

BASE_URL = "http://localhost:8000"

# Sample WhatsApp webhook payload
SAMPLE_WHATSAPP_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123456789",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "+1234567890",
                            "phone_number_id": "987654321"
                        },
                        "contacts": [
                            {
                                "profile": {
                                    "name": "John Doe"
                                },
                                "wa_id": "5551234567"
                            }
                        ],
                        "messages": [
                            {
                                "from": "5551234567",
                                "id": "wamid.12345",
                                "timestamp": "1669233778",
                                "text": {
                                    "body": "Necesito transporte al aeropuerto mañana"
                                },
                                "type": "text"
                            }
                        ]
                    },
                    "field": "messages"
                }
            ]
        }
    ]
}

def test_webhook_verification():
    """Test WhatsApp webhook verification (GET)"""
    print("🔍 Testing webhook verification...")
    try:
        params = {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'your_verify_token_here',
            'hub.challenge': 'test_challenge_123'
        }
        
        response = requests.get(f"{BASE_URL}/webhook", params=params)
        print(f"✅ Verification: {response.status_code} - {response.text}")
        
        return response.status_code == 200 and response.text == "test_challenge_123"
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def test_whatsapp_webhook_parsing():
    """Test WhatsApp webhook with real payload structure"""
    print("🔍 Testing WhatsApp webhook parsing...")
    try:
        response = requests.post(
            f"{BASE_URL}/webhook",
            json=SAMPLE_WHATSAPP_PAYLOAD,
            headers={"Content-Type": "application/json"}
        )
        
        result = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Response: {result}")
        
        return (response.status_code == 200 and 
                "Processed 1 WhatsApp messages" in result.get("message", ""))
    except Exception as e:
        print(f"❌ WhatsApp webhook test failed: {e}")
        return False

def test_whatsapp_models():
    """Test WhatsApp model validation"""
    print("\n🔍 Testing WhatsApp models...")
    try:
        # Import locally to test
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        
        from src.webhook_service.whatsapp_models import WhatsAppWebhook
        
        # Parse sample payload
        webhook = WhatsAppWebhook(**SAMPLE_WHATSAPP_PAYLOAD)
        print(f"✅ Parsed webhook: {webhook.object}")
        print(f"✅ Messages: {len(webhook.entry[0].changes[0].value.messages)}")
        
        return True
    except Exception as e:
        print(f"❌ Model validation failed: {e}")
        return False

def test_session_storage():
    """Test if session is stored after webhook"""
    print("\n🔍 Testing session storage...")
    try:
        # Send webhook first
        requests.post(f"{BASE_URL}/webhook", json=SAMPLE_WHATSAPP_PAYLOAD)
        
        # Check if session was stored
        response = requests.get(f"{BASE_URL}/api/sessions/5551234567")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Session stored: {result}")
            return True
        else:
            print(f"❌ Session not found: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Session test failed: {e}")
        return False

def main():
    print("🚀 WhatsApp Webhook Structure Tests")
    print("=" * 40)

    tests = [
        ("Webhook Verification", test_webhook_verification),
        ("Model Validation", test_whatsapp_models),
        ("Webhook Parsing", test_whatsapp_webhook_parsing),
        ("Session Storage", test_session_storage)
    ]

    results = []
    for name, test_func in tests:
        success = test_func()
        results.append((name, success))

    print("\n" + "=" * 40)
    print("📊 RESULTS")
    print("=" * 40)

    all_passed = all(success for _, success in results)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")

    if all_passed:
        print("\n🎉 WHATSAPP WEBHOOK READY!")
        print("Step 2.4 complete")
    else:
        print("\n❌ Some tests failed")

if __name__ == "__main__":
    main()

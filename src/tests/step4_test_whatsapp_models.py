import sys
from pathlib import Path
import requests
from typing import Dict, Any

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.webhook_service.wa_models.base_models import (
        InteractiveType,
)
from src.webhook_service.wa_models.helpers import (
        create_text_message,
        create_reply_button,
        create_list_row,
        create_list_section,
        create_cta_url_button,
        parse_webhook,
        extract_user_message,
        extract_user_phone,
        extract_button_response,
)

from src.webhook_service.wa_models.base_models import (
    # WhatsAppBaseModel,
    MessageType,
    FooterContent,
    # ContactAddress,
    # ContactEmail,
    # ContactPhone,
    # ContactName,
    # ContactOrganization,
    # ContactUrl,
    # WhatsAppConfig,
)
from src.webhook_service.wa_models.message_models import (
    WhatsAppMessageRequest,
    # TextMessage,
    # ImageMessage,
    # LocationMessage,
)
from src.webhook_service.wa_models.interactive_models import (
    # ButtonReply,
    # CTAUrlAction,
    # CTAUrlParameters,
    ButtonAction,
    Interactive,
    InteractiveBody,
    ListAction,
    # InteractiveButton,
    # ListRow,
    # ListSection,
)
# from src.webhook_service.wa_models.webhook_models import (
#     WhatsAppWebhook,
# )


class WhatsAppClient:
    """WhatsApp Cloud API client"""
    
    def __init__(self, access_token: str, phone_number_id: str, api_version: str = "v23.0"):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    
    def send_message(self, message: WhatsAppMessageRequest) -> Dict[str, Any]:
        """Send WhatsApp message"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        payload = message.model_dump(exclude_none=True, by_alias=True)
        response = requests.post(self.base_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def test_text_messages():
    """Test text message creation"""
    simple_text = create_text_message("+1234567890", "Hello! Welcome to our service.")
    text_with_link = create_text_message("+1234567890", "Visit: https://example.com", preview_url=True)
    return [simple_text, text_with_link]


def test_interactive_buttons():
    """Test interactive button messages"""
    buttons = [
        create_reply_button("yes_btn", "Yes"),
        create_reply_button("no_btn", "No"),
        create_reply_button("maybe_btn", "Maybe")
    ]
    
    interactive = Interactive(
        type=InteractiveType.BUTTON,
        body=InteractiveBody(text="Continue with order?"),
        footer=FooterContent(text="Select option"),
        action=ButtonAction(buttons=buttons)
    )
    
    return WhatsAppMessageRequest(
        to="+1234567890",
        type=MessageType.INTERACTIVE,
        interactive=interactive
    )


def test_interactive_list():
    """Test interactive list messages"""
    shipping_rows = [
        create_list_row("express", "Express", "Next day"),
        create_list_row("standard", "Standard", "3-5 days"),
        create_list_row("economy", "Economy", "7-10 days")
    ]
    
    sections = [create_list_section("Shipping Options", shipping_rows)]
    
    interactive = Interactive(
        type=InteractiveType.LIST,
        body=InteractiveBody(text="Select shipping preference:"),
        action=ListAction(button="View Options", sections=sections)
    )
    
    return WhatsAppMessageRequest(
        to="+1234567890",
        type=MessageType.INTERACTIVE,
        interactive=interactive
    )


def test_cta_button():
    """Test CTA URL button"""
    interactive = Interactive(
        type=InteractiveType.CTA_URL,
        body=InteractiveBody(text="Ready to book?"),
        action=create_cta_url_button("Book Now", "https://booking.example.com")
    )
    
    return WhatsAppMessageRequest(
        to="+1234567890",
        type=MessageType.INTERACTIVE,
        interactive=interactive
    )


def test_webhook_handling():
    """Test webhook parsing"""
    webhook_data = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "102290129340398",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15550783881",
                        "phone_number_id": "106540352242922"
                    },
                    "contacts": [{"profile": {"name": "John"}, "wa_id": "1234567890"}],
                    "messages": [{
                        "from": "1234567890",
                        "id": "wamid.123",
                        "timestamp": "1712595443",
                        "type": "text",
                        "text": {"body": "Hello, need help"}
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    webhook = parse_webhook(webhook_data)
    user_phone = extract_user_phone(webhook)
    user_message = extract_user_message(webhook)
    
    return create_text_message(f"+{user_phone}", "Thanks! We'll respond shortly.")


def test_interactive_response():
    """Test interactive response handling"""
    webhook_data = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "102290129340398",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "15550783881", "phone_number_id": "106540352242922"},
                    "contacts": [{"profile": {"name": "John"}, "wa_id": "1234567890"}],
                    "messages": [{
                        "from": "1234567890",
                        "id": "wamid.456",
                        "timestamp": "1714510003",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": "yes_btn", "title": "Yes"}
                        }
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    webhook = parse_webhook(webhook_data)
    return extract_button_response(webhook)


def main():
    """Run WhatsApp model examples"""
    print("🔧 WhatsApp Cloud API Model Tests")
    print("=" * 40)

    tests = [
        ("Text Messages", test_text_messages),
        ("Interactive Buttons", test_interactive_buttons), 
        ("Interactive List", test_interactive_list),
        ("CTA Button", test_cta_button),
        ("Webhook Handling", test_webhook_handling),
        ("Interactive Response", test_interactive_response)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            print(f"✅ {test_name}: Created successfully")
            results.append((test_name, True))
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            results.append((test_name, False))

    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All WhatsApp models working correctly!")
    else:
        print("⚠️  Some tests failed - check model definitions")

    return passed == total


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 WHATSAPP MODELS READY!")
    else:
        print("\n❌ Fix errors before integration")

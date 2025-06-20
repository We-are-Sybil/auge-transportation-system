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
    # parse_webhook,
    # Vextract_user_message,
    # Vextract_user_phone,
    # Vextract_button_response,
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
    LocationRequestAction,
    # InteractiveButton,
    # ListRow,
    # ListSection,
)
from src.webhook_service.wa_models.client import WhatsAppClient


def should_send_messages():
    """Check if we should actually send WhatsApp messages"""
    import os
    return os.getenv('SEND_WHATSAPP_MESSAGES', 'false').lower() == 'true'


def send_or_test(message: WhatsAppMessageRequest) -> bool:
    """Send message if env var is set, otherwise just test creation"""
    if should_send_messages():
        client = get_whatsapp_client()
        if not client:
            print("   ⚠️  No WhatsApp credentials - testing model only")
            return True
        try:
            response = client.send_message(message)
            return response.get('messages', [{}])[0].get('id') is not None
        except Exception as e:
            print(f"   ❌ Send failed: {e}")
            return False
    else:
        # Just test model creation
        return message.model_dump(exclude_none=True) is not None


def test_text_messages():
    """Test text message creation/sending"""
    simple_text = create_text_message(get_test_phone(), "Hello! Welcome to our service.")
    text_with_link = create_text_message(get_test_phone(), "Visit: https://example.com", preview_url=True)
    
    return send_or_test(simple_text) and send_or_test(text_with_link)


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
    
    message = WhatsAppMessageRequest(
        to=get_test_phone(),
        type=MessageType.INTERACTIVE,
        interactive=interactive
    )
    
    return send_or_test(message)


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
    
    message = WhatsAppMessageRequest(
        to=get_test_phone(),
        type=MessageType.INTERACTIVE,
        interactive=interactive
    )
    
    return send_or_test(message)


def test_cta_button():
    """Test CTA URL button"""
    interactive = Interactive(
        type=InteractiveType.CTA_URL,
        body=InteractiveBody(text="Ready to book?"),
        action=create_cta_url_button("Book Now", "https://booking.example.com")
    )
    
    message = WhatsAppMessageRequest(
        to=get_test_phone(),
        type=MessageType.INTERACTIVE,
        interactive=interactive
    )
    
    return send_or_test(message)


def test_location_request():
    """Test sending location request message"""
    interactive = Interactive(
        type=InteractiveType.LOCATION_REQUEST_MESSAGE,
        body=InteractiveBody(text="Please share your pickup location for transportation service."),
        action=LocationRequestAction()
    )
    
    message = WhatsAppMessageRequest(
        to=get_test_phone(),
        type=MessageType.INTERACTIVE,
        interactive=interactive
    )
    
    return send_or_test(message)


def test_transportation_buttons():
    """Test sending transportation service buttons"""
    buttons = [
        create_reply_button("book_now", "Book Now"),
        create_reply_button("get_quote", "Get Quote"),
        create_reply_button("track_order", "Track Order")
    ]
    
    interactive = Interactive(
        type=InteractiveType.BUTTON,
        body=InteractiveBody(text="How can we help with your transportation needs?"),
        footer=FooterContent(text="Select an option below"),
        action=ButtonAction(buttons=buttons)
    )
    
    message = WhatsAppMessageRequest(
        to=get_test_phone(),
        type=MessageType.INTERACTIVE,
        interactive=interactive
    )
    
    return send_or_test(message)


def test_service_list():
    """Test sending transportation service list"""
    services = [
        create_list_row("airport", "Airport Transfer", "Professional airport service"),
        create_list_row("city", "City Transport", "Local transportation"),
        create_list_row("luxury", "Luxury Service", "Premium vehicles")
    ]
    
    sections = [create_list_section("Transportation Services", services)]
    
    interactive = Interactive(
        type=InteractiveType.LIST,
        body=InteractiveBody(text="Select your transportation service:"),
        action=ListAction(button="View Services", sections=sections)
    )
    
    message = WhatsAppMessageRequest(
        to=get_test_phone(),
        type=MessageType.INTERACTIVE,
        interactive=interactive
    )
    
    return send_or_test(message)


def get_whatsapp_client():
    """Get WhatsApp client with credentials"""
    import os
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    
    if not access_token or not phone_number_id:
        return None
    
    return WhatsAppClient(access_token, phone_number_id)


def get_test_phone():
    """Get test phone number"""
    import os
    return os.getenv('TEST_PHONE_NUMBER', '+1234567890')


def main():
    """Run WhatsApp model examples"""
    print("🔧 WhatsApp Cloud API Model Tests")
    print("=" * 40)

    tests = [
        ("Text Messages", test_text_messages),
        ("Interactive Buttons", test_interactive_buttons), 
        ("Interactive List", test_interactive_list),
        ("CTA Button", test_cta_button),
        ("Location Request", test_location_request),
        ("Transportation Buttons", test_transportation_buttons),
        ("Service List", test_service_list)
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

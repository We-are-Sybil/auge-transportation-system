import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.webhook_service.wa_models.base_models import MessageType
from src.webhook_service.wa_models.message_models import (
    WhatsAppMessageRequest,
    TextMessage,
    ImageMessage,
    LocationMessage,
)
from src.webhook_service.wa_models.interactive_models import (
    ButtonReply,
    CTAUrlAction,
    CTAUrlParameters,
    Interactive,
    InteractiveButton,
    ListRow,
    ListSection,
)
from src.webhook_service.wa_models.webhook_models import WhatsAppWebhook

# Message models

def create_text_message(
    to: str, text: str, preview_url: bool = False
) -> WhatsAppMessageRequest:
    return WhatsAppMessageRequest(
        to=to,
        type=MessageType.TEXT,
        text=TextMessage(body=text, preview_url=preview_url),
    )


def create_image_message(
    to: str, media_id: str = None, media_link: str = None, caption: str = None
) -> WhatsAppMessageRequest:
    return WhatsAppMessageRequest(
        to=to,
        type=MessageType.IMAGE,
        image=ImageMessage(id=media_id, link=media_link, caption=caption),
    )


def create_location_message(
    to: str, latitude: str, longitude: str, name: str = None, address: str = None
) -> WhatsAppMessageRequest:
    return WhatsAppMessageRequest(
        to=to,
        type=MessageType.LOCATION,
        location=LocationMessage(
            latitude=latitude, longitude=longitude, name=name, address=address
        ),
    )

# Interactive models

def create_reply_button(id: str, title: str) -> InteractiveButton:
    return InteractiveButton(reply=ButtonReply(id=id, title=title))


def create_list_row(id: str, title: str, description: Optional[str] = None) -> ListRow:
    return ListRow(id=id, title=title, description=description)


def create_list_section(title: str, rows: List[ListRow]) -> ListSection:
    return ListSection(title=title, rows=rows)


def create_cta_url_button(display_text: str, url: str) -> CTAUrlAction:
    return CTAUrlAction(parameters=CTAUrlParameters(display_text=display_text, url=url))


def create_interactive_message(
    to: str, interactive: Interactive
) -> WhatsAppMessageRequest:
    return WhatsAppMessageRequest(
        to=to, type=MessageType.INTERACTIVE, interactive=interactive
    )

# Webhook models

def parse_webhook(webhook_data: Dict[str, Any]) -> WhatsAppWebhook:
    """Parse webhook data into structured model"""
    return WhatsAppWebhook.model_validate(webhook_data)


def extract_user_message(webhook: WhatsAppWebhook) -> Optional[str]:
    """Extract user text message content from webhook"""
    message = webhook.get_first_message()
    if message and message.type == "text" and message.text:
        return message.text.body
    return None


def extract_user_phone(webhook: WhatsAppWebhook) -> Optional[str]:
    """Extract user phone number from webhook"""
    message = webhook.get_first_message()
    if message:
        return message.from_
    return None


def is_interactive_response(webhook: WhatsAppWebhook) -> bool:
    """Check if webhook contains an interactive message response"""
    message = webhook.get_first_message()
    return message is not None and message.type == "interactive"


def extract_button_response(webhook: WhatsAppWebhook) -> Optional[str]:
    """Extract button ID from interactive response"""
    message = webhook.get_first_message()
    if (message and message.type == "interactive" and 
        message.interactive and message.interactive.type == "button_reply"):
        return message.interactive.button_reply.id
    return None


def extract_list_response(webhook: WhatsAppWebhook) -> Optional[str]:
    """Extract list row ID from interactive response"""
    message = webhook.get_first_message()
    if (message and message.type == "interactive" and 
        message.interactive and message.interactive.type == "list_reply"):
        return message.interactive.list_reply.id
    return None

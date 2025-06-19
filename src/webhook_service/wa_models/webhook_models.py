from pydantic import Field, field_validator, model_validator
from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime
from .base_models import WhatsAppBaseModel
from .interactive_models import InteractiveWebhookResponse


class WebhookProfile(WhatsAppBaseModel):
    """User profile information in webhook"""
    
    name: str = Field(description="WhatsApp user display name")


class WebhookContact(WhatsAppBaseModel):
    """Contact information in webhook"""
    
    profile: WebhookProfile = Field(description="User profile")
    wa_id: str = Field(description="WhatsApp user ID")


class WebhookMetadata(WhatsAppBaseModel):
    """Metadata in webhook payload"""
    
    display_phone_number: str = Field(description="Business phone number display format")
    phone_number_id: str = Field(description="Business phone number ID")


class WebhookContext(WhatsAppBaseModel):
    """Context information for replied messages"""
    
    from_: str = Field(alias="from", description="Sender phone number")
    id: str = Field(description="Message ID being replied to")


# Incoming message content models

class IncomingTextMessage(WhatsAppBaseModel):
    """Incoming text message content"""
    
    body: str = Field(description="Text message content")


class IncomingMediaMessage(WhatsAppBaseModel):
    """Incoming media message content"""
    
    caption: Optional[str] = Field(None, description="Media caption")
    mime_type: str = Field(description="Media MIME type")
    sha256: str = Field(description="Media file hash")
    id: str = Field(description="Media ID for downloading")


class IncomingLocationMessage(WhatsAppBaseModel):
    """Incoming location message content"""
    
    latitude: float = Field(description="Location latitude")
    longitude: float = Field(description="Location longitude")
    name: Optional[str] = Field(None, description="Location name")
    address: Optional[str] = Field(None, description="Location address")


class IncomingReactionMessage(WhatsAppBaseModel):
    """Incoming reaction message content"""
    
    message_id: str = Field(description="ID of message being reacted to")
    emoji: str = Field(description="Reaction emoji")


class IncomingReferralMessage(WhatsAppBaseModel):
    """Incoming referral from Click to WhatsApp ads"""
    
    source_url: str = Field(description="Source URL of the ad or post")
    source_id: str = Field(description="Ad ID")
    source_type: Literal["ad", "post"] = Field(description="Source type")
    headline: str = Field(description="Ad headline")
    body: str = Field(description="Ad body text")
    media_type: Literal["image", "video"] = Field(description="Media type")
    image_url: Optional[str] = Field(None, description="Image URL")
    video_url: Optional[str] = Field(None, description="Video URL")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    ctwa_clid: str = Field(description="Click to WhatsApp click ID")


class IncomingButtonMessage(WhatsAppBaseModel):
    """Incoming button reply (legacy template format)"""
    
    text: str = Field(description="Button text")
    payload: str = Field(description="Button payload")


class IncomingContactMessage(WhatsAppBaseModel):
    """Incoming contact message"""
    
    # Note: This would include all the contact fields from the outgoing format
    # For brevity, showing key fields - full implementation would mirror Contact model
    name: Dict[str, Any] = Field(description="Contact name information")
    phones: Optional[List[Dict[str, Any]]] = Field(None, description="Phone numbers")
    emails: Optional[List[Dict[str, Any]]] = Field(None, description="Email addresses")


class IncomingErrorMessage(WhatsAppBaseModel):
    """Error information for unsupported messages"""
    
    code: int = Field(description="Error code")
    title: str = Field(description="Error title")
    details: str = Field(description="Error details")


# Main incoming message model

class IncomingMessage(WhatsAppBaseModel):
    """Incoming WhatsApp message from webhook"""
    
    from_: str = Field(alias="from", description="Sender phone number")
    id: str = Field(description="Message ID")
    timestamp: str = Field(description="Message timestamp")
    type: str = Field(description="Message type")
    
    # Message content (based on type)
    text: Optional[IncomingTextMessage] = Field(None, description="Text content")
    image: Optional[IncomingMediaMessage] = Field(None, description="Image content")
    audio: Optional[IncomingMediaMessage] = Field(None, description="Audio content")
    video: Optional[IncomingMediaMessage] = Field(None, description="Video content")
    document: Optional[IncomingMediaMessage] = Field(None, description="Document content")
    sticker: Optional[IncomingMediaMessage] = Field(None, description="Sticker content")
    location: Optional[IncomingLocationMessage] = Field(None, description="Location content")
    contacts: Optional[List[IncomingContactMessage]] = Field(None, description="Contacts content")
    reaction: Optional[IncomingReactionMessage] = Field(None, description="Reaction content")
    referral: Optional[IncomingReferralMessage] = Field(None, description="Referral content")
    button: Optional[IncomingButtonMessage] = Field(None, description="Button reply content")
    interactive: Optional[InteractiveWebhookResponse] = Field(None, description="Interactive response")
    
    # Context for replies
    context: Optional[WebhookContext] = Field(None, description="Reply context")
    
    # Errors for unsupported messages
    errors: Optional[List[IncomingErrorMessage]] = Field(None, description="Error information")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp format"""
        try:
            # WhatsApp sends Unix timestamps as strings
            int(v)
        except ValueError:
            raise ValueError('Timestamp must be a valid Unix timestamp string')
        return v
    
    def get_timestamp_datetime(self) -> datetime:
        """Convert timestamp to datetime object"""
        return datetime.fromtimestamp(int(self.timestamp))
    
    def get_message_content(self) -> Optional[Union[str, Dict[str, Any]]]:
        """Extract the actual message content based on type"""
        content_map = {
            'text': lambda: self.text.body if self.text else None,
            'image': lambda: {'caption': self.image.caption, 'id': self.image.id} if self.image else None,
            'audio': lambda: {'id': self.audio.id} if self.audio else None,
            'video': lambda: {'caption': self.video.caption, 'id': self.video.id} if self.video else None,
            'document': lambda: {'caption': self.document.caption, 'id': self.document.id} if self.document else None,
            'location': lambda: {
                'latitude': self.location.latitude,
                'longitude': self.location.longitude,
                'name': self.location.name,
                'address': self.location.address
            } if self.location else None,
            'reaction': lambda: {
                'emoji': self.reaction.emoji,
                'message_id': self.reaction.message_id
            } if self.reaction else None,
            'interactive': lambda: self.interactive.model_dump() if self.interactive else None,
            'button': lambda: {
                'text': self.button.text,
                'payload': self.button.payload
            } if self.button else None
        }
        
        return content_map.get(self.type, lambda: None)()


# Webhook value container

class WebhookValue(WhatsAppBaseModel):
    """Value container in webhook payload"""
    
    messaging_product: Literal["whatsapp"] = Field(description="Messaging product")
    metadata: WebhookMetadata = Field(description="Webhook metadata")
    contacts: Optional[List[WebhookContact]] = Field(None, description="Contact information")
    messages: Optional[List[IncomingMessage]] = Field(None, description="Incoming messages")
    statuses: Optional[List[Dict[str, Any]]] = Field(None, description="Message status updates")


class WebhookChange(WhatsAppBaseModel):
    """Change container in webhook payload"""
    
    value: WebhookValue = Field(description="Webhook value data")
    field: Literal["messages"] = Field(description="Changed field")


class WebhookEntry(WhatsAppBaseModel):
    """Entry container in webhook payload"""
    
    id: str = Field(description="WhatsApp Business Account ID")
    changes: List[WebhookChange] = Field(description="List of changes")


class WhatsAppWebhook(WhatsAppBaseModel):
    """Complete WhatsApp webhook payload"""
    
    object: Literal["whatsapp_business_account"] = Field(description="Object type")
    entry: List[WebhookEntry] = Field(description="Webhook entries")
    
    def get_messages(self) -> List[IncomingMessage]:
        """Extract all incoming messages from webhook"""
        messages = []
        for entry in self.entry:
            for change in entry.changes:
                if change.value.messages:
                    messages.extend(change.value.messages)
        return messages
    
    def get_first_message(self) -> Optional[IncomingMessage]:
        """Get the first message from webhook (common use case)"""
        messages = self.get_messages()
        return messages[0] if messages else None
    
    def get_business_phone_id(self) -> Optional[str]:
        """Extract business phone number ID"""
        for entry in self.entry:
            for change in entry.changes:
                return change.value.metadata.phone_number_id
        return None


# Webhook verification model

class WebhookVerification(WhatsAppBaseModel):
    """Webhook verification challenge"""
    
    mode: str = Field(description="Verification mode")
    token: str = Field(description="Verification token")
    challenge: str = Field(description="Challenge string to echo back")

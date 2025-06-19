from pydantic import Field, field_validator, model_validator
from typing import Optional, List, Literal
from datetime import datetime
from .base_models import (
    WhatsAppBaseModel, MessageType,
    ContactAddress, ContactEmail, ContactPhone, ContactName, 
    ContactOrganization, ContactUrl, WhatsAppConfig
)

from .interactive_models import Interactive


class TextMessage(WhatsAppBaseModel):
    """Text message content"""
    
    preview_url: Optional[bool] = Field(
        None,
        description="Enable link preview for URLs in text"
    )
    body: str = Field(
        description="Text message body",
        min_length=1,
        max_length=WhatsAppConfig.MAX_TEXT_LENGTH
    )


class ImageMessage(WhatsAppBaseModel):
    """Image message content"""
    
    id: Optional[str] = Field(None, description="Uploaded media ID")
    link: Optional[str] = Field(None, description="Public image URL")
    caption: Optional[str] = Field(
        None,
        description="Image caption",
        max_length=WhatsAppConfig.MAX_CAPTION_LENGTH
    )
    
    def model_post_init(self, __context) -> None:
        """Ensure exactly one of id or link is provided"""
        if not self.id and not self.link:
            raise ValueError('Either id or link must be provided')
        if self.id and self.link:
            raise ValueError('Cannot provide both id and link')


class AudioMessage(WhatsAppBaseModel):
    """Audio message content"""
    
    id: Optional[str] = Field(None, description="Uploaded media ID")
    link: Optional[str] = Field(None, description="Public audio URL")
    
    def model_post_init(self, __context) -> None:
        """Ensure exactly one of id or link is provided"""
        if not self.id and not self.link:
            raise ValueError('Either id or link must be provided')
        if self.id and self.link:
            raise ValueError('Cannot provide both id and link')


class VideoMessage(WhatsAppBaseModel):
    """Video message content"""
    
    id: Optional[str] = Field(None, description="Uploaded media ID")
    link: Optional[str] = Field(None, description="Public video URL")
    caption: Optional[str] = Field(
        None,
        description="Video caption",
        max_length=WhatsAppConfig.MAX_CAPTION_LENGTH
    )
    
    def model_post_init(self, __context) -> None:
        """Ensure exactly one of id or link is provided"""
        if not self.id and not self.link:
            raise ValueError('Either id or link must be provided')
        if self.id and self.link:
            raise ValueError('Cannot provide both id and link')


class DocumentMessage(WhatsAppBaseModel):
    """Document message content"""
    
    id: Optional[str] = Field(None, description="Uploaded media ID")
    link: Optional[str] = Field(None, description="Public document URL")
    caption: Optional[str] = Field(
        None,
        description="Document caption",
        max_length=WhatsAppConfig.MAX_CAPTION_LENGTH
    )
    filename: Optional[str] = Field(
        None,
        description="Document filename with extension"
    )
    
    def model_post_init(self, __context) -> None:
        """Ensure exactly one of id or link is provided"""
        if not self.id and not self.link:
            raise ValueError('Either id or link must be provided')
        if self.id and self.link:
            raise ValueError('Cannot provide both id and link')


class LocationMessage(WhatsAppBaseModel):
    """Location message content"""
    
    latitude: str = Field(description="Location latitude in decimal degrees")
    longitude: str = Field(description="Location longitude in decimal degrees")
    name: Optional[str] = Field(None, description="Location name")
    address: Optional[str] = Field(None, description="Location address")
    
    @field_validator('latitude', 'longitude')
    @classmethod
    def validate_coordinates(cls, v: str) -> str:
        """Validate latitude/longitude format"""
        try:
            coord = float(v)
            # Basic coordinate range validation
            if 'latitude' in cls.model_fields and abs(coord) > 90:
                raise ValueError('Latitude must be between -90 and 90')
            if 'longitude' in cls.model_fields and abs(coord) > 180:
                raise ValueError('Longitude must be between -180 and 180')
        except ValueError as e:
            if 'could not convert' in str(e):
                raise ValueError('Coordinate must be a valid number')
            raise
        return v


class Contact(WhatsAppBaseModel):
    """Individual contact information"""
    
    addresses: Optional[List[ContactAddress]] = Field(None, description="Contact addresses")
    birthday: Optional[str] = Field(None, description="Birthday in YYYY-MM-DD format")
    emails: Optional[List[ContactEmail]] = Field(None, description="Email addresses")
    name: ContactName = Field(description="Contact name information")
    org: Optional[ContactOrganization] = Field(None, description="Organization information")
    phones: Optional[List[ContactPhone]] = Field(None, description="Phone numbers")
    urls: Optional[List[ContactUrl]] = Field(None, description="Website URLs")
    
    @field_validator('birthday')
    @classmethod
    def validate_birthday(cls, v: Optional[str]) -> Optional[str]:
        """Validate birthday format"""
        if v is None:
            return v
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Birthday must be in YYYY-MM-DD format')
        return v


class ContactsMessage(WhatsAppBaseModel):
    """Contacts message content"""
    
    contacts: List[Contact] = Field(
        description="List of contacts to share",
        min_length=1
    )


# Main message request model

class WhatsAppMessageRequest(WhatsAppBaseModel):
    """Complete WhatsApp message request"""
    
    messaging_product: Literal["whatsapp"] = Field(
        default="whatsapp",
        description="Messaging product identifier"
    )
    recipient_type: Literal["individual"] = Field(
        default="individual",
        description="Type of recipient"
    )
    to: str = Field(description="Recipient WhatsApp number in international format")
    type: MessageType = Field(description="Type of message being sent")
    
    # Message content (only one should be provided based on type)
    text: Optional[TextMessage] = Field(None, description="Text message content")
    image: Optional[ImageMessage] = Field(None, description="Image message content")
    audio: Optional[AudioMessage] = Field(None, description="Audio message content")
    video: Optional[VideoMessage] = Field(None, description="Video message content")
    document: Optional[DocumentMessage] = Field(None, description="Document message content")
    location: Optional[LocationMessage] = Field(None, description="Location message content")
    contacts: Optional[ContactsMessage] = Field(None, description="Contacts message content")
    interactive: Optional[Interactive] = Field(None, description="Interactive message content")
    
    @field_validator('to')
    @classmethod
    def validate_recipient_phone(cls, v: str) -> str:
        """Validate recipient phone number format"""
        if not v.startswith('+'):
            raise ValueError('Phone number must start with +')
        digits = v[1:]
        if not digits.isdigit():
            raise ValueError('Phone number must contain only digits after +')
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError('Phone number must be between 7 and 15 digits')
        return v
    
    @model_validator(mode='after')
    def validate_message_content(self) -> 'WhatsAppMessageRequest':
        """Validate that message content matches the specified type"""
        content_map = {
            MessageType.TEXT: self.text,
            MessageType.IMAGE: self.image,
            MessageType.AUDIO: self.audio,
            MessageType.VIDEO: self.video,
            MessageType.DOCUMENT: self.document,
            MessageType.LOCATION: self.location,
            MessageType.CONTACTS: self.contacts,
            MessageType.INTERACTIVE: self.interactive
        }
        
        expected_content = content_map[self.type]
        if expected_content is None:
            raise ValueError(f'Message type {self.type} requires corresponding content')
        
        # Ensure no other content is provided
        provided_content = [content for content in content_map.values() if content is not None]
        if len(provided_content) > 1:
            raise ValueError('Only one message content type should be provided')
        
        return self


# Response models

class WhatsAppContact(WhatsAppBaseModel):
    """Contact information in API response"""
    
    input: str = Field(description="Input phone number")
    wa_id: str = Field(description="WhatsApp ID")


class WhatsAppMessageResponse(WhatsAppBaseModel):
    """Message ID in API response"""
    
    id: str = Field(description="WhatsApp message ID")


class WhatsAppApiResponse(WhatsAppBaseModel):
    """Complete WhatsApp API response"""
    
    messaging_product: Literal["whatsapp"] = Field(description="Messaging product")
    contacts: List[WhatsAppContact] = Field(description="Contact information")
    messages: List[WhatsAppMessageResponse] = Field(description="Message information")

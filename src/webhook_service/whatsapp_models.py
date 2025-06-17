"""WhatsApp webhook payload models"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class WhatsAppMessageType(str, Enum):
    TEXT = "text"
    AUDIO = "audio" 
    BUTTON = "button"
    DOCUMENT = "document"
    IMAGE = "image"
    INTERACTIVE = "interactive"
    LOCATION = "location"
    STICKER = "sticker"
    TEMPLATE = "template"
    VIDEO = "video"
    CONTACTS = "contacts"
    REACTION = "reaction"
    ORDER = "order"
    SYSTEM = "system"

class WhatsAppText(BaseModel):
    body: str

class WhatsAppProfile(BaseModel):
    name: str

class WhatsAppContact(BaseModel):
    profile: WhatsAppProfile
    wa_id: str

class WhatsAppMessage(BaseModel):
    id: str
    from_: str = Field(alias='from')
    timestamp: str
    type: WhatsAppMessageType
    text: Optional[WhatsAppText] = None

    class Config:
        populate_by_name = True

class WhatsAppMetadata(BaseModel):
    display_phone_number: str
    phone_number_id: str

class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: WhatsAppMetadata
    contacts: Optional[List[WhatsAppContact]] = []
    messages: Optional[List[WhatsAppMessage]] = []

class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str

class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]

class WhatsAppWebhook(BaseModel):
    object: str
    entry: List[WhatsAppEntry]

class ProcessedWhatsAppMessage(BaseModel):
    """Simplified processed message"""
    message_id: str
    sender: str
    content: str
    sender_name: Optional[str] = None
    timestamp: str
    message_type: WhatsAppMessageType

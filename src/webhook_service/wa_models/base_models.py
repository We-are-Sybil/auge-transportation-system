from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from enum import Enum
import re

class WhatsAppConfig:
    """Configuration constants for WhatsApp Cloud API"""

    # API Version
    DEFAULT_API_VERSION = "v23.0"

    # Text limits
    MAX_TEXT_LENGTH = 1024
    MAX_CAPTION_LENGTH = 1024
    MAX_HEADER_TEXT_LENGTH = 60
    MAX_FOOTER_TEXT_LENGTH = 60
    MAX_BUTTON_TEXT_LENGTH = 20
    MAX_SECTION_TITLE_LENGTH = 24
    MAX_ROW_TITLE_LENGTH = 24
    MAX_ROW_DESCRIPTION_LENGTH = 72
    MAX_ROW_ID_LENGTH = 200
    
    # Media limits
    MAX_IMAGE_SIZE_MB = 5
    MAX_DOCUMENT_SIZE_MB = 100
    MAX_AUDIO_SIZE_MB = 16
    MAX_VIDEO_SIZE_MB = 16
    
    # Interactive limits
    MAX_BUTTONS = 3
    MAX_LIST_SECTIONS = 10
    MAX_LIST_ROWS_TOTAL = 10


class MessageType(str, Enum):
    """WhatsApp message types"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"


class InteractiveType(str, Enum):
    """Interactive message type"""
    BUTTON = "button"
    LIST = "list"
    CTA_URL = "cta_url"
    LOCATION_REQUEST_MESSAGE = "location_request_message"

class HeaderType(str, Enum):
    """Header types for interactive messages"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"


class MediaFormat(str, Enum):
    """Supported media formats"""
    # Images
    JPEG = "image/jpeg"
    PNG = "image/png"
    
    # Audio
    AAC = "audio/aac"
    AMR = "audio/amr"
    MP3 = "audio/mpeg"
    MP4_AUDIO = "audio/mp4"
    OGG = "audio/ogg"
    
    # Video
    MP4_VIDEO = "video/mp4"
    THREE_GPP = "video/3gpp"
    
    # Documents
    PDF = "application/pdf"
    DOC = "application/msword"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    XLS = "application/vnd.ms-excel"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    PPT = "application/vnd.ms-powerpoint"
    PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    TXT = "text/plain"


class WhatsAppBaseModel(BaseModel):
    """Base model with common configuration for all WhatsApp API models"""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid',
        frozen=False
    )


class PhoneNumber(WhatsAppBaseModel):
    """WhatsApp phone number with validation"""
    
    number: str = Field(
        description="Phone number in international format with + prefix",
        pattern=r'^\+[1-9]\d{1,14}$'
    )
    
    @field_validator('number')
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Validate phone number format according to E.164 standard"""
        if not v.startswith('+'):
            raise ValueError('Phone number must start with +')
        
        # Remove + for digit validation
        digits = v[1:]
        if not digits.isdigit():
            raise ValueError('Phone number must contain only digits after +')
        
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError('Phone number must be between 7 and 15 digits')
        
        return v
    
    def __str__(self) -> str:
        return self.number


class MediaReference(WhatsAppBaseModel):
    """Reference to media asset (either uploaded ID or URL)"""
    
    id: Optional[str] = Field(
        None,
        description="ID of uploaded media asset (recommended)"
    )
    link: Optional[str] = Field(
        None,
        description="Public URL of media asset (not recommended for production)"
    )
    
    @field_validator('link')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format"""
        if v is None:
            return v
        
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError('Invalid URL format')
        
        return v
    
    def model_post_init(self, __context) -> None:
        """Ensure exactly one of id or link is provided"""
        if not self.id and not self.link:
            raise ValueError('Either id or link must be provided')
        if self.id and self.link:
            raise ValueError('Cannot provide both id and link, choose one')


class TextContent(WhatsAppBaseModel):
    """Text content with length validation"""
    
    text: str = Field(
        description="Text content",
        min_length=1,
        max_length=WhatsAppConfig.MAX_TEXT_LENGTH
    )


class CaptionContent(WhatsAppBaseModel):
    """Media caption with length validation"""
    
    caption: Optional[str] = Field(
        None,
        description="Media caption text",
        max_length=WhatsAppConfig.MAX_CAPTION_LENGTH
    )


class HeaderContent(WhatsAppBaseModel):
    """Header content for interactive messages"""
    
    type: HeaderType = Field(description="Type of header content")
    text: Optional[str] = Field(
        None,
        description="Header text (for text headers)",
        max_length=WhatsAppConfig.MAX_HEADER_TEXT_LENGTH
    )
    image: Optional[MediaReference] = Field(
        None,
        description="Image reference (for image headers)"
    )
    video: Optional[MediaReference] = Field(
        None,
        description="Video reference (for video headers)"
    )
    document: Optional[MediaReference] = Field(
        None,
        description="Document reference (for document headers)"
    )
    
    def model_post_init(self, __context) -> None:
        """Validate header content matches type"""
        content_map = {
            HeaderType.TEXT: self.text,
            HeaderType.IMAGE: self.image,
            HeaderType.VIDEO: self.video,
            HeaderType.DOCUMENT: self.document
        }
        
        expected_content = content_map[self.type]
        if expected_content is None:
            raise ValueError(f'Header type {self.type} requires corresponding content')
        
        # Ensure no other content is provided
        for header_type, content in content_map.items():
            if header_type != self.type and content is not None:
                raise ValueError(f'Header type {self.type} cannot have {header_type} content')


class FooterContent(WhatsAppBaseModel):
    """Footer content for interactive messages"""
    
    text: str = Field(
        description="Footer text",
        min_length=1,
        max_length=WhatsAppConfig.MAX_FOOTER_TEXT_LENGTH
    )


# Contact-related models

class ContactAddress(WhatsAppBaseModel):
    """Contact address information"""
    
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State or province")
    zip: Optional[str] = Field(None, description="Postal or ZIP code")
    country: Optional[str] = Field(None, description="Country name")
    country_code: Optional[str] = Field(None, description="ISO two-letter country code")
    type: Optional[str] = Field(None, description="Address type (e.g., Home, Work)")
    
    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO country code format"""
        if v is None:
            return v
        if len(v) != 2 or not v.isalpha():
            raise ValueError('Country code must be 2 letters')
        return v.upper()


class ContactEmail(WhatsAppBaseModel):
    """Contact email information"""
    
    email: str = Field(description="Email address")
    type: Optional[str] = Field(None, description="Email type (e.g., Work, Personal)")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation"""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(v):
            raise ValueError('Invalid email format')
        return v


class ContactPhone(WhatsAppBaseModel):
    """Contact phone information"""
    
    phone: str = Field(description="Phone number")
    type: Optional[str] = Field(None, description="Phone type (e.g., Mobile, Home, Work)")
    wa_id: Optional[str] = Field(None, description="WhatsApp ID for this phone number")


class ContactName(WhatsAppBaseModel):
    """Contact name information"""
    
    formatted_name: str = Field(description="Full formatted name")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    middle_name: Optional[str] = Field(None, description="Middle name")
    suffix: Optional[str] = Field(None, description="Name suffix")
    prefix: Optional[str] = Field(None, description="Name prefix")


class ContactOrganization(WhatsAppBaseModel):
    """Contact organization information"""
    
    company: Optional[str] = Field(None, description="Company name")
    department: Optional[str] = Field(None, description="Department")
    title: Optional[str] = Field(None, description="Job title")


class ContactUrl(WhatsAppBaseModel):
    """Contact URL information"""
    
    url: str = Field(description="Website URL")
    type: Optional[str] = Field(None, description="URL type (e.g., Company, Personal)")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')

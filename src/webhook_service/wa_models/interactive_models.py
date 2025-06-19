from pydantic import Field, field_validator, model_validator
from typing import Optional, List, Literal, Union
from .base_models import WhatsAppBaseModel, WhatsAppConfig, InteractiveType, HeaderContent, FooterContent


class ButtonReply(WhatsAppBaseModel):
    """Reply button configuration"""
    
    id: str = Field(
        description="Unique button identifier",
        max_length=WhatsAppConfig.MAX_ROW_ID_LENGTH
    )
    title: str = Field(
        description="Button text displayed to user",
        min_length=1,
        max_length=WhatsAppConfig.MAX_BUTTON_TEXT_LENGTH
    )


class InteractiveButton(WhatsAppBaseModel):
    """Interactive reply button"""
    
    type: Literal["reply"] = Field(default="reply", description="Button type")
    reply: ButtonReply = Field(description="Button reply configuration")


class ListRow(WhatsAppBaseModel):
    """Row item in a list section"""
    
    id: str = Field(
        description="Unique row identifier for webhook responses",
        max_length=WhatsAppConfig.MAX_ROW_ID_LENGTH
    )
    title: str = Field(
        description="Row title text",
        min_length=1,
        max_length=WhatsAppConfig.MAX_ROW_TITLE_LENGTH
    )
    description: Optional[str] = Field(
        None,
        description="Optional row description",
        max_length=WhatsAppConfig.MAX_ROW_DESCRIPTION_LENGTH
    )


class ListSection(WhatsAppBaseModel):
    """Section containing multiple rows in a list message"""
    
    title: str = Field(
        description="Section title",
        min_length=1,
        max_length=WhatsAppConfig.MAX_SECTION_TITLE_LENGTH
    )
    rows: List[ListRow] = Field(
        description="List of rows in this section",
        min_length=1
    )
    
    @field_validator('rows')
    @classmethod
    def validate_rows_count(cls, v: List[ListRow]) -> List[ListRow]:
        """Validate row count within section"""
        if len(v) > WhatsAppConfig.MAX_LIST_ROWS_TOTAL:
            raise ValueError(f'Section cannot have more than {WhatsAppConfig.MAX_LIST_ROWS_TOTAL} rows')
        return v


class CTAUrlParameters(WhatsAppBaseModel):
    """Parameters for CTA URL button"""
    
    display_text: str = Field(
        description="Text displayed on the button",
        min_length=1,
        max_length=WhatsAppConfig.MAX_BUTTON_TEXT_LENGTH
    )
    url: str = Field(description="URL to open when button is tapped")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class CTAUrlAction(WhatsAppBaseModel):
    """CTA URL action configuration"""
    
    name: Literal["cta_url"] = Field(default="cta_url", description="Action name")
    parameters: CTAUrlParameters = Field(description="CTA URL parameters")


class ButtonAction(WhatsAppBaseModel):
    """Button action configuration for reply buttons"""
    
    buttons: List[InteractiveButton] = Field(
        description="List of reply buttons",
        min_length=1,
        max_length=WhatsAppConfig.MAX_BUTTONS
    )
    
    @field_validator('buttons')
    @classmethod
    def validate_unique_button_ids(cls, v: List[InteractiveButton]) -> List[InteractiveButton]:
        """Ensure button IDs are unique"""
        ids = [button.reply.id for button in v]
        if len(ids) != len(set(ids)):
            raise ValueError('Button IDs must be unique')
        return v
    
    @field_validator('buttons')
    @classmethod
    def validate_unique_button_titles(cls, v: List[InteractiveButton]) -> List[InteractiveButton]:
        """Ensure button titles are unique"""
        titles = [button.reply.title for button in v]
        if len(titles) != len(set(titles)):
            raise ValueError('Button titles must be unique')
        return v


class ListAction(WhatsAppBaseModel):
    """List action configuration"""
    
    button: str = Field(
        description="Button text that reveals the list",
        min_length=1,
        max_length=WhatsAppConfig.MAX_BUTTON_TEXT_LENGTH
    )
    sections: List[ListSection] = Field(
        description="List sections",
        min_length=1,
        max_length=WhatsAppConfig.MAX_LIST_SECTIONS
    )
    
    @field_validator('sections')
    @classmethod
    def validate_total_rows(cls, v: List[ListSection]) -> List[ListSection]:
        """Validate total rows across all sections"""
        total_rows = sum(len(section.rows) for section in v)
        if total_rows > WhatsAppConfig.MAX_LIST_ROWS_TOTAL:
            raise ValueError(f'Total rows across all sections cannot exceed {WhatsAppConfig.MAX_LIST_ROWS_TOTAL}')
        return v
    
    @field_validator('sections')
    @classmethod
    def validate_unique_row_ids(cls, v: List[ListSection]) -> List[ListSection]:
        """Ensure row IDs are unique across all sections"""
        all_ids = []
        for section in v:
            all_ids.extend(row.id for row in section.rows)
        
        if len(all_ids) != len(set(all_ids)):
            raise ValueError('Row IDs must be unique across all sections')
        return v


class LocationRequestAction(WhatsAppBaseModel):
    """Location request action configuration"""
    
    name: Literal["send_location"] = Field(
        default="send_location",
        description="Action name for location requests"
    )


# Interactive message body components

class InteractiveBody(WhatsAppBaseModel):
    """Body content for interactive messages"""
    
    text: str = Field(
        description="Body text content",
        min_length=1,
        max_length=WhatsAppConfig.MAX_TEXT_LENGTH
    )


class Interactive(WhatsAppBaseModel):
    """Interactive message content"""
    
    type: InteractiveType = Field(description="Type of interactive message")
    header: Optional['HeaderContent'] = Field(None, description="Optional header")
    body: InteractiveBody = Field(description="Message body")
    footer: Optional['FooterContent'] = Field(None, description="Optional footer")
    action: Union[ButtonAction, ListAction, CTAUrlAction, LocationRequestAction] = Field(
        description="Interactive action configuration"
    )
    
    @model_validator(mode='after')
    def validate_action_matches_type(self) -> 'Interactive':
        """Validate that action type matches interactive type"""
        type_action_map = {
            InteractiveType.BUTTON: ButtonAction,
            InteractiveType.LIST: ListAction,
            InteractiveType.CTA_URL: CTAUrlAction,
            InteractiveType.LOCATION_REQUEST_MESSAGE: LocationRequestAction
        }
        
        expected_action_type = type_action_map[self.type]
        if not isinstance(self.action, expected_action_type):
            raise ValueError(f'Interactive type {self.type} requires {expected_action_type.__name__} action')
        
        return self


# Webhook response models for interactive messages

class ButtonReplyWebhook(WhatsAppBaseModel):
    """Button reply received via webhook"""
    
    id: str = Field(description="Button ID that was tapped")
    title: str = Field(description="Button title that was tapped")


class ListReplyWebhook(WhatsAppBaseModel):
    """List reply received via webhook"""
    
    id: str = Field(description="Row ID that was selected")
    title: str = Field(description="Row title that was selected")
    description: Optional[str] = Field(None, description="Row description if provided")


class InteractiveWebhookResponse(WhatsAppBaseModel):
    """Interactive message response received via webhook"""
    
    type: Literal["button_reply", "list_reply"] = Field(description="Type of interactive response")
    button_reply: Optional[ButtonReplyWebhook] = Field(None, description="Button reply data")
    list_reply: Optional[ListReplyWebhook] = Field(None, description="List reply data")
    
    @model_validator(mode='after')
    def validate_response_data(self) -> 'InteractiveWebhookResponse':
        """Validate that response data matches type"""
        if self.type == "button_reply" and self.button_reply is None:
            raise ValueError('button_reply data required for button_reply type')
        if self.type == "list_reply" and self.list_reply is None:
            raise ValueError('list_reply data required for list_reply type')
        if self.type == "button_reply" and self.list_reply is not None:
            raise ValueError('list_reply data not allowed for button_reply type')
        if self.type == "list_reply" and self.button_reply is not None:
            raise ValueError('button_reply data not allowed for list_reply type')
        return self

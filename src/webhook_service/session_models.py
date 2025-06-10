from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ConversationStage(str, Enum):
    """Conversation stages for transportation requests"""
    INITIAL = "initial"
    GREETING = "greeting"
    COLLECTING_INFO = "collecting_info"
    GENERATING_QUOTE = "generating_quote"
    AWAITING_RESPONSE = "awaiting_response"
    COLLECTING_BILLING = "collecting_billing"
    COMPLETED = "completed"

class ConversationState(BaseModel):
    """Complete conversation state for Redis storage"""
    
    # Basic identifiers
    user_id: str
    session_id: Optional[str] = None
    
    # Conversation tracking
    stage: ConversationStage = ConversationStage.INITIAL
    message_count: int = 0
    last_message: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    
    # Message history (keep last 10 for context)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Transportation request data collection
    collected_data: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)
    
    # State flags
    is_active: bool = True
    needs_response: bool = False
    
    def update_message(self, content: str, role: str = "user"):
        """Add new message and update state"""
        self.message_count += 1
        self.last_message = content
        self.last_updated = datetime.now()
        
        # Add to message history (keep last 10)
        message_entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(message_entry)
        
        # Keep only last 10 messages
        if len(self.messages) > 10:
            self.messages = self.messages[-10:]
    
    def set_stage(self, stage: ConversationStage):
        """Update conversation stage"""
        self.stage = stage
        self.last_updated = datetime.now()
    
    def collect_data(self, field: str, value: Any):
        """Collect transportation request data"""
        self.collected_data[field] = value
        self.last_updated = datetime.now()
        
        # Remove from missing fields if present
        if field in self.missing_fields:
            self.missing_fields.remove(field)
    
    def set_missing_fields(self, fields: List[str]):
        """Set fields that still need to be collected"""
        self.missing_fields = fields
        self.needs_response = len(fields) > 0
    
    def get_context_summary(self) -> str:
        """Get conversation context for AI agents"""
        return f"Stage: {self.stage.value}, Messages: {self.message_count}, Missing: {len(self.missing_fields)} fields"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

import asyncio
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

from src.database.crewai_extensions import ExtendedDatabaseManager
from src.database.models import MessageRole, ConversationStep
import logging

logger = logging.getLogger(__name__)


class ConversationContextTool(BaseTool):
    """Tool for agents to retrieve conversation context from existing database"""
    
    name: str = "get_conversation_context"
    description: str = (
        "Retrieve the current conversation context including collected data, "
        "current step, missing fields, and message history. "
        "Use this to understand the conversation state and continue appropriately."
    )
    
    class ConversationContextInput(BaseModel):
        session_id: str = Field(description="The session ID to retrieve context for")
        include_messages: bool = Field(
            default=True, 
            description="Whether to include recent message history"
        )
        message_limit: int = Field(
            default=5,
            description="Number of recent messages to include"
        )
    
    args_schema: type[BaseModel] = ConversationContextInput
    
    def _run(self, session_id: str, include_messages: bool = True, message_limit: int = 5) -> str:
        """Retrieve conversation context"""
        return asyncio.run(self._async_run(session_id, include_messages, message_limit))
    
    async def _async_run(self, session_id: str, include_messages: bool = True, message_limit: int = 5) -> str:
        db = ExtendedDatabaseManager()
        try:
            # Get conversation context
            context = await db.get_conversation_context(session_id)
            
            if not context:
                return json.dumps({
                    "error": "Conversation not found",
                    "session_id": session_id
                })
            
            # Extract customer info from context data or user_id
            context_data = context.get("context", {})
            collected_data = context_data.get("collected_data", {})
            client_info = collected_data.get("client_info", {})
            
            # Try to get customer info from different sources
            customer_phone = (
                client_info.get("phone") or 
                context.get("user_id", "")  # user_id often contains phone number
            )
            customer_name = (
                client_info.get("name") or 
                client_info.get("nombre") or
                "N/A"
            )
            
            result_data = {
                "session_id": session_id,
                "customer_phone": customer_phone,
                "customer_name": customer_name,
                "user_id": context.get("user_id"),
                "current_step": context["current_step"],
                "session_status": context["session_status"],
                "context": context["context"],
                "missing_information": await db.get_missing_information(session_id)
            }
            
            # Add recent messages if requested
            if include_messages:
                messages = await db.get_conversation_messages(session_id, message_limit)
                result_data["recent_messages"] = messages
            
            return json.dumps(result_data, indent=2)
            
        except Exception as e:
            logger.error(f"Error retrieving conversation context: {e}")
            return json.dumps({
                "error": str(e),
                "session_id": session_id
            })
        finally:
            await db.close()


class UpdateContextTool(BaseTool):
    """Tool for agents to update conversation context"""
    
    name: str = "update_conversation_context"
    description: str = (
        "Update the conversation context with new information collected from the user. "
        "Use this to save progress, update collected data, mark completion steps."
    )
    
    class UpdateContextInput(BaseModel):
        session_id: str = Field(description="The session ID to update")
        context_updates: Dict[str, Any] = Field(
            description="Dictionary of context updates to apply"
        )
        current_step: Optional[str] = Field(
            default=None, 
            description="Current conversation step (e.g., 'collecting_info', 'generating_quote')"
        )
        
    args_schema: type[BaseModel] = UpdateContextInput
    
    def _run(
        self, 
        session_id: str, 
        context_updates: Dict[str, Any],
        current_step: Optional[str] = None
    ) -> str:
        """Update conversation context"""
        return asyncio.run(self._async_run(session_id, context_updates, current_step))
    
    async def _async_run(
        self, 
        session_id: str, 
        context_updates: Dict[str, Any],
        current_step: Optional[str] = None
    ) -> str:
        db = ExtendedDatabaseManager()
        try:
            # Convert string step to enum if provided
            step_enum = None
            if current_step:
                try:
                    step_enum = ConversationStep(current_step)
                except ValueError:
                    step_enum = ConversationStep.COLLECTING_INFO  # Default fallback
            
            # Update conversation context
            success = await db.update_conversation_context(
                session_id, context_updates, step_enum
            )
            
            if success:
                return json.dumps({
                    "success": True,
                    "message": "Context updated successfully",
                    "session_id": session_id,
                    "updates_applied": context_updates,
                    "current_step": current_step
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": "Failed to update context - session not found",
                    "session_id": session_id
                })
                
        except Exception as e:
            logger.error(f"Error updating conversation context: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "session_id": session_id
            })
        finally:
            await db.close()


class SaveCollectedDataTool(BaseTool):
    """Tool for agents to save user-provided data"""
    
    name: str = "save_collected_data"
    description: str = (
        "Save data collected from the user during the conversation. "
        "This includes client information, service requirements, preferences, etc."
    )
    
    class SaveDataInput(BaseModel):
        session_id: str = Field(description="The session ID")
        data_category: str = Field(
            description="Category of data (e.g., 'client_info', 'service_request')"
        )
        data: Dict[str, Any] = Field(description="The data to save")
        mark_step_complete: bool = Field(
            default=False, 
            description="Whether to mark current step as complete"
        )
    
    args_schema: type[BaseModel] = SaveDataInput
    
    def _run(
        self, 
        session_id: str, 
        data_category: str,
        data: Dict[str, Any],
        mark_step_complete: bool = False
    ) -> str:
        """Save collected data"""
        return asyncio.run(self._async_run(session_id, data_category, data, mark_step_complete))
    
    async def _async_run(
        self, 
        session_id: str, 
        data_category: str,
        data: Dict[str, Any],
        mark_step_complete: bool = False
    ) -> str:
        db = ExtendedDatabaseManager()
        try:
            # Save collected data
            success = await db.save_collected_data(session_id, data_category, data)
            
            if not success:
                return json.dumps({
                    "success": False,
                    "error": "Session not found"
                })
            
            # Mark step complete if requested
            if mark_step_complete:
                step = ConversationStep.COLLECTING_INFO  # Default step
                await db.mark_conversation_step_complete(
                    session_id, step, {"completed_category": data_category}
                )
            
            return json.dumps({
                "success": True,
                "message": f"Saved {data_category} data",
                "data_category": data_category,
                "marked_complete": mark_step_complete
            })
            
        except Exception as e:
            logger.error(f"Error saving collected data: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
        finally:
            await db.close()


class CreateServiceRequestTool(BaseTool):
    """Tool for agents to create service requests from conversation data"""
    
    name: str = "create_service_request"
    description: str = (
        "Create a new service request based on collected conversation data. "
        "Use this when enough information has been gathered to process a quotation request."
    )
    
    class ServiceRequestInput(BaseModel):
        session_id: str = Field(description="The session ID")
        request_type: str = Field(
            default="transportation_quotation",
            description="Type of service request"
        )
    
    args_schema: type[BaseModel] = ServiceRequestInput
    
    def _run(self, session_id: str, request_type: str = "transportation_quotation") -> str:
        """Create service request"""
        return asyncio.run(self._async_run(session_id, request_type))
    
    async def _async_run(self, session_id: str, request_type: str) -> str:
        db = ExtendedDatabaseManager()
        try:
            # Create service request from conversation context
            request_id = await db.create_service_request_from_context(session_id, request_type)
            
            if request_id:
                return json.dumps({
                    "success": True,
                    "request_id": request_id,
                    "request_type": request_type,
                    "session_id": session_id,
                    "message": "Service request created successfully"
                })
            else:
                missing_info = await db.get_missing_information(session_id)
                return json.dumps({
                    "success": False,
                    "error": "Insufficient information to create service request",
                    "missing_information": missing_info,
                    "session_id": session_id
                })
                
        except Exception as e:
            logger.error(f"Error creating service request: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
        finally:
            await db.close()


class AddMessageTool(BaseTool):
    """Tool for agents to add messages to conversation history"""
    
    name: str = "add_message"
    description: str = (
        "Add a message to the conversation history. "
        "Use this to record agent responses or system notifications."
    )
    
    class AddMessageInput(BaseModel):
        session_id: str = Field(description="The session ID")
        role: str = Field(
            description="Message role: 'user', 'assistant', or 'system'"
        )
        content: str = Field(description="Message content")
        metadata: Optional[Dict[str, Any]] = Field(
            default=None,
            description="Optional metadata for the message"
        )
    
    args_schema: type[BaseModel] = AddMessageInput
    
    def _run(
        self, 
        session_id: str, 
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add message to conversation"""
        return asyncio.run(self._async_run(session_id, role, content, metadata))
    
    async def _async_run(
        self, 
        session_id: str, 
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        db = ExtendedDatabaseManager()
        try:
            # Convert string role to enum
            try:
                role_enum = MessageRole(role)
            except ValueError:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid role: {role}. Must be 'user', 'assistant', or 'system'"
                })
            
            # Add message
            message_id = await db.add_crewai_message(session_id, role_enum, content, metadata)
            
            if message_id:
                return json.dumps({
                    "success": True,
                    "message_id": message_id,
                    "session_id": session_id,
                    "role": role,
                    "content": content[:100] + "..." if len(content) > 100 else content
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": "Session not found"
                })
                
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
        finally:
            await db.close()


# Tool registry for easy access
CONVERSATION_TOOLS = [
    ConversationContextTool(),
    UpdateContextTool(),
    SaveCollectedDataTool(),
    CreateServiceRequestTool(),
    AddMessageTool()
]


def get_conversation_tools() -> List[BaseTool]:
    """Get all conversation state management tools"""
    return CONVERSATION_TOOLS.copy()


def get_tool_by_name(tool_name: str) -> Optional[BaseTool]:
    """Get a specific tool by name"""
    for tool in CONVERSATION_TOOLS:
        if tool.name == tool_name:
            return tool
    return None

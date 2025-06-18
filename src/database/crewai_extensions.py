import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .manager import DatabaseManager
from .models import ConversationSession, Message, MessageRole, ConversationStep, Client, QuotationRequest


class CrewAIConversationMixin:
    """Mixin to extend DatabaseManager with CrewAI conversation state methods"""
    
    async def get_conversation_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation context from existing session"""
        async with self.get_session() as session:
            result = await session.execute(
                select(ConversationSession).where(ConversationSession.session_id == session_id)
            )
            conv_session = result.scalar_one_or_none()
            
            if not conv_session:
                return None
            
            # Parse context JSON
            context_data = json.loads(conv_session.context or '{}')
            
            return {
                "session_id": session_id,
                "user_id": conv_session.user_id,
                "current_step": conv_session.current_step.value if conv_session.current_step else None,
                "session_status": conv_session.status.value if conv_session.status else None,
                "context": context_data,
                "created_at": conv_session.created_at.isoformat() if conv_session.created_at else None,
                "updated_at": conv_session.updated_at.isoformat() if conv_session.updated_at else None
            }
    
    async def update_conversation_context(
        self, 
        session_id: str, 
        context_updates: Dict[str, Any],
        current_step: Optional[ConversationStep] = None
    ) -> bool:
        """Update conversation context with new data"""
        async with self.get_session() as session:
            # Get current session
            result = await session.execute(
                select(ConversationSession).where(ConversationSession.session_id == session_id)
            )
            conv_session = result.scalar_one_or_none()
            
            if not conv_session:
                return False
            
            # Update context
            current_context = json.loads(conv_session.context or '{}')
            current_context.update(context_updates)
            
            # Prepare update values
            update_values = {
                "context": json.dumps(current_context),
                "updated_at": datetime.utcnow()
            }
            
            if current_step:
                update_values["current_step"] = current_step
            
            # Update database
            await session.execute(
                update(ConversationSession)
                .where(ConversationSession.session_id == session_id)
                .values(**update_values)
            )
            
            return True
    
    async def save_collected_data(
        self, 
        session_id: str, 
        data_category: str, 
        data: Dict[str, Any]
    ) -> bool:
        """Save collected data to conversation context"""
        context_updates = {
            f"collected_data.{data_category}": data,
            f"data_collected_at.{data_category}": datetime.utcnow().isoformat()
        }
        
        return await self.update_conversation_context(session_id, context_updates)
    
    async def get_conversation_messages(
        self, 
        session_id: str, 
        limit: Optional[int] = None,
        include_system: bool = False
    ) -> List[Dict[str, Any]]:
        """Get conversation message history"""
        async with self.get_session() as session:
            # Get conversation session first
            conv_result = await session.execute(
                select(ConversationSession).where(ConversationSession.session_id == session_id)
            )
            conv_session = conv_result.scalar_one_or_none()
            
            if not conv_session:
                return []
            
            # Build query for messages using session ID (int)
            query = select(Message).where(Message.session_id == conv_session.id)
            
            if not include_system:
                query = query.where(Message.role != MessageRole.SYSTEM)
            
            query = query.order_by(Message.created_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            messages = result.scalars().all()
            
            return [
                {
                    "message_id": msg.id,
                    "role": msg.role.value,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "metadata": json.loads(msg._metadata or '{}')
                }
                for msg in reversed(messages)  # Return in chronological order
            ]
    
    async def add_crewai_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """Add a message to conversation (CrewAI specific)"""
        async with self.get_session() as session:
            # Get conversation session
            conv_result = await session.execute(
                select(ConversationSession).where(ConversationSession.session_id == session_id)
            )
            conv_session = conv_result.scalar_one_or_none()
            
            if not conv_session:
                return None
            
            # Add message using existing add_message method
            message_id = await self.add_message(conv_session.id, role, content)
            
            # Update session metadata if provided
            if metadata:
                await self.update_conversation_context(session_id, {"last_message_metadata": metadata})
            
            return message_id
    
    async def create_service_request_from_context(
        self,
        session_id: str,
        request_type: str = "transportation_quotation"
    ) -> Optional[int]:
        """Create service request from conversation context"""
        # Get conversation context
        context = await self.get_conversation_context(session_id)
        if not context:
            return None
        
        session_data = context.get("context", {})
        collected_data = session_data.get("collected_data", {})
        
        # Extract client information
        client_info = collected_data.get("client_info", {})
        service_info = collected_data.get("service_request", {})
        
        if not client_info or not service_info:
            return None
        
        try:
            # Get internal session ID for the quotation request
            async with self.get_session() as db_session:
                from .models import ConversationSession
                result = await db_session.execute(
                    select(ConversationSession).where(ConversationSession.session_id == session_id)
                )
                conv_session = result.scalar_one_or_none()
                if not conv_session:
                    return None
                internal_session_id = conv_session.id
            
            # Create or get client
            client_cc_nit = client_info.get("cc_nit") or client_info.get("phone", context.get("user_id", ""))
            client_name = client_info.get("name") or client_info.get("nombre") or "Cliente WhatsApp"
            client_phone = client_info.get("phone") or context.get("user_id", "")
            
            existing_client = await self.get_client_by_cc_nit(client_cc_nit)
            if not existing_client:
                client_id = await self.create_client(client_cc_nit, client_name, client_phone)
            else:
                # Get client ID from existing client
                async with self.get_session() as db_session:
                    from .models import Client
                    result = await db_session.execute(
                        select(Client).where(Client.cc_nit == client_cc_nit)
                    )
                    client = result.scalar_one()
                    client_id = client.id
            
            # Create quotation request (keep form_number under 20 chars)
            timestamp_short = str(int(datetime.utcnow().timestamp()))[-8:]  # Last 8 digits
            form_number = f"WA-{timestamp_short}"
            
            # Parse service details
            service_date_str = service_info.get("travel_date") or service_info.get("fecha_inicio_servicio")
            if service_date_str:
                if isinstance(service_date_str, str):
                    service_date = datetime.fromisoformat(service_date_str.replace('Z', '+00:00'))
                else:
                    service_date = service_date_str
            else:
                service_date = datetime.utcnow() + timedelta(days=1)  # Default to tomorrow
            
            request_id = await self.create_quotation_request(
                form_number=form_number,
                client_id=client_id,
                session_id=internal_session_id,
                quien_solicita=service_info.get("quien_solicita", client_name),
                fecha_inicio_servicio=service_date,
                hora_inicio_servicio=service_info.get("hora_inicio_servicio", "08:00"),
                direccion_inicio=service_info.get("direccion_inicio", ""),
                direccion_terminacion=service_info.get("direccion_terminacion"),
                caracteristicas_servicio=service_info.get("caracteristicas_servicio", "Servicio de transporte"),
                cantidad_pasajeros=int(service_info.get("cantidad_pasajeros", 1)),
                equipaje_carga=service_info.get("equipaje_carga", False)
            )
            
            # Update conversation context with service request ID
            await self.update_conversation_context(
                session_id,
                {
                    "service_request_id": request_id,
                    "service_request_created_at": datetime.utcnow().isoformat(),
                    "form_number": form_number
                },
                ConversationStep.GENERATING_QUOTE
            )
            
            return request_id
            
        except Exception as e:
            # Log error but don't raise - let caller handle
            print(f"DEBUG: Exception in create_service_request_from_context: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_missing_information(self, session_id: str) -> List[str]:
        """Analyze conversation context to determine missing information"""
        context = await self.get_conversation_context(session_id)
        if not context:
            return ["session_not_found"]
        
        session_data = context.get("context", {})
        collected_data = session_data.get("collected_data", {})
        
        missing_fields = []
        
        # Check client information
        client_info = collected_data.get("client_info", {})
        if not client_info.get("name") and not client_info.get("nombre"):
            missing_fields.append("client_name")
        if not client_info.get("phone") and not context.get("user_id"):
            missing_fields.append("client_phone")
        
        # Check service request information
        service_info = collected_data.get("service_request", {})
        if not service_info.get("direccion_inicio"):
            missing_fields.append("pickup_location")
        if not service_info.get("travel_date") and not service_info.get("fecha_inicio_servicio"):
            missing_fields.append("travel_date")
        if not service_info.get("cantidad_pasajeros"):
            missing_fields.append("passenger_count")
        
        return missing_fields
    
    async def mark_conversation_step_complete(
        self, 
        session_id: str, 
        step: ConversationStep,
        completion_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Mark a conversation step as complete"""
        context_updates = {
            f"steps_completed.{step.value}": True,
            f"step_completed_at.{step.value}": datetime.utcnow().isoformat()
        }
        
        if completion_data:
            context_updates[f"step_data.{step.value}"] = completion_data
        
        return await self.update_conversation_context(session_id, context_updates, step)


class ExtendedDatabaseManager(DatabaseManager, CrewAIConversationMixin):
    """Extended DatabaseManager with CrewAI conversation state capabilities"""
    pass

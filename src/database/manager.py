"""Database manager with complete models support"""
from contextlib import asynccontextmanager
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, select
from .models import (
    Base, ConnectionTest, ConversationSession, Message, Client, 
    QuotationRequest, Quotation, SessionStatus, MessageRole, 
    ConversationStep, RequestStatus
)
from typing import Optional
from ..config import db_config

class DatabaseManager:
    def __init__(self):
        self.engine = create_async_engine(db_config.url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession)

    async def init_tables(self):
        """Create all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def get_session(self):
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # ============ TEST METHODS ============

    async def test_connection(self) -> str:
        async with self.get_session() as session:
            result = await session.execute(text("SELECT version()"))
            return result.scalar()

    async def create_test_record(self, message: str) -> int:
        async with self.get_session() as session:
            record = ConnectionTest(test_message=message)
            session.add(record)
            await session.flush()
            return record.id

    async def get_test_records(self) -> list:
        async with self.get_session() as session:
            result = await session.execute(text("SELECT * FROM connection_test ORDER BY id"))
            return result.fetchall()

    # ============ CONVERSATION METHODS ============

    async def create_conversation_session(self, user_id: str, session_id: str) -> ConversationSession:
        async with self.get_session() as session:
            conv_session = ConversationSession(
                user_id=user_id,
                session_id=session_id,
                status=SessionStatus.ACTIVE,
                current_step=ConversationStep.COLLECTING_INFO
            )
            session.add(conv_session)
            await session.flush()
            # Return the ID, not the object
            return conv_session.id

    async def add_message(self, session_id: int, role: MessageRole, content: str, metadata: str = None) -> int:
        async with self.get_session() as session:
            message = Message(
                session_id=session_id,
                role=role,
                content=content,
                _metadata=metadata
            )
            session.add(message)
            await session.flush()
            return message.id

    async def update_session_step(self, session_id: int, step: ConversationStep):
        async with self.get_session() as session:
            conv_session = await session.get(ConversationSession, session_id)
            if conv_session:
                conv_session.current_step = step
                conv_session.updated_at = datetime.now()

    async def get_or_create_conversation(self, user_id: str) -> int:
        """Get existing conversation or create new one"""
        async with self.get_session() as session:
            # Try to get active conversation
            result = await session.execute(
                select(ConversationSession).where(
                    ConversationSession.user_id == user_id,
                    ConversationSession.status == SessionStatus.ACTIVE
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                return existing.id
            
            # Create new conversation
            session_id = f"wa_{user_id}_{int(datetime.now().timestamp())}"
            return await self.create_conversation_session(user_id, session_id)

    async def create_client(self, cc_nit: str, nombre: str, celular: str) -> int:
        async with self.get_session() as session:
            client = Client(
                cc_nit=cc_nit,
                nombre_solicitante=nombre,
                celular_contacto=celular
            )
            session.add(client)
            await session.flush()
            return client.id

    async def get_client_by_cc_nit(self, cc_nit: str) -> Optional[str]:
        async with self.get_session() as session:
            result = await session.execute(
                select(Client).where(Client.cc_nit == cc_nit)
            )
            client = result.scalar_one_or_none()
            return client.nombre_solicitante if client else None

    async def create_quotation_request(self, form_number: str, client_id: int, session_id: int = None, **kwargs) -> int:
        async with self.get_session() as session:
            request = QuotationRequest(
                form_number=form_number,
                client_id=client_id,
                session_id=session_id,
                status=RequestStatus.PENDING,
                **kwargs
            )
            session.add(request)
            await session.flush()
            return request.id

    async def close(self):
        await self.engine.dispose()

"""Complete SQLAlchemy models for conversation + business logic"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, Text, Boolean, Numeric, ForeignKey, func, Enum as SQLEnum
from enum import Enum

class Base(DeclarativeBase):
    pass

# === ENUMS ===

class SessionStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

class ConversationStep(Enum):
    COLLECTING_INFO = "collecting_info"
    GENERATING_QUOTE = "generating_quote"
    AWAITING_RESPONSE = "awaiting_response"
    COLLECTING_BILLING = "collecting_billing"
    COMPLETED = "completed"

class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class RequestStatus(Enum):
    PENDING = "pending"
    QUOTED = "quoted"
    ACCEPTED = "accepted"
    COMPLETED = "completed"

class QuotationStatus(Enum):
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"

# === CONVERSATION LAYER ===

class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[SessionStatus] = mapped_column(SQLEnum(SessionStatus), default=SessionStatus.ACTIVE)
    current_step: Mapped[Optional[ConversationStep]] = mapped_column(SQLEnum(ConversationStep))
    context: Mapped[Optional[str]] = mapped_column(Text)  # JSON context
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    messages = relationship("Message", back_populates="session")
    quotation_requests = relationship("QuotationRequest", back_populates="session")

class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversation_sessions.id"), index=True)
    role: Mapped[MessageRole] = mapped_column(SQLEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    _metadata: Mapped[Optional[str]] = mapped_column(Text)  # JSON metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    session = relationship("ConversationSession", back_populates="messages")

# === BUSINESS LAYER ===

class Client(Base):
    __tablename__ = "clients"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cc_nit: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombre_solicitante: Mapped[str] = mapped_column(String(200), nullable=False)
    celular_contacto: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    quotation_requests = relationship("QuotationRequest", back_populates="client")

class QuotationRequest(Base):
    __tablename__ = "quotation_requests"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # Prenumbered form
    session_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("conversation_sessions.id"))
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id"))
    
    # Request metadata
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    quien_solicita: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Service details
    fecha_inicio_servicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    hora_inicio_servicio: Mapped[str] = mapped_column(String(10), nullable=False)
    direccion_inicio: Mapped[str] = mapped_column(String(500), nullable=False)
    hora_terminacion: Mapped[Optional[str]] = mapped_column(String(10))
    direccion_terminacion: Mapped[Optional[str]] = mapped_column(String(500))
    caracteristicas_servicio: Mapped[str] = mapped_column(Text, nullable=False)
    cantidad_pasajeros: Mapped[int] = mapped_column(Integer, nullable=False)
    equipaje_carga: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Multiple services flag
    es_servicio_multiple: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Status tracking
    status: Mapped[RequestStatus] = mapped_column(SQLEnum(RequestStatus), default=RequestStatus.PENDING)
    
    # Relationships
    session = relationship("ConversationSession", back_populates="quotation_requests")
    client = relationship("Client", back_populates="quotation_requests")
    quotations = relationship("Quotation", back_populates="request")
    additional_services = relationship("AdditionalService", back_populates="main_request")

class AdditionalService(Base):
    __tablename__ = "additional_services"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    main_request_id: Mapped[int] = mapped_column(Integer, ForeignKey("quotation_requests.id"))
    
    fecha_servicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    hora_inicio: Mapped[str] = mapped_column(String(10), nullable=False)
    direccion_inicio: Mapped[str] = mapped_column(String(500), nullable=False)
    direccion_destino: Mapped[Optional[str]] = mapped_column(String(500))
    detalles: Mapped[str] = mapped_column(Text)
    
    # Relationships
    main_request = relationship("QuotationRequest", back_populates="additional_services")

class Quotation(Base):
    __tablename__ = "quotations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("quotation_requests.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)  # For iterative changes
    
    # Pricing
    precio_base: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
    precio_total: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Conditions
    condiciones_servicio: Mapped[str] = mapped_column(Text, nullable=False)
    condiciones_pago: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status
    status: Mapped[QuotationStatus] = mapped_column(SQLEnum(QuotationStatus), default=QuotationStatus.SENT)
    fecha_envio: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_respuesta: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    request = relationship("QuotationRequest", back_populates="quotations")
    billing_info = relationship("BillingInfo", back_populates="quotation", uselist=False)

class BillingInfo(Base):
    __tablename__ = "billing_info"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quotation_id: Mapped[int] = mapped_column(Integer, ForeignKey("quotations.id"))
    
    # Billing details (collected after acceptance)
    facturar_a_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    nit_facturacion: Mapped[str] = mapped_column(String(20), nullable=False)
    direccion_facturacion: Mapped[str] = mapped_column(String(500), nullable=False)
    telefono_facturacion: Mapped[str] = mapped_column(String(20), nullable=False)
    email_facturacion: Mapped[str] = mapped_column(String(100), nullable=False)
    responsable_servicio: Mapped[str] = mapped_column(String(100), nullable=False)
    celular_responsable: Mapped[str] = mapped_column(String(20), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationships
    quotation = relationship("Quotation", back_populates="billing_info")

# === TEST TABLE ===

class ConnectionTest(Base):
    __tablename__ = "connection_test"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_message: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

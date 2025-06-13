from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from decimal import Decimal

class QuotationEventType(str, Enum):
    """Types of quotation events"""
    REQUEST_CREATED = "request_created"
    REQUEST_VALIDATED = "request_validated"
    QUOTE_GENERATED = "quote_generated"
    QUOTE_SENT = "quote_sent"
    QUOTE_VIEWED = "quote_viewed"
    MODIFICATION_REQUESTED = "modification_requested"
    QUOTE_ACCEPTED = "quote_accepted"
    QUOTE_REJECTED = "quote_rejected"
    BILLING_INFO_COLLECTED = "billing_info_collected"
    SERVICE_CONFIRMED = "service_confirmed"

class QuotationRequestEvent(BaseModel):
    """Event for quotation request creation"""
    event_type: QuotationEventType = QuotationEventType.REQUEST_CREATED
    event_id: str = Field(description="Unique event ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Request details
    request_id: int
    form_number: str
    client_id: int
    session_id: Optional[int] = None
    
    # Service details
    quien_solicita: str
    fecha_inicio_servicio: datetime
    hora_inicio_servicio: str
    direccion_inicio: str
    direccion_terminacion: Optional[str] = None
    caracteristicas_servicio: str
    cantidad_pasajeros: int
    equipaje_carga: bool = False
    es_servicio_multiple: bool = False
    
    # Metadata
    source: str = "quotation_service"
    user_id: Optional[str] = None

class QuotationProcessingEvent(BaseModel):
    """Event for quotation processing stages"""
    event_type: QuotationEventType
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # References
    request_id: int
    quotation_id: Optional[int] = None
    
    # Processing data
    processing_stage: str
    processing_notes: Optional[str] = None
    assigned_processor: Optional[str] = None
    
    # Metadata
    source: str = "quotation_service"

class QuotationResponseEvent(BaseModel):
    """Event for quotation responses (generated quotes)"""
    event_type: QuotationEventType = QuotationEventType.QUOTE_GENERATED
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # References
    request_id: int
    quotation_id: int
    version: int = 1
    
    # Quote details
    precio_base: Decimal
    precio_total: Decimal
    condiciones_servicio: str
    condiciones_pago: str
    
    # Delivery info
    sent_to: Optional[str] = None
    delivery_method: str = "whatsapp"
    
    # Metadata
    source: str = "quotation_service"

class QuotationModificationEvent(BaseModel):
    """Event for quotation modifications"""
    event_type: QuotationEventType = QuotationEventType.MODIFICATION_REQUESTED
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # References
    original_quotation_id: int
    request_id: int
    
    # Modification details
    modification_reason: str
    requested_changes: Dict[str, Any]
    change_type: str  # "service_change", "date_change", "passenger_change", etc.
    
    # Client info
    requested_by: str
    client_notes: Optional[str] = None
    
    # Metadata
    source: str = "quotation_service"

class QuotationConfirmationEvent(BaseModel):
    """Event for quotation confirmations and decisions"""
    event_type: QuotationEventType
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # References
    quotation_id: int
    request_id: int
    
    # Decision details
    decision: str  # "accepted", "rejected"
    decision_reason: Optional[str] = None
    confirmed_by: str
    
    # For acceptances - billing info
    billing_data: Optional[Dict[str, Any]] = None
    
    # Service order info (for acceptances)
    service_order_id: Optional[str] = None
    
    # Metadata
    source: str = "quotation_service"

class QuotationEventMetadata(BaseModel):
    """Common metadata for all quotation events"""
    conversation_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # Business context
    business_unit: str = "transportation"
    service_type: Optional[str] = None
    priority: str = "normal"

# Event wrapper for Kafka
class QuotationKafkaEvent(BaseModel):
    """Wrapper for quotation events in Kafka messages"""
    event_data: Dict[str, Any]
    event_type: QuotationEventType
    topic: str
    partition_key: str
    headers: Dict[str, str] = Field(default_factory=dict)
    metadata: QuotationEventMetadata = Field(default_factory=QuotationEventMetadata)
    
    def to_kafka_message(self) -> Dict[str, Any]:
        """Convert to Kafka message format"""
        return {
            "event_type": self.event_type.value,
            "timestamp": datetime.now().isoformat(),
            "event_data": self.event_data,
            "metadata": self.metadata.model_dump(),
            "source": "quotation_workflow"
        }

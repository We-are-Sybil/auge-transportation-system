import pytest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict
import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.database.models import (
        Client,
        QuotationRequest,
        AdditionalService,
        Quotation,
        BillingInfo,
        RequestStatus,
        QuotationStatus,
        # ConversationSession
)

class TestClient:
    """Test suite for Client model."""

    @pytest.fixture
    def sample_client_data(self):
        """Sample client data for testing."""
        return {
                "cc_nit": "123456890",
                "nombre_solicitante": "Carlos Camargo Tobar",
                "celular_contacto": "3001234567",
        }

    @pytest.mark.unit
    @pytest.mark.database
    def test_client_initialization_with_required_fields(self, sample_client_data):
        """Test Client initialization with all required fields."""
        
        client = Client(**sample_client_data)

        assert client.cc_nit == "123456890"
        assert client.nombre_solicitante == "Carlos Camargo Tobar"
        assert client.celular_contacto == "3001234567"

    @pytest.mark.unit
    @pytest.mark.database
    def test_client_cc_nit_accepts_various_formats(self):
        """Test cc_nit field accepts various ID number formats."""
        id_formats = [
            "1234567890",       # Standard cedula
            "900123456-7",      # NIT with verification digit
            "52123456",         # Shorter cedular
            "CC1234567890",     # Cedula with CC prefix
        ]

        for cc_nit in id_formats:
            client = Client(
                cc_nit=cc_nit,
                nombre_solicitante="Usuario de prueba",
                celular_contacto="3001234567",
            )
            assert client.cc_nit == cc_nit

    @pytest.mark.unit
    @pytest.mark.database
    def test_client_handle_special_characters_in_name(self):
        """Test client name field handles special (spanish) characters and accents."""
        
        names = [
            "José María Hernández",
            "Ana Sofía Muñoz",
            "Carlos Andrés Peña",
            "María José Rodríguez-Vélez"
        ]

        for name in names:
            client = Client(
                cc_nit = "1234567890",
                nombre_solicitante = name,
                celular_contacto = "3001234567",
            )
            assert client.nombre_solicitante == name

    @pytest.mark.unit
    @pytest.mark.database
    def test_client_relationship_setup(self):
        """Test Client has relationship to QuotationRequest defined."""

        client = Client(
            cc_nit = "1234567890",
            nombre_solicitante = "Usuario de Prueba",
            celular_contacto = "3001234567",
        )

        assert hasattr(client, 'quotation_requests')
    

class TestQuotationRequest:
    """Test suite for QuotationRequest model."""

    @pytest.fixture
    def sample_quotation_data(self):
        """Sample quotation request data for testing."""
        return {
            "form_number": "FORM-2025-001",
            "client_id": 1,
            "session_id": 1,
            "quien_solicita": "María Garía",
            "fecha_inicio_servicio": datetime(2025, 6, 25, 14, 30),
            "hora_inicio_servicio": "14:30",
            "direccion_inicio": "Aeropuerto El Dorado, Terminal 1",
            "direccion_terminacion": "Hotel Hilton, Zona Rosa",
            "caracteristicas_servicio": "Transporte ejecutivo para 2 pasajeros",
            "cantidad_pasajeros": 2,
        }

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_request_initialization_required_fields(self, sample_quotation_data):
        """Test QuotationRequest initialization with required fields."""

        quotation = QuotationRequest(**sample_quotation_data)

        assert quotation.form_number == "FORM-2025-001"
        assert quotation.client_id == 1
        assert quotation.session_id == 1
        assert quotation.quien_solicita == "María Garía"
        assert quotation.fecha_inicio_servicio == datetime(2025, 6, 25, 14, 30)
        assert quotation.hora_inicio_servicio == "14:30"
        assert quotation.direccion_inicio == "Aeropuerto El Dorado, Terminal 1"
        assert quotation.direccion_terminacion == "Hotel Hilton, Zona Rosa"
        assert quotation.caracteristicas_servicio == "Transporte ejecutivo para 2 pasajeros"
        assert quotation.cantidad_pasajeros == 2

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_request_optional_fields_defaults(self):
        """Test QuotationRequest optional fields and defaults."""

        quotation = QuotationRequest(
            form_number="FORM-TEST",
            client_id=1,
            quien_solicita="Test User",
            fecha_inicio_servicio=datetime.now(),
            hora_inicio_servicio="10:00",
            direccion_inicio="Test Address",
            caracteristicas_servicio="Test Service",
            cantidad_pasajeros=1
        )
        

        assert quotation.session_id is None  # Optional field
        assert quotation.hora_terminacion is None  # Optional field
        assert quotation.direccion_terminacion is None  # Optional field
        assert quotation.equipaje_carga is None  # Database default not applied in Python
        assert quotation.es_servicio_multiple is None  # Database default not applied in Python
        assert quotation.status is None  # Database default not applied in Python

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_request_status_enum_validation(self):
        """Test RequestStatus enum values accepted."""

        for status in RequestStatus:
            quotation = QuotationRequest(
                form_number=f"FORM-{status.value}",
                client_id=1,
                quien_solicita="Usuario de Prueba",
                fecha_inicio_servicio=datetime.now(),
                hora_inicio_servicio="10:00",
                direccion_inicio="Dirección de prueba.",
                caracteristicas_servicio="Caracteristicas de prueba.",
                cantidad_pasajeros=1,
                status=status,
            )
            assert quotation.status == status

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_request_boolean_fields_explicit_values(self):
        """Test boolean fields accept explicit values."""

        quotation = QuotationRequest(
            form_number="FORM-BOOL-TEST",
            client_id=1,
            quien_solicita="Test User",
            fecha_inicio_servicio=datetime.now(),
            hora_inicio_servicio="10:00",
            direccion_inicio="Test Address",
            caracteristicas_servicio="Test Service",
            cantidad_pasajeros=1,
            equipaje_carga=True,
            es_servicio_multiple=True
        )

        assert quotation.equipaje_carga is True
        assert quotation.es_servicio_multiple is True

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_request_relationships_defined(self):
        """Test QuotationRequest relationships are properly defined."""

        quotation = QuotationRequest(
            form_number="FORM-REL-TEST",
            client_id=1,
            quien_solicita="Test User",
            fecha_inicio_servicio=datetime.now(),
            hora_inicio_servicio="10:00",
            direccion_inicio="Test Address",
            caracteristicas_servicio="Test Service",
            cantidad_pasajeros=1
        )
        

        assert hasattr(quotation, 'session')
        assert hasattr(quotation, 'client')
        assert hasattr(quotation, 'quotations')
        assert hasattr(quotation, 'additional_services')

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_request_time_format_validation(self):
        """Test time fields accept valid time formats."""

        time_formats = ["09:00 am", "14:30", "23:59", "01:00PM"]
        
        for time_str in time_formats:
            quotation = QuotationRequest(
                form_number=f"FORM-TIME-{time_str.replace(':', '')}",
                client_id=1,
                quien_solicita="Test User",
                fecha_inicio_servicio=datetime.now(),
                hora_inicio_servicio=time_str,
                direccion_inicio="Test Address",
                caracteristicas_servicio="Test Service",
                cantidad_pasajeros=1
            )
            assert quotation.hora_inicio_servicio == time_str

class TestAdditionalService:
    """Test suite for AdditionalService model."""

    @pytest.fixture
    def sample_additional_service_data(self):
        """Sample additional service data for testing."""
        return {
            "main_request_id": 1,
            "fecha_servicio": datetime(2025, 6, 26, 9, 0),
            "hora_inicio": "09:00",
            "direccion_inicio": "Hotel Hilton, Zona Rosa",
            "direccion_destino": "Centro Comercial Andino",
            "detalles": "Regreso del cliente al centro comercial"
        }

    @pytest.mark.unit
    @pytest.mark.database
    def test_additional_service_initialization(self, sample_additional_service_data):
        """Test AdditionalService initialization with all fields."""

        service = AdditionalService(**sample_additional_service_data)
        
        assert service.main_request_id == 1
        assert service.fecha_servicio == datetime(2025, 6, 26, 9, 0)
        assert service.hora_inicio == "09:00"
        assert service.direccion_inicio == "Hotel Hilton, Zona Rosa"
        assert service.direccion_destino == "Centro Comercial Andino"
        assert service.detalles == "Regreso del cliente al centro comercial"

    @pytest.mark.unit
    @pytest.mark.database
    def test_additional_service_required_fields_only(self):
        """Test AdditionalService with only required fields."""

        service = AdditionalService(
            main_request_id=1,
            fecha_servicio=datetime.now(),
            hora_inicio="10:00",
            direccion_inicio="Start Location"
        )
        

        assert service.main_request_id == 1
        assert service.direccion_destino is None  # Optional field
        assert service.detalles is None  # Optional field

    @pytest.mark.unit
    @pytest.mark.database
    def test_additional_service_foreign_key_relationship(self):
        """Test AdditionalService foreign key to QuotationRequest."""

        service = AdditionalService(
            main_request_id=123,
            fecha_servicio=datetime.now(),
            hora_inicio="15:00",
            direccion_inicio="Test Location"
        )
        

        assert service.main_request_id == 123
        assert hasattr(service, 'main_request')  # Relationship attribute


class TestQuotation:
    """Test suite for Quotation model."""

    @pytest.fixture
    def sample_quotation_data(self):
        """Sample quotation data for testing."""
        return {
            "request_id": 1,
            "version": 1,
            "precio_base": Decimal("150000.00"),
            "precio_total": Decimal("178500.00"),
            "condiciones_servicio": "Servicio incluye espera de 30 minutos",
            "condiciones_pago": "Pago contra entrega, efectivo o transferencia"
        }

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_initialization_with_required_fields(self, sample_quotation_data):
        """Test Quotation initialization with required fields."""

        quotation = Quotation(**sample_quotation_data)
        
        assert quotation.request_id == 1
        assert quotation.version == 1
        assert quotation.precio_base == Decimal("150000.00")
        assert quotation.precio_total == Decimal("178500.00")
        assert quotation.condiciones_servicio == "Servicio incluye espera de 30 minutos"
        assert quotation.condiciones_pago == "Pago contra entrega, efectivo o transferencia"

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_status_enum_validation(self):
        """Test QuotationStatus enum values are accepted."""

        for status in QuotationStatus:
            quotation = Quotation(
                request_id=1,
                precio_base=Decimal("100.00"),
                precio_total=Decimal("119.00"),
                condiciones_servicio="Test conditions",
                condiciones_pago="Test payment",
                status=status
            )
            assert quotation.status == status

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_version_default_and_custom(self):
        """Test quotation version default and custom values."""

        quotation1 = Quotation(
            request_id=1,
            precio_base=Decimal("100.00"),
            precio_total=Decimal("119.00"),
            condiciones_servicio="Test conditions",
            condiciones_pago="Test payment"
        )
        assert quotation1.version is None  # Database default not applied in Python
        
        quotation2 = Quotation(
            request_id=1,
            version=3,
            precio_base=Decimal("100.00"),
            precio_total=Decimal("119.00"),
            condiciones_servicio="Test conditions",
            condiciones_pago="Test payment"
        )
        assert quotation2.version == 3

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_decimal_precision_handling(self):
        """Test Decimal fields handle precision correctly."""

        quotation = Quotation(
            request_id=1,
            precio_base=Decimal("1234567.89"),
            precio_total=Decimal("1468255.50"),
            condiciones_servicio="Test conditions",
            condiciones_pago="Test payment"
        )
        

        assert isinstance(quotation.precio_base, Decimal)
        assert isinstance(quotation.precio_total, Decimal)
        assert quotation.precio_base == Decimal("1234567.89")
        assert quotation.precio_total == Decimal("1468255.50")

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_optional_datetime_fields(self):
        """Test optional datetime fields behavior."""

        quotation = Quotation(
            request_id=1,
            precio_base=Decimal("100.00"),
            precio_total=Decimal("119.00"),
            condiciones_servicio="Test conditions",
            condiciones_pago="Test payment"
        )
        

        # fecha_envio has server_default, so it's None in Python object
        assert quotation.fecha_respuesta is None  # Optional field

    @pytest.mark.unit
    @pytest.mark.database
    def test_quotation_relationships_defined(self):
        """Test Quotation relationships are properly defined."""

        quotation = Quotation(
            request_id=1,
            precio_base=Decimal("100.00"),
            precio_total=Decimal("119.00"),
            condiciones_servicio="Test conditions",
            condiciones_pago="Test payment"
        )
        
        assert hasattr(quotation, 'request')
        assert hasattr(quotation, 'billing_info')


class TestBillingInfo:
    """Test suite for BillingInfo model."""

    @pytest.fixture
    def sample_billing_data(self):
        """Sample billing info data for testing."""
        return {
            "quotation_id": 1,
            "facturar_a_nombre": "Empresa XYZ S.A.S.",
            "nit_facturacion": "900123456-7",
            "direccion_facturacion": "Calle 100 # 20-30, Oficina 401",
            "telefono_facturacion": "6012345678",
            "email_facturacion": "facturacion@empresaxyz.com",
            "responsable_servicio": "Ana María López",
            "celular_responsable": "3101234567"
        }

    @pytest.mark.unit
    @pytest.mark.database
    def test_billing_info_initialization_all_fields(self, sample_billing_data):
        """Test BillingInfo initialization with all required fields."""

        billing = BillingInfo(**sample_billing_data)
        
        assert billing.quotation_id == 1
        assert billing.facturar_a_nombre == "Empresa XYZ S.A.S."
        assert billing.nit_facturacion == "900123456-7"
        assert billing.direccion_facturacion == "Calle 100 # 20-30, Oficina 401"
        assert billing.telefono_facturacion == "6012345678"
        assert billing.email_facturacion == "facturacion@empresaxyz.com"
        assert billing.responsable_servicio == "Ana María López"
        assert billing.celular_responsable == "3101234567"

    @pytest.mark.unit
    @pytest.mark.database
    def test_billing_info_nit_format_validation(self):
        """Test NIT field accepts valid Colombian tax ID formats."""

        nit_formats = [
            "900123456-7",        # Standard NIT with verification digit
            "900123456",          # NIT without verification digit  
            "123456789-0",        # Different verification digit
            "8001234567",         # Natural person NIT
        ]
        
        for nit in nit_formats:
            billing = BillingInfo(
                quotation_id=1,
                facturar_a_nombre="Test Company",
                nit_facturacion=nit,
                direccion_facturacion="Test Address",
                telefono_facturacion="6012345678",
                email_facturacion="test@example.com",
                responsable_servicio="Test Person",
                celular_responsable="3101234567"
            )
            assert billing.nit_facturacion == nit

    @pytest.mark.unit
    @pytest.mark.database
    def test_billing_info_email_format_acceptance(self):
        """Test billing info accepts various email formats."""

        emails = [
            "simple@example.com",
            "user.name@domain.com",
            "user+tag@company.co.uk",
            "123numbers@test.org"
        ]
        
        for email in emails:
            billing = BillingInfo(
                quotation_id=1,
                facturar_a_nombre="Test Company",
                nit_facturacion="123456789",
                direccion_facturacion="Test Address",
                telefono_facturacion="6012345678",
                email_facturacion=email,
                responsable_servicio="Test Person",
                celular_responsable="3101234567"
            )
            assert billing.email_facturacion == email

    @pytest.mark.unit
    @pytest.mark.database
    def test_billing_info_quotation_relationship(self):
        """Test BillingInfo relationship to Quotation."""

        billing = BillingInfo(
            quotation_id=123,
            facturar_a_nombre="Test Company",
            nit_facturacion="123456789",
            direccion_facturacion="Test Address",
            telefono_facturacion="6012345678",
            email_facturacion="test@example.com",
            responsable_servicio="Test Person",
            celular_responsable="3101234567"
        )
        
        assert billing.quotation_id == 123
        assert hasattr(billing, 'quotation')  # Relationship attribute

    @pytest.mark.unit
    @pytest.mark.database
    def test_billing_info_phone_number_formats(self):
        """Test billing info accepts various phone number formats."""
        # Various phone formats
        phone_numbers = [
            "6012345678",      # Landline
            "3101234567",      # Mobile
            "+57 601 234 5678", # International format
            "601-234-5678"     # With dashes
        ]
        
        for phone in phone_numbers:
            billing = BillingInfo(
                quotation_id=1,
                facturar_a_nombre="Test Company",
                nit_facturacion="123456789",
                direccion_facturacion="Test Address",
                telefono_facturacion=phone,
                email_facturacion="test@example.com",
                responsable_servicio="Test Person",
                celular_responsable="3101234567"
            )
            assert billing.telefono_facturacion == phone

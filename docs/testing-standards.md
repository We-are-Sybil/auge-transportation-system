# Testing Standards & Guidelines

## Testing Pyramid Structure

### Unit Tests (70%)
- **Scope**: Individual functions, methods, and classes
- **Dependencies**: Mocked/stubbed
- **Execution**: Fast (<100ms per test)
- **Location**: `tests/unit/`

### Integration Tests (20%)
- **Scope**: Service-to-service communication
- **Dependencies**: Real connections to test services
- **Execution**: Medium speed (<5s per test)
- **Location**: `tests/integration/`

### End-to-End Tests (10%)
- **Scope**: Complete workflow validation
- **Dependencies**: Full stack running
- **Execution**: Slow (>5s per test)
- **Location**: `tests/e2e/`

## Naming Conventions

### Test Files
```
test_<module_name>.py          # Unit tests
test_<service>_integration.py  # Integration tests
test_<workflow>_e2e.py        # End-to-end tests
```

### Test Classes & Methods
```python
class TestCrewAIService:
    def test_agent_initialization_success(self):
    def test_agent_initialization_with_invalid_config_raises_error(self):
    def test_message_processing_updates_state(self):

class TestFastAPIEndpoints:
    def test_webhook_receive_valid_payload_returns_200(self):
    def test_webhook_receive_invalid_signature_returns_401(self):
```

### Test Markers
```python
@pytest.mark.unit
@pytest.mark.crewai
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.database
```

## Code Structure Patterns

### Unit Test Template
```python
"""Unit tests for <component_name>."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.<module> import <Component>

class Test<Component>:
    """Test suite for <Component>."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies."""
        return {
            'db': AsyncMock(),
            'redis': Mock(),
            'config': Mock()
        }
    
    @pytest.fixture
    def component(self, mock_dependencies):
        """Create component instance with mocked dependencies."""
        return <Component>(**mock_dependencies)
    
    async def test_method_success_case(self, component):
        """Test successful execution path."""
        # Arrange
        expected_result = "expected"
        
        # Act
        result = await component.method()
        
        # Assert
        assert result == expected_result
    
    async def test_method_error_case_raises_exception(self, component):
        """Test error handling."""
        # Arrange
        component.dependency.side_effect = ValueError("error")
        
        # Act & Assert
        with pytest.raises(ValueError, match="error"):
            await component.method()
```

### Integration Test Template
```python
"""Integration tests for <service_name>."""

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
async def postgres_container():
    """Start PostgreSQL container for tests."""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture(scope="session") 
async def redis_container():
    """Start Redis container for tests."""
    with RedisContainer("redis:7") as redis:
        yield redis

class Test<Service>Integration:
    """Integration tests for <Service>."""
    
    async def test_service_workflow_with_real_dependencies(
        self, postgres_container, redis_container
    ):
        """Test complete service workflow."""
        # Test with real database and cache connections
        pass
```

## CrewAI Testing Patterns

### Agent Testing
```python
class TestTransportationAgent:
    @pytest.fixture
    def agent_config(self):
        return {
            "role": "Transportation Coordinator",
            "goal": "Process transportation requests",
            "backstory": "Expert in logistics",
        }
    
    async def test_agent_processes_request_successfully(self, agent_config):
        """Test agent processes valid transportation request."""
        pass
```

### Crew Testing
```python
class TestRequestCrew:
    @pytest.fixture
    def crew_config(self):
        return {
            "agents": [mock_agent],
            "tasks": [mock_task],
            "process": "sequential"
        }
    
    async def test_crew_executes_tasks_in_sequence(self, crew_config):
        """Test crew task execution flow."""
        pass
```

## FastAPI Testing Patterns

### Endpoint Testing
```python
import httpx
from fastapi.testclient import TestClient

class TestWebhookEndpoints:
    @pytest.fixture
    def client(self):
        from src.api_server import app
        return TestClient(app)
    
    async def test_webhook_endpoint_processes_whatsapp_message(self, client):
        """Test webhook processes WhatsApp message correctly."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{"text": {"body": "Hello"}}]
                    }
                }]
            }]
        }
        
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
```

## Database Testing Patterns

### Model Testing
```python
class TestTransportationModels:
    async def test_quotation_model_validation(self):
        """Test quotation model field validation."""
        pass
    
    async def test_quotation_model_relationships(self):
        """Test model relationships are correctly defined."""
        pass
```

## Test Data Management

### Factories
```python
import factory
from src.schemas.quotation import QuotationCreate

class QuotationFactory(factory.Factory):
    class Meta:
        model = QuotationCreate
    
    origin = factory.Faker('address')
    destination = factory.Faker('address')
    service_type = factory.Faker('random_element', elements=['taxi', 'van', 'truck'])
    passenger_count = factory.Faker('random_int', min=1, max=8)
```

### Fixtures
```python
@pytest.fixture
def sample_quotation_request():
    """Sample quotation request for testing."""
    return QuotationFactory()

@pytest.fixture
def sample_whatsapp_message():
    """Sample WhatsApp message payload."""
    return {
        "from": "573001234567",
        "text": {"body": "Need transportation from Airport to Hotel"},
        "timestamp": "1234567890"
    }
```

## Performance Testing

### Load Testing
```python
@pytest.mark.slow
async def test_concurrent_webhook_processing():
    """Test system handles concurrent webhook requests."""
    # Use asyncio.gather() to simulate concurrent requests
    pass

@pytest.mark.performance
async def test_crew_processing_time_under_threshold():
    """Test crew processes requests within time limits."""
    # Assert processing time < 30 seconds
    pass
```

## Assertion Patterns

### State Assertions
```python
# Good: Specific assertions
assert quotation.status == QuotationStatus.PENDING
assert len(quotation.items) == 3
assert quotation.total_amount == Decimal('150.00')

# Avoid: Vague assertions
assert quotation
assert quotation.items
```

### Exception Testing
```python
# Test specific exception types and messages
with pytest.raises(ValidationError) as exc_info:
    await service.process_invalid_request(request)

assert "origin address is required" in str(exc_info.value)
```

## Mock Usage Guidelines

### External Services
```python
@patch('src.tools.provider_api_tool.ProviderAPITool.get_availability')
async def test_availability_check(mock_get_availability):
    """Mock external provider API calls."""
    mock_get_availability.return_value = {"available": True}
    # Test logic
```

### Database Operations
```python
@pytest.fixture
def mock_db_session():
    """Mock database session for unit tests."""
    session = AsyncMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    return session
```

## Coverage Requirements

- **Minimum Coverage**: 80% overall
- **Critical Paths**: 95% coverage
- **New Code**: 90% coverage
- **Integration Tests**: Cover all service boundaries
- **E2E Tests**: Cover main user workflows

## Continuous Integration

### Test Execution Order
1. Unit tests (parallel execution)
2. Integration tests (sequential)
3. E2E tests (critical workflows only)

### Test Commands
```bash
# All tests
uv run pytest

# Unit tests only
uv run pytest -m unit

# Integration tests
uv run pytest -m integration

# Coverage report
uv run pytest --cov-report=html
```

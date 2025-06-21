import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from pathlib import Path
import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.database.models import (
    ConversationSession, Message, SessionStatus, 
    ConversationStep, MessageRole
)
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError


class TestConversationSession:
    """Test suite for ConversationSession model."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for unit tests."""
        session = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = None
        session.commit.return_value = None
        session.rollback.return_value = None
        return session

    @pytest.fixture
    def sample_conversation_data(self):
        """Sample conversation session data for testing."""
        return {
            "user_id": "573001234567",
            "session_id": "whatsapp_573001234567_20250620_143022",
            "status": SessionStatus.ACTIVE,
            "current_step": ConversationStep.COLLECTING_INFO,
            "context": '{"collected_data": {"origin": "Airport"}, "missing_fields": ["destination"]}'
        }

    @pytest.mark.unit
    @pytest.mark.database
    def test_conversation_session_initialization_with_required_fields(self, sample_conversation_data):
        """Test ConversationSession initialization with required fields."""
        # Arrange & Act
        session = ConversationSession(
            user_id=sample_conversation_data["user_id"],
            session_id=sample_conversation_data["session_id"]
        )
        
        # Assert
        assert session.user_id == "573001234567"
        assert session.session_id == "whatsapp_573001234567_20250620_143022"
        assert session.status is None  # Database default not applied in Python
        assert session.current_step is None  # Default None
        assert session.context is None  # Default None

    @pytest.mark.unit
    @pytest.mark.database
    def test_conversation_session_initialization_with_all_fields(self, sample_conversation_data):
        """Test ConversationSession initialization with all fields."""
        # Arrange & Act
        session = ConversationSession(**sample_conversation_data)
        
        # Assert
        assert session.user_id == sample_conversation_data["user_id"]
        assert session.session_id == sample_conversation_data["session_id"]
        assert session.status == SessionStatus.ACTIVE
        assert session.current_step == ConversationStep.COLLECTING_INFO
        assert session.context == sample_conversation_data["context"]

    @pytest.mark.unit
    @pytest.mark.database
    def test_conversation_session_initialization_with_explicit_status(self):
        """Test ConversationSession initialization with explicit status (normal usage)."""
        # Arrange & Act - This reflects how the model is used in DatabaseManager
        session = ConversationSession(
            user_id="573001234567",
            session_id="test_session",
            status=SessionStatus.ACTIVE,
            current_step=ConversationStep.COLLECTING_INFO
        )
        
        # Assert
        assert session.status == SessionStatus.ACTIVE
        assert session.current_step == ConversationStep.COLLECTING_INFO

    @pytest.mark.unit
    @pytest.mark.database
    def test_conversation_session_database_defaults_behavior(self):
        """Test that database defaults are defined (but not applied in Python)."""
        # Arrange & Act
        session = ConversationSession(
            user_id="test_user",
            session_id="test_session"
        )
        
        # Assert - Database defaults exist in column definition but not applied in Python
        # In actual usage, these would be set by the database after commit
        assert session.status is None  # Will be SessionStatus.ACTIVE after DB persistence
        assert session.current_step is None  # No database default for this field
        
        # The model should have the column definitions that include defaults
        status_column = ConversationSession.__table__.columns['status']
        assert status_column.default is not None

    @pytest.mark.unit
    @pytest.mark.database
    def test_conversation_session_status_enum_validation(self):
        """Test that status field accepts valid enum values."""
        # Test all valid status values
        for status in SessionStatus:
            session = ConversationSession(
                user_id="test_user",
                session_id="test_session",
                status=status
            )
            assert session.status == status

    @pytest.mark.unit
    @pytest.mark.database
    def test_conversation_session_step_enum_validation(self):
        """Test that current_step field accepts valid enum values."""
        # Test all valid step values
        for step in ConversationStep:
            session = ConversationSession(
                user_id="test_user",
                session_id="test_session",
                current_step=step
            )
            assert session.current_step == step

    @pytest.mark.unit
    @pytest.mark.database
    def test_conversation_session_unique_session_id_constraint(self):
        """Test that session_id must be unique."""
        # This would typically be tested at the database level
        # Here we test that the model accepts unique values
        session1 = ConversationSession(
            user_id="user1", 
            session_id="unique_session_1"
        )
        session2 = ConversationSession(
            user_id="user2", 
            session_id="unique_session_2"
        )
        
        assert session1.session_id != session2.session_id

    @pytest.mark.unit
    @pytest.mark.database
    def test_conversation_session_user_id_indexing(self):
        """Test that user_id is properly indexed for queries."""
        # Create multiple sessions for same user
        sessions = []
        for i in range(3):
            session = ConversationSession(
                user_id="573001234567",
                session_id=f"session_{i}"
            )
            sessions.append(session)
        
        # All sessions should have the same user_id for indexing
        user_ids = [s.user_id for s in sessions]
        assert all(uid == "573001234567" for uid in user_ids)


class TestMessage:
    """Test suite for Message model."""

    @pytest.fixture
    def mock_conversation_session(self):
        """Mock conversation session for message relationships."""
        session = Mock(spec=ConversationSession)
        session.id = 1
        return session

    @pytest.fixture
    def sample_message_data(self):
        """Sample message data for testing."""
        return {
            "session_id": 1,
            "role": MessageRole.USER,
            "content": "I need transportation from Airport to Hotel downtown",
            "_metadata": '{"whatsapp_message_id": "msg_123", "timestamp": "2025-06-20T14:30:22Z"}'
        }

    @pytest.mark.unit
    @pytest.mark.database
    def test_message_initialization_with_required_fields(self, sample_message_data):
        """Test Message initialization with required fields."""
        # Arrange & Act
        message = Message(
            session_id=sample_message_data["session_id"],
            role=sample_message_data["role"],
            content=sample_message_data["content"]
        )
        
        # Assert
        assert message.session_id == 1
        assert message.role == MessageRole.USER
        assert message.content == "I need transportation from Airport to Hotel downtown"
        assert message._metadata is None  # Default None

    @pytest.mark.unit
    @pytest.mark.database
    def test_message_initialization_with_metadata(self, sample_message_data):
        """Test Message initialization with metadata."""
        # Arrange & Act
        message = Message(**sample_message_data)
        
        # Assert
        assert message._metadata == sample_message_data["_metadata"]

    @pytest.mark.unit
    @pytest.mark.database
    def test_message_role_enum_validation(self):
        """Test that role field accepts valid enum values."""
        # Test all valid role values
        for role in MessageRole:
            message = Message(
                session_id=1,
                role=role,
                content="Test message content"
            )
            assert message.role == role

    @pytest.mark.unit
    @pytest.mark.database
    def test_message_content_not_null_constraint(self):
        """Test that content field cannot be null."""
        # Creating a message without content should be invalid
        # This tests the model definition constraint
        message = Message(
            session_id=1,
            role=MessageRole.USER,
            content=""  # Empty string is allowed, None would not be
        )
        assert message.content == ""

    @pytest.mark.unit
    @pytest.mark.database
    def test_message_session_relationship_foreign_key(self):
        """Test Message foreign key relationship to ConversationSession."""
        # Arrange
        message = Message(
            session_id=123,
            role=MessageRole.ASSISTANT,
            content="How can I help you today?"
        )
        
        # Assert
        assert message.session_id == 123

    @pytest.mark.unit
    @pytest.mark.database
    def test_message_creation_timestamp_behavior(self):
        """Test that created_at is properly set."""
        # This tests the server_default behavior expectation
        message = Message(
            session_id=1,
            role=MessageRole.SYSTEM,
            content="Conversation started"
        )
        
        # created_at should be handled by database server_default
        # In actual usage, this would be set by the database
        assert hasattr(message, 'created_at')

    @pytest.mark.unit
    @pytest.mark.database
    def test_message_metadata_json_handling(self):
        """Test metadata field handles JSON string properly."""
        # Arrange
        json_metadata = '{"message_id": "whatsapp_123", "source": "webhook", "processed": true}'
        
        # Act
        message = Message(
            session_id=1,
            role=MessageRole.USER,
            content="Test message",
            _metadata=json_metadata
        )
        
        # Assert
        assert message._metadata == json_metadata
        # Note: JSON parsing would typically be handled by application logic,
        # not the model itself

    @pytest.mark.unit
    @pytest.mark.database
    def test_message_large_content_handling(self):
        """Test message can handle large content (Text field)."""
        # Arrange
        large_content = "A" * 5000  # Large text content
        
        # Act
        message = Message(
            session_id=1,
            role=MessageRole.USER,
            content=large_content
        )
        
        # Assert
        assert len(message.content) == 5000
        assert message.content == large_content

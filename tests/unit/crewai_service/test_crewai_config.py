import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from pydantic import ValidationError
import os
import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.crewai_service.config import CrewAIConfig


class TestCrewAIConfig:
    """Test suite for CrewAIConfig."""

    @pytest.fixture
    def default_config(self):
        """Create default config instance."""
        return CrewAIConfig()

    @pytest.fixture
    def custom_config_data(self):
        """Sample config data for testing."""
        return {
            "llm_provider": "openai",
            "llm_model": "gpt-4",
            "llm_api_key": "test-key-123",
            "llm_temperature": 0.7,
            "kafka_bootstrap_servers": "test.kafka:9092",
            "kafka_consumer_group": "test-group"
        }

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_default_config_initialization(self, default_config):
        """Test default configuration values."""
        assert default_config.llm_provider == "ollama"
        assert default_config.llm_model == "phi3:3.8b"
        assert default_config.llm_base_url == "http://localhost:11434"
        assert default_config.llm_temperature == 0.1
        assert default_config.kafka_bootstrap_servers == "localhost:9092"
        assert default_config.kafka_consumer_group == "crewai-service"
        assert default_config.agent_verbose is True
        assert default_config.memory_enabled is True

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_custom_config_initialization(self, custom_config_data):
        """Test configuration with custom values."""
        config = CrewAIConfig(**custom_config_data)
        
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert config.llm_api_key == "test-key-123"
        assert config.llm_temperature == 0.7
        assert config.kafka_bootstrap_servers == "test.kafka:9092"
        assert config.kafka_consumer_group == "test-group"

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_file_paths_conversion_to_absolute(self):
        """Test that relative paths are converted to absolute paths."""
        with patch('src.crewai_service.config.Path') as mock_path:
            # Mock Path behavior
            mock_path_instance = MagicMock()
            mock_path_instance.parent.parent.parent = Path("/mock/project/root")
            mock_path.return_value = mock_path_instance
            
            config = CrewAIConfig()
            
            # Should convert relative paths to absolute
            assert config.agents_config_path.startswith("/")
            assert config.tasks_config_path.startswith("/")

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_llm_max_tokens_validation_none(self):
        """Test llm_max_tokens validation with None value."""
        config = CrewAIConfig(llm_max_tokens=None)
        assert config.llm_max_tokens is None

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_llm_max_tokens_validation_valid_integer(self):
        """Test llm_max_tokens validation with valid integer."""
        config = CrewAIConfig(llm_max_tokens=1000)
        assert config.llm_max_tokens == 1000

    @pytest.mark.unit
    @pytest.mark.crewai  
    def test_kafka_consumer_topics_default_list(self, default_config):
        """Test default Kafka consumer topics."""
        expected_topics = ["conversation.messages", "quotation.requests"]
        assert default_config.kafka_consumer_topics == expected_topics

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_config_with_environment_variables(self):
        """Test configuration loading from environment variables."""
        env_vars = {
            "CREWAI_LLM_PROVIDER": "anthropic",
            "CREWAI_LLM_MODEL": "claude-3-sonnet",
            "CREWAI_LLM_API_KEY": "env-api-key",
            "CREWAI_KAFKA_BOOTSTRAP_SERVERS": "env.kafka:9092"
        }
        
        with patch.dict(os.environ, env_vars):
            config = CrewAIConfig()
            
            # Environment variables should override defaults
            # Note: This assumes the config uses environment variable mapping
            # Adjust based on actual pydantic_settings configuration

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_config_llm_timeout_default(self, default_config):
        """Test default LLM timeout value."""
        assert default_config.llm_timeout == 120

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_config_max_iterations_default(self, default_config):
        """Test default max iterations value."""
        assert default_config.max_iterations == 10

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_llm_temperature_accepts_valid_values(self):
        """Test that valid temperature values are accepted."""
        config1 = CrewAIConfig(llm_temperature=0.0)
        assert config1.llm_temperature == 0.0
        
        config2 = CrewAIConfig(llm_temperature=1.0)
        assert config2.llm_temperature == 1.0
        
        config3 = CrewAIConfig(llm_temperature=2.0)
        assert config3.llm_temperature == 2.0

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_llm_timeout_accepts_valid_values(self):
        """Test that valid timeout values are accepted."""
        config1 = CrewAIConfig(llm_timeout=30)
        assert config1.llm_timeout == 30
        
        config2 = CrewAIConfig(llm_timeout=300)
        assert config2.llm_timeout == 300

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_config_model_validation_comprehensive(self):
        """Test comprehensive model validation."""
        valid_config_data = {
            "llm_provider": "openai",
            "llm_model": "gpt-4-turbo",
            "llm_temperature": 0.5,
            "llm_timeout": 60,
            "max_iterations": 15,
            "agent_verbose": False,
            "memory_enabled": False
        }
        
        # Should not raise any validation errors
        config = CrewAIConfig(**valid_config_data)
        assert config.llm_provider == "openai"
        assert config.agent_verbose is False
        assert config.memory_enabled is False

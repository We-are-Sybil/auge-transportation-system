import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional, Dict, Any


class CrewAIConfig(BaseSettings):
    """Configuration for CrewAI service with generalized LLM support"""
    
    # LLM Configuration - Provider Agnostic
    llm_provider: str = "ollama"  # ollama, openai, anthropic, google, etc.
    llm_model: str = "phi3:3.8b"  # Model name without provider prefix
    llm_base_url: Optional[str] = "http://localhost:11434"  # For local providers like Ollama
    llm_api_key: Optional[str] = None  # API key for cloud providers
    llm_temperature: float = 0.1
    llm_max_tokens: Optional[int] = None
    llm_timeout: int = 120  # seconds
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_topics: List[str] = [
        "conversation.messages",
        "quotation.requests"
    ]
    kafka_consumer_group: str = "crewai-service"
    kafka_consumer_timeout: int = 30
    
    # Service Configuration
    agent_verbose: bool = True
    max_iterations: int = 10
    memory_enabled: bool = True
    
    # File paths (use absolute paths to avoid working directory issues)
    agents_config_path: str = "src/crewai_service/crews/config/agents.yaml"
    tasks_config_path: str = "src/crewai_service/crews/config/tasks.yaml"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Convert to absolute paths if they're relative
        project_root = Path(__file__).parent.parent.parent
        self.agents_config_path = str(project_root / self.agents_config_path)
        self.tasks_config_path = str(project_root / self.tasks_config_path)
    
    @field_validator('llm_max_tokens', mode='before')
    @classmethod
    def validate_llm_max_tokens(cls, v):
        """Handle empty strings for optional integer fields"""
        if v == "" or v is None:
            return None
        return int(v)
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = "CREWAI_"
        extra = "ignore"  # Ignore extra environment variables
    
    @property
    def llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration based on provider"""
        base_config = {
            "model": self._get_full_model_name(),
            "temperature": self.llm_temperature,
            "timeout": self.llm_timeout
        }
        
        # Add provider-specific configurations
        if self.llm_provider == "ollama":
            if self.llm_base_url:
                base_config["base_url"] = self.llm_base_url
        elif self.llm_provider in ["openai", "anthropic", "google"]:
            if self.llm_api_key:
                base_config["api_key"] = self.llm_api_key
        
        if self.llm_max_tokens:
            base_config["max_tokens"] = self.llm_max_tokens
            
        return base_config
    
    def _get_full_model_name(self) -> str:
        """Get full model name with provider prefix for CrewAI"""
        if self.llm_provider == "ollama":
            return f"ollama/{self.llm_model}"
        elif self.llm_provider == "openai":
            return self.llm_model  # OpenAI models don't need prefix
        elif self.llm_provider == "anthropic":
            return f"anthropic/{self.llm_model}"
        elif self.llm_provider == "google":
            return f"gemini/{self.llm_model}"
        else:
            # For other providers, use provider/model format
            return f"{self.llm_provider}/{self.llm_model}"
    
    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables needed for the LLM provider"""
        env_vars = {}
        
        if self.llm_provider == "openai" and self.llm_api_key:
            env_vars["OPENAI_API_KEY"] = self.llm_api_key
        elif self.llm_provider == "anthropic" and self.llm_api_key:
            env_vars["ANTHROPIC_API_KEY"] = self.llm_api_key
        elif self.llm_provider == "google" and self.llm_api_key:
            env_vars["GOOGLE_API_KEY"] = self.llm_api_key
        
        return env_vars


# Global config instance
config = CrewAIConfig()

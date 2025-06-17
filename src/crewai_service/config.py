import os
from pydantic_settings import BaseSettings
from typing import List, Optional


class CrewAIConfig(BaseSettings):
    """Configuration for CrewAI service"""

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "ollama/phi3:3.8"

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

    # File paths
    agents_config_path: str = "src/crewai_service/config/agents.yaml"
    tasks_config_path: str = "src/crewai_service/config/tasks.yaml"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
config = CrewAIConfig()

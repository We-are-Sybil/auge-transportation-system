__version__ = "0.1.0"

from .service import CrewAIService
from .kafka_consumer import CrewAIKafkaConsumer

__all__ = ["CrewAIService", "CrewAIKafkaConsumer"]

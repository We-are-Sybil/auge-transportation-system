import os
import logging
from datetime import datetime
from typing import Dict, Any
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from ..config import config


@CrewBase
class EchoCrew:
    """Simple echo crew for testing CrewAI service"""

    agents_config_path = config.agents_config_path
    tasks_config_path = config.tasks_config_path

    def __init__(self):
        # Set environment variables for the LLM provider
        env_vars = config.get_environment_variables()
        for key, value in env_vars.items():
            os.environ[key] = value
        
        # Create LLM instance using CrewAI's LLM class
        self.llm = LLM(**config.llm_config)

    @agent
    def echo_agent(self) -> Agent:
        """Create echo agent with generalized LLM"""
        return Agent(
            config=self.agents_config['echo_agent'],
            llm=self.llm,
            verbose=config.agent_verbose,
            memory=config.memory_enabled,
            max_iter=config.max_iterations
        )

    @task
    def echo_task(self) -> Task:
        """Create echo task"""
        return Task(
            config=self.tasks_config['echo_task']
        )

    @crew
    def crew(self) -> Crew:
        """Create the echo crew"""
        return Crew(
            agents=[self.echo_agent()],
            tasks=[self.echo_task()],
            process=Process.sequential,
            verbose=config.agent_verbose
        )

    def process_message(self, kafka_message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message from Kafka"""
        try:
            # Prepare input for the crew
            inputs = {
                "kafka_message": kafka_message
            }
            
            # Execute the crew
            result = self.crew().kickoff(inputs=inputs)
            
            return {
                "success": True,
                "processed_at": datetime.now().isoformat(),
                "agent_response": result.raw,
                "llm_provider": config.llm_provider,
                "llm_model": config.llm_model,
                "usage_metrics": result.usage_metrics if hasattr(result, 'usage_metrics') else None
            }
            
        except Exception as e:
            # Better error logging
            import traceback
            error_details = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "processed_at": datetime.now().isoformat(),
                "llm_provider": config.llm_provider,
                "llm_model": config.llm_model,
                "llm_config": config.llm_config,
                "original_message": kafka_message
            }
            
            # Log the full error for debugging
            logger = logging.getLogger(__name__)
            logger.error(f"CrewAI processing failed: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            logger.error(f"LLM config: {config.llm_config}")
            
            return error_details

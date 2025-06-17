from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List, Dict, Any, Optional
import sys
import os

# Add project root to path for config import
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
from src.crewai_service.config import config


@CrewBase
class QuotationCrew:
    """Crew for processing quotation requests and handling business logic"""
    agents: List[BaseAgent]
    tasks: List[Task]
    
    def __init__(self):
        super().__init__()
        # Initialize LLM using CrewAI's native LLM class
        self.llm = LLM(
            model=config._get_full_model_name(),
            temperature=config.llm_temperature,
            timeout=config.llm_timeout
        )

    @agent
    def quotation_processor(self) -> Agent:
        """Agent responsible for processing quotation requests and business logic"""
        return Agent(
            config=self.agents_config['quotation_processor'],
            llm=self.llm,
            verbose=True,
            allow_delegation=True  # Enable delegation for complex cases
        )

    @agent 
    def pricing_specialist(self) -> Agent:
        """Agent responsible for calculating pricing and generating quotes"""
        return Agent(
            config=self.agents_config['pricing_specialist'],
            llm=self.llm,
            verbose=True
        )

    @task
    def process_quotation_request(self) -> Task:
        """Process incoming quotation request and validate requirements"""
        return Task(
            config=self.tasks_config['process_quotation_request']
        )

    @task
    def generate_quotation(self) -> Task:
        """Generate detailed quotation with pricing and terms"""
        return Task(
            config=self.tasks_config['generate_quotation']
        )

    @crew
    def crew(self) -> Crew:
        """Creates the quotation processing crew with sequential processing"""
        return Crew(
            agents=[self.quotation_processor(), self.pricing_specialist()],
            tasks=[self.process_quotation_request(), self.generate_quotation()],
            process=Process.sequential,
            verbose=True,
            memory=True,  # Enable memory for quotation context
            llm=self.llm  # Add LLM configuration to the crew
        )

    def create_quotation(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process quotation request and generate quote
        
        Args:
            request_data: Dictionary containing quotation request data
            
        Returns:
            Dictionary with quotation details and status
        """
        try:
            # Execute the crew with the request data
            result = self.crew().kickoff(inputs={'request_data': request_data})
            
            return {
                'success': True,
                'quotation': result,
                'status': 'generated',
                'next_action': 'send_to_customer'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status': 'failed',
                'next_action': 'retry_or_manual_review'
            }

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
class ConversationCrew:
    """Crew for managing conversation state and dialogue flow"""
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
    def conversation_manager(self) -> Agent:
        """Agent responsible for tracking dialogue state and managing conversation flow"""
        return Agent(
            config=self.agents_config['conversation_manager'],
            llm=self.llm,
            verbose=True,
            allow_delegation=True  # Enable delegation to other agents
        )

    @agent 
    def dialogue_state_tracker(self) -> Agent:
        """Agent responsible for maintaining conversation context and state"""
        return Agent(
            config=self.agents_config['dialogue_state_tracker'],
            llm=self.llm,
            verbose=True
        )

    @task
    def track_conversation_state(self) -> Task:
        """Track and maintain conversation context and state"""
        return Task(
            config=self.tasks_config['track_conversation_state']
        )

    @task
    def manage_dialogue_flow(self) -> Task:
        """Manage conversation flow and determine next actions"""
        return Task(
            config=self.tasks_config['manage_dialogue_flow']
        )

    @crew
    def crew(self) -> Crew:
        """Creates the conversation management crew with sequential processing"""
        return Crew(
            agents=[self.conversation_manager(), self.dialogue_state_tracker()],
            tasks=[self.track_conversation_state(), self.manage_dialogue_flow()],
            process=Process.sequential,
            verbose=True,
            memory=True,  # Enable memory for conversation context
            llm=self.llm  # Add LLM configuration to the crew
        )

    def process_conversation_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming conversation message and return response with state
        
        Args:
            message: Dictionary containing conversation message data
            
        Returns:
            Dictionary with conversation response and updated state
        """
        try:
            # Execute the crew with the message input
            result = self.crew().kickoff(inputs={'message': message})
            
            return {
                'success': True,
                'response': result,
                'conversation_state': 'processed',
                'next_action': 'await_user_response'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'conversation_state': 'error',
                'next_action': 'retry_or_escalate'
            }

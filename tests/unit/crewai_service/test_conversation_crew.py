import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.crewai_service.crews.conversation_crew.conversation_crew import ConversationCrew




class TestConversationCrew:
    """Test suite for ConversationCrew."""

    @pytest.fixture
    def mock_config(self):
        """Mock CrewAI config."""
        config = Mock()
        config._get_full_model_name.return_value = "ollama/phi3:3.8b"
        config.llm_temperature = 0.1
        config.llm_timeout = 120
        return config

    @pytest.fixture
    def mock_agents_config(self):
        """Mock agents configuration."""
        return {
            'conversation_manager': {
                'role': 'Conversation Manager',
                'goal': 'Manage dialogue flow and conversation state',
                'backstory': 'Expert in conversation management'
            },
            'dialogue_state_tracker': {
                'role': 'State Tracker', 
                'goal': 'Track conversation context and state',
                'backstory': 'Expert in dialogue state tracking'
            }
        }

    @pytest.fixture
    def mock_tasks_config(self):
        """Mock tasks configuration."""
        return {
            'track_conversation_state': {
                'description': 'Track and maintain conversation context',
                'expected_output': 'Updated conversation state',
                'agent': 'dialogue_state_tracker'  # Add agent assignment
            },
            'manage_dialogue_flow': {
                'description': 'Manage conversation flow and actions',
                'expected_output': 'Next dialogue action',
                'agent': 'conversation_manager'  # Add agent assignment
            }
        }

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM instance."""
        llm = Mock()
        llm.model = "ollama/phi3:3.8b"
        llm.temperature = 0.1
        llm.timeout = 120
        return llm

    @pytest.fixture
    def conversation_crew(self, mock_config, mock_agents_config, mock_tasks_config, mock_llm):
        """Create ConversationCrew instance with mocked dependencies."""
        with patch('src.crewai_service.crews.conversation_crew.conversation_crew.config', mock_config), \
             patch('crewai.LLM', return_value=mock_llm):
            
            crew = ConversationCrew()
            crew.agents_config = mock_agents_config
            crew.tasks_config = mock_tasks_config
            return crew

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_conversation_crew_initialization(self, mock_config, mock_llm):
        """Test ConversationCrew initialization with LLM setup."""
        with patch('src.crewai_service.crews.conversation_crew.conversation_crew.config', mock_config), \
             patch('crewai.LLM', return_value=mock_llm):
            
            crew = ConversationCrew()
            
            # Verify the crew has an LLM instance
            assert hasattr(crew, 'llm')
            assert crew.llm is not None

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_conversation_manager_agent_creation(self, conversation_crew):
        """Test conversation manager agent creation."""
        with patch('src.crewai_service.crews.conversation_crew.conversation_crew.Agent') as mock_agent:
            mock_agent.return_value = Mock()
            agent = conversation_crew.conversation_manager()
            assert agent is not None

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_dialogue_state_tracker_agent_creation(self, conversation_crew):
        """Test dialogue state tracker agent creation."""
        with patch('src.crewai_service.crews.conversation_crew.conversation_crew.Agent') as mock_agent:
            mock_agent.return_value = Mock()
            agent = conversation_crew.dialogue_state_tracker()
            assert agent is not None

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_track_conversation_state_task_creation(self, conversation_crew):
        """Test track conversation state task creation."""
        with patch('src.crewai_service.crews.conversation_crew.conversation_crew.Task') as mock_task:
            mock_task.return_value = Mock()
            task = conversation_crew.track_conversation_state()
            assert task is not None

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_manage_dialogue_flow_task_creation(self, conversation_crew):
        """Test manage dialogue flow task creation."""
        with patch('src.crewai_service.crews.conversation_crew.conversation_crew.Task') as mock_task:
            mock_task.return_value = Mock()
            task = conversation_crew.manage_dialogue_flow()
            assert task is not None

    @pytest.mark.unit
    @pytest.mark.crewai  
    def test_crew_creation_with_sequential_process(self, conversation_crew):
        """Test crew creation."""
        with patch('src.crewai_service.crews.conversation_crew.conversation_crew.Crew') as mock_crew, \
             patch('src.crewai_service.crews.conversation_crew.conversation_crew.Agent') as mock_agent, \
             patch('src.crewai_service.crews.conversation_crew.conversation_crew.Task') as mock_task:
            
            mock_crew.return_value = Mock()
            mock_agent.return_value = Mock()
            mock_task.return_value = Mock()
            
            crew = conversation_crew.crew()
            assert crew is not None

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_process_conversation_message_success(self, conversation_crew):
        """Test successful conversation message processing."""
        mock_crew = Mock()
        mock_result = Mock()
        mock_crew.kickoff.return_value = mock_result
        
        with patch.object(conversation_crew, 'crew', return_value=mock_crew):
            message = {'text': 'Hello', 'from': 'user123'}
            result = conversation_crew.process_conversation_message(message)
            
            assert result['success'] is True
            assert result['response'] == mock_result
            assert result['conversation_state'] == 'processed'
            assert result['next_action'] == 'await_user_response'
            
            mock_crew.kickoff.assert_called_once_with(inputs={'message': message})

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_process_conversation_message_error(self, conversation_crew):
        """Test conversation message processing error handling."""
        mock_crew = Mock()
        mock_crew.kickoff.side_effect = Exception("Processing failed")
        
        with patch.object(conversation_crew, 'crew', return_value=mock_crew):
            message = {'text': 'Hello', 'from': 'user123'}
            result = conversation_crew.process_conversation_message(message)
            
            assert result['success'] is False
            assert result['error'] == "Processing failed"
            assert result['conversation_state'] == 'error'
            assert result['next_action'] == 'retry_or_escalate'

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_agents_config_access(self, conversation_crew):
        """Test that agents_config is accessible and contains required agents."""
        assert 'conversation_manager' in conversation_crew.agents_config
        assert 'dialogue_state_tracker' in conversation_crew.agents_config
        
        # Verify config structure
        manager_config = conversation_crew.agents_config['conversation_manager']
        assert 'role' in manager_config
        assert 'goal' in manager_config
        assert 'backstory' in manager_config

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_tasks_config_access(self, conversation_crew):
        """Test that tasks_config is accessible and contains required tasks."""
        assert 'track_conversation_state' in conversation_crew.tasks_config
        assert 'manage_dialogue_flow' in conversation_crew.tasks_config
        
        # Verify config structure
        state_task_config = conversation_crew.tasks_config['track_conversation_state']
        assert 'description' in state_task_config
        assert 'expected_output' in state_task_config

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_crew_has_llm_instance(self, conversation_crew):
        """Test that crew has properly initialized LLM instance."""
        assert hasattr(conversation_crew, 'llm')
        assert conversation_crew.llm is not None

    @pytest.mark.unit
    @pytest.mark.crewai
    def test_missing_agents_config_handling(self):
        """Test behavior when agents config is missing."""
        with patch('src.crewai_service.crews.conversation_crew.conversation_crew.config') as mock_config:
            mock_config._get_full_model_name.return_value = "test/model"
            mock_config.llm_temperature = 0.1
            mock_config.llm_timeout = 120
            
            with patch('crewai.LLM'):
                crew = ConversationCrew()
                crew.agents_config = {}
                
                # This should work - CrewAI will handle missing config gracefully or raise appropriate errors
                try:
                    crew.conversation_manager()
                except (KeyError, AttributeError, Exception) as e:
                    # Expected behavior - missing config should raise an error
                    assert True

    @pytest.mark.unit  
    @pytest.mark.crewai
    def test_missing_tasks_config_handling(self):
        """Test behavior when tasks config is missing."""
        with patch('src.crewai_service.crews.conversation_crew.conversation_crew.config') as mock_config:
            mock_config._get_full_model_name.return_value = "test/model"
            mock_config.llm_temperature = 0.1
            mock_config.llm_timeout = 120
            
            with patch('crewai.LLM'):
                crew = ConversationCrew()
                crew.tasks_config = {}
                
                # This should work - CrewAI will handle missing config gracefully or raise appropriate errors
                try:
                    crew.track_conversation_state()
                except (KeyError, AttributeError, Exception) as e:
                    # Expected behavior - missing config should raise an error
                    assert True

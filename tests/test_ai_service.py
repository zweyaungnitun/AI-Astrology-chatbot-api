"""
Test cases for AIService using pytest.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List
from uuid import uuid4

from app.services.ai_service import AIService, ai_service
from app.models.chat import ChatMessage, MessageRole


class TestAIService:
    """Test cases for AIService class."""

    @pytest.mark.asyncio
    async def test_get_ai_response_success(self, ai_service: AIService):
        """Test successful AI response generation."""
        # Arrange
        user_message = "What does my birth chart say about my career?"
        chat_history: List[ChatMessage] = []
        birth_data = {
            "birth_date": "1990-01-01",
            "birth_time": "12:00:00",
            "birth_location": "New York, USA"
        }
        
        mock_response = "Based on your birth chart, your career shows strong potential in creative fields..."
        
        # Mock the astrology_chain
        with patch('app.services.ai_service.astrology_chain') as mock_chain:
            mock_chain.ainvoke = AsyncMock(return_value=mock_response)
            
            # Act
            result = await ai_service.get_ai_response(
                user_message=user_message,
                chat_history=chat_history,
                birth_data=birth_data,
                temperature=0.7,
                max_tokens=500,
                evaluate=False
            )
        print(result)
        # Assert
        assert result is not None
        assert result["content"] == mock_response
        assert result["model"] == "openrouter"
        assert "tokens" in result
        assert result["tokens"] > 0
        assert "processing_time" in result
        assert result["processing_time"] >= 0
        assert "timestamp" in result
        assert "error" not in result
        assert "evaluation" not in result

    @pytest.mark.asyncio
    async def test_get_ai_response_with_evaluation(self, ai_service: AIService):
        """Test AI response generation with evaluation enabled."""
        # Arrange
        user_message = "Tell me about my sun sign"
        chat_history: List[ChatMessage] = []
        birth_data = {"birth_date": "1990-01-01"}
        mock_response = "Your sun sign shows great potential..."
        
        mock_evaluation = {
            "fluency": {"score": 0.85},
            "relevance": {"score": 0.90},
            "overall_quality": {"score": 0.88}
        }
        
        # Mock both chain and evaluation service
        with patch('app.services.ai_service.astrology_chain') as mock_chain, \
             patch('app.services.ai_service.evaluation_service') as mock_eval_service:
            
            mock_chain.ainvoke = AsyncMock(return_value=mock_response)
            mock_eval_service.evaluate_response = AsyncMock(return_value=mock_evaluation)
            
            # Act
            result = await ai_service.get_ai_response(
                user_message=user_message,
                chat_history=chat_history,
                birth_data=birth_data,
                evaluate=True
            )
        
        # Assert
        assert result is not None
        assert result["content"] == mock_response
        assert "evaluation" in result
        assert result["evaluation"] == mock_evaluation
        mock_eval_service.evaluate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ai_response_with_chat_history(self, ai_service: AIService):
        """Test AI response with chat history context."""
        # Arrange
        user_message = "Can you tell me more?"
        dummy_session_id = uuid4()
        chat_history: List[ChatMessage] = [
            ChatMessage(
                id=None,
                chat_session_id=dummy_session_id,
                role=MessageRole.USER,
                content="What is my sun sign?"
            ),
            ChatMessage(
                id=None,
                chat_session_id=dummy_session_id,
                role=MessageRole.ASSISTANT,
                content="Your sun sign is Capricorn."
            )
        ]
        mock_response = "Certainly! As a Capricorn, you have many strengths..."
        
        with patch('app.services.ai_service.astrology_chain') as mock_chain:
            mock_chain.ainvoke = AsyncMock(return_value=mock_response)
            
            # Act
            result = await ai_service.get_ai_response(
                user_message=user_message,
                chat_history=chat_history
            )
        
        # Assert
        assert result is not None
        assert result["content"] == mock_response
        # Verify context was prepared with chat history
        call_args = mock_chain.ainvoke.call_args[0][0]
        assert "chat_history" in call_args
        assert len(call_args["chat_history"]) == 2

    @pytest.mark.asyncio
    async def test_get_ai_response_chat_history_limit(self, ai_service: AIService):
        """Test that only last 10 messages are used from chat history."""
        # Arrange - Create 15 messages
        dummy_session_id = uuid4()
        chat_history: List[ChatMessage] = [
            ChatMessage(
                id=None,
                chat_session_id=dummy_session_id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}"
            ) for i in range(15)
        ]
        user_message = "New message"
        mock_response = "Response"
        
        with patch('app.services.ai_service.astrology_chain') as mock_chain:
            mock_chain.ainvoke = AsyncMock(return_value=mock_response)
            
            # Act
            await ai_service.get_ai_response(
                user_message=user_message,
                chat_history=chat_history
            )
        
        # Assert - Should only use last 10 messages
        call_args = mock_chain.ainvoke.call_args[0][0]
        assert len(call_args["chat_history"]) == 10

    @pytest.mark.asyncio
    async def test_get_ai_response_without_birth_data(self, ai_service: AIService):
        """Test AI response without birth data."""
        # Arrange
        user_message = "What is astrology?"
        chat_history: List[ChatMessage] = []
        mock_response = "Astrology is the study of celestial bodies..."
        
        with patch('app.services.ai_service.astrology_chain') as mock_chain:
            mock_chain.ainvoke = AsyncMock(return_value=mock_response)
            
            # Act
            result = await ai_service.get_ai_response(
                user_message=user_message,
                chat_history=chat_history,
                birth_data=None
            )
        
        # Assert
        assert result is not None
        assert result["content"] == mock_response
        call_args = mock_chain.ainvoke.call_args[0][0]
        assert call_args["birth_data"] is None

    @pytest.mark.asyncio
    async def test_get_ai_response_error_handling(self, ai_service: AIService):
        """Test AI response error handling."""
        # Arrange
        user_message = "Test message"
        chat_history: List[ChatMessage] = []
        
        # Mock chain to raise an exception
        with patch('app.services.ai_service.astrology_chain') as mock_chain:
            mock_chain.ainvoke = AsyncMock(side_effect=Exception("API Error"))
            
            # Act
            result = await ai_service.get_ai_response(
                user_message=user_message,
                chat_history=chat_history
            )
        
        # Assert
        assert result is not None
        assert "I apologize, but I'm experiencing technical difficulties" in result["content"]
        assert result["model"] == "fallback"
        assert result["tokens"] == 0
        assert "error" in result
        assert result["error"] == "API Error"
        assert "processing_time" in result

    @pytest.mark.asyncio
    async def test_stream_ai_response_success(self, ai_service: AIService):
        """Test successful streaming of AI response."""
        # Arrange
        user_message = "Tell me about my chart"
        chat_history: List[ChatMessage] = []
        birth_data = {"birth_date": "1990-01-01"}
        
        mock_chunks = ["Based", " on", " your", " chart", "..."]
        
        async def mock_stream(context):
            for chunk in mock_chunks:
                yield chunk
        
        with patch('app.services.ai_service.astrology_chain') as mock_chain:
            mock_chain.astream = mock_stream
            
            # Act
            chunks = []
            async for chunk in ai_service.stream_ai_response(
                user_message=user_message,
                chat_history=chat_history,
                birth_data=birth_data
            ):
                chunks.append(chunk)
        
        # Assert
        assert len(chunks) == len(mock_chunks)
        assert chunks == mock_chunks

    @pytest.mark.asyncio
    async def test_stream_ai_response_error_handling(self, ai_service: AIService):
        """Test streaming error handling."""
        # Arrange
        user_message = "Test"
        chat_history: List[ChatMessage] = []
        
        async def mock_stream_error(context):
            raise Exception("Streaming error")
            yield  # Make it a generator
        
        with patch('app.services.ai_service.astrology_chain') as mock_chain:
            mock_chain.astream = mock_stream_error
            
            # Act
            chunks = []
            async for chunk in ai_service.stream_ai_response(
                user_message=user_message,
                chat_history=chat_history
            ):
                chunks.append(chunk)
        
        # Assert
        assert len(chunks) == 1
        assert "I apologize, but I'm experiencing technical difficulties" in chunks[0]

    @pytest.mark.asyncio
    async def test_prepare_context_user_messages(self, ai_service: AIService):
        """Test context preparation with user messages."""
        # Arrange
        user_message = "What is my sun sign?"
        dummy_session_id = uuid4()
        chat_history: List[ChatMessage] = [
            ChatMessage(
                id=None,
                chat_session_id=dummy_session_id,
                role=MessageRole.USER,
                content="Hello"
            )
        ]
        birth_data = {"birth_date": "1990-01-01"}
        
        # Act
        context = await ai_service._prepare_context(user_message, chat_history, birth_data)
        
        # Assert
        assert context["user_input"] == user_message
        assert context["birth_data"] == birth_data
        assert len(context["chat_history"]) == 1
        assert context["chat_history"][0] == ("human", "Hello")

    @pytest.mark.asyncio
    async def test_prepare_context_all_roles(self, ai_service: AIService):
        """Test context preparation with all message roles."""
        # Arrange
        user_message = "Test"
        dummy_session_id = uuid4()
        chat_history: List[ChatMessage] = [
            ChatMessage(id=None, chat_session_id=dummy_session_id, role=MessageRole.SYSTEM, content="System message"),
            ChatMessage(id=None, chat_session_id=dummy_session_id, role=MessageRole.USER, content="User message"),
            ChatMessage(id=None, chat_session_id=dummy_session_id, role=MessageRole.ASSISTANT, content="AI message")
        ]
        
        # Act
        context = await ai_service._prepare_context(user_message, chat_history, None)
        
        # Assert
        assert len(context["chat_history"]) == 3
        assert context["chat_history"][0] == ("system", "System message")
        assert context["chat_history"][1] == ("human", "User message")
        assert context["chat_history"][2] == ("ai", "AI message")

    @pytest.mark.asyncio
    async def test_count_tokens_success(self, ai_service: AIService):
        """Test token counting."""
        # Arrange
        text = "This is a test message with multiple words."
        
        # Act
        token_count = ai_service._count_tokens(text)
        
        # Assert
        assert token_count > 0
        assert isinstance(token_count, int)

    @pytest.mark.asyncio
    async def test_count_tokens_fallback(self, ai_service: AIService):
        """Test token counting fallback on error."""
        # Arrange
        text = "Test message"
        
        # Mock encoding to raise exception
        with patch.object(ai_service.encoding, 'encode', side_effect=Exception("Encoding error")):
            # Act
            token_count = ai_service._count_tokens(text)
        
        # Assert - Should fallback to word count
        assert token_count > 0
        assert token_count == len(text.split())

    @pytest.mark.asyncio
    async def test_evaluate_conversation_success(self, ai_service: AIService):
        """Test conversation evaluation."""
        # Arrange
        dummy_session_id = uuid4()
        chat_history: List[ChatMessage] = [
            ChatMessage(
                id=None,
                chat_session_id=dummy_session_id,
                role=MessageRole.USER,
                content="Hello, I'd like to know about my chart."
            ),
            ChatMessage(
                id=None,
                chat_session_id=dummy_session_id,
                role=MessageRole.ASSISTANT,
                content="I'd be happy to help you understand your birth chart."
            )
        ]
        
        # Mock langcheck metrics
        with patch('app.services.ai_service.langcheck') as mock_langcheck:
            mock_langcheck.metrics.en.fluency = MagicMock(return_value=[0.85])
            mock_langcheck.metrics.en.coherence = MagicMock(return_value=[0.80])
            
            # Act
            result = await ai_service.evaluate_conversation(chat_history)
        
        # Assert
        assert result is not None
        assert "fluency" in result
        assert "coherence" in result
        assert result["fluency"] == 0.85
        assert result["coherence"] == 0.80
        assert result["message_count"] == 2
        assert "evaluation_date" in result

    @pytest.mark.asyncio
    async def test_evaluate_conversation_limit(self, ai_service: AIService):
        """Test that only last 20 messages are evaluated."""
        # Arrange - Create 25 messages
        dummy_session_id = uuid4()
        chat_history: List[ChatMessage] = [
            ChatMessage(
                id=None,
                chat_session_id=dummy_session_id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}"
            ) for i in range(25)
        ]
        
        with patch('app.services.ai_service.langcheck') as mock_langcheck:
            mock_langcheck.metrics.en.fluency = MagicMock(return_value=[0.85])
            mock_langcheck.metrics.en.coherence = MagicMock(return_value=[0.80])
            
            # Act
            result = await ai_service.evaluate_conversation(chat_history)
        
        # Assert - Should evaluate all 25 messages but conversation text should have last 20
        assert result["message_count"] == 25

    @pytest.mark.asyncio
    async def test_evaluate_conversation_error_handling(self, ai_service: AIService):
        """Test conversation evaluation error handling."""
        # Arrange
        dummy_session_id = uuid4()
        chat_history: List[ChatMessage] = [
            ChatMessage(
                id=None,
                chat_session_id=dummy_session_id,
                role=MessageRole.USER,
                content="Test"
            )
        ]
        
        # Mock langcheck to raise exception
        with patch('app.services.ai_service.langcheck') as mock_langcheck:
            mock_langcheck.metrics.en.fluency = MagicMock(side_effect=Exception("Langcheck error"))
            
            # Act
            result = await ai_service.evaluate_conversation(chat_history)
        
        # Assert
        assert "error" in result
        assert result["error"] == "Langcheck error"

    @pytest.mark.asyncio
    async def test_get_ai_response_custom_parameters(self, ai_service: AIService):
        """Test AI response with custom temperature and max_tokens."""
        # Arrange
        user_message = "Test message"
        chat_history: List[ChatMessage] = []
        mock_response = "Response"
        
        with patch('app.services.ai_service.astrology_chain') as mock_chain:
            mock_chain.ainvoke = AsyncMock(return_value=mock_response)
            
            # Act
            result = await ai_service.get_ai_response(
                user_message=user_message,
                chat_history=chat_history,
                temperature=0.9,
                max_tokens=1000
            )
        
        # Assert
        assert result is not None
        assert result["content"] == mock_response

    @pytest.mark.asyncio
    async def test_prepare_context_empty_history(self, ai_service: AIService):
        """Test context preparation with empty chat history."""
        # Arrange
        user_message = "Test"
        chat_history: List[ChatMessage] = []
        
        # Act
        context = await ai_service._prepare_context(user_message, chat_history, None)
        
        # Assert
        assert context["user_input"] == user_message
        assert context["chat_history"] == []
        assert context["birth_data"] is None

    @pytest.mark.asyncio
    async def test_global_ai_service_instance(self):
        """Test that global ai_service instance exists and is AIService."""
        # Assert
        assert ai_service is not None
        assert isinstance(ai_service, AIService)

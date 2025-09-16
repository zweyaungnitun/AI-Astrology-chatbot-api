# app/services/ai_service.py
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging
import time
from datetime import datetime
import tiktoken

from app.core.langchain_config import astrology_chain
from app.services.evaluation_service import evaluation_service
from app.models.chat import ChatMessage, MessageRole

logger = logging.getLogger(__name__)

class AIService:
    """Service for handling AI interactions with LangChain and LangCheck."""
    
    def __init__(self):
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    async def get_ai_response(
        self,
        user_message: str,
        chat_history: List[ChatMessage],
        birth_data: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        evaluate: bool = False
    ) -> Dict[str, Any]:
        """Get AI response using LangChain with optional evaluation."""
        start_time = time.time()
        
        try:
            # Prepare context for LangChain
            context = await self._prepare_context(
                user_message, chat_history, birth_data
            )
            
            # Get response from LangChain
            response = await astrology_chain.ainvoke(context)
            
            # Calculate tokens
            token_count = self._count_tokens(response)
            
            processing_time = time.time() - start_time
            
            result = {
                "content": response,
                "model": "openrouter",  # Will be overridden by actual model
                "tokens": token_count,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
            # Evaluate response if requested
            if evaluate:
                evaluation = await evaluation_service.evaluate_response(
                    user_message, response, {"birth_data": birth_data}
                )
                result["evaluation"] = evaluation
            
            return result
            
        except Exception as e:
            logger.error(f"AI service error: {str(e)}")
            processing_time = time.time() - start_time
            
            return {
                "content": "I apologize, but I'm experiencing technical difficulties. Please try again shortly.",
                "model": "fallback",
                "tokens": 0,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def stream_ai_response(
        self,
        user_message: str,
        chat_history: List[ChatMessage],
        birth_data: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream AI response using LangChain."""
        try:
            context = await self._prepare_context(
                user_message, chat_history, birth_data
            )
            
            # Stream response
            async for chunk in astrology_chain.astream(context):
                yield chunk
                
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield "I apologize, but I'm experiencing technical difficulties."
    
    async def _prepare_context(
        self,
        user_message: str,
        chat_history: List[ChatMessage],
        birth_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare context for LangChain invocation."""
        # Format chat history for LangChain
        formatted_history = []
        for msg in chat_history[-10:]:  # Last 10 messages for context
            if msg.role == MessageRole.USER:
                formatted_history.append(("human", msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                formatted_history.append(("ai", msg.content))
            elif msg.role == MessageRole.SYSTEM:
                formatted_history.append(("system", msg.content))
        
        return {
            "user_input": user_message,
            "chat_history": formatted_history,
            "birth_data": birth_data
        }
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {str(e)}")
            return len(text.split())  # Fallback to word count
    
    async def evaluate_conversation(
        self,
        chat_history: List[ChatMessage],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate overall conversation quality."""
        try:
            # Convert to text for evaluation
            conversation_text = "\n".join([
                f"{msg.role.value}: {msg.content}" for msg in chat_history[-20:]  # Last 20 messages
            ])
            
            # Use LangCheck for conversation-level evaluation
            fluency_score = langcheck.metrics.en.fluency([conversation_text])
            coherence_score = langcheck.metrics.en.coherence([conversation_text])
            
            return {
                "fluency": float(fluency_score[0]),
                "coherence": float(coherence_score[0]),
                "message_count": len(chat_history),
                "evaluation_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Conversation evaluation failed: {str(e)}")
            return {"error": str(e)}

# Global AI service instance
ai_service = AIService()
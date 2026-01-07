# app/services/ai_service.py
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging
import time
from datetime import datetime
import tiktoken
import langcheck
import json

from app.core.langchain_config import astrology_chain, create_astrology_tools
from app.services.evaluation_service import evaluation_service
from app.models.chat import ChatMessage, MessageRole
from langchain_core.messages import ToolMessage, AIMessage

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
        """Get AI response using LangChain with tool calling support."""
        start_time = time.time()
        
        try:
            # Prepare context for LangChain
            context = await self._prepare_context(
                user_message, chat_history, birth_data
            )
            
            # Get tools for execution
            tools = create_astrology_tools()
            tool_map = {tool.name: tool for tool in tools}
            
            # Invoke chain - may return tool calls
            response = await astrology_chain.ainvoke(context)
            
            # Handle tool calling
            final_response = await self._handle_tool_calls(
                response, context, tool_map, chat_history, birth_data
            )
            
            # Calculate tokens
            token_count = self._count_tokens(final_response)
            
            processing_time = time.time() - start_time
            
            result = {
                "content": final_response,
                "model": "openrouter",
                "tokens": token_count,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
            # Evaluate response if requested
            if evaluate:
                evaluation = await evaluation_service.evaluate_response(
                    user_message, final_response, {"birth_data": birth_data}
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
    
    async def _handle_tool_calls(
        self,
        response: Any,
        context: Dict[str, Any],
        tool_map: Dict[str, Any],
        chat_history: List[ChatMessage],
        birth_data: Optional[Dict[str, Any]]
    ) -> str:
        """Handle tool calls from the LLM response."""
        from langchain_core.messages import HumanMessage
        from app.core.langchain_config import get_chat_model
        
        # Check if response has tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"Processing {len(response.tool_calls)} tool calls")
            
            # Execute tool calls
            tool_messages = []
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                
                if tool_name in tool_map:
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    try:
                        tool_result = await tool_map[tool_name].ainvoke(tool_args)
                        tool_messages.append(
                            ToolMessage(
                                content=str(tool_result),
                                tool_call_id=tool_call.get("id", "")
                            )
                        )
                    except Exception as e:
                        logger.error(f"Tool execution error: {str(e)}")
                        tool_messages.append(
                            ToolMessage(
                                content=f"Error executing tool: {str(e)}",
                                tool_call_id=tool_call.get("id", "")
                            )
                        )
            
            # Get final response with tool results
            # Prepare messages for final response
            messages = list(context.get("chat_history", []))
            messages.append(HumanMessage(content=context["user_input"]))
            messages.append(response)  # AI message with tool calls
            messages.extend(tool_messages)  # Tool results
            
            # Get final response
            model = get_chat_model()
            final_response = await model.ainvoke(messages)
            
            # Extract text from response
            if hasattr(final_response, 'content'):
                return final_response.content
            else:
                return str(final_response)
        else:
            # No tool calls, return direct response
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)
    
    async def stream_ai_response(
        self,
        user_message: str,
        chat_history: List[ChatMessage],
        birth_data: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream AI response using LangChain with tool calling support."""
        try:
            context = await self._prepare_context(
                user_message, chat_history, birth_data
            )
            
            # Get tools for execution
            tools = create_astrology_tools()
            tool_map = {tool.name: tool for tool in tools}
            
            # Stream initial response
            full_response = None
            async for chunk in astrology_chain.astream(context):
                if full_response is None:
                    full_response = chunk
                else:
                    # Accumulate chunks if needed
                    if hasattr(chunk, 'content'):
                        yield chunk.content
                    else:
                        yield str(chunk)
            
            # Check if we need to handle tool calls
            if full_response and hasattr(full_response, 'tool_calls') and full_response.tool_calls:
                # Execute tools and get final response
                final_response = await self._handle_tool_calls(
                    full_response, context, tool_map, chat_history, birth_data
                )
                yield final_response
            elif full_response:
                # No tool calls, stream the response
                if hasattr(full_response, 'content'):
                    yield full_response.content
                else:
                    yield str(full_response)
                
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
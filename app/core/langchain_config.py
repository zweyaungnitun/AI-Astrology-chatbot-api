import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableConfig
from langchain_core.output_parsers import StrOutputParser
from langchain_core.callbacks import AsyncCallbackHandler
from langchain.memory import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from typing import Optional, Dict, Any, List, AsyncGenerator
from app.core.config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def configure_langsmith():
    """Configure LangSmith for tracing and monitoring."""
    if os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = f"astrology-chatbot-{settings.ENVIRONMENT}"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        logger.info("✅ LangSmith tracing enabled")
    else:
        logger.info("ℹ️ LangSmith not configured - set LANGCHAIN_API_KEY to enable")

configure_langsmith()

class AstrologyCallbackHandler(AsyncCallbackHandler):
    """Custom callback handler for astrology chatbot."""
    
    async def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Run when LLM starts."""
        logger.info(f"LLM started with {len(prompts)} prompts")
    
    async def on_llm_end(self, response, **kwargs: Any) -> None:
        """Run when LLM ends."""
        logger.info(f"LLM completed: {response.generations[0][0].text[:100]}...")

def get_chat_model(temperature: float = 0.7, max_tokens: int = 500) -> ChatOpenAI:
    """Get configured LangChain chat model."""
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=settings.OPENROUTER_API_BASE,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=True,
        callbacks=[AstrologyCallbackHandler()],
        extra_headers={
            "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER,
            "X-Title": settings.OPENROUTER_APP_TITLE,
        }
    )

def create_astrology_chain() -> RunnablePassthrough:
    """Create LangChain chain for astrology conversations."""
    # System prompt template
    system_template = """
    You are Stella, an expert astrologer with deep knowledge of Western astrology. 
    You are wise, empathetic, and insightful, but you always encourage users to 
    make their own choices. You speak in a warm, engaging, and professional tone.

    {% if birth_data %}
    ## User's Birth Chart Data
    - Birth Date: {{ birth_data.birth_date }}
    - Birth Time: {{ birth_data.birth_time }}
    - Birth Location: {{ birth_data.birth_location }}
    
    Use this birth data as the absolute basis for your astrological interpretations.
    Be specific about planetary positions, houses, and aspects.
    {% else %}
    ## Important: No Birth Data Available
    If the user asks astrological questions without providing birth data,
    gently explain that you need their birth information for accurate readings.
    Offer to help them understand how to provide this information.
    {% endif %}

    ## Guidelines:
    1. Be accurate and don't make up planetary positions
    2. Focus on practical, empowering insights
    3. Avoid fatalistic or deterministic language
    4. Encourage self-reflection and personal agency
    5. Be culturally sensitive and inclusive

    Current Date: {{ current_date }}
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{user_input}"),
    ])
    
    # Create the chain
    chain = (
        RunnablePassthrough.assign(
            current_date=lambda x: datetime.now().strftime("%Y-%m-%d"),
            birth_data=lambda x: x.get("birth_data"),
            chat_history=lambda x: x.get("chat_history", [])
        )
        | prompt
        | get_chat_model()
        | StrOutputParser()
    )
    
    return chain

# Global chain instance
astrology_chain = create_astrology_chain()
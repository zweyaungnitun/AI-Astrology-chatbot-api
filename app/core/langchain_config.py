import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableConfig
from langchain_core.output_parsers import StrOutputParser
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.tools import StructuredTool
from langchain_core.runnables import RunnableLambda
from typing import Optional, Dict, Any, List, AsyncGenerator
from app.core.config import settings
from app.services.astrology_service import AstrologyService
from app.schemas.chart import ChartCalculationRequest, HouseSystem, ZodiacSystem
from datetime import date, time
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

def create_astrology_tools() -> List[StructuredTool]:
    """Create LangChain tools for astrology calculations."""
    astrology_service = AstrologyService()
    
    async def calculate_chart_tool(
        birth_date: str,
        birth_time: str,
        birth_location: str,
        birth_latitude: Optional[float] = None,
        birth_longitude: Optional[float] = None,
        birth_timezone: Optional[str] = None,
        house_system: Optional[str] = None,
        zodiac_system: Optional[str] = None,
        ayanamsa: Optional[float] = None
    ) -> str:
        """Calculate a birth chart with planetary positions, houses, and aspects.
        
        Args:
            birth_date: Birth date in YYYY-MM-DD format
            birth_time: Birth time in HH:MM:SS format (24-hour)
            birth_location: Birth location (city name or coordinates)
            birth_latitude: Optional latitude (decimal degrees)
            birth_longitude: Optional longitude (decimal degrees)
            birth_timezone: Timezone (default: UTC)
            house_system: House system (placidus, koch, porphyry, equal, whole_sign)
            zodiac_system: Zodiac system (tropical, sidereal)
            ayanamsa: Optional ayanamsa value for sidereal calculations
        
        Returns:
            JSON string with chart data including planetary positions, houses, aspects, and summary
        """
        try:
            # Parse date and time
            birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date()
            time_parts = birth_time.split(":")
            birth_time_obj = time(
                int(time_parts[0]),
                int(time_parts[1]) if len(time_parts) > 1 else 0,
                int(time_parts[2]) if len(time_parts) > 2 else 0
            )
            
            # Map house system
            house_system_map = {
                "placidus": HouseSystem.PLACIDUS,
                "koch": HouseSystem.KOCH,
                "porphyry": HouseSystem.PORPHYRY,
                "equal": HouseSystem.EQUAL,
                "whole_sign": HouseSystem.WHOLE_SIGN
            }
            
            # Map zodiac system
            zodiac_system_map = {
                "tropical": ZodiacSystem.TROPICAL,
                "sidereal": ZodiacSystem.SIDEREAL
            }
            
            request = ChartCalculationRequest(
                birth_date=birth_date_obj,
                birth_time=birth_time_obj,
                birth_location=birth_location,
                birth_latitude=birth_latitude,
                birth_longitude=birth_longitude,
                birth_timezone=birth_timezone or "UTC",
                house_system=house_system_map.get(house_system or "placidus", HouseSystem.PLACIDUS),
                zodiac_system=zodiac_system_map.get(zodiac_system or "tropical", ZodiacSystem.TROPICAL),
                ayanamsa=ayanamsa
            )
            
            result = await astrology_service.calculate_chart(request)
            
            # Format result as readable string
            import json
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Error in calculate_chart_tool: {str(e)}")
            return f"Error calculating chart: {str(e)}"
    
    async def parse_location_tool(location_str: str) -> str:
        """Parse a location string and return coordinates.
        
        Args:
            location_str: Location name (e.g., "New York") or coordinates (e.g., "40.7128,-74.0060")
        
        Returns:
            JSON string with latitude, longitude, and place name
        """
        try:
            lat, lon, place_name = astrology_service.parse_location(location_str)
            import json
            return json.dumps({
                "latitude": lat,
                "longitude": lon,
                "place_name": place_name
            })
        except Exception as e:
            logger.error(f"Error in parse_location_tool: {str(e)}")
            return f"Error parsing location: {str(e)}"
    
    tools = [
        StructuredTool.from_function(
            func=calculate_chart_tool,
            name="calculate_birth_chart",
            description="""Calculate a complete birth chart including:
            - Planetary positions (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Rahu, Ketu)
            - House positions (12 houses)
            - Planetary aspects (conjunctions, oppositions, trines, squares, sextiles)
            - Chart summary
            
            Use this tool when the user provides birth information (date, time, location) and wants a chart calculation.
            Always use this tool before providing astrological interpretations based on birth data."""
        ),
        StructuredTool.from_function(
            func=parse_location_tool,
            name="parse_location",
            description="""Parse a location string to get latitude and longitude coordinates.
            Accepts city names (e.g., 'New York', 'London') or coordinate strings (e.g., '40.7128,-74.0060').
            Use this when you need to convert a location name to coordinates for chart calculations."""
        )
    ]
    
    return tools

def create_astrology_chain() -> RunnablePassthrough:
    """Create LangChain chain for astrology conversations with tool calling."""
    # Get astrology tools
    tools = create_astrology_tools()
    
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
    
    You have access to birth chart calculation tools. When users ask about their chart,
    use the calculate_birth_chart tool to get accurate planetary positions, houses, and aspects.
    {% else %}
    ## Important: No Birth Data Available
    If the user asks astrological questions without providing birth data,
    gently explain that you need their birth information for accurate readings.
    Offer to help them understand how to provide this information.
    {% endif %}

    ## Guidelines:
    1. Always use the calculate_birth_chart tool when birth data is available and the user asks about their chart
    2. Be accurate and don't make up planetary positions - use the tools to get real data
    3. Focus on practical, empowering insights based on actual chart calculations
    4. Avoid fatalistic or deterministic language
    5. Encourage self-reflection and personal agency
    6. Be culturally sensitive and inclusive
    7. When interpreting charts, reference specific planetary positions, houses, and aspects from the tool results

    Current Date: {{ current_date }}
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{user_input}"),
    ])
    
    # Create model with tools
    model_with_tools = get_chat_model().bind_tools(tools)
    
    # Create the chain with tool calling
    chain = (
        RunnablePassthrough.assign(
            current_date=lambda x: datetime.now().strftime("%Y-%m-%d"),
            birth_data=lambda x: x.get("birth_data"),
            chat_history=lambda x: x.get("chat_history", [])
        )
        | prompt
        | model_with_tools
    )
    
    return chain

# Global chain instance
astrology_chain = create_astrology_chain()
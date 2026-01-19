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
    
    async def calculate_vimshottari_dasha_tool(
        birth_date: str,
        birth_time: str,
        moon_longitude: Optional[float] = None,
        current_date: Optional[str] = None
    ) -> str:
        """Calculate Vimshottari Dasha periods and provide interpretations.
        
        Vimshottari Dasha is a 120-year cycle system in Vedic astrology that divides life into periods
        ruled by different planets. The dasha starts from the Moon's nakshatra at birth.
        
        Args:
            birth_date: Birth date in YYYY-MM-DD format
            birth_time: Birth time in HH:MM:SS format (24-hour)
            moon_longitude: Optional Moon's sidereal longitude in degrees (if not provided, will be calculated from chart)
            current_date: Optional current date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            JSON string with dasha periods, current dasha/antardasha, and interpretations
        """
        try:
            from datetime import datetime
            
            # Parse birth date and time
            birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date()
            time_parts = birth_time.split(":")
            birth_time_obj = time(
                int(time_parts[0]),
                int(time_parts[1]) if len(time_parts) > 1 else 0,
                int(time_parts[2]) if len(time_parts) > 2 else 0
            )
            birth_datetime = datetime.combine(birth_date_obj, birth_time_obj)
            
            # Parse current date if provided
            current_datetime = None
            if current_date:
                current_datetime = datetime.strptime(current_date, "%Y-%m-%d")
            
            # If moon_longitude not provided, calculate it from chart
            chart_data_for_dasha = None
            if moon_longitude is None:
                # Calculate chart to get Moon position
                chart_request = ChartCalculationRequest(
                    birth_date=birth_date_obj,
                    birth_time=birth_time_obj,
                    birth_location="Unknown",  # Will use default
                    zodiac_system=ZodiacSystem.SIDEREAL  # Use sidereal for dasha
                )
                chart_result = await astrology_service.calculate_chart(chart_request)
                chart_data_for_dasha = chart_result
                
                # Find Moon's longitude
                moon_position = next(
                    (p for p in chart_result.get("planetary_positions", []) if p["planet"] == "Moon"),
                    None
                )
                if moon_position:
                    moon_longitude = moon_position["longitude"]
                else:
                    import json
                    return json.dumps({"error": "Could not calculate Moon position"})
            
            # Calculate dasha with interpretation (synchronous method)
            dasha_result = astrology_service.calculate_vimshottari_dasha_with_interpretation(
                birth_datetime,
                moon_longitude,
                chart_data_for_dasha,
                current_datetime
            )
            
            import json
            return json.dumps(dasha_result, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error in calculate_vimshottari_dasha_tool: {str(e)}")
            import json
            return json.dumps({"error": f"Error calculating dasha: {str(e)}"})
    
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
        ),
        StructuredTool.from_function(
            func=calculate_vimshottari_dasha_tool,
            name="calculate_vimshottari_dasha",
            description="""Calculate Vimshottari Dasha periods and provide interpretations.
            
            Vimshottari Dasha is a major timing system in Vedic astrology that divides a person's life into
            periods ruled by different planets. It's a 120-year cycle starting from the Moon's nakshatra at birth.
            
            Use this tool when:
            - User asks about their dasha periods
            - User wants to know their current dasha or antardasha
            - User asks about timing of events or planetary periods
            - User wants dasha interpretations or readings
            
            The tool calculates:
            - All dasha periods (Mahadasha) in the 120-year cycle
            - Current Mahadasha and Antardasha (sub-period)
            - Interpretations for the current periods
            - Personalized insights based on chart positions
            
            Always use this tool when birth data is available and user asks about dashas, timing, or planetary periods."""
        )
    ]
    
    return tools

def create_astrology_chain() -> RunnablePassthrough:
    """Create LangChain chain for astrology conversations with tool calling."""
    # Get astrology tools
    tools = create_astrology_tools()
    
    # System prompt template
    system_template = """
    You are Stella, an expert astrologer with deep knowledge of both Western and Vedic astrology. 
    You are wise, empathetic, and insightful, but you always encourage users to 
    make their own choices. You speak in a warm, engaging, and professional tone.
    
    You have expertise in:
    - Western astrology (tropical zodiac, planetary aspects, houses)
    - Vedic astrology (sidereal zodiac, nakshatras, dashas, timing systems)
    - Vimshottari Dasha system (120-year planetary periods for timing events)

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

    ## Conversation Context:
    You have access to the full conversation history with this user. Use it to:
    - Remember what the user has asked about previously
    - Reference past discussions and insights
    - Build on previous conversations naturally
    - Maintain continuity across the conversation
    - Avoid repeating information you've already shared
    - Reference specific past messages when relevant

    ## Guidelines:
    1. Always use the calculate_birth_chart tool when birth data is available and the user asks about their chart
    2. Use the calculate_vimshottari_dasha tool when users ask about:
       - Their dasha periods (Mahadasha, Antardasha)
       - Timing of events or planetary periods
       - Current dasha or what dasha they're in
       - Dasha interpretations or readings
    3. Be accurate and don't make up planetary positions or dasha periods - use the tools to get real data
    4. Focus on practical, empowering insights based on actual chart calculations and dasha periods
    5. Avoid fatalistic or deterministic language
    6. Encourage self-reflection and personal agency
    7. Be culturally sensitive and inclusive
    8. When interpreting charts or dashas, reference specific planetary positions, houses, aspects, and dasha periods from the tool results
    9. Reference past conversations when relevant - show you remember what was discussed
    10. Build on previous insights rather than starting from scratch each time
    11. When discussing dashas, explain both the Mahadasha (major period) and Antardasha (sub-period) for comprehensive timing insights

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
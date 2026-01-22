import os
import asyncio
from typing import Optional, Dict, Any, List, Type
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableConfig
from langchain_core.output_parsers import StrOutputParser
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.tools import StructuredTool
from langchain_core.runnables import RunnableLambda
from datetime import date, datetime
import logging
import json

from app.core.config import settings
from app.services.astrology_service import AstrologyService
from app.schemas.chart import ChartCalculationRequest, HouseSystem, ZodiacSystem

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
        if response.generations:
            text = response.generations[0][0].text
            logger.info(f"LLM completed: {text[:100]}...")

def get_chat_model(temperature: float = 0.7, max_tokens: int = 8000) -> ChatOpenAI:
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

class ChartArgs(BaseModel):
    birth_date: str = Field(description="Birth date in YYYY-MM-DD format")
    birth_time: str = Field(description="Birth time in HH:MM:SS format (24-hour)")
    birth_location: str = Field(description="Birth location (city name)")
    birth_timezone: Optional[str] = Field(default="UTC", description="Timezone (e.g., UTC)")

class LocationArgs(BaseModel):
    location_str: str = Field(description="City name or coordinates to parse")

class DashaArgs(BaseModel):
    birth_date: str = Field(description="Birth date in YYYY-MM-DD format")
    birth_time: str = Field(description="Birth time in HH:MM:SS format (24-hour)")
    current_date: Optional[str] = Field(default=None, description="Target date for prediction (YYYY-MM-DD)")

def create_astrology_tools() -> List[StructuredTool]:
    """Create LangChain tools for astrology calculations."""
    astrology_service = AstrologyService()
    
    
    async def calculate_chart_impl(
        birth_date: str, 
        birth_time: str, 
        birth_location: str, 
        birth_timezone: str = "UTC",
        **kwargs
    ) -> str:
        """Async implementation of calculate_chart."""
        try:
            # Parse date
            b_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
            # Parse time (handle seconds or no seconds)
            try:
                b_time = datetime.strptime(birth_time, "%H:%M:%S").time()
            except ValueError:
                b_time = datetime.strptime(birth_time, "%H:%M").time()

            request = ChartCalculationRequest(
                birth_date=b_date,
                birth_time=b_time,
                birth_location=birth_location,
                birth_timezone=birth_timezone,
                house_system=HouseSystem.PLACIDUS,
                zodiac_system=ZodiacSystem.TROPICAL
            )
            
            result = await astrology_service.calculate_chart(request)
            return json.dumps(result, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error in calculate_chart_tool: {str(e)}")
            return f"Error calculating chart: {str(e)}"

    async def parse_location_impl(location_str: str, **kwargs) -> str:
        """Async implementation of parse_location."""
        try:
            lat, lon, place_name = astrology_service.parse_location(location_str)
            return json.dumps({
                "latitude": lat,
                "longitude": lon,
                "place_name": place_name
            })
        except Exception as e:
            logger.error(f"Error in parse_location_tool: {str(e)}")
            return f"Error parsing location: {str(e)}"

    async def calculate_dasha_impl(
        birth_date: str, 
        birth_time: str, 
        current_date: Optional[str] = None,
        **kwargs
    ) -> str:
        """Async implementation of calculate_vimshottari_dasha."""
        try:
            b_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
            try:
                b_time = datetime.strptime(birth_time, "%H:%M:%S").time()
            except ValueError:
                b_time = datetime.strptime(birth_time, "%H:%M").time()
            
            birth_datetime = datetime.combine(b_date, b_time)
            
            current_datetime = None
            if current_date:
                current_datetime = datetime.strptime(current_date, "%Y-%m-%d")
            chart_req = ChartCalculationRequest(
                birth_date=b_date,
                birth_time=b_time,
                birth_location="Unknown",
                zodiac_system=ZodiacSystem.SIDEREAL 
            )
            chart_result = await astrology_service.calculate_chart(chart_req)
            
            moon_position = next(
                (p for p in chart_result.get("planetary_positions", []) if p["planet"] == "Moon"),
                None
            )
            
            if not moon_position:
                return json.dumps({"error": "Could not calculate Moon position"})
            
            moon_longitude = moon_position["longitude"]
            
            dasha_result = astrology_service.calculate_vimshottari_dasha_with_interpretation(
                birth_datetime,
                moon_longitude,
                chart_result,
                current_datetime
            )
            
            return json.dumps(dasha_result, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error in calculate_vimshottari_dasha_tool: {str(e)}")
            return json.dumps({"error": f"Error calculating dasha: {str(e)}"})
    def sync_placeholder(*args, **kwargs):
        """Placeholder for sync execution which shouldn't happen in this async app."""
        raise NotImplementedError("This tool is async-only. Use ainvoke().")
    return [
        StructuredTool.from_function(
            func=sync_placeholder,
            coroutine=calculate_chart_impl,
            name="calculate_birth_chart",
            description="Calculate a complete birth chart including planetary positions and houses.",
            args_schema=ChartArgs
        ),
        StructuredTool.from_function(
            func=sync_placeholder,
            coroutine=parse_location_impl,
            name="parse_location",
            description="Parse a location string to get latitude and longitude coordinates.",
            args_schema=LocationArgs
        ),
        StructuredTool.from_function(
            func=sync_placeholder,
            coroutine=calculate_dasha_impl,
            name="calculate_vimshottari_dasha",
            description="Calculate Vedic Vimshottari Dasha periods for timing and prediction.",
            args_schema=DashaArgs
        )
    ]

def create_astrology_chain() -> RunnablePassthrough:
    """Create LangChain chain for astrology conversations with tool calling."""

    tools = create_astrology_tools()
   
    base_system_template = """
    You are Stella, an expert astrologer with deep knowledge of both Western and Vedic astrology. 
    You are wise, empathetic, and insightful, but you always encourage users to 
    make their own choices. You speak in a warm, engaging, and professional tone.
    
    You have expertise in:
    - Western astrology (tropical zodiac, planetary aspects, houses)
    - Vedic astrology (sidereal zodiac, nakshatras, dashas, timing systems)
    - Vimshottari Dasha system (120-year planetary periods for timing events)

    {birth_data_section}

    ## Conversation Context:
    You have access to the full conversation history. Use it to maintain continuity.

    ## Guidelines:
    1. **PRIORITY: If chart_data is available in context, ALWAYS use it instead of recalculating.**
    2. Use the 'calculate_vimshottari_dasha' tool when users ask about timing, future predictions, or dasha periods.
    3. Be accurate and don't make up planetary positions - use the provided chart_data or tools.
    4. Focus on practical, empowering insights.
    5. When discussing dashas, explain both the Mahadasha (major) and Antardasha (sub) periods.

    Current Date: {current_date}
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", base_system_template),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{user_input}"),
    ])
    
    # Bind tools with auto choice to help the model decide
    model_with_tools = get_chat_model().bind_tools(tools, tool_choice="auto")
    
    # Helper to format birth data
    def format_birth_data_section(context: Dict[str, Any]) -> str:
        """Format birth data section based on available data."""
        birth_data = context.get("birth_data")
        chart_data = context.get("chart_data")
        
        sections = []
        
        if birth_data and isinstance(birth_data, dict):
            sections.append(f"""## User's Birth Data
            - Birth Date: {birth_data.get('birth_date', 'Not provided')}
            - Birth Time: {birth_data.get('birth_time', 'Not provided')}
            - Birth Location: {birth_data.get('birth_location', 'Not provided')}""")
        
        if chart_data and isinstance(chart_data, dict):
            chart_name = chart_data.get('chart_name', 'Chart')
            chart_type = chart_data.get('chart_type', 'birth_chart')
            summary = chart_data.get('summary', '')
            planetary_positions = chart_data.get('planetary_positions', {})
            house_positions = chart_data.get('house_positions', {})
            aspects = chart_data.get('aspects', [])
            
            chart_section = f"""## User's Uploaded Chart: {chart_name} ({chart_type})
            This chart has been uploaded to this chat session and contains COMPLETE astrological data for reference.

            ### Chart Configuration:
            - Birth Date: {chart_data.get('birth_date', 'Not provided')}
            - Birth Time: {chart_data.get('birth_time', 'Not provided')}
            - Birth Location: {chart_data.get('birth_location', 'Not provided')}
            - Birth Timezone: {chart_data.get('birth_timezone', 'Not provided')}
            - House System: {chart_data.get('house_system', 'Not provided')}
            - Zodiac System: {chart_data.get('zodiac_system', 'Not provided')}
            - Ayanamsa: {chart_data.get('ayanamsa', 'Not provided')}
            - Is Primary Chart: {chart_data.get('is_primary', False)}"""
            
            if summary:
                chart_section += f"\n\n### Chart Summary:\n{summary}"
 
            if planetary_positions:
                chart_section += "\n\n### PLANETARY POSITIONS (Complete Chart Data):"
                
                if isinstance(planetary_positions, list):
                    for planet in planetary_positions:
                        planet_name = planet.get('planet', 'Unknown')
                        sign = planet.get('sign', 'Unknown')
                        degree = planet.get('degree', 0)
                        house = planet.get('house', 0)
                        retrograde = planet.get('retrograde', False)
                        retro_str = " (R)" if retrograde else ""
                        chart_section += f"\n- {planet_name}: {sign} {degree:.2f}° (House {house}){retro_str}"
                elif isinstance(planetary_positions, dict):
                  
                    for planet_name, planet_data in planetary_positions.items():
                        if isinstance(planet_data, dict):
                            sign = planet_data.get('sign', 'Unknown')
                            degree = planet_data.get('degree', 0)
                            house = planet_data.get('house', 0)
                            retrograde = planet_data.get('retrograde', False)
                            retro_str = " (R)" if retrograde else ""
                            chart_section += f"\n- {planet_name}: {sign} {degree:.2f}° (House {house}){retro_str}"
                        else:
                            chart_section += f"\n- {planet_name}: {planet_data}"

            if house_positions:
                chart_section += "\n\n### HOUSE POSITIONS (Complete Chart Data):"
                if isinstance(house_positions, list):
                    for house in house_positions:
                        house_num = house.get('house', 0)
                        sign = house.get('sign', 'Unknown')
                        degree = house.get('degree', 0)
                        chart_section += f"\n- House {house_num}: {sign} {degree:.2f}°"
                elif isinstance(house_positions, dict):
                    for house_num, house_data in sorted(house_positions.items()):
                        if isinstance(house_data, dict):
                            sign = house_data.get('sign', 'Unknown')
                            degree = house_data.get('degree', 0)
                            chart_section += f"\n- House {house_num}: {sign} {degree:.2f}°"
                        else:
                            chart_section += f"\n- House {house_num}: {house_data}"
            
            if aspects:
                aspect_count = len(aspects) if isinstance(aspects, list) else 0
                chart_section += f"\n\n### PLANETARY ASPECTS (Complete Chart Data - {aspect_count} aspects):"
                max_major_aspects = 20
                if isinstance(aspects, list):
                    for aspect in aspects[:max_major_aspects]:
                        planet1 = aspect.get('planet1', aspect.get('from', 'Unknown'))
                        planet2 = aspect.get('planet2', aspect.get('to', 'Unknown'))
                        aspect_type = aspect.get('aspect_type', aspect.get('aspect', aspect.get('type', 'conjunction')))
                        orb = aspect.get('orb', aspect.get('orb_degrees', 0))
                        chart_section += f"\n- {planet1} {aspect_type} {planet2} (orb: {orb:.2f}°)"
                    if aspect_count > max_major_aspects:
                        chart_section += f"\n- ... and {aspect_count - max_major_aspects} more aspects (see chart_data for complete list)"
            
            sections.append(chart_section)
        
        if sections:
            return "\n\n".join(sections) + "\n\nYou have access to birth chart calculation tools if needed, but prefer using the uploaded chart data when available."
        else:
            return """## Important: No Birth Data or Chart Available
If the user asks astrological questions without providing birth data or uploading a chart,
gently explain that you need their birth information for accurate readings.
Offer to help them understand how to provide this information or upload a chart."""

    chain = (
        RunnablePassthrough.assign(
            current_date=lambda x: datetime.now().strftime("%Y-%m-%d"),
            birth_data_section=lambda x: format_birth_data_section(x),
            chat_history=lambda x: x.get("chat_history", []),
            chart_data=lambda x: x.get("chart_data")
        )
        | prompt
        | model_with_tools
    )
    
    return chain

astrology_chain = create_astrology_chain()
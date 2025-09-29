# app/services/evaluation_service.py
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class AstrologyEvaluationService:
    """Simplified evaluation service for astrology chatbot without langcheck dependencies."""
    
    async def evaluate_response(
        self,
        user_input: str,
        ai_response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate AI response using simple heuristics."""
        try:
            evaluation_results = {}
            
            # Evaluate fluency (simple word-based heuristic)
            fluency_score = self._evaluate_fluency(ai_response)
            evaluation_results["fluency"] = {
                "score": fluency_score,
                "interpretation": self._interpret_fluency(fluency_score)
            }
            
            # Evaluate relevance (keyword matching)
            relevance_score = self._evaluate_relevance(user_input, ai_response)
            evaluation_results["relevance"] = {
                "score": relevance_score,
                "interpretation": self._interpret_relevance(relevance_score)
            }
            
            # Evaluate sentiment (positive/negative words)
            sentiment_score = self._evaluate_sentiment(ai_response)
            evaluation_results["sentiment"] = {
                "score": sentiment_score,
                "interpretation": self._interpret_sentiment(sentiment_score)
            }
            
            # Evaluate astrology-specific factors
            astrology_score = self._evaluate_astrology_quality(ai_response, context)
            evaluation_results["astrology_quality"] = {
                "score": astrology_score,
                "interpretation": self._interpret_astrology_quality(astrology_score)
            }
            
            # Overall quality (average of scores)
            overall_score = (fluency_score + relevance_score + sentiment_score + astrology_score) / 4
            evaluation_results["overall_quality"] = {
                "score": overall_score,
                "interpretation": self._interpret_overall_quality(overall_score),
                "timestamp": datetime.now().isoformat()
            }
            
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Evaluation error: {str(e)}")
            return {"error": str(e)}
    
    def _evaluate_fluency(self, text: str) -> float:
        """Evaluate text fluency using simple heuristics."""
        # Basic fluency checks
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) < 2:
            return 0.6  # Short response
        
        # Check sentence length variation
        sentence_lengths = [len(sentence.split()) for sentence in sentences if sentence.strip()]
        if not sentence_lengths:
            return 0.5
            
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        length_variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
        
        # Good fluency: moderate sentence length variation
        if 5 <= avg_length <= 20 and length_variance < 50:
            return 0.8 + min(length_variance / 100, 0.2)
        else:
            return 0.6
    
    def _evaluate_relevance(self, user_input: str, ai_response: str) -> float:
        """Evaluate relevance to user input."""
        user_words = set(user_input.lower().split())
        ai_words = set(ai_response.lower().split())
        
        if not user_words:
            return 0.5
            
        # Calculate word overlap
        overlap = user_words.intersection(ai_words)
        relevance = len(overlap) / len(user_words)
        
        return min(relevance * 1.5, 1.0)  # Scale to 0-1 range
    
    def _evaluate_sentiment(self, text: str) -> float:
        """Evaluate sentiment of response."""
        positive_words = {
            'good', 'great', 'excellent', 'wonderful', 'positive', 'happy', 
            'joy', 'love', 'beautiful', 'amazing', 'fantastic', 'awesome',
            'encouraging', 'supportive', 'helpful', 'beneficial', 'positive'
        }
        
        negative_words = {
            'bad', 'terrible', 'awful', 'negative', 'sad', 'unhappy',
            'hate', 'ugly', 'horrible', 'disappointing', 'problem', 'issue',
            'warning', 'danger', 'avoid', 'negative'
        }
        
        words = text.lower().split()
        pos_count = sum(1 for word in words if word in positive_words)
        neg_count = sum(1 for word in words if word in negative_words)
        
        total_emotional = pos_count + neg_count
        if total_emotional == 0:
            return 0.5  # Neutral
            
        sentiment = (pos_count - neg_count) / total_emotional
        return (sentiment + 1) / 2  # Convert from -1-1 to 0-1 range
    
    def _evaluate_astrology_quality(self, response: str, context: Optional[Dict[str, Any]]) -> float:
        """Evaluate astrology-specific quality factors."""
        score = 0.7  # Base score
        
        # Positive indicators for astrology responses
        astrology_indicators = {
            'planet', 'zodiac', 'sign', 'house', 'aspect', 'transit',
            'birth chart', 'natal chart', 'horoscope', 'astrology',
            'cosmic', 'celestial', 'alignment', 'energy'
        }
        
        # Check for astrology terminology
        response_lower = response.lower()
        astrology_terms = sum(1 for term in astrology_indicators if term in response_lower)
        score += min(astrology_terms * 0.05, 0.2)  # Max 0.2 bonus
        
        # Check for empowering language (important for astrology)
        empowering_phrases = {
            'you can', 'you might', 'consider', 'suggest', 'recommend',
            'opportunity', 'possibility', 'potential', 'explore'
        }
        
        empowering_count = sum(1 for phrase in empowering_phrases if phrase in response_lower)
        score += min(empowering_count * 0.03, 0.15)  # Max 0.15 bonus
        
        # Penalize deterministic language
        deterministic_phrases = {
            'will happen', 'must', 'certainly', 'definitely', 'inevitable',
            'fated', 'destined', 'cannot change'
        }
        
        deterministic_count = sum(1 for phrase in deterministic_phrases if phrase in response_lower)
        score -= min(deterministic_count * 0.1, 0.2)  # Max 0.2 penalty
        
        return max(0.0, min(1.0, score))
    
    def _interpret_fluency(self, score: float) -> str:
        if score >= 0.8: return "Excellent fluency, very natural language"
        if score >= 0.6: return "Good fluency, clear communication"
        if score >= 0.4: return "Average fluency, some awkward phrasing"
        return "Poor fluency, difficult to understand"
    
    def _interpret_relevance(self, score: float) -> str:
        if score >= 0.8: return "Highly relevant, comprehensive response"
        if score >= 0.6: return "Relevant, addresses main points"
        if score >= 0.4: return "Somewhat relevant, but off-topic"
        return "Irrelevant to user query"
    
    def _interpret_sentiment(self, score: float) -> str:
        if score >= 0.7: return "Very positive, highly supportive"
        if score >= 0.6: return "Positive tone, encouraging"
        if score >= 0.4: return "Neutral tone, factual"
        return "Negative tone, potentially discouraging"
    
    def _interpret_astrology_quality(self, score: float) -> str:
        if score >= 0.8: return "Excellent astrology content, empowering and accurate"
        if score >= 0.6: return "Good astrology content, mostly accurate"
        if score >= 0.4: return "Average astrology content, some issues"
        return "Poor astrology content, inaccurate or disempowering"
    
    def _interpret_overall_quality(self, score: float) -> str:
        if score >= 0.8: return "Excellent quality response"
        if score >= 0.6: return "Good quality response"
        if score >= 0.4: return "Average quality, needs improvement"
        return "Poor quality response"
    
    async def monitor_conversation_quality(
        self,
        conversation_history: List[Dict[str, Any]],
        threshold: float = 0.6
    ) -> Dict[str, Any]:
        """Monitor overall conversation quality."""
        try:
            if not conversation_history:
                return {"status": "no_messages", "score": None}
            
            # Get recent AI responses
            ai_responses = [
                msg["content"] for msg in conversation_history 
                if msg.get("role") == "assistant"
            ][-5:]  # Last 5 AI responses
            
            if not ai_responses:
                return {"status": "no_ai_responses", "score": None}
            
            # Calculate average quality
            quality_scores = []
            for response in ai_responses:
                # Simple quality heuristic based on length and structure
                words = response.split()
                if len(words) < 10:
                    quality_scores.append(0.4)  # Very short response
                elif len(words) > 100:
                    quality_scores.append(0.8)  # Detailed response
                else:
                    quality_scores.append(0.6)  # Medium response
            
            avg_quality = sum(quality_scores) / len(quality_scores)
            
            # Determine conversation health
            health_status = "healthy"
            if avg_quality < threshold:
                health_status = "degraded"
            if avg_quality < threshold / 2:
                health_status = "critical"
            
            return {
                "status": health_status,
                "quality_score": avg_quality,
                "message_count": len(conversation_history),
                "ai_response_count": len(ai_responses)
            }
            
        except Exception as e:
            logger.error(f"Conversation monitoring error: {str(e)}")
            return {"status": "error", "error": str(e)}

# Global evaluation service instance
evaluation_service = AstrologyEvaluationService()
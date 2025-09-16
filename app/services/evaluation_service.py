import langcheck
from langcheck.metrics import de, en, ja, zh
from typing import List, Dict, Any, Optional, Tuple
import logging
import numpy as np
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class AstrologyEvaluationService:
    """Service for evaluating chat responses using LangCheck."""

    def __init__(self):
        self.metrics = self._initialize_metrics()
    
    def _initialize_metrics(self) -> Dict[str, Any]:
        """Initialize evaluation metrics for astrology chatbot."""
        return {
            "fluency": en.fluency,
            "coherence": en.coherence,
            "sentiment": en.sentiment,
            "toxicity": en.toxicity,
            "relevance": en.relevance,
            "factual_accuracy": self._astrology_factual_accuracy,
            "empowerment_score": self._empowerment_score,
            "professionalism_score": self._professionalism_score
        }
    
    async def evaluate_response(
        self,
        user_input: str,
        ai_response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Comprehensive evaluation of AI response."""
        try:
            evaluation_results = {}
            
            # Evaluate each metric asynchronously
            tasks = []
            for metric_name, metric_func in self.metrics.items():
                task = self._evaluate_metric(metric_name, metric_func, ai_response, user_input, context)
                tasks.append(task)
            
            # Run all evaluations concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for metric_name, result in zip(self.metrics.keys(), results):
                if isinstance(result, Exception):
                    logger.warning(f"Metric {metric_name} failed: {str(result)}")
                    evaluation_results[metric_name] = {
                        "score": None,
                        "error": str(result),
                        "interpretation": "Evaluation failed"
                    }
                else:
                    evaluation_results[metric_name] = result
            
            # Calculate overall quality score
            valid_scores = [
                result["score"] for result in evaluation_results.values() 
                if result["score"] is not None and isinstance(result["score"], (int, float))
            ]
            
            if valid_scores:
                overall_score = np.mean(valid_scores)
                evaluation_results["overall_quality"] = {
                    "score": float(overall_score),
                    "interpretation": self._interpret_score("overall_quality", overall_score),
                    "timestamp": datetime.now().isoformat()
                }
            
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Evaluation error: {str(e)}")
            return {"error": str(e)}
    
    async def _evaluate_metric(
        self,
        metric_name: str,
        metric_func: callable,
        ai_response: str,
        user_input: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate a single metric."""
        try:
            if metric_name in ["relevance"]:
                score = metric_func([ai_response], [[user_input]])
            else:
                score = metric_func([ai_response])
            
            # Convert to scalar if it's a array-like
            if hasattr(score, '__getitem__'):
                score_value = float(score[0])
            else:
                score_value = float(score)
            
            return {
                "score": score_value,
                "interpretation": self._interpret_score(metric_name, score_value),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Metric {metric_name} evaluation failed: {str(e)}")
            raise e
    
    def _astrology_factual_accuracy(self, responses: List[str]) -> List[float]:
        """Custom metric for astrology factual accuracy."""
        scores = []
        for response in responses:
            # Simple heuristic-based scoring
            score = 0.7  # Base score
            
            # Positive indicators
            if any(term in response.lower() for term in ["based on your chart", "according to your birth", "your planetary"]):
                score += 0.1
            if "house" in response.lower() and any(term in response.lower() for term in ["position", "placement", "cusp"]):
                score += 0.1
            if any(term in response.lower() for term in ["transit", "aspect", "conjunction", "opposition"]):
                score += 0.1
            
            # Negative indicators
            if any(term in response.lower() for term in ["definitely", "certainly", "will happen", "must"]):
                score -= 0.1
            if "fate" in response.lower() or "destiny" in response.lower():
                score -= 0.1
            
            scores.append(min(max(score, 0.0), 1.0))
        
        return scores
    
    def _empowerment_score(self, responses: List[str]) -> List[float]:
        """Score for empowering language."""
        scores = []
        empowering_phrases = [
            "you can choose", "your decision", "opportunity to", "consider",
            "possibility", "option", "you might want to", "suggest", "recommend"
        ]
        
        disempowering_phrases = [
            "you must", "you have to", "it will happen", "inevitable",
            "certainly", "definitely", "fated", "destined"
        ]
        
        for response in responses:
            score = 0.5  # Neutral base
            
            # Count empowering phrases
            emp_count = sum(1 for phrase in empowering_phrases if phrase in response.lower())
            score += emp_count * 0.05
            
            # Count disempowering phrases
            disemp_count = sum(1 for phrase in disempowering_phrases if phrase in response.lower())
            score -= disemp_count * 0.1
            
            scores.append(min(max(score, 0.0), 1.0))
        
        return scores
    
    def _professionalism_score(self, responses: List[str]) -> List[float]:
        """Score for professional tone."""
        scores = []
        professional_indicators = [
            "respectfully", "professionally", "according to", "based on",
            "astrological principles", "chart indicates", "planetary influences"
        ]
        
        unprofessional_indicators = [
            "lol", "omg", "wtf", "haha", "😜", "😂", "!!!", "???"
        ]
        
        for response in responses:
            score = 0.6  # Base score
            
            # Positive indicators
            prof_count = sum(1 for phrase in professional_indicators if phrase in response.lower())
            score += prof_count * 0.05
            
            # Negative indicators
            unprof_count = sum(1 for phrase in unprofessional_indicators if phrase in response.lower())
            score -= unprof_count * 0.1
            
            scores.append(min(max(score, 0.0), 1.0))
        
        return scores
    
    def _interpret_score(self, metric_name: str, score: float) -> str:
        """Interpret metric scores for astrology context."""
        interpretations = {
            "fluency": {
                (0.0, 0.4): "Poor fluency, difficult to understand",
                (0.4, 0.6): "Average fluency, some awkward phrasing",
                (0.6, 0.8): "Good fluency, clear communication",
                (0.8, 1.0): "Excellent fluency, very natural language"
            },
            "coherence": {
                (0.0, 0.4): "Incoherent, disjointed thoughts",
                (0.4, 0.6): "Somewhat coherent, occasional tangents",
                (0.6, 0.8): "Coherent, logical flow",
                (0.8, 1.0): "Highly coherent, excellent structure"
            },
            "sentiment": {
                (0.0, 0.3): "Negative tone, potentially discouraging",
                (0.3, 0.6): "Neutral tone, factual but dry",
                (0.6, 0.8): "Positive tone, encouraging",
                (0.8, 1.0): "Very positive, highly supportive"
            },
            "toxicity": {
                (0.0, 0.1): "Non-toxic, respectful",
                (0.1, 0.3): "Slightly problematic phrasing",
                (0.3, 0.6): "Moderately toxic content",
                (0.6, 1.0): "Highly toxic, unacceptable"
            },
            "relevance": {
                (0.0, 0.4): "Irrelevant to user query",
                (0.4, 0.6): "Somewhat relevant, but off-topic",
                (0.6, 0.8): "Relevant, addresses main points",
                (0.8, 1.0): "Highly relevant, comprehensive response"
            },
            "factual_accuracy": {
                (0.0, 0.4): "Inaccurate astrological information",
                (0.4, 0.6): "Mixed accuracy, some errors",
                (0.6, 0.8): "Mostly accurate, minor issues",
                (0.8, 1.0): "Highly accurate, precise information"
            },
            "empowerment_score": {
                (0.0, 0.4): "Disempowering, deterministic language",
                (0.4, 0.6): "Neutral, neither empowering nor limiting",
                (0.6, 0.8): "Empowering, encourages agency",
                (0.8, 1.0): "Highly empowering, fosters self-determination"
            },
            "professionalism_score": {
                (0.0, 0.4): "Unprofessional, inappropriate tone",
                (0.4, 0.6): "Casual, could be more professional",
                (0.6, 0.8): "Professional, appropriate tone",
                (0.8, 1.0): "Highly professional, expert demeanor"
            },
            "overall_quality": {
                (0.0, 0.4): "Poor quality response",
                (0.4, 0.6): "Average quality, needs improvement",
                (0.6, 0.8): "Good quality response",
                (0.8, 1.0): "Excellent quality response"
            }
        }
        
        if metric_name in interpretations:
            for (low, high), interpretation in interpretations[metric_name].items():
                if low <= score < high:
                    return interpretation
        
        return "No interpretation available"

evaluation_service = AstrologyEvaluationService()

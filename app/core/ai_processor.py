"""
AI Processing Engine - Handles all AI operations
"""
import openai
from typing import Dict, List, Tuple, Optional
import json
import logging
from datetime import datetime
from config import settings, BRAND_VOICE, COMMENT_TYPES

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        """Initialize AI processor with OpenAI"""
        openai.api_key = settings.openai_api_key
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = settings.ai_temperature
        
    def classify_comment(self, comment_text: str, platform: str) -> Tuple[str, Dict]:
        """Classify comment type using AI and keyword analysis"""
        
        # Quick keyword-based classification
        comment_lower = comment_text.lower()
        
        # Check each comment type
        for comment_type, config in COMMENT_TYPES.items():
            if any(keyword in comment_lower for keyword in config["keywords"]):
                return comment_type, {
                    "confidence": 0.85,
                    "method": "keyword",
                    "matched_keywords": [k for k in config["keywords"] if k in comment_lower]
                }
        
        # Use AI for nuanced classification
        try:
            prompt = f"""
            Analyze this social media comment and classify it into ONE of these categories:
            - lead: Shows buying interest, asks about services/products, wants more info
            - praise: Compliments, positive feedback, appreciation
            - question: Asks genuine questions about content/topic
            - complaint: Negative feedback, problems, dissatisfaction
            - spam: Promotional, irrelevant, suspicious content
            - general: Normal engagement, casual comments
            
            Comment: "{comment_text}"
            Platform: {platform}
            
            Respond with JSON only: {{"type": "category", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a social media comment classifier. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            result = json.loads(response.choices[0].message.content)
            return result["type"], {
                "confidence": result["confidence"],
                "reasoning": result["reasoning"],
                "method": "ai"
            }
            
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return "general", {
                "confidence": 0.5,
                "method": "fallback",
                "error": str(e)
            }
    
    def generate_reply(self, comment_text: str, comment_type: str, platform: str,
                      post_context: Optional[str] = None, author_name: str = "Friend") -> Dict:
        """Generate contextual reply based on comment"""
        
        try:
            # Build system prompt with brand voice
            system_prompt = f"""
            You are Ervin's AI assistant managing his social media presence.
            
            BRAND VOICE:
            - Tone: {BRAND_VOICE['tone']}
            - Style: {BRAND_VOICE['style']}
            - Values: {', '.join(BRAND_VOICE['values'])}
            - Avoid: {', '.join(BRAND_VOICE['avoid'])}
            
            PLATFORM-SPECIFIC GUIDELINES:
            - YouTube: Educational, detailed responses (2-3 sentences)
            - Instagram: Visual, emoji-friendly, concise (1-2 sentences)
            - Facebook: Community-focused, warm (2 sentences)
            - LinkedIn: Professional yet personal (2-3 sentences)
            - Twitter: Brief, impactful (1 sentence)
            
            REPLY RULES BY TYPE:
            
            LEAD REPLIES:
            - Acknowledge interest warmly
            - Provide value without hard selling
            - Include soft CTA (link in bio, DM for details)
            
            PRAISE REPLIES:
            - Express genuine gratitude
            - Ask engaging follow-up question
            - Build community connection
            
            QUESTION REPLIES:
            - Give helpful, specific answers
            - Share expertise simply
            - Invite further discussion
            
            COMPLAINT REPLIES:
            - Show empathy first
            - Take responsibility if needed
            - Offer concrete next steps
            
            Use the commenter's name when appropriate. Keep replies natural and conversational.
            """
            
            # Build user prompt
            context_info = f"\nPost context: {post_context}" if post_context else ""
            
            user_prompt = f"""
            Platform: {platform}
            Comment type: {comment_type}
            Commenter: {author_name}
            Comment: "{comment_text}"{context_info}
            
            Generate an appropriate reply following the guidelines.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=settings.max_reply_tokens
            )
            
            reply_text = response.choices[0].message.content.strip()
            
            # Detect triggers for GHL
            triggers = self._detect_triggers(comment_text, reply_text, comment_type)
            
            # Calculate confidence
            confidence = self._calculate_confidence(comment_type, reply_text)
            
            return {
                "reply": reply_text,
                "confidence": confidence,
                "triggers": triggers,
                "needs_approval": self._needs_approval(comment_type, confidence),
                "metadata": {
                    "platform": platform,
                    "comment_type": comment_type,
                    "model": self.model
                }
            }
            
        except Exception as e:
            logger.error(f"Reply generation failed: {e}")
            return {
                "reply": self._get_fallback_reply(comment_type, platform),
                "confidence": 0.3,
                "triggers": {},
                "needs_approval": True,
                "error": str(e)
            }
    
    def _detect_triggers(self, comment: str, reply: str, comment_type: str) -> Dict:
        """Detect GHL workflow triggers"""
        triggers = {
            "tags": [],
            "workflows": []
        }
        
        combined_text = f"{comment} {reply}".lower()
        
        # Lead triggers
        if comment_type == "lead" or any(word in combined_text for word in ["interested", "price", "buy", "info"]):
            triggers["tags"].append("hot_lead")
            triggers["workflows"].append("lead_nurture")
        
        # Support triggers
        if comment_type == "complaint" or any(word in combined_text for word in ["help", "problem", "issue"]):
            triggers["tags"].append("needs_support")
            triggers["workflows"].append("customer_service")
        
        # Testimonial triggers
        if comment_type == "praise":
            triggers["tags"].append("happy_customer")
            triggers["workflows"].append("testimonial_request")
        
        # High value triggers
        if any(word in combined_text for word in ["course", "program", "coaching", "consultation"]):
            triggers["tags"].append("high_value_prospect")
            triggers["workflows"].append("sales_followup")
        
        return triggers
    
    def _calculate_confidence(self, comment_type: str, reply: str) -> float:
        """Calculate confidence score for the reply"""
        base_confidence = 0.7
        
        # Adjust based on comment type
        if comment_type in ["praise", "general"]:
            base_confidence += 0.15
        elif comment_type in ["lead", "complaint"]:
            base_confidence -= 0.1
        
        # Adjust based on reply length
        if 20 <= len(reply.split()) <= 50:
            base_confidence += 0.05
        
        return min(max(base_confidence, 0.1), 1.0)
    
    def _needs_approval(self, comment_type: str, confidence: float) -> bool:
        """Determine if reply needs manual approval"""
        # Auto-approve high confidence praise and general comments
        if comment_type in ["praise", "general"] and confidence >= settings.auto_approve_confidence:
            return False
        
        # Always require approval for complaints and leads
        if comment_type in ["complaint", "lead"]:
            return True
        
        # Require approval for low confidence
        return confidence < settings.auto_approve_confidence
    
    def _get_fallback_reply(self, comment_type: str, platform: str) -> str:
        """Get fallback reply when AI fails"""
        fallbacks = {
            "praise": "Thank you so much for your kind words! 🙏",
            "question": "Great question! Let me get back to you on this.",
            "lead": "Thanks for your interest! Please check the link in bio for more details.",
            "complaint": "I appreciate your feedback and want to help. Please DM me so we can resolve this.",
            "general": "Thanks for being part of this community! 🙌"
        }
        return fallbacks.get(comment_type, "Thanks for your comment!")
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": f"""
                    Analyze the sentiment of this text. Respond with JSON only:
                    
                    Text: "{text}"
                    
                    Format: {{"sentiment": "positive/negative/neutral", "score": 0.0-1.0, "emotions": ["list", "of", "emotions"]}}
                    """
                }],
                temperature=0.3,
                max_tokens=100
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.5,
                "emotions": ["unknown"]
            }
    
    def test_reply_generation(self, comment: str, platform: str = "instagram") -> Dict:
        """Test reply generation for manual testing"""
        # First classify the comment
        comment_type, classification = self.classify_comment(comment, platform)
        
        # Then generate reply
        result = self.generate_reply(
            comment_text=comment,
            comment_type=comment_type,
            platform=platform,
            author_name="Test User"
        )
        
        # Add classification info
        result["classification"] = {
            "type": comment_type,
            "metadata": classification
        }
        
        # Add sentiment analysis
        result["sentiment"] = self.analyze_sentiment(comment)
        
        return result
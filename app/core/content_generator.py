"""
Content Generator - AI-powered content creation
"""
from typing import List, Dict, Optional
import logging
from datetime import datetime
from core.ai_processor import AIProcessor
from config import BRAND_VOICE

logger = logging.getLogger(__name__)

class ContentGenerator:
    def __init__(self):
        """Initialize content generator"""
        self.ai = AIProcessor()
        
        self.content_templates = {
            "social_caption": {
                "description": "Engaging social media captions",
                "prompt_template": "Create an engaging social media caption about {topic}. Include 3-5 relevant hashtags and a call-to-action. Make it {tone}.",
                "max_length": 300
            },
            "devotional": {
                "description": "Daily devotional content",
                "prompt_template": "Write a short daily devotional about {topic}. Include:\n1. A relevant Bible verse\n2. A 2-3 paragraph reflection\n3. A practical application\n4. A closing prayer\n\nMake it {tone} and authentic.",
                "max_length": 500
            },
            "video_description": {
                "description": "YouTube video descriptions",
                "prompt_template": "Write a YouTube video description for content about {topic}. Include:\n- Hook sentence\n- What viewers will learn (3-5 points)\n- Relevant timestamps (if applicable)\n- Call-to-action\n- Related links section\n\nTone: {tone}",
                "max_length": 400
            },
            "story_series": {
                "description": "Instagram/Facebook story series",
                "prompt_template": "Create a 5-part story series about {topic}. Each part should:\n- Be 1-2 sentences\n- Build on the previous\n- End with intrigue (except the last)\n- Include relevant emoji\n\nTone: {tone}",
                "max_length": 500
            },
            "email_newsletter": {
                "description": "Email newsletter content",
                "prompt_template": "Write an email newsletter about {topic}. Include:\n- Engaging subject line\n- Personal greeting\n- Main content (2-3 paragraphs)\n- Call-to-action\n- Sign-off\n\nTone: {tone}",
                "max_length": 600
            },
            "hashtag_set": {
                "description": "Curated hashtag sets",
                "prompt_template": "Generate 20 hashtags for {topic} content. Mix:\n- 5 high-volume (1M+ posts)\n- 10 medium-volume (100K-1M posts)\n- 5 niche/specific hashtags\n\nFormat as comma-separated list.",
                "max_length": 300
            }
        }
    
    def generate_content(self, content_type: str, topic: str, 
                        series: Optional[str] = None, count: int = 1,
                        tone: str = "inspirational") -> List[Dict]:
        """Generate content based on type and parameters"""
        
        if content_type not in self.content_templates:
            raise ValueError(f"Invalid content type: {content_type}")
        
        template = self.content_templates[content_type]
        generated_content = []
        
        for i in range(count):
            try:
                # Build the prompt
                prompt = template["prompt_template"].format(
                    topic=topic,
                    tone=tone
                )
                
                if series:
                    prompt += f"\n\nThis is part of the '{series}' series."
                
                # Add brand voice context
                system_prompt = f"""
                You are Ervin's content creator. Generate {content_type} that matches his brand:
                
                Brand Voice: {BRAND_VOICE['tone']}
                Style: {BRAND_VOICE['style']}
                Values: {', '.join(BRAND_VOICE['values'])}
                
                Make content authentic, valuable, and actionable. Avoid clichés and generic motivational quotes.
                """
                
                # Generate content
                response = self.ai.client.chat.completions.create(
                    model=self.ai.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                    max_tokens=template["max_length"]
                )
                
                content_text = response.choices[0].message.content.strip()
                
                # Parse hashtags if present
                hashtags = self._extract_hashtags(content_text) if "#" in content_text else []
                
                content_item = {
                    "type": content_type,
                    "topic": topic,
                    "series": series,
                    "content": content_text,
                    "hashtags": hashtags,
                    "metadata": {
                        "tone": tone,
                        "generated_at": datetime.utcnow().isoformat(),
                        "model": self.ai.model,
                        "index": i + 1 if count > 1 else None
                    }
                }
                
                generated_content.append(content_item)
                
            except Exception as e:
                logger.error(f"Content generation failed: {e}")
                generated_content.append({
                    "type": content_type,
                    "topic": topic,
                    "series": series,
                    "content": f"[Generation failed: {str(e)}]",
                    "hashtags": [],
                    "metadata": {"error": str(e)}
                })
        
        return generated_content
    
    def generate_bulk_captions(self, topics: List[str], tone: str = "inspirational") -> List[Dict]:
        """Generate multiple captions for different topics"""
        all_captions = []
        
        for topic in topics:
            captions = self.generate_content(
                content_type="social_caption",
                topic=topic,
                count=3,
                tone=tone
            )
            all_captions.extend(captions)
        
        return all_captions
    
    def generate_content_calendar(self, theme: str, days: int = 7) -> Dict:
        """Generate a content calendar with various content types"""
        calendar = {
            "theme": theme,
            "days": days,
            "content": []
        }
        
        content_rotation = [
            ("devotional", "morning reflection"),
            ("social_caption", "motivational post"),
            ("story_series", "behind the scenes"),
            ("video_description", "teaching video"),
            ("social_caption", "community engagement"),
            ("email_newsletter", "weekly update"),
            ("devotional", "evening meditation")
        ]
        
        for day in range(days):
            content_type, subtitle = content_rotation[day % len(content_rotation)]
            
            day_content = self.generate_content(
                content_type=content_type,
                topic=f"{theme} - {subtitle}",
                series=f"{theme} Week",
                count=1
            )[0]
            
            day_content["day"] = day + 1
            day_content["subtitle"] = subtitle
            calendar["content"].append(day_content)
        
        return calendar
    
    def generate_campaign_content(self, campaign_name: str, platforms: List[str]) -> Dict:
        """Generate coordinated content for a multi-platform campaign"""
        campaign = {
            "name": campaign_name,
            "platforms": platforms,
            "content": {}
        }
        
        # Platform-specific content types
        platform_content_map = {
            "instagram": ["social_caption", "story_series", "hashtag_set"],
            "youtube": ["video_description", "social_caption"],
            "facebook": ["social_caption", "devotional"],
            "linkedin": ["social_caption"],
            "twitter": ["social_caption", "hashtag_set"],
            "email": ["email_newsletter"]
        }
        
        for platform in platforms:
            if platform in platform_content_map:
                platform_content = []
                
                for content_type in platform_content_map[platform]:
                    content = self.generate_content(
                        content_type=content_type,
                        topic=campaign_name,
                        series=f"{campaign_name} Campaign",
                        count=1
                    )[0]
                    
                    content["platform"] = platform
                    platform_content.append(content)
                
                campaign["content"][platform] = platform_content
        
        return campaign
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        import re
        hashtags = re.findall(r'#\w+', text)
        return [tag.lower() for tag in hashtags]
    
    def refresh_content(self, content_id: int, content_type: str, original_content: str) -> Dict:
        """Refresh/regenerate existing content with a new angle"""
        try:
            prompt = f"""
            Take this existing {content_type} content and create a fresh version with a new angle:
            
            Original: {original_content}
            
            Create a new version that:
            - Maintains the core message
            - Uses different wording and structure
            - Adds a fresh perspective
            - Keeps the same tone and purpose
            """
            
            response = self.ai.client.chat.completions.create(
                model=self.ai.model,
                messages=[
                    {"role": "system", "content": "You are a creative content refresher. Make content feel new while keeping its essence."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=self.content_templates.get(content_type, {}).get("max_length", 400)
            )
            
            return {
                "original_id": content_id,
                "refreshed_content": response.choices[0].message.content.strip(),
                "metadata": {
                    "refreshed_at": datetime.utcnow().isoformat(),
                    "method": "ai_refresh"
                }
            }
            
        except Exception as e:
            logger.error(f"Content refresh failed: {e}")
            return {
                "original_id": content_id,
                "error": str(e)
            }
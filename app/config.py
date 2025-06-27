"""
Configuration management for the application
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    """Application settings"""
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4"
    
    # Database
    postgres_url: str
    
    # Social Media APIs
    youtube_api_key: Optional[str] = None
    facebook_access_token: Optional[str] = None
    facebook_page_id: Optional[str] = None
    instagram_access_token: Optional[str] = None
    instagram_business_account_id: Optional[str] = None
    linkedin_access_token: Optional[str] = None
    twitter_bearer_token: Optional[str] = None
    
    # GoHighLevel
    ghl_api_key: Optional[str] = None
    ghl_location_id: Optional[str] = None
    
    # Application settings
    fetch_interval: int = 300  # 5 minutes
    max_comments_per_fetch: int = 50
    auto_approve_confidence: float = 0.8
    
    # AI settings
    ai_temperature: float = 0.7
    max_reply_tokens: int = 200
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator("postgres_url")
    def validate_postgres_url(cls, v):
        if not v:
            raise ValueError("POSTGRES_URL is required")
        return v
    
    @validator("openai_api_key")
    def validate_openai_key(cls, v):
        if not v:
            raise ValueError("OPENAI_API_KEY is required")
        return v

# Create settings instance
settings = Settings()

# Brand voice configuration
BRAND_VOICE = {
    "tone": "inspirational, authentic, faith-based",
    "style": "conversational, encouraging, professional",
    "values": ["faith", "motivation", "community", "growth"],
    "avoid": ["overly promotional", "generic responses", "religious preaching"]
}

# Comment type definitions
COMMENT_TYPES = {
    "lead": {
        "keywords": ["interested", "how much", "price", "buy", "want", "need", "sign up"],
        "color": "#ff9800",
        "priority": 1
    },
    "praise": {
        "keywords": ["amazing", "great", "awesome", "love", "fantastic", "thank you"],
        "color": "#4caf50",
        "priority": 3
    },
    "question": {
        "keywords": ["?", "how", "what", "when", "where", "why", "can you"],
        "color": "#2196f3",
        "priority": 2
    },
    "complaint": {
        "keywords": ["problem", "issue", "wrong", "bad", "terrible", "hate", "disappointed"],
        "color": "#f44336",
        "priority": 1
    },
    "spam": {
        "keywords": ["click here", "follow me", "check my", "dm me", "link in bio"],
        "color": "#9e9e9e",
        "priority": 5
    }
}

# GHL workflow mappings
GHL_WORKFLOWS = {
    "lead": "lead_nurture_sequence",
    "praise": "testimonial_request",
    "question": "support_followup",
    "complaint": "customer_service",
    "high_value": "sales_followup"
}
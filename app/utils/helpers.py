"""
Helper functions and utilities
"""
import re
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import pytz

def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text"""
    pattern = r'#\w+'
    hashtags = re.findall(pattern, text)
    return [tag.lower() for tag in hashtags]

def extract_mentions(text: str) -> List[str]:
    """Extract @mentions from text"""
    pattern = r'@\w+'
    mentions = re.findall(pattern, text)
    return mentions

def clean_text(text: str) -> str:
    """Clean text for processing"""
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\!\?\-\#\@]', '', text)
    return text.strip()

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def format_number(num: int) -> str:
    """Format large numbers (1.2K, 3.4M, etc.)"""
    if num < 1000:
        return str(num)
    elif num < 1_000_000:
        return f"{num/1000:.1f}K"
    elif num < 1_000_000_000:
        return f"{num/1_000_000:.1f}M"
    else:
        return f"{num/1_000_000_000:.1f}B"

def time_ago(timestamp: datetime) -> str:
    """Convert timestamp to human-readable time ago"""
    now = datetime.utcnow()
    if timestamp.tzinfo:
        now = pytz.utc.localize(now)
    
    diff = now - timestamp
    
    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes}m ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}h ago"
    elif diff < timedelta(days=30):
        days = diff.days
        return f"{days}d ago"
    else:
        return timestamp.strftime("%b %d, %Y")

def parse_platform_timestamp(timestamp_str: str, platform: str) -> datetime:
    """Parse platform-specific timestamp formats"""
    try:
        if platform == "youtube":
            # YouTube uses ISO format with Z
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        elif platform == "facebook":
            # Facebook uses ISO format
            return datetime.fromisoformat(timestamp_str)
        elif platform == "instagram":
            # Instagram uses ISO format
            return datetime.fromisoformat(timestamp_str)
        elif platform == "linkedin":
            # LinkedIn might use milliseconds
            if isinstance(timestamp_str, (int, float)):
                return datetime.fromtimestamp(timestamp_str / 1000)
            return datetime.fromisoformat(timestamp_str)
        elif platform == "twitter":
            # Twitter uses ISO format
            return datetime.fromisoformat(timestamp_str)
        else:
            return datetime.fromisoformat(timestamp_str)
    except Exception as e:
        # Fallback to current time if parsing fails
        return datetime.utcnow()

def generate_comment_id(platform: str, comment_id: str) -> str:
    """Generate unique comment identifier"""
    return f"{platform}_{comment_id}"

def parse_platform_metrics(metrics: Dict, platform: str) -> Dict:
    """Standardize platform metrics"""
    standardized = {
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "views": 0
    }
    
    if platform == "youtube":
        standardized["likes"] = metrics.get("likeCount", 0)
        standardized["views"] = metrics.get("viewCount", 0)
        standardized["comments"] = metrics.get("commentCount", 0)
    elif platform == "facebook":
        standardized["likes"] = metrics.get("like_count", 0)
        standardized["comments"] = metrics.get("comment_count", 0)
        standardized["shares"] = metrics.get("share_count", 0)
    elif platform == "instagram":
        standardized["likes"] = metrics.get("like_count", 0)
        standardized["comments"] = metrics.get("comments_count", 0)
    elif platform == "twitter":
        if isinstance(metrics, dict):
            standardized["likes"] = metrics.get("like_count", 0)
            standardized["comments"] = metrics.get("reply_count", 0)
            standardized["shares"] = metrics.get("retweet_count", 0)
            standardized["views"] = metrics.get("impression_count", 0)
    
    return standardized

def validate_api_keys() -> Dict[str, bool]:
    """Validate which API keys are configured"""
    from app.config import settings
    
    return {
        "openai": bool(settings.openai_api_key),
        "youtube": bool(settings.youtube_api_key),
        "facebook": bool(settings.facebook_access_token),
        "instagram": bool(settings.instagram_access_token),
        "linkedin": bool(settings.linkedin_access_token),
        "twitter": bool(settings.twitter_bearer_token),
        "ghl": bool(settings.ghl_api_key)
    }

def sanitize_for_platform(text: str, platform: str, max_length: Optional[int] = None) -> str:
    """Sanitize text for specific platform requirements"""
    # Platform-specific max lengths
    platform_limits = {
        "twitter": 280,
        "instagram": 2200,
        "facebook": 63206,
        "linkedin": 3000,
        "youtube": 10000
    }
    
    # Use provided max_length or platform default
    limit = max_length or platform_limits.get(platform, 2000)
    
    # Clean the text
    text = clean_text(text)
    
    # Platform-specific formatting
    if platform == "instagram":
        # Instagram doesn't support line breaks in comments
        text = text.replace('\n', ' ')
    elif platform == "youtube":
        # YouTube supports basic formatting
        pass
    
    # Truncate if needed
    if len(text) > limit:
        text = truncate_text(text, limit - 3)
    
    return text

def batch_process(items: List[Any], batch_size: int = 10) -> List[List[Any]]:
    """Split items into batches for processing"""
    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i:i + batch_size])
    return batches

def merge_metadata(existing: Dict, new: Dict) -> Dict:
    """Merge metadata dictionaries"""
    merged = existing.copy()
    for key, value in new.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_metadata(merged[key], value)
        else:
            merged[key] = value
    return merged

def calculate_engagement_score(metrics: Dict, platform: str) -> float:
    """Calculate engagement score based on platform metrics"""
    weights = {
        "youtube": {"likes": 1, "comments": 3, "views": 0.1},
        "facebook": {"likes": 1, "comments": 2, "shares": 3},
        "instagram": {"likes": 1, "comments": 2},
        "linkedin": {"likes": 1, "comments": 2, "shares": 3},
        "twitter": {"likes": 1, "comments": 2, "shares": 3, "views": 0.1}
    }
    
    platform_weights = weights.get(platform, {"likes": 1, "comments": 2})
    score = 0.0
    
    for metric, weight in platform_weights.items():
        score += metrics.get(metric, 0) * weight
    
    return score

def is_business_hours(timezone: str = "US/Eastern") -> bool:
    """Check if current time is within business hours"""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    
    # Monday = 0, Sunday = 6
    if now.weekday() >= 5:  # Weekend
        return False
    
    # Business hours: 9 AM - 6 PM
    return 9 <= now.hour < 18

def get_platform_icon(platform: str) -> str:
    """Get emoji icon for platform"""
    icons = {
        "youtube": "📺",
        "facebook": "📘",
        "instagram": "📷",
        "linkedin": "💼",
        "twitter": "🐦",
        "email": "📧"
    }
    return icons.get(platform, "🌐")

def format_platform_url(platform: str, post_id: str, username: Optional[str] = None) -> str:
    """Generate platform URL for a post"""
    if platform == "youtube":
        return f"https://youtube.com/watch?v={post_id}"
    elif platform == "facebook":
        return f"https://facebook.com/{post_id}"
    elif platform == "instagram":
        return f"https://instagram.com/p/{post_id}"
    elif platform == "linkedin":
        return f"https://linkedin.com/feed/update/{post_id}"
    elif platform == "twitter" and username:
        return f"https://twitter.com/{username}/status/{post_id}"
    else:
        return "#"
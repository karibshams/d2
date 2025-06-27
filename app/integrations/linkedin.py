"""
LinkedIn API Integration
"""
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional
from config import settings

logger = logging.getLogger(__name__)

class LinkedInIntegration:
    def __init__(self):
        """Initialize LinkedIn API client"""
        self.access_token = settings.linkedin_access_token
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json"
        }
        
    def is_configured(self) -> bool:
        """Check if LinkedIn is configured"""
        return bool(self.access_token)
    
    def get_user_posts(self, limit: int = 25) -> List[Dict]:
        """Get recent LinkedIn posts"""
        if not self.is_configured():
            return []
        
        try:
            # First get user ID
            user_response = requests.get(
                f"{self.base_url}/me",
                headers=self.headers
            )
            user_response.raise_for_status()
            user_id = user_response.json()["id"]
            
            # Get posts
            url = f"{self.base_url}/shares"
            params = {
                "q": "owners",
                "owners": f"urn:li:person:{user_id}",
                "count": limit,
                "sharesPerOwner": limit
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            posts = []
            for item in response.json().get("elements", []):
                post_data = {
                    "platform": "linkedin",
                    "platform_post_id": item.get("id", ""),
                    "content": item.get("text", {}).get("text", ""),
                    "author": f"User: {user_id}",
                    "url": f"https://www.linkedin.com/feed/update/{item.get('id', '')}",
                    "media_type": "text",
                    "published_at": datetime.fromtimestamp(item.get("created", {}).get("time", 0) / 1000).isoformat(),
                    "metadata": {
                        "visibility": item.get("visibility", {}).get("code", "")
                    }
                }
                posts.append(post_data)
            
            logger.info(f"Retrieved {len(posts)} LinkedIn posts")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to get LinkedIn posts: {e}")
            return []
    
    def get_post_comments(self, post_urn: str) -> List[Dict]:
        """Get comments for a LinkedIn post"""
        if not self.is_configured():
            return []
        
        try:
            url = f"{self.base_url}/socialActions/{post_urn}/comments"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            comments = []
            for item in response.json().get("elements", []):
                comment_data = {
                    "platform": "linkedin",
                    "platform_comment_id": item.get("id", ""),
                    "parent_comment_id": item.get("parentComment"),
                    "content": item.get("message", {}).get("text", ""),
                    "author": item.get("actor", {}).get("name", {}).get("localized", {}).get("en_US", "Unknown"),
                    "author_id": item.get("actor", {}).get("id", ""),
                    "published_at": datetime.fromtimestamp(item.get("created", {}).get("time", 0) / 1000).isoformat(),
                    "metadata": {
                        "post_urn": post_urn
                    }
                }
                comments.append(comment_data)
            
            logger.info(f"Retrieved {len(comments)} comments for LinkedIn post")
            return comments
            
        except Exception as e:
            logger.error(f"Failed to get LinkedIn comments: {e}")
            return []
    
    def reply_to_comment(self, post_urn: str, comment_text: str, parent_comment_id: str = None) -> Dict:
        """Reply to a LinkedIn comment or post"""
        if not self.is_configured():
            return {
                "success": False,
                "error": "LinkedIn not configured"
            }
        
        try:
            url = f"{self.base_url}/socialActions/{post_urn}/comments"
            
            payload = {
                "actor": f"urn:li:person:MEMBER_ID",  # Need to get member ID
                "message": {
                    "text": comment_text
                }
            }
            
            if parent_comment_id:
                payload["parentComment"] = parent_comment_id
            
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"Successfully replied to LinkedIn comment/post")
            return {
                "success": True,
                "reply_id": result.get("id", ""),
                "message": "Reply posted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to reply to LinkedIn: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_profile_analytics(self) -> Dict:
        """Get LinkedIn profile analytics"""
        if not self.is_configured():
            return {}
        
        try:
            # This is a simplified example - actual implementation would use proper analytics endpoints
            return {
                "profile_views": 0,
                "post_impressions": 0,
                "search_appearances": 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get LinkedIn analytics: {e}")
            return {}
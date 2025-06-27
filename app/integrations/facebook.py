"""
Facebook API Integration
"""
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional
from config import settings

logger = logging.getLogger(__name__)

class FacebookIntegration:
    def __init__(self):
        """Initialize Facebook API client"""
        self.access_token = settings.facebook_access_token
        self.page_id = settings.facebook_page_id
        self.base_url = "https://graph.facebook.com/v18.0"
        
    def is_configured(self) -> bool:
        """Check if Facebook is configured"""
        return bool(self.access_token and self.page_id)
    
    def get_page_posts(self, limit: int = 25) -> List[Dict]:
        """Get recent posts from Facebook page"""
        if not self.is_configured():
            return []
        
        try:
            url = f"{self.base_url}/{self.page_id}/posts"
            params = {
                "access_token": self.access_token,
                "limit": limit,
                "fields": "id,message,created_time,permalink_url,type,attachments"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            posts = []
            for item in response.json().get("data", []):
                post_data = {
                    "platform": "facebook",
                    "platform_post_id": item["id"],
                    "content": item.get("message", ""),
                    "author": f"Page: {self.page_id}",
                    "url": item.get("permalink_url"),
                    "media_type": item.get("type", "text"),
                    "published_at": item["created_time"],
                    "metadata": {
                        "attachments": item.get("attachments", {})
                    }
                }
                posts.append(post_data)
            
            logger.info(f"Retrieved {len(posts)} Facebook posts")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to get Facebook posts: {e}")
            return []
    
    def get_post_comments(self, post_id: str) -> List[Dict]:
        """Get comments for a Facebook post"""
        if not self.is_configured():
            return []
        
        try:
            url = f"{self.base_url}/{post_id}/comments"
            params = {
                "access_token": self.access_token,
                "fields": "id,message,from,created_time,like_count,comment_count,parent",
                "filter": "stream",
                "order": "reverse_chronological"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            comments = []
            for item in response.json().get("data", []):
                comment_data = {
                    "platform": "facebook",
                    "platform_comment_id": item["id"],
                    "parent_comment_id": item.get("parent", {}).get("id"),
                    "content": item.get("message", ""),
                    "author": item["from"]["name"],
                    "author_id": item["from"]["id"],
                    "published_at": item["created_time"],
                    "metadata": {
                        "post_id": post_id,
                        "like_count": item.get("like_count", 0),
                        "comment_count": item.get("comment_count", 0)
                    }
                }
                comments.append(comment_data)
            
            logger.info(f"Retrieved {len(comments)} comments for post {post_id}")
            return comments
            
        except Exception as e:
            logger.error(f"Failed to get Facebook comments: {e}")
            return []
    
    def reply_to_comment(self, comment_id: str, reply_text: str) -> Dict:
        """Reply to a Facebook comment"""
        if not self.is_configured():
            return {
                "success": False,
                "error": "Facebook not configured"
            }
        
        try:
            url = f"{self.base_url}/{comment_id}/comments"
            data = {
                "access_token": self.access_token,
                "message": reply_text
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"Successfully replied to Facebook comment {comment_id}")
            return {
                "success": True,
                "reply_id": result["id"],
                "message": "Reply posted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to reply to Facebook comment: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_page_insights(self, metrics: List[str] = None) -> Dict:
        """Get page insights/analytics"""
        if not self.is_configured():
            return {}
        
        if not metrics:
            metrics = ["page_engaged_users", "page_post_engagements", "page_fans"]
        
        try:
            url = f"{self.base_url}/{self.page_id}/insights"
            params = {
                "access_token": self.access_token,
                "metric": ",".join(metrics),
                "period": "day"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            insights = {}
            for item in response.json().get("data", []):
                insights[item["name"]] = item["values"][-1]["value"] if item["values"] else 0
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get page insights: {e}")
            return {}
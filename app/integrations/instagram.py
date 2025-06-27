"""
Instagram Business API Integration
"""
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional
from config import settings

logger = logging.getLogger(__name__)

class InstagramIntegration:
    def __init__(self):
        """Initialize Instagram API client"""
        self.access_token = settings.instagram_access_token
        self.account_id = settings.instagram_business_account_id
        self.base_url = "https://graph.facebook.com/v18.0"
        
    def is_configured(self) -> bool:
        """Check if Instagram is configured"""
        return bool(self.access_token and self.account_id)
    
    def get_media_posts(self, limit: int = 25) -> List[Dict]:
        """Get recent Instagram media posts"""
        if not self.is_configured():
            return []
        
        try:
            url = f"{self.base_url}/{self.account_id}/media"
            params = {
                "access_token": self.access_token,
                "limit": limit,
                "fields": "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            posts = []
            for item in response.json().get("data", []):
                post_data = {
                    "platform": "instagram",
                    "platform_post_id": item["id"],
                    "content": item.get("caption", ""),
                    "author": f"Account: {self.account_id}",
                    "url": item.get("permalink"),
                    "media_type": item.get("media_type", "IMAGE").lower(),
                    "published_at": item["timestamp"],
                    "metadata": {
                        "media_url": item.get("media_url"),
                        "like_count": item.get("like_count", 0),
                        "comments_count": item.get("comments_count", 0)
                    }
                }
                posts.append(post_data)
            
            logger.info(f"Retrieved {len(posts)} Instagram posts")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to get Instagram posts: {e}")
            return []
    
    def get_media_comments(self, media_id: str) -> List[Dict]:
        """Get comments for Instagram media"""
        if not self.is_configured():
            return []
        
        try:
            url = f"{self.base_url}/{media_id}/comments"
            params = {
                "access_token": self.access_token,
                "fields": "id,text,username,timestamp,like_count,replies{id,text,username,timestamp}"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            comments = []
            for item in response.json().get("data", []):
                # Process main comment
                comment_data = {
                    "platform": "instagram",
                    "platform_comment_id": item["id"],
                    "parent_comment_id": None,
                    "content": item.get("text", ""),
                    "author": item.get("username", "Unknown"),
                    "author_id": item.get("username"),  # Instagram uses username as ID
                    "published_at": item.get("timestamp"),
                    "metadata": {
                        "media_id": media_id,
                        "like_count": item.get("like_count", 0)
                    }
                }
                comments.append(comment_data)
                
                # Process replies
                if "replies" in item:
                    for reply in item["replies"]["data"]:
                        reply_data = {
                            "platform": "instagram",
                            "platform_comment_id": reply["id"],
                            "parent_comment_id": item["id"],
                            "content": reply.get("text", ""),
                            "author": reply.get("username", "Unknown"),
                            "author_id": reply.get("username"),
                            "published_at": reply.get("timestamp"),
                            "metadata": {
                                "media_id": media_id,
                                "is_reply": True
                            }
                        }
                        comments.append(reply_data)
            
            logger.info(f"Retrieved {len(comments)} comments for media {media_id}")
            return comments
            
        except Exception as e:
            logger.error(f"Failed to get Instagram comments: {e}")
            return []
    
    def reply_to_comment(self, comment_id: str, reply_text: str) -> Dict:
        """Reply to an Instagram comment"""
        if not self.is_configured():
            return {
                "success": False,
                "error": "Instagram not configured"
            }
        
        try:
            url = f"{self.base_url}/{comment_id}/replies"
            data = {
                "access_token": self.access_token,
                "message": reply_text
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"Successfully replied to Instagram comment {comment_id}")
            return {
                "success": True,
                "reply_id": result["id"],
                "message": "Reply posted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to reply to Instagram comment: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_account_insights(self, metrics: List[str] = None, period: str = "day") -> Dict:
        """Get Instagram account insights"""
        if not self.is_configured():
            return {}
        
        if not metrics:
            metrics = ["impressions", "reach", "profile_views", "website_clicks"]
        
        try:
            url = f"{self.base_url}/{self.account_id}/insights"
            params = {
                "access_token": self.access_token,
                "metric": ",".join(metrics),
                "period": period
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            insights = {}
            for item in response.json().get("data", []):
                insights[item["name"]] = item["values"][-1]["value"] if item["values"] else 0
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get Instagram insights: {e}")
            return {}
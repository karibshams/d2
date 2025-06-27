"""
Twitter API v2 Integration
"""
import tweepy
import logging
from datetime import datetime
from typing import Dict, List, Optional
from config import settings

logger = logging.getLogger(__name__)

class TwitterIntegration:
    def __init__(self):
        """Initialize Twitter API client"""
        self.bearer_token = settings.twitter_bearer_token
        self.client = None
        
        if self.bearer_token:
            try:
                self.client = tweepy.Client(
                    bearer_token=self.bearer_token,
                    wait_on_rate_limit=True
                )
                logger.info("Twitter API client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twitter API: {e}")
    
    def is_configured(self) -> bool:
        """Check if Twitter is configured"""
        return bool(self.client)
    
    def get_user_tweets(self, username: str, max_results: int = 100) -> List[Dict]:
        """Get recent tweets from user"""
        if not self.client:
            return []
        
        try:
            # Get user ID
            user = self.client.get_user(username=username)
            if not user.data:
                logger.error(f"User {username} not found")
                return []
            
            user_id = user.data.id
            
            # Get tweets
            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=min(max_results, 100),
                tweet_fields=['created_at', 'public_metrics', 'conversation_id', 'referenced_tweets'],
                exclude=['retweets', 'replies']
            )
            
            if not tweets.data:
                return []
            
            posts = []
            for tweet in tweets.data:
                post_data = {
                    "platform": "twitter",
                    "platform_post_id": str(tweet.id),
                    "content": tweet.text,
                    "author": username,
                    "url": f"https://twitter.com/{username}/status/{tweet.id}",
                    "media_type": "text",
                    "published_at": tweet.created_at.isoformat() if tweet.created_at else "",
                    "metadata": {
                        "metrics": tweet.public_metrics,
                        "conversation_id": tweet.conversation_id
                    }
                }
                posts.append(post_data)
            
            logger.info(f"Retrieved {len(posts)} tweets")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to get tweets: {e}")
            return []
    
    def get_tweet_replies(self, tweet_id: str) -> List[Dict]:
        """Get replies to a tweet"""
        if not self.client:
            return []
        
        try:
            # Search for replies using conversation_id
            replies = self.client.search_recent_tweets(
                query=f"conversation_id:{tweet_id}",
                tweet_fields=['created_at', 'author_id', 'in_reply_to_user_id', 'referenced_tweets'],
                user_fields=['username'],
                expansions=['author_id'],
                max_results=100
            )
            
            if not replies.data:
                return []
            
            # Build user lookup
            users = {user.id: user.username for user in (replies.includes.get('users', []) or [])}
            
            comments = []
            for tweet in replies.data:
                if str(tweet.id) != tweet_id:  # Exclude original tweet
                    comment_data = {
                        "platform": "twitter",
                        "platform_comment_id": str(tweet.id),
                        "parent_comment_id": tweet_id,
                        "content": tweet.text,
                        "author": users.get(tweet.author_id, "Unknown"),
                        "author_id": tweet.author_id,
                        "published_at": tweet.created_at.isoformat() if tweet.created_at else "",
                        "metadata": {
                            "original_tweet_id": tweet_id,
                            "is_reply": True
                        }
                    }
                    comments.append(comment_data)
            
            logger.info(f"Retrieved {len(comments)} replies to tweet {tweet_id}")
            return comments
            
        except Exception as e:
            logger.error(f"Failed to get tweet replies: {e}")
            return []
    
    def reply_to_tweet(self, tweet_id: str, reply_text: str) -> Dict:
        """Reply to a tweet (requires elevated access)"""
        if not self.client:
            return {
                "success": False,
                "error": "Twitter not configured"
            }
        
        try:
            # Note: This requires OAuth 1.0a User Context authentication
            # For read-only access, we can't post replies with just bearer token
            logger.warning("Twitter reply requires elevated access with OAuth 1.0a")
            return {
                "success": False,
                "error": "Twitter posting requires elevated API access"
            }
            
        except Exception as e:
            logger.error(f"Failed to reply to tweet: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_mentions(self, user_id: str, max_results: int = 100) -> List[Dict]:
        """Get mentions of a user"""
        if not self.client:
            return []
        
        try:
            mentions = self.client.get_users_mentions(
                id=user_id,
                max_results=min(max_results, 100),
                tweet_fields=['created_at', 'author_id', 'conversation_id'],
                user_fields=['username'],
                expansions=['author_id']
            )
            
            if not mentions.data:
                return []
            
            # Build user lookup
            users = {user.id: user.username for user in (mentions.includes.get('users', []) or [])}
            
            comments = []
            for tweet in mentions.data:
                comment_data = {
                    "platform": "twitter",
                    "platform_comment_id": str(tweet.id),
                    "content": tweet.text,
                    "author": users.get(tweet.author_id, "Unknown"),
                    "author_id": tweet.author_id,
                    "published_at": tweet.created_at.isoformat() if tweet.created_at else "",
                    "metadata": {
                        "is_mention": True,
                        "conversation_id": tweet.conversation_id
                    }
                }
                comments.append(comment_data)
            
            return comments
            
        except Exception as e:
            logger.error(f"Failed to get mentions: {e}")
            return []
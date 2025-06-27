"""
Background Task Scheduler for continuous comment fetching and processing
"""
import schedule
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.crud import crud_post, crud_comment, crud_reply, crud_settings, crud_analytics
from app.core.comment_processor import CommentProcessor
from app.integrations import (
    youtube, facebook, instagram, linkedin, twitter
)
from app.config import settings

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        """Initialize task scheduler"""
        self.running = False
        self.thread = None
        self.comment_processor = CommentProcessor()
        
        # Initialize integrations
        self.integrations = {
            "youtube": youtube.YouTubeIntegration(),
            "facebook": facebook.FacebookIntegration(),
            "instagram": instagram.InstagramIntegration(),
            "linkedin": linkedin.LinkedInIntegration(),
            "twitter": twitter.TwitterIntegration()
        }
        
        # Callbacks for real-time updates
        self.update_callbacks: List[Callable] = []
        
        # Track last fetch times
        self.last_fetch = {}
        
    def register_callback(self, callback: Callable):
        """Register callback for real-time updates"""
        self.update_callbacks.append(callback)
        
    def notify_update(self, update_type: str, data: Dict):
        """Notify all registered callbacks"""
        for callback in self.update_callbacks:
            try:
                callback(update_type, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("Task scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Task scheduler stopped")
    
    def _run(self):
        """Run the scheduler loop"""
        # Schedule tasks
        schedule.every(settings.fetch_interval).seconds.do(self.fetch_all_comments)
        schedule.every(60).seconds.do(self.process_pending_replies)
        schedule.every(300).seconds.do(self.update_analytics)
        
        # Initial fetch
        self.fetch_all_comments()
        
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def fetch_all_comments(self):
        """Fetch comments from all configured platforms"""
        logger.info("Starting scheduled comment fetch")
        
        db = SessionLocal()
        try:
            owner_active = crud_settings.get_owner_active(db)
            
            for platform, integration in self.integrations.items():
                if integration.is_configured():
                    try:
                        self._fetch_platform_data(db, platform, integration, owner_active)
                    except Exception as e:
                        logger.error(f"Error fetching {platform} data: {e}")
                        
        finally:
            db.close()
    
    def _fetch_platform_data(self, db: Session, platform: str, integration, owner_active: bool):
        """Fetch data for specific platform"""
        last_fetch_time = self.last_fetch.get(platform, datetime.utcnow() - timedelta(hours=1))
        new_posts = []
        new_comments = []
        
        # Fetch posts based on platform
        if platform == "youtube":
            # Get channel videos
            channel_id = "YOUR_CHANNEL_ID"  # Should be in config
            posts = integration.get_channel_videos(channel_id, max_results=10)
            new_posts.extend(posts)
            
            # Get comments for each video
            for post in posts:
                comments = integration.get_video_comments(post["platform_post_id"])
                new_comments.extend(comments)
                
        elif platform == "facebook":
            # Get page posts
            posts = integration.get_page_posts(limit=10)
            new_posts.extend(posts)
            
            # Get comments for each post
            for post in posts:
                comments = integration.get_post_comments(post["platform_post_id"])
                new_comments.extend(comments)
                
        elif platform == "instagram":
            # Get media posts
            posts = integration.get_media_posts(limit=10)
            new_posts.extend(posts)
            
            # Get comments for each post
            for post in posts:
                comments = integration.get_media_comments(post["platform_post_id"])
                new_comments.extend(comments)
                
        elif platform == "linkedin":
            # Get user posts
            posts = integration.get_user_posts(limit=10)
            new_posts.extend(posts)
            
            # Get comments for each post
            for post in posts:
                comments = integration.get_post_comments(post["platform_post_id"])
                new_comments.extend(comments)
                
        elif platform == "twitter":
            # Get user tweets
            username = "YOUR_USERNAME"  # Should be in config
            posts = integration.get_user_tweets(username, max_results=10)
            new_posts.extend(posts)
            
            # Get replies for each tweet
            for post in posts:
                replies = integration.get_tweet_replies(post["platform_post_id"])
                new_comments.extend(replies)
        
        # Save posts to database
        for post_data in new_posts:
            db_post = crud_post.create_or_update(db, post_data)
            post_data["id"] = db_post.id
        
        # Process new comments
        for comment_data in new_comments:
            # Find the post
            post = crud_post.get_by_platform_id(
                db, 
                comment_data["platform"], 
                comment_data.get("metadata", {}).get("post_id") or comment_data.get("metadata", {}).get("video_id") or comment_data.get("metadata", {}).get("media_id")
            )
            
            if post:
                comment_data["post_id"] = post.id
                
                # Check if comment is new
                existing = crud_comment.get_by_platform_id(
                    db,
                    comment_data["platform"],
                    comment_data["platform_comment_id"]
                )
                
                if not existing:
                    # Process new comment
                    result = self.comment_processor.process_comment(db, comment_data)
                    
                    # Notify dashboard of new comment
                    self.notify_update("new_comment", {
                        "comment": comment_data,
                        "processing_result": result
                    })
                    
                    # If owner inactive and auto-approved, post reply
                    if not owner_active and result.get("reply", {}).get("status") == "auto_approved":
                        self._post_reply(
                            db,
                            platform,
                            integration,
                            comment_data,
                            result["reply"]
                        )
        
        # Update last fetch time
        self.last_fetch[platform] = datetime.utcnow()
        
        # Log results
        logger.info(f"{platform}: Found {len(new_posts)} posts, {len(new_comments)} comments")
    
    def _post_reply(self, db: Session, platform: str, integration, 
                   comment_data: Dict, reply_data: Dict):
        """Post reply to platform"""
        try:
            reply_text = reply_data["content"]
            comment_id = comment_data["platform_comment_id"]
            
            # Post based on platform
            if platform == "youtube":
                result = integration.reply_to_comment(comment_id, reply_text)
            elif platform == "facebook":
                result = integration.reply_to_comment(comment_id, reply_text)
            elif platform == "instagram":
                result = integration.reply_to_comment(comment_id, reply_text)
            elif platform == "linkedin":
                post_urn = comment_data.get("metadata", {}).get("post_urn")
                result = integration.reply_to_comment(post_urn, reply_text, comment_id)
            elif platform == "twitter":
                result = integration.reply_to_tweet(comment_id, reply_text)
            else:
                result = {"success": False, "error": "Unknown platform"}
            
            if result.get("success"):
                # Update reply status
                crud_reply.mark_as_posted(
                    db,
                    reply_data["id"],
                    result.get("reply_id", "")
                )
                
                # Notify dashboard
                self.notify_update("reply_posted", {
                    "platform": platform,
                    "comment_id": comment_id,
                    "reply_id": result.get("reply_id")
                })
                
                logger.info(f"Successfully posted reply to {platform}")
            else:
                logger.error(f"Failed to post reply: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error posting reply: {e}")
    
    def process_pending_replies(self):
        """Process pending replies for auto-approval"""
        db = SessionLocal()
        try:
            owner_active = crud_settings.get_owner_active(db)
            
            if not owner_active:
                # Get pending replies
                pending = crud_reply.get_pending(db, limit=50)
                
                for reply in pending:
                    # Check if can auto-approve
                    if reply.confidence >= settings.auto_approve_confidence:
                        # Auto-approve
                        crud_reply.approve(db, reply.id, "ai_auto")
                        
                        # Get comment and platform info
                        comment = crud_comment.get(db, reply.comment_id)
                        if comment:
                            platform = comment.platform
                            integration = self.integrations.get(platform)
                            
                            if integration and integration.is_configured():
                                comment_data = {
                                    "platform_comment_id": comment.platform_comment_id,
                                    "metadata": comment.metadata
                                }
                                
                                reply_data = {
                                    "id": reply.id,
                                    "content": reply.content
                                }
                                
                                self._post_reply(
                                    db, platform, integration,
                                    comment_data, reply_data
                                )
                        
        finally:
            db.close()
    
    def update_analytics(self):
        """Update analytics metrics"""
        db = SessionLocal()
        try:
            # Record current metrics
            for platform in self.integrations.keys():
                # Count comments in last hour
                hour_ago = datetime.utcnow() - timedelta(hours=1)
                comment_count = db.query(crud_comment.model).filter(
                    crud_comment.model.platform == platform,
                    crud_comment.model.created_at >= hour_ago
                ).count()
                
                if comment_count > 0:
                    crud_analytics.record_metric(
                        db,
                        platform=platform,
                        metric_type="hourly_comments",
                        value=float(comment_count)
                    )
            
        finally:
            db.close()
"""
YouTube API Integration
"""
import googleapiclient.discovery
import googleapiclient.errors
from datetime import datetime
import logging
from typing import Dict, List, Optional
from config import settings

logger = logging.getLogger(__name__)

class YouTubeIntegration:
    def __init__(self):
        """Initialize YouTube API client"""
        self.api_key = settings.youtube_api_key
        self.youtube = None
        
        if self.api_key:
            try:
                self.youtube = googleapiclient.discovery.build(
                    "youtube", "v3", developerKey=self.api_key
                )
                logger.info("YouTube API client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API: {e}")
    
    def is_configured(self) -> bool:
        """Check if YouTube is configured"""
        return bool(self.youtube)
    
    def get_channel_videos(self, channel_id: str, max_results: int = 10) -> List[Dict]:
        """Get recent videos from channel"""
        if not self.youtube:
            return []
        
        try:
            # Get channel's uploads playlist
            channel_response = self.youtube.channels().list(
                part="contentDetails",
                id=channel_id
            ).execute()
            
            if not channel_response.get("items"):
                logger.warning(f"Channel not found: {channel_id}")
                return []
            
            uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # Get videos from uploads playlist
            playlist_response = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=max_results
            ).execute()
            
            videos = []
            for item in playlist_response.get("items", []):
                video_data = {
                    "platform": "youtube",
                    "platform_post_id": item["snippet"]["resourceId"]["videoId"],
                    "content": item["snippet"]["description"],
                    "title": item["snippet"]["title"],
                    "author": item["snippet"]["channelTitle"],
                    "url": f"https://youtube.com/watch?v={item['snippet']['resourceId']['videoId']}",
                    "media_type": "video",
                    "published_at": item["snippet"]["publishedAt"],
                    "metadata": {
                        "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
                        "channel_id": channel_id
                    }
                }
                videos.append(video_data)
            
            logger.info(f"Retrieved {len(videos)} videos from YouTube")
            return videos
            
        except Exception as e:
            logger.error(f"Failed to get YouTube videos: {e}")
            return []
    
    def get_video_comments(self, video_id: str, max_results: int = 100) -> List[Dict]:
        """Get comments for a video"""
        if not self.youtube:
            return []
        
        try:
            comments = []
            next_page_token = None
            
            while len(comments) < max_results:
                request = self.youtube.commentThreads().list(
                    part="snippet,replies",
                    videoId=video_id,
                    maxResults=min(100, max_results - len(comments)),
                    order="time",
                    pageToken=next_page_token
                )
                
                response = request.execute()
                
                for item in response.get("items", []):
                    # Process top-level comment
                    comment_data = self._parse_comment(item["snippet"]["topLevelComment"], video_id)
                    comments.append(comment_data)
                    
                    # Process replies
                    if "replies" in item:
                        for reply in item["replies"]["comments"]:
                            reply_data = self._parse_comment(reply, video_id, parent_id=item["id"])
                            comments.append(reply_data)
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break
            
            logger.info(f"Retrieved {len(comments)} comments for video {video_id}")
            return comments[:max_results]
            
        except googleapiclient.errors.HttpError as e:
            if e.resp.status == 403:
                logger.warning(f"Comments disabled for video {video_id}")
            else:
                logger.error(f"YouTube API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to get video comments: {e}")
            return []
    
    def _parse_comment(self, comment: Dict, video_id: str, parent_id: str = None) -> Dict:
        """Parse YouTube comment data"""
        snippet = comment["snippet"]
        
        return {
            "platform": "youtube",
            "platform_comment_id": comment["id"],
            "parent_comment_id": parent_id,
            "content": snippet["textDisplay"],
            "author": snippet["authorDisplayName"],
            "author_id": snippet.get("authorChannelId", {}).get("value"),
            "published_at": snippet["publishedAt"],
            "metadata": {
                "video_id": video_id,
                "like_count": snippet.get("likeCount", 0),
                "can_reply": snippet.get("canReply", True),
                "author_channel_url": snippet.get("authorChannelUrl")
            }
        }
    
    def reply_to_comment(self, comment_id: str, reply_text: str) -> Dict:
        """Reply to a YouTube comment"""
        if not self.youtube:
            return {
                "success": False,
                "error": "YouTube not configured"
            }
        
        try:
            response = self.youtube.comments().insert(
                part="snippet",
                body={
                    "snippet": {
                        "parentId": comment_id,
                        "textOriginal": reply_text
                    }
                }
            ).execute()
            
            logger.info(f"Successfully replied to YouTube comment {comment_id}")
            return {
                "success": True,
                "reply_id": response["id"],
                "message": "Reply posted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to reply to YouTube comment: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """Get channel information"""
        if not self.youtube:
            return None
        
        try:
            response = self.youtube.channels().list(
                part="snippet,statistics",
                id=channel_id
            ).execute()
            
            if response.get("items"):
                channel = response["items"][0]
                return {
                    "id": channel["id"],
                    "title": channel["snippet"]["title"],
                    "description": channel["snippet"]["description"],
                    "subscriber_count": channel["statistics"].get("subscriberCount"),
                    "video_count": channel["statistics"].get("videoCount"),
                    "view_count": channel["statistics"].get("viewCount")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            return None
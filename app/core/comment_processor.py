"""
Comment Processor - Main workflow for processing comments
"""
from typing import Dict, List, Optional
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from core.ai_processor import AIProcessor
from core.ghl_manager import GHLManager
from database.crud import crud_comment, crud_reply, crud_post, crud_analytics, crud_settings
from database.models import Comment, Reply
from config import settings

logger = logging.getLogger(__name__)

class CommentProcessor:
    def __init__(self):
        """Initialize comment processor"""
        self.ai = AIProcessor()
        self.ghl = GHLManager()
        
    def process_comment(self, db: Session, comment_data: Dict) -> Dict:
        """Main workflow to process incoming comment"""
        try:
            # Extract comment info
            platform = comment_data["platform"]
            comment_text = comment_data["content"]
            author = comment_data.get("author", "Unknown")
            post_id = comment_data.get("post_id")
            
            # Get post context if available
            post_context = None
            if post_id:
                post = crud_post.get(db, post_id)
                if post:
                    post_context = f"{post.content[:100]}..." if post.content else None
            
            # Step 1: Classify comment
            comment_type, classification_meta = self.ai.classify_comment(comment_text, platform)
            
            # Update comment data with classification
            comment_data["comment_type"] = comment_type
            comment_data["confidence"] = classification_meta.get("confidence", 0.5)
            comment_data["metadata"] = {
                **comment_data.get("metadata", {}),
                "classification": classification_meta
            }
            
            # Save/update comment in database
            db_comment = crud_comment.create_or_update(db, comment_data)
            
            # Step 2: Generate AI reply
            reply_result = self.ai.generate_reply(
                comment_text=comment_text,
                comment_type=comment_type,
                platform=platform,
                post_context=post_context,
                author_name=author
            )
            
            # Step 3: Analyze sentiment
            sentiment = self.ai.analyze_sentiment(comment_text)
            
            # Update comment with sentiment
            crud_comment.update(db, db_comment.id, {
                "sentiment": sentiment["sentiment"],
                "metadata": {
                    **db_comment.metadata,
                    "sentiment_analysis": sentiment
                }
            })
            
            # Step 4: Create reply record
            reply_data = {
                "comment_id": db_comment.id,
                "content": reply_result["reply"],
                "status": "pending" if reply_result["needs_approval"] else "auto_approved",
                "reply_type": "ai",
                "confidence": reply_result["confidence"],
                "ghl_triggers": reply_result.get("triggers", {})
            }
            
            db_reply = crud_reply.create(db, reply_data)
            
            # Step 5: Handle GHL integration if needed
            ghl_result = None
            if reply_result.get("triggers", {}).get("workflows"):
                ghl_result = self._process_ghl_actions(
                    db=db,
                    comment=db_comment,
                    triggers=reply_result["triggers"],
                    sentiment=sentiment
                )
            
            # Step 6: Auto-post if approved and owner inactive
            posted = False
            if not reply_result["needs_approval"] and not crud_settings.get_owner_active(db):
                # Auto-post logic will be handled by scheduler
                posted = True
                logger.info(f"Reply auto-approved for comment {db_comment.id}")
            
            # Record analytics
            crud_analytics.record_metric(
                db=db,
                platform=platform,
                metric_type="comment_processed",
                value=1.0,
                metadata={
                    "comment_type": comment_type,
                    "auto_approved": not reply_result["needs_approval"]
                }
            )
            
            return {
                "success": True,
                "comment": {
                    "id": db_comment.id,
                    "type": comment_type,
                    "sentiment": sentiment["sentiment"]
                },
                "reply": {
                    "id": db_reply.id,
                    "content": reply_result["reply"],
                    "status": db_reply.status,
                    "confidence": reply_result["confidence"]
                },
                "ghl": ghl_result,
                "auto_posted": posted
            }
            
        except Exception as e:
            logger.error(f"Comment processing failed: {e}", exc_info=True)
            
            # Record failure
            crud_analytics.record_metric(
                db=db,
                platform=comment_data.get("platform", "unknown"),
                metric_type="processing_error",
                value=1.0,
                metadata={"error": str(e)}
            )
            
            return {
                "success": False,
                "error": str(e),
                "comment_id": comment_data.get("platform_comment_id")
            }
    
    def _process_ghl_actions(self, db: Session, comment: Comment, 
                           triggers: Dict, sentiment: Dict) -> Dict:
        """Process GoHighLevel actions"""
        try:
            # Prepare contact data
            contact_data = {
                "name": comment.author or "Social Media Contact",
                "platform": comment.platform,
                "tags": triggers.get("tags", []),
                "custom_fields": {
                    "comment_text": comment.content,
                    "comment_type": comment.comment_type,
                    "sentiment": sentiment["sentiment"],
                    "platform_id": comment.platform_comment_id
                }
            }
            
            # Create/update contact
            contact_result = self.ghl.create_or_update_contact(contact_data)
            
            if contact_result["success"]:
                # Trigger workflows
                workflow_results = []
                for workflow in triggers.get("workflows", []):
                    result = self.ghl.trigger_workflow(
                        workflow_name=workflow,
                        contact_id=contact_result["contact_id"],
                        trigger_data={
                            "source": "social_media_comment",
                            "platform": comment.platform,
                            "comment_type": comment.comment_type
                        }
                    )
                    workflow_results.append(result)
                
                # Record GHL actions in database
                from app.database.crud import crud_ghl
                for tag in triggers.get("tags", []):
                    crud_ghl.create(db, {
                        "comment_id": comment.id,
                        "action_type": "tag_added",
                        "contact_id": contact_result["contact_id"],
                        "tags": [tag],
                        "status": "executed",
                        "executed_at": datetime.utcnow()
                    })
                
                return {
                    "success": True,
                    "contact_id": contact_result["contact_id"],
                    "workflows_triggered": len(workflow_results),
                    "tags_added": len(triggers.get("tags", []))
                }
            
            return {
                "success": False,
                "error": contact_result.get("error", "Unknown error")
            }
            
        except Exception as e:
            logger.error(f"GHL processing failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_batch(self, db: Session, comments: List[Dict]) -> Dict:
        """Process multiple comments in batch"""
        results = {
            "processed": 0,
            "failed": 0,
            "auto_approved": 0,
            "results": []
        }
        
        for comment in comments:
            try:
                result = self.process_comment(db, comment)
                results["results"].append(result)
                
                if result["success"]:
                    results["processed"] += 1
                    if result.get("auto_posted"):
                        results["auto_approved"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                results["failed"] += 1
                results["results"].append({
                    "success": False,
                    "error": str(e),
                    "comment": comment
                })
        
        return results
    
    def approve_reply(self, db: Session, reply_id: int, approved_by: str = "manual") -> bool:
        """Approve a pending reply"""
        try:
            reply = crud_reply.approve(db, reply_id, approved_by)
            if reply:
                # Mark comment as replied
                crud_comment.mark_as_replied(db, reply.comment_id)
                
                # Record metric
                crud_analytics.record_metric(
                    db=db,
                    platform="system",
                    metric_type="reply_approved",
                    value=1.0,
                    metadata={"approved_by": approved_by}
                )
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Reply approval failed: {e}")
            return False
    
    def reject_reply(self, db: Session, reply_id: int) -> bool:
        """Reject a pending reply"""
        try:
            reply = crud_reply.reject(db, reply_id)
            if reply:
                # Record metric
                crud_analytics.record_metric(
                    db=db,
                    platform="system",
                    metric_type="reply_rejected",
                    value=1.0
                )
                return True
            return False
            
        except Exception as e:
            logger.error(f"Reply rejection failed: {e}")
            return False
    
    def bulk_approve_replies(self, db: Session, reply_ids: List[int]) -> Dict:
        """Bulk approve multiple replies"""
        results = {
            "approved": 0,
            "failed": 0
        }
        
        for reply_id in reply_ids:
            if self.approve_reply(db, reply_id, "bulk_manual"):
                results["approved"] += 1
            else:
                results["failed"] += 1
        
        return results
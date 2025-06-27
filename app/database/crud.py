"""
CRUD operations for database models
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import models
import json

class CRUDBase:
    """Base CRUD operations"""
    def __init__(self, model):
        self.model = model
    
    def get(self, db: Session, id: int):
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, db: Session, obj_in: Dict):
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(self, db: Session, id: int, obj_in: Dict):
        db_obj = self.get(db, id)
        if db_obj:
            for field, value in obj_in.items():
                setattr(db_obj, field, value)
            db.commit()
            db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, id: int):
        db_obj = self.get(db, id)
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj

class CRUDPost(CRUDBase):
    """CRUD operations for posts"""
    
    def get_by_platform_id(self, db: Session, platform: str, platform_post_id: str):
        return db.query(models.Post).filter(
            and_(
                models.Post.platform == platform,
                models.Post.platform_post_id == platform_post_id
            )
        ).first()
    
    def get_recent(self, db: Session, platform: str = None, limit: int = 50):
        query = db.query(models.Post)
        if platform:
            query = query.filter(models.Post.platform == platform)
        return query.order_by(desc(models.Post.published_at)).limit(limit).all()
    
    def create_or_update(self, db: Session, post_data: Dict):
        existing = self.get_by_platform_id(
            db, 
            post_data["platform"], 
            post_data["platform_post_id"]
        )
        if existing:
            return self.update(db, existing.id, post_data)
        return self.create(db, post_data)

class CRUDComment(CRUDBase):
    """CRUD operations for comments"""
    
    def get_by_platform_id(self, db: Session, platform: str, platform_comment_id: str):
        return db.query(models.Comment).filter(
            and_(
                models.Comment.platform == platform,
                models.Comment.platform_comment_id == platform_comment_id
            )
        ).first()
    
    def get_pending(self, db: Session, limit: int = 50):
        """Get comments without replies"""
        return db.query(models.Comment).filter(
            models.Comment.has_reply == False
        ).order_by(desc(models.Comment.created_at)).limit(limit).all()
    
    def get_filtered(self, db: Session, platforms: List[str] = None, 
                    comment_types: List[str] = None, time_range: tuple = None, 
                    limit: int = 50):
        """Get comments with filters"""
        query = db.query(models.Comment)
        
        if platforms:
            query = query.filter(models.Comment.platform.in_(platforms))
        
        if comment_types:
            query = query.filter(models.Comment.comment_type.in_(comment_types))
        
        if time_range and len(time_range) == 2:
            query = query.filter(
                and_(
                    models.Comment.created_at >= time_range[0],
                    models.Comment.created_at <= time_range[1]
                )
            )
        
        return query.order_by(desc(models.Comment.created_at)).limit(limit).all()
    
    def create_or_update(self, db: Session, comment_data: Dict):
        existing = self.get_by_platform_id(
            db,
            comment_data["platform"],
            comment_data["platform_comment_id"]
        )
        if existing:
            return self.update(db, existing.id, comment_data)
        return self.create(db, comment_data)
    
    def mark_as_replied(self, db: Session, comment_id: int):
        return self.update(db, comment_id, {"has_reply": True})

class CRUDReply(CRUDBase):
    """CRUD operations for replies"""
    
    def get_pending(self, db: Session, limit: int = 50):
        return db.query(models.Reply).filter(
            models.Reply.status == "pending"
        ).order_by(desc(models.Reply.created_at)).limit(limit).all()
    
    def get_by_comment(self, db: Session, comment_id: int):
        return db.query(models.Reply).filter(
            models.Reply.comment_id == comment_id
        ).all()
    
    def approve(self, db: Session, reply_id: int, approved_by: str = "manual"):
        return self.update(db, reply_id, {
            "status": "approved",
            "approved_at": datetime.utcnow(),
            "approved_by": approved_by
        })
    
    def reject(self, db: Session, reply_id: int):
        return self.update(db, reply_id, {"status": "rejected"})
    
    def mark_as_posted(self, db: Session, reply_id: int, platform_reply_id: str):
        return self.update(db, reply_id, {
            "status": "posted",
            "platform_reply_id": platform_reply_id,
            "posted_at": datetime.utcnow()
        })

class CRUDSettings(CRUDBase):
    """CRUD operations for settings"""
    
    def get_by_key(self, db: Session, key: str):
        return db.query(models.Settings).filter(
            models.Settings.key == key
        ).first()
    
    def get_value(self, db: Session, key: str, default=None):
        setting = self.get_by_key(db, key)
        return setting.value if setting else default
    
    def set_value(self, db: Session, key: str, value: str, description: str = None):
        setting = self.get_by_key(db, key)
        if setting:
            return self.update(db, setting.id, {"value": value})
        return self.create(db, {
            "key": key,
            "value": value,
            "description": description
        })
    
    def get_owner_active(self, db: Session) -> bool:
        value = self.get_value(db, "owner_active", "false")
        return value.lower() == "true"
    
    def set_owner_active(self, db: Session, active: bool):
        return self.set_value(db, "owner_active", str(active).lower())

class CRUDAnalytics(CRUDBase):
    """CRUD operations for analytics"""
    
    def get_summary(self, db: Session, start_date: datetime = None, end_date: datetime = None):
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Get comment stats
        total_comments = db.query(models.Comment).filter(
            and_(
                models.Comment.created_at >= start_date,
                models.Comment.created_at <= end_date
            )
        ).count()
        
        # Get reply stats
        total_replies = db.query(models.Reply).filter(
            and_(
                models.Reply.created_at >= start_date,
                models.Reply.created_at <= end_date,
                models.Reply.status == "posted"
            )
        ).count()
        
        # Calculate response rate
        response_rate = (total_replies / total_comments * 100) if total_comments > 0 else 0
        
        # Platform breakdown
        platform_stats = {}
        for platform in ["youtube", "facebook", "instagram", "linkedin", "twitter"]:
            count = db.query(models.Comment).filter(
                and_(
                    models.Comment.platform == platform,
                    models.Comment.created_at >= start_date,
                    models.Comment.created_at <= end_date
                )
            ).count()
            if count > 0:
                platform_stats[platform] = count
        
        # Comment type breakdown
        type_stats = {}
        for comment_type in ["lead", "praise", "question", "complaint", "spam", "general"]:
            count = db.query(models.Comment).filter(
                and_(
                    models.Comment.comment_type == comment_type,
                    models.Comment.created_at >= start_date,
                    models.Comment.created_at <= end_date
                )
            ).count()
            if count > 0:
                type_stats[comment_type] = count
        
        return {
            "total_comments": total_comments,
            "total_replies": total_replies,
            "response_rate": response_rate,
            "platform_breakdown": platform_stats,
            "comment_types": type_stats,
            "avg_response_time": 0,  # TODO: Calculate actual response time
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
    
    def record_metric(self, db: Session, platform: str, metric_type: str, value: float, metadata: Dict = None):
        return self.create(db, {
            "date": datetime.utcnow(),
            "platform": platform,
            "metric_type": metric_type,
            "value": value,
            "metadata": metadata or {}
        })

class CRUDGeneratedContent(CRUDBase):
    """CRUD operations for generated content"""
    
    def get_by_type(self, db: Session, content_type: str, status: str = None, limit: int = 50):
        query = db.query(models.GeneratedContent).filter(
            models.GeneratedContent.content_type == content_type
        )
        if status:
            query = query.filter(models.GeneratedContent.status == status)
        return query.order_by(desc(models.GeneratedContent.created_at)).limit(limit).all()
    
    def get_drafts(self, db: Session, limit: int = 50):
        return db.query(models.GeneratedContent).filter(
            models.GeneratedContent.status == "draft"
        ).order_by(desc(models.GeneratedContent.created_at)).limit(limit).all()

class CRUDGHLAction(CRUDBase):
    """CRUD operations for GHL actions"""
    
    def get_pending(self, db: Session, limit: int = 50):
        return db.query(models.GHLAction).filter(
            models.GHLAction.status == "pending"
        ).order_by(desc(models.GHLAction.created_at)).limit(limit).all()
    
    def mark_executed(self, db: Session, action_id: int, response_data: Dict):
        return self.update(db, action_id, {
            "status": "executed",
            "executed_at": datetime.utcnow(),
            "response_data": response_data
        })
    
    def get_by_comment(self, db: Session, comment_id: int):
        return db.query(models.GHLAction).filter(
            models.GHLAction.comment_id == comment_id
        ).all()

# Create instances
crud_post = CRUDPost(models.Post)
crud_comment = CRUDComment(models.Comment)
crud_reply = CRUDReply(models.Reply)
crud_settings = CRUDSettings(models.Settings)
crud_analytics = CRUDAnalytics(models.Analytics)
crud_content = CRUDGeneratedContent(models.GeneratedContent)
crud_ghl = CRUDGHLAction(models.GHLAction)
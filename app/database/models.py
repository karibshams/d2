"""
SQLAlchemy database models
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float, JSON, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Post(Base):
    """Social media posts"""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False, index=True)
    platform_post_id = Column(String(255), nullable=False)
    content = Column(Text)
    author = Column(String(255))
    url = Column(Text)
    media_type = Column(String(50))  # video, image, text
    post_metadata = Column(JSON) # Store platform-specific data
    published_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    
    # Unique constraint
    __table_args__ = (
        {'postgresql_on_conflict': 'platform, platform_post_id'},
    )

class Comment(Base):
    """Comments on social media posts"""
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    platform = Column(String(50), nullable=False, index=True)
    platform_comment_id = Column(String(255), nullable=False)
    parent_comment_id = Column(String(255))  # For nested replies
    author = Column(String(255))
    author_id = Column(String(255))
    content = Column(Text, nullable=False)
    comment_type = Column(String(50), index=True)  # lead, praise, question, etc.
    sentiment = Column(String(50))  # positive, negative, neutral
    confidence = Column(Float)
    extra_data = Column(JSON)  # Platform-specific data
    published_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    has_reply = Column(Boolean, default=False)
    
    # Relationships
    post = relationship("Post", back_populates="comments")
    replies = relationship("Reply", back_populates="comment", cascade="all, delete-orphan")
    ghl_actions = relationship("GHLAction", back_populates="comment")

class Reply(Base):
    """AI-generated or manual replies"""
    __tablename__ = "replies"
    
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), default="pending", index=True)  # pending, approved, rejected, posted
    reply_type = Column(String(50), default="ai")  # ai, manual
    platform_reply_id = Column(String(255))  # ID after posting
    confidence = Column(Float)
    ghl_triggers = Column(JSON)  # Detected triggers
    posted_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    approved_at = Column(DateTime)
    approved_by = Column(String(50))  # ai_auto, manual
    
    # Relationships
    comment = relationship("Comment", back_populates="replies")

class GHLAction(Base):
    """GoHighLevel integration actions"""
    __tablename__ = "ghl_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=False)
    action_type = Column(String(50))  # contact_created, tag_added, workflow_triggered
    contact_id = Column(String(255))
    tags = Column(JSON)
    workflow_name = Column(String(255))
    status = Column(String(50), default="pending")
    response_data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    executed_at = Column(DateTime)
    
    # Relationships
    comment = relationship("Comment", back_populates="ghl_actions")

class GeneratedContent(Base):
    """AI-generated content for posting"""
    __tablename__ = "generated_content"
    
    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String(50), nullable=False)  # caption, devotional, etc.
    topic = Column(String(255))
    series = Column(String(255))
    content = Column(Text, nullable=False)
    hashtags = Column(JSON)
    status = Column(String(50), default="draft")  # draft, scheduled, posted
    extra_data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    scheduled_for = Column(DateTime)
    posted_at = Column(DateTime)

class Settings(Base):
    """Application settings"""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime, onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())

class Analytics(Base):
    """Analytics and metrics"""
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    platform = Column(String(50), index=True)
    metric_type = Column(String(100))  # comments_received, replies_sent, etc.
    value = Column(Float)
    extra_data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
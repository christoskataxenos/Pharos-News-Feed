from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Index, Float
from sqlalchemy.orm import relationship
from database import Base

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    
    feeds = relationship('Feed', back_populates='category', cascade="all, delete-orphan")

class Feed(Base):
    __tablename__ = 'feeds'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    url = Column(String(200), nullable=False, unique=True)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete="CASCADE"), nullable=False)
    is_favorite = Column(Boolean, default=False)
    type = Column(String(20), default='article')  # 'article' or 'video'
    last_fetched = Column(DateTime, nullable=True)
    
    category = relationship('Category', back_populates='feeds')
    articles = relationship('Article', back_populates='feed', cascade="all, delete-orphan")

class Article(Base):
    __tablename__ = 'articles'
    __table_args__ = (
        Index('ix_feed_published', 'feed_id', 'published'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey('feeds.id', ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    link = Column(String(255), nullable=False, unique=True)
    published = Column(DateTime, index=True, default=datetime.utcnow)
    summary = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    quality_score = Column(Float, default=1.0, index=True)
    filter_flags = Column(String(500), nullable=True)
    is_filtered = Column(Boolean, default=False, index=True)
    
    feed = relationship('Feed', back_populates='articles')
    interactions = relationship('UserInteraction', back_populates='article', cascade="all, delete-orphan")

class UserInteraction(Base):
    __tablename__ = 'user_interactions'
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey('articles.id', ondelete="CASCADE"), nullable=False)
    interaction_type = Column(String(20)) # 'read', 'favorite'
    timestamp = Column(DateTime, default=datetime.utcnow)

    article = relationship('Article', back_populates='interactions')

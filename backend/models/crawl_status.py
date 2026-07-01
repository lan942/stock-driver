from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from backend.utils.db import Base


class CrawlStatus(Base):
    """爬取状态记录模型"""
    __tablename__ = 'crawl_status'

    id = Column(Integer, primary_key=True, index=True)
    crawl_type = Column(String(20), nullable=False)  # 'list' or 'realtime'
    status = Column(String(20), nullable=False)  # 'success', 'partial', 'failed'
    crawl_time = Column(DateTime, nullable=False, server_default=func.now())
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    error_message = Column(Text)  # 仅失败时记录
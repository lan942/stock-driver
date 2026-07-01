from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text
from sqlalchemy.sql import func
from backend.utils.db import Base

class Stock(Base):
    __tablename__ = 'stocks'
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    industry = Column(String(100))
    sector = Column(String(100))
    price = Column(Float)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    change_percent = Column(Float)
    volume = Column(Float)
    turnover = Column(Float)
    turnover_rate = Column(Float)
    pe = Column(Float)
    pb = Column(Float)
    market_cap = Column(Float)
    price_date = Column(Date)  # 价格数据日期（不含时间）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class StockDaily(Base):
    __tablename__ = 'stock_daily'
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), index=True, nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    turnover = Column(Float)
    turnover_rate = Column(Float)
    change_percent = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

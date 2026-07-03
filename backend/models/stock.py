from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from backend.utils.db import Base


class Stock(Base):
    """股票基本信息（行情数据见 StockDaily）"""

    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    industry = Column(String(100))
    sector = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StockDaily(Base):
    """每日行情数据"""

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
    pe = Column(Float)
    pb = Column(Float)
    market_cap = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('code', 'date', name='uq_stock_daily_code_date'),
        {'sqlite_autoincrement': True},
    )

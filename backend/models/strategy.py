"""策略模块数据模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from backend.utils.db import Base


class StrategyCash(Base):
    """策略现金余额模型"""

    __tablename__ = 'strategy_cash'

    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Float, nullable=False, default=0.0)
    initial_capital = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StrategyConfig(Base):
    """策略配置模型"""

    __tablename__ = 'strategy_config'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(String(500), nullable=False)
    description = Column(String(200))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from backend.utils.db import Base


class Portfolio(Base):
    """持仓模型"""

    __tablename__ = 'portfolio'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    cost_price = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('code', name='uq_portfolio_code'),
        {'sqlite_autoincrement': True},
    )


class Transaction(Base):
    """交易记录模型"""

    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(10), nullable=False)
    code = Column(String(20), index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class CashBalance(Base):
    """现金余额模型"""

    __tablename__ = 'cash_balance'

    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
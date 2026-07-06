"""save_daily_batch 单元测试：重点覆盖单日补爬时 change_percent 从 DB 补全。"""
import os
import sys
import unittest
from datetime import date
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.stock import Stock, StockDaily
from backend.utils.db import Base
from backend.services import stock_service


def _make_in_memory_db():
    """构建内存 SQLite 会话，并建表。返回 SessionLocal 工厂。"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestSaveDailyBatchChangePercent(unittest.TestCase):
    def setUp(self):
        self.SessionLocal = _make_in_memory_db()

        def _fake_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        # patch stock_service 模块内引用的 get_db
        self._patcher = patch.object(stock_service, "get_db", _fake_get_db)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def _seed_stock(self, code: str, name: str):
        db = self.SessionLocal()
        db.add(Stock(code=code, name=name))
        db.commit()
        db.close()

    def _seed_prev_daily(self, code: str, prev_date: date, close: float):
        db = self.SessionLocal()
        db.add(StockDaily(code=code, date=prev_date, close=close))
        db.commit()
        db.close()

    def test_single_day_backfill_from_db_prev_close(self):
        """单日补爬、df 内 change_percent 为 None 时，从 DB 上一交易日 close 补全。"""
        code = "000001"
        self._seed_stock(code, "平安银行")
        self._seed_prev_daily(code, date(2026, 7, 3), close=10.0)

        df = pd.DataFrame([{
            "code": code,
            "date": date(2026, 7, 6),
            "open": 10.2, "high": 10.5, "low": 10.1,
            "close": 11.0,
            "volume": 1000.0, "turnover": 11000.0,
            "turnover_rate": 1.0,
            "change_percent": None,
            "pe": None, "pb": None, "market_cap": None,
        }])

        success, fail, added, updated = stock_service.save_daily_batch([df])
        self.assertEqual((success, fail, added, updated), (1, 0, 1, 0))

        db = self.SessionLocal()
        row = db.query(StockDaily).filter(
            StockDaily.code == code, StockDaily.date == date(2026, 7, 6)
        ).first()
        db.close()
        self.assertIsNotNone(row)
        self.assertEqual(row.close, 11.0)
        # (11.0 - 10.0) / 10.0 * 100 = 10.0
        self.assertEqual(row.change_percent, 10.0)

    def test_no_prev_close_keeps_none(self):
        """DB 内没有上一交易日 close 时（如新股首日），change_percent 保持 None。"""
        code = "300001"
        self._seed_stock(code, "新股")

        df = pd.DataFrame([{
            "code": code,
            "date": date(2026, 7, 6),
            "open": 10.0, "high": 11.0, "low": 9.5,
            "close": 10.5,
            "volume": 1000.0, "turnover": 10500.0,
            "turnover_rate": 1.0,
            "change_percent": None,
            "pe": None, "pb": None, "market_cap": None,
        }])

        success, fail, added, updated = stock_service.save_daily_batch([df])
        self.assertEqual((success, fail, added, updated), (1, 0, 1, 0))

        db = self.SessionLocal()
        row = db.query(StockDaily).filter(
            StockDaily.code == code, StockDaily.date == date(2026, 7, 6)
        ).first()
        db.close()
        self.assertIsNotNone(row)
        self.assertIsNone(row.change_percent)

    def test_multi_day_batch_uses_in_batch_prev_close(self):
        """同批次多日数据：首日从 DB 取 prev_close，次日复用同批次 close。"""
        code = "000002"
        self._seed_stock(code, "万科A")
        self._seed_prev_daily(code, date(2026, 7, 3), close=10.0)

        df = pd.DataFrame([
            {
                "code": code, "date": date(2026, 7, 6),
                "open": 10.0, "high": 11.0, "low": 9.5, "close": 11.0,
                "volume": 1000.0, "turnover": 11000.0, "turnover_rate": 1.0,
                "change_percent": None, "pe": None, "pb": None, "market_cap": None,
            },
            {
                "code": code, "date": date(2026, 7, 7),
                "open": 11.0, "high": 12.0, "low": 10.8, "close": 12.0,
                "volume": 2000.0, "turnover": 24000.0, "turnover_rate": 2.0,
                "change_percent": None, "pe": None, "pb": None, "market_cap": None,
            },
        ])

        success, fail, added, updated = stock_service.save_daily_batch([df])
        self.assertEqual((success, fail, added, updated), (1, 0, 2, 0))

        db = self.SessionLocal()
        d6 = db.query(StockDaily).filter(
            StockDaily.code == code, StockDaily.date == date(2026, 7, 6)
        ).first()
        d7 = db.query(StockDaily).filter(
            StockDaily.code == code, StockDaily.date == date(2026, 7, 7)
        ).first()
        db.close()
        # 7-6: (11 - 10) / 10 * 100 = 10.0
        self.assertEqual(d6.change_percent, 10.0)
        # 7-7: (12 - 11) / 11 * 100 ≈ 9.0909
        self.assertEqual(d7.change_percent, round((12 - 11) / 11 * 100, 4))

    def test_existing_change_percent_not_overwritten_by_none(self):
        """已有 change_percent 的记录：df 里为 None 时不应被覆盖为 None。"""
        code = "000003"
        self._seed_stock(code, "测试股")
        # DB 里已有 7-6 记录，change_percent=5.0
        db = self.SessionLocal()
        db.add(StockDaily(
            code=code, date=date(2026, 7, 6),
            close=10.0, change_percent=5.0,
        ))
        db.commit()
        db.close()
        # 但前一日 close 不可用（5.0 是历史值），新的 df 又传 None
        # 我们要保证不会被 None 覆盖
        df = pd.DataFrame([{
            "code": code, "date": date(2026, 7, 6),
            "open": 10.0, "high": 10.5, "low": 9.5, "close": 10.5,
            "volume": 1000.0, "turnover": 10500.0, "turnover_rate": 1.0,
            "change_percent": None, "pe": None, "pb": None, "market_cap": None,
        }])

        success, _, added, updated = stock_service.save_daily_batch([df])
        self.assertEqual((success, added, updated), (1, 0, 1))

        db = self.SessionLocal()
        row = db.query(StockDaily).filter(
            StockDaily.code == code, StockDaily.date == date(2026, 7, 6)
        ).first()
        db.close()
        # 没有 prev_close 时算不出来，但也不应覆盖已有的 5.0
        self.assertEqual(row.change_percent, 5.0)


if __name__ == "__main__":
    unittest.main()

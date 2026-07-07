from backend.models.stock import Stock, StockDaily
from sqlalchemy import func


class StockAnalysis:
    @staticmethod
    def get_top_gainers(db, limit=10, query_date=None):
        """涨幅榜：按指定日期从 StockDaily 表查询 change_percent 降序 Top N。

        Args:
            db: SQLAlchemy 会话
            limit: 返回条数上限
            query_date: 查询日期，None 时自动取 stock_daily 表最新日期

        Returns:
            (rows, used_date): rows 为 (StockDaily, stock_name) 元组列表；
            used_date 为实际使用的日期（None 表示表无数据，rows 为空）
        """
        if query_date is None:
            query_date = db.query(func.max(StockDaily.date)).scalar()
            if query_date is None:
                return [], None
        rows = db.query(StockDaily, Stock.name).outerjoin(
            Stock, StockDaily.code == Stock.code
        ).filter(
            StockDaily.date == query_date,
            StockDaily.change_percent.isnot(None)
        ).order_by(StockDaily.change_percent.desc()).limit(limit).all()
        return rows, query_date

    @staticmethod
    def get_top_losers(db, limit=10, query_date=None):
        """跌幅榜：按指定日期从 StockDaily 表查询 change_percent 升序 Top N。

        Args:
            db: SQLAlchemy 会话
            limit: 返回条数上限
            query_date: 查询日期，None 时自动取 stock_daily 表最新日期

        Returns:
            (rows, used_date): 同 get_top_gainers
        """
        if query_date is None:
            query_date = db.query(func.max(StockDaily.date)).scalar()
            if query_date is None:
                return [], None
        rows = db.query(StockDaily, Stock.name).outerjoin(
            Stock, StockDaily.code == Stock.code
        ).filter(
            StockDaily.date == query_date,
            StockDaily.change_percent.isnot(None)
        ).order_by(StockDaily.change_percent.asc()).limit(limit).all()
        return rows, query_date

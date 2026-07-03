import pandas as pd
from backend.models.stock import Stock, StockDaily
from sqlalchemy import func


class StockAnalysis:
    @staticmethod
    def calculate_ma(data, period):
        data[f'ma{period}'] = data['close'].rolling(window=period).mean()
        return data

    @staticmethod
    def calculate_macd(data):
        data['ema12'] = data['close'].ewm(span=12, adjust=False).mean()
        data['ema26'] = data['close'].ewm(span=26, adjust=False).mean()
        data['macd'] = data['ema12'] - data['ema26']
        data['signal'] = data['macd'].ewm(span=9, adjust=False).mean()
        data['histogram'] = data['macd'] - data['signal']
        return data

    @staticmethod
    def calculate_rsi(data, period=14):
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        data['rsi'] = 100 - (100 / (1 + rs))
        return data

    @staticmethod
    def get_stock_analysis(db, code, days=60):
        daily_data = db.query(StockDaily).filter(
            StockDaily.code == code
        ).order_by(StockDaily.date.desc()).limit(days).all()

        if not daily_data:
            return None

        data = []
        for item in daily_data:
            data.append({
                'date': item.date.strftime('%Y-%m-%d'),
                'open': item.open,
                'high': item.high,
                'low': item.low,
                'close': item.close,
                'volume': item.volume,
                'change_percent': item.change_percent
            })

        df = pd.DataFrame(data)
        df = df.sort_values('date')

        df = StockAnalysis.calculate_ma(df, 5)
        df = StockAnalysis.calculate_ma(df, 10)
        df = StockAnalysis.calculate_ma(df, 20)
        df = StockAnalysis.calculate_ma(df, 60)
        df = StockAnalysis.calculate_macd(df)
        df = StockAnalysis.calculate_rsi(df)

        return df.to_dict('records')

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

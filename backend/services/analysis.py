import pandas as pd
import numpy as np
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
    def filter_stocks(db, filters):
        query = db.query(Stock)
        
        if 'name' in filters and filters['name']:
            query = query.filter(Stock.name.like(f'%{filters["name"]}%'))
        
        if 'code' in filters and filters['code']:
            query = query.filter(Stock.code.like(f'%{filters["code"]}%'))
        
        if 'industry' in filters and filters['industry']:
            query = query.filter(Stock.industry.like(f'%{filters["industry"]}%'))
        
        if 'min_price' in filters and filters['min_price']:
            query = query.filter(Stock.price >= filters['min_price'])
        
        if 'max_price' in filters and filters['max_price']:
            query = query.filter(Stock.price <= filters['max_price'])
        
        if 'min_market_cap' in filters and filters['min_market_cap']:
            query = query.filter(Stock.market_cap >= filters['min_market_cap'])
        
        if 'max_market_cap' in filters and filters['max_market_cap']:
            query = query.filter(Stock.market_cap <= filters['max_market_cap'])
        
        return query.all()
    
    @staticmethod
    def get_top_gainers(db, limit=10):
        stocks = db.query(Stock).filter(
            Stock.change_percent.isnot(None)
        ).order_by(Stock.change_percent.desc()).limit(limit).all()
        return stocks
    
    @staticmethod
    def get_top_losers(db, limit=10):
        stocks = db.query(Stock).filter(
            Stock.change_percent.isnot(None)
        ).order_by(Stock.change_percent.asc()).limit(limit).all()
        return stocks

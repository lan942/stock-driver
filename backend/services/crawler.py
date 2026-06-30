import akshare as ak
import pandas as pd
from datetime import datetime
from backend.models.stock import Stock, StockDaily, StockFinancial
from backend.utils.db import get_db
from sqlalchemy import text

class StockCrawler:
    @staticmethod
    def fetch_stock_list():
        try:
            df = ak.stock_info_a_code_name()
            return df
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def fetch_stock_daily(code, start_date=None, end_date=None):
        try:
            if start_date is None:
                start_date = '20200101'
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            return df
        except Exception as e:
            print(f"获取股票{code}日线数据失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def fetch_stock_realtime():
        try:
            df = ak.stock_zh_a_spot_em()
            return df
        except Exception as e:
            print(f"获取实时行情失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def fetch_stock_financial(code):
        try:
            df = ak.stock_financial_analysis_indicator(symbol=code)
            return df
        except Exception as e:
            print(f"获取股票{code}财务数据失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def save_stock_list(db):
        df = StockCrawler.fetch_stock_list()
        if df.empty:
            return 0
        
        count = 0
        for _, row in df.iterrows():
            code = row['code']
            name = row['name']
            
            stock = db.query(Stock).filter(Stock.code == code).first()
            if stock:
                stock.name = name
            else:
                stock = Stock(code=code, name=name)
                db.add(stock)
            count += 1
        
        db.commit()
        return count
    
    @staticmethod
    def save_stock_daily(db, code):
        df = StockCrawler.fetch_stock_daily(code)
        if df.empty:
            return 0
        
        count = 0
        for _, row in df.iterrows():
            date_str = str(row['日期'])
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            existing = db.query(StockDaily).filter(
                StockDaily.code == code,
                StockDaily.date == date
            ).first()
            
            if not existing:
                daily = StockDaily(
                    code=code,
                    date=date,
                    open=row.get('开盘', None),
                    high=row.get('最高', None),
                    low=row.get('最低', None),
                    close=row.get('收盘', None),
                    volume=row.get('成交量', None),
                    turnover=row.get('成交额', None),
                    change_percent=row.get('涨跌幅', None)
                )
                db.add(daily)
                count += 1
        
        db.commit()
        return count
    
    @staticmethod
    def update_stock_realtime(db):
        df = StockCrawler.fetch_stock_realtime()
        if df.empty:
            return 0
        
        count = 0
        for _, row in df.iterrows():
            code = str(row['代码'])
            stock = db.query(Stock).filter(Stock.code == code).first()
            if stock:
                stock.price = row.get('最新价', None)
                stock.change_percent = row.get('涨跌幅', None)
                stock.volume = row.get('成交量', None)
                stock.turnover = row.get('成交额', None)
                stock.pe = row.get('市盈率', None)
                stock.pb = row.get('市净率', None)
                stock.market_cap = row.get('总市值', None)
                count += 1
        
        db.commit()
        return count

"""股票数据服务：集中处理股票数据的保存和更新逻辑"""
import logging
import pandas as pd
from datetime import date, datetime
from typing import Optional, Tuple

from backend.models.stock import Stock, StockDaily
from backend.models.crawl_status import CrawlStatus
from backend.utils.db import get_db

logger = logging.getLogger(__name__)


def save_stock_list(df: pd.DataFrame) -> Tuple[int, int]:
    """保存股票列表，返回(成功数, 失败数)"""
    if df.empty:
        return 0, 0

    db = next(get_db())
    success_count = 0
    fail_count = 0

    for _, row in df.iterrows():
        code = str(row['code'])
        name = str(row['name'])

        stock = db.query(Stock).filter(Stock.code == code).first()
        if stock:
            stock.name = name
        else:
            stock = Stock(code=code, name=name)
            db.add(stock)
        success_count += 1

    db.commit()
    db.close()
    return success_count, fail_count


def save_realtime_quotes(df: pd.DataFrame, quote_date: Optional[date] = None) -> Tuple[int, int]:
    """保存实时行情数据到 StockDaily 表，返回(成功数, 失败数)"""
    if df.empty:
        return 0, 0

    if quote_date is None:
        quote_date = date.today()

    db = next(get_db())
    success_count = 0
    fail_count = 0

    for _, row in df.iterrows():
        code = str(row['code'])
        # 只有 Stock 表中存在的股票才写入（过滤掉已退市等）
        if not db.query(Stock.code).filter(Stock.code == code).first():
            fail_count += 1
            continue

        try:
            daily = db.query(StockDaily).filter(
                StockDaily.code == code, StockDaily.date == quote_date
            ).first()
            if daily:
                daily.close = row.get('close')
                daily.open = row.get('open')
                daily.high = row.get('high')
                daily.low = row.get('low')
                daily.change_percent = row.get('change_percent')
                daily.volume = row.get('volume')
                daily.turnover = row.get('turnover')
                daily.turnover_rate = row.get('turnover_rate')
                daily.pe = row.get('pe')
                daily.pb = row.get('pb')
                daily.market_cap = row.get('market_cap')
            else:
                daily = StockDaily(
                    code=code,
                    date=quote_date,
                    close=row.get('close'),
                    open=row.get('open'),
                    high=row.get('high'),
                    low=row.get('low'),
                    change_percent=row.get('change_percent'),
                    volume=row.get('volume'),
                    turnover=row.get('turnover'),
                    turnover_rate=row.get('turnover_rate'),
                    pe=row.get('pe'),
                    pb=row.get('pb'),
                    market_cap=row.get('market_cap'),
                )
                db.add(daily)
            success_count += 1
        except Exception as e:
            logger.warning(f"保存 {code} 行情失败: {e}")
            fail_count += 1

    db.commit()
    db.close()
    logger.info(f"StockDaily 写入完成: 成功 {success_count}, 失败 {fail_count}, 日期 {quote_date}")
    return success_count, fail_count


def record_crawl_status(
    crawl_type: str,
    status: str,
    success_count: int,
    fail_count: int,
    error_message: Optional[str] = None,
    crawl_time: Optional[datetime] = None,
) -> None:
    """记录爬取状态"""
    if crawl_time is None:
        crawl_time = datetime.now()

    try:
        db = next(get_db())
        crawl_status = CrawlStatus(
            crawl_type=crawl_type,
            status=status,
            crawl_time=crawl_time,
            success_count=success_count,
            fail_count=fail_count,
            error_message=error_message,
        )
        db.add(crawl_status)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"记录爬取状态失败: {e}")


def has_today_success_record(crawl_type: str, today: date) -> bool:
    """检查当天是否已有成功的爬取记录"""
    try:
        db = next(get_db())
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())

        record = db.query(CrawlStatus).filter(
            CrawlStatus.crawl_type == crawl_type,
            CrawlStatus.status.in_(["success", "partial"]),
            CrawlStatus.crawl_time >= start_of_day,
            CrawlStatus.crawl_time <= end_of_day,
        ).first()

        db.close()
        return record is not None
    except Exception as e:
        logger.error(f"检查今日爬取记录失败: {e}")
        return False

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
                for field in ('close', 'open', 'high', 'low', 'change_percent',
                              'volume', 'turnover', 'turnover_rate',
                              'pe', 'pb', 'market_cap'):
                    val = row.get(field)
                    if val is not None:
                        setattr(daily, field, val)
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


def _resolve_prev_close(
    db, code: str, current_date: date, in_batch_prev_close: Optional[float]
) -> Optional[float]:
    """获取上一交易日 close：优先用同批次内前一日，否则查数据库。"""
    if in_batch_prev_close is not None:
        return in_batch_prev_close
    prev = db.query(StockDaily.close).filter(
        StockDaily.code == code,
        StockDaily.date < current_date,
        StockDaily.close.isnot(None),
    ).order_by(StockDaily.date.desc()).limit(1).first()
    return prev[0] if prev else None


def _compute_change_percent(
    prev_close: Optional[float], curr_close: Optional[float]
) -> Optional[float]:
    """计算涨跌幅百分比；prev_close 为 0/None 或 curr_close 为 None 时返回 None。"""
    if not prev_close or prev_close == 0 or curr_close is None:
        return None
    return round((curr_close - prev_close) / prev_close * 100, 4)


def save_daily_batch(df_list: list[pd.DataFrame]) -> Tuple[int, int, int, int]:
    """
    批量保存多只股票的日线数据，返回(成功数, 失败数, 新增数, 更新数)

    Args:
        df_list: 多个DataFrame的列表，每个DataFrame对应一只股票的日线数据

    Returns:
        (成功股票数, 失败股票数, 新增记录数, 更新记录数)

    Note:
        腾讯 stock_zh_a_daily 接口不返回涨跌幅，normalizer 在 df 内有前一日 close
        时才计算。单日补爬或 df 首行的 change_percent 会缺失，这里在写入前用
        同批次前一日 close 或数据库上一交易日 close 补全。
    """
    if not df_list:
        return 0, 0, 0, 0

    db = next(get_db())
    success_stocks = 0
    fail_stocks = 0
    added_count = 0
    updated_count = 0

    for df in df_list:
        if df.empty:
            fail_stocks += 1
            continue

        try:
            code = str(df.iloc[0]['code'])
            if not db.query(Stock.code).filter(Stock.code == code).first():
                fail_stocks += 1
                continue

            # 按日期升序，保证同批次内多日数据能把 prev_close 传给次日
            df_sorted = df.sort_values('date').reset_index(drop=True)

            stock_added = 0
            stock_updated = 0
            in_batch_prev_close: Optional[float] = None

            for _, row in df_sorted.iterrows():
                date_val = row['date']
                close_val = row.get('close')
                change_percent_val = row.get('change_percent')

                # change_percent 缺失且 close 可用 → 从同批次或 DB 上一交易日 close 补全
                if change_percent_val is None and close_val is not None:
                    prev_close = _resolve_prev_close(
                        db, code, date_val, in_batch_prev_close
                    )
                    change_percent_val = _compute_change_percent(prev_close, close_val)

                existing = db.query(StockDaily).filter(
                    StockDaily.code == code, StockDaily.date == date_val
                ).first()

                if existing:
                    for field in ('open', 'high', 'low', 'close', 'volume', 'turnover',
                                  'turnover_rate', 'change_percent',
                                  'pe', 'pb', 'market_cap'):
                        # change_percent 用上面补全后的值，其余字段直接取 row
                        val = change_percent_val if field == 'change_percent' else row.get(field)
                        if val is not None:
                            setattr(existing, field, val)
                    stock_updated += 1
                else:
                    daily = StockDaily(
                        code=code,
                        date=date_val,
                        open=row.get('open'),
                        high=row.get('high'),
                        low=row.get('low'),
                        close=close_val,
                        volume=row.get('volume'),
                        turnover=row.get('turnover'),
                        turnover_rate=row.get('turnover_rate'),
                        change_percent=change_percent_val,
                        pe=row.get('pe'),
                        pb=row.get('pb'),
                        market_cap=row.get('market_cap'),
                    )
                    db.add(daily)
                    stock_added += 1

                # 同批次下一日优先用这个 close，避免再去查 DB
                if close_val is not None:
                    in_batch_prev_close = close_val

            success_stocks += 1
            added_count += stock_added
            updated_count += stock_updated

        except Exception as e:
            logger.warning(f"保存股票日线失败: {e}")
            fail_stocks += 1

    db.commit()
    db.close()
    logger.info(f"批量日线保存完成: 成功{success_stocks}只, 失败{fail_stocks}只, "
                f"新增{added_count}条, 更新{updated_count}条")
    return success_stocks, fail_stocks, added_count, updated_count


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


def get_daily_summary(start_date: Optional[date] = None, end_date: Optional[date] = None) -> list[dict]:
    """
    获取每日数据统计摘要

    Args:
        start_date: 起始日期，默认为数据库中最早日期
        end_date: 结束日期，默认为数据库中最晚日期

    Returns:
        每日统计列表，包含 date, count, total_stocks, coverage_percent
    """
    from sqlalchemy import func
    from datetime import timedelta
    from backend.utils.trading_day import is_trading_day

    db = next(get_db())

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=90)

    total_stocks = db.query(Stock).count()

    query = db.query(
        StockDaily.date,
        func.count(StockDaily.code).label('count')
    ).filter(
        StockDaily.date >= start_date,
        StockDaily.date <= end_date
    ).group_by(StockDaily.date)

    results = query.all()
    data_map = {row.date: row.count for row in results}

    summary = []
    current = end_date
    while current >= start_date:
        if is_trading_day(current):
            count = data_map.get(current, 0)
            coverage = (count / total_stocks) * 100 if total_stocks > 0 else 0
            summary.append({
                'date': current.strftime('%Y-%m-%d'),
                'count': count,
                'total_stocks': total_stocks,
                'coverage_percent': round(coverage, 2)
            })
        current -= timedelta(days=1)

    db.close()
    return summary

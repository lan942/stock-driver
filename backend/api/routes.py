from flask import Blueprint, request, jsonify
import time
import threading
from datetime import date, datetime
from sqlalchemy import func
from backend.services.analysis import StockAnalysis
from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.models.crawl_status import CrawlStatus
from backend.services.crawler.stock_list import StockListCrawler
from backend.services.crawler.stock_realtime import StockRealtimeCrawler
from backend.services.crawler.stock_daily import TencentStockDailyCrawler
from backend.services.stock_service import (
    save_stock_list,
    save_realtime_quotes,
    save_daily_batch,
    record_crawl_status,
    has_today_success_record,
)
from backend.services.scheduler import get_scheduler

api = Blueprint('api', __name__)

_daily_crawl_progress = {
    'running': False,
    'current': 0,
    'total': 0,
    'current_code': '',
    'success': 0,
    'failed': 0,
    'added': 0,
    'updated': 0,
    'start_time': None,
    'error': None,
}
_daily_crawl_lock = threading.Lock()


def _build_daily_result(d, stock):
    return {
        'id': stock.id if stock else None,
        'code': d.code,
        'name': stock.name if stock else '',
        'price_date': d.date.strftime('%Y-%m-%d') if d.date else None,
        'price': d.close,
        'open': d.open,
        'high': d.high,
        'low': d.low,
        'change_percent': d.change_percent,
        'volume': d.volume,
        'turnover': d.turnover,
        'turnover_rate': d.turnover_rate,
        'pe': d.pe,
        'pb': d.pb,
        'market_cap': d.market_cap,
    }


@api.route('/stocks', methods=['GET'])
def get_stocks():
    db = next(get_db())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    query_date = request.args.get('date', None)
    search_code = request.args.get('code', None)
    search_name = request.args.get('name', None)

    max_date = db.query(func.max(StockDaily.date)).scalar()

    has_search = bool(search_code or search_name)
    has_date_filter = bool(query_date and query_date.strip())

    q_date = None
    if has_date_filter:
        try:
            q_date = datetime.strptime(query_date.strip(), '%Y-%m-%d').date()
        except ValueError:
            db.close()
            return jsonify({'error': '日期格式错误，应为 YYYY-MM-DD'}), 400
    elif not has_search:
        q_date = max_date

    query = db.query(StockDaily)
    if q_date is not None:
        query = query.filter(StockDaily.date == q_date)
    if search_code:
        query = query.filter(StockDaily.code.like(f'%{search_code}%'))
    if search_name:
        query = query.join(Stock, StockDaily.code == Stock.code).filter(Stock.name.like(f'%{search_name}%'))

    total = query.count()

    if q_date is not None:
        dailies = query.order_by(StockDaily.code).offset((page - 1) * per_page).limit(per_page).all()
    else:
        dailies = query.order_by(StockDaily.date.desc(), StockDaily.code).offset((page - 1) * per_page).limit(per_page).all()

    stock_cache = {}
    result = []
    for d in dailies:
        if d.code not in stock_cache:
            stock_cache[d.code] = db.query(Stock).filter(Stock.code == d.code).first()
        result.append(_build_daily_result(d, stock_cache[d.code]))

    db.close()
    resp = {
        'data': result,
        'total': total,
        'page': page,
        'per_page': per_page,
    }
    if q_date is not None:
        resp['price_date'] = q_date.strftime('%Y-%m-%d')
    resp['latest_date'] = max_date.strftime('%Y-%m-%d') if max_date else None
    return jsonify(resp)


@api.route('/stocks/<code>', methods=['GET'])
def get_stock(code):
    db = next(get_db())
    stock = db.query(Stock).filter(Stock.code == code).first()

    if not stock:
        return jsonify({'error': '股票不存在'}), 404

    latest = db.query(StockDaily).filter(
        StockDaily.code == code
    ).order_by(StockDaily.date.desc()).first()

    return jsonify({
        'id': stock.id,
        'code': stock.code,
        'name': stock.name,
        'industry': stock.industry,
        'sector': stock.sector,
        'price': latest.close if latest else None,
        'open': latest.open if latest else None,
        'high': latest.high if latest else None,
        'low': latest.low if latest else None,
        'price_date': latest.date.strftime('%Y-%m-%d') if latest and latest.date else None,
        'change_percent': latest.change_percent if latest else None,
        'volume': latest.volume if latest else None,
        'turnover': latest.turnover if latest else None,
        'turnover_rate': latest.turnover_rate if latest else None,
        'pe': latest.pe if latest else None,
        'pb': latest.pb if latest else None,
        'market_cap': latest.market_cap if latest else None,
    })


@api.route('/stocks/<code>/daily', methods=['GET'])
def get_stock_daily(code):
    db = next(get_db())
    days = request.args.get('days', 60, type=int)

    analysis = StockAnalysis.get_stock_analysis(db, code, days)
    if not analysis:
        return jsonify({'error': '没有找到数据'}), 404

    return jsonify(analysis)


@api.route('/stocks/<code>/chart', methods=['GET'])
def get_stock_chart(code):
    db = next(get_db())
    days = request.args.get('days', 60, type=int)

    daily_data = db.query(StockDaily).filter(
        StockDaily.code == code
    ).order_by(StockDaily.date.desc()).limit(days).all()

    if not daily_data:
        return jsonify({'error': '没有找到数据'}), 404

    result = [{
        'date': item.date.strftime('%Y-%m-%d'),
        'open': item.open,
        'high': item.high,
        'low': item.low,
        'close': item.close,
        'volume': item.volume
    } for item in reversed(daily_data)]

    return jsonify(result)


@api.route('/stocks/top/gainers', methods=['GET'])
def get_top_gainers():
    db = next(get_db())
    limit = request.args.get('limit', 10, type=int)
    query_date = request.args.get('date', None)

    q_date = None
    if query_date:
        try:
            q_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        except ValueError:
            db.close()
            return jsonify({'error': '日期格式错误，应为 YYYY-MM-DD'}), 400

    rows, used_date = StockAnalysis.get_top_gainers(db, limit, q_date)
    price_date_str = used_date.strftime('%Y-%m-%d') if used_date else None

    result = [{
        'code': d.code,
        'name': name or '',
        'price': d.close,
        'change_percent': d.change_percent,
        'price_date': price_date_str,
    } for d, name in rows]

    db.close()
    return jsonify(result)


@api.route('/stocks/top/losers', methods=['GET'])
def get_top_losers():
    db = next(get_db())
    limit = request.args.get('limit', 10, type=int)
    query_date = request.args.get('date', None)

    q_date = None
    if query_date:
        try:
            q_date = datetime.strptime(query_date, '%Y-%m-%d').date()
        except ValueError:
            db.close()
            return jsonify({'error': '日期格式错误，应为 YYYY-MM-DD'}), 400

    rows, used_date = StockAnalysis.get_top_losers(db, limit, q_date)
    price_date_str = used_date.strftime('%Y-%m-%d') if used_date else None

    result = [{
        'code': d.code,
        'name': name or '',
        'price': d.close,
        'change_percent': d.change_percent,
        'price_date': price_date_str,
    } for d, name in rows]

    db.close()
    return jsonify(result)


@api.route('/crawler/update_list', methods=['POST'])
def update_stock_list():
    start_time = time.time()
    crawler = StockListCrawler()
    df = crawler.fetch_stock_list_df()
    elapsed = round(time.time() - start_time, 1)
    if df.empty:
        return jsonify({'message': '获取股票列表失败', 'success_count': 0, 'fail_count': 0, 'elapsed': elapsed}), 500

    success_count, fail_count = save_stock_list(df)
    record_crawl_status(
        crawl_type="list",
        status="success" if fail_count == 0 else "partial",
        success_count=success_count,
        fail_count=fail_count,
    )
    return jsonify({
        'message': f'成功更新 {success_count} 只股票',
        'success_count': success_count,
        'fail_count': fail_count,
        'elapsed': elapsed,
    })


@api.route('/crawler/update_realtime', methods=['POST'])
def update_realtime():
    force = request.json.get('force', True) if request.is_json else True
    quote_date_str = request.json.get('date', None) if request.is_json else None

    if not force:
        today = date.today()
        if has_today_success_record('realtime', today):
            return jsonify({
                'message': '今日已有成功爬取记录，如需强制更新请勾选强制刷新',
                'success_count': 0,
                'fail_count': 0,
                'elapsed': 0,
                'skipped': True,
            })

    quote_date = None
    if quote_date_str:
        quote_date = datetime.strptime(quote_date_str, '%Y-%m-%d').date()

    start_time = time.time()
    crawler = StockRealtimeCrawler()
    df = crawler.fetch_realtime_df()
    elapsed = round(time.time() - start_time, 1)
    if df.empty:
        return jsonify({'message': '获取实时行情失败', 'success_count': 0, 'fail_count': 0, 'elapsed': elapsed}), 500

    success_count, fail_count = save_realtime_quotes(df, quote_date=quote_date)
    status = "success" if fail_count == 0 else "partial"
    record_crawl_status(
        crawl_type="realtime",
        status=status,
        success_count=success_count,
        fail_count=fail_count,
    )
    return jsonify({
        'message': f'成功更新 {success_count} 只股票实时数据',
        'success_count': success_count,
        'fail_count': fail_count,
        'elapsed': elapsed,
        'price_date': quote_date.strftime('%Y-%m-%d') if quote_date else date.today().strftime('%Y-%m-%d'),
    })


@api.route('/crawler/fetch_daily/<code>', methods=['POST'])
def fetch_daily(code):
    """获取单只股票历史日线数据（腾讯源）"""
    data = request.get_json(silent=True) or {}
    start_date = data.get('start_date', '20250101')
    end_date = data.get('end_date', datetime.now().strftime('%Y%m%d'))
    adjust = data.get('adjust', 'qfq')

    try:
        crawler = TencentStockDailyCrawler()
        df = crawler.fetch_single(code, start_date, end_date, adjust)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    if df.empty:
        return jsonify({'message': '没有获取到数据'}), 404

    success_stocks, fail_stocks, added, updated = save_daily_batch([df])
    return jsonify({
        'message': f'成功获取 {len(df)} 条日线数据',
        'count': len(df),
        'added': added,
        'updated': updated,
        'code': code,
    })


@api.route('/crawler/fetch_daily_batch', methods=['POST'])
def fetch_daily_batch():
    """批量获取股票日线数据（腾讯源），异步执行，通过 /crawler/progress/daily 查询进度"""
    global _daily_crawl_progress

    with _daily_crawl_lock:
        if _daily_crawl_progress['running']:
            return jsonify({'error': '已有批量爬取任务正在进行中'}), 400

    data = request.get_json(silent=True) or {}
    start_date = data.get('start_date', '20250101')
    end_date = data.get('end_date', datetime.now().strftime('%Y%m%d'))
    adjust = data.get('adjust', 'qfq')
    codes = data.get('codes', [])

    if not codes:
        db = next(get_db())
        stocks = db.query(Stock.code).all()
        codes = [s[0] for s in stocks]
        db.close()

    if not codes:
        return jsonify({'error': '没有可爬取的股票代码'}), 400

    def _progress_callback(current, total, current_code, success=0, failed=0):
        with _daily_crawl_lock:
            _daily_crawl_progress['current'] = current
            _daily_crawl_progress['total'] = total
            _daily_crawl_progress['current_code'] = current_code
            _daily_crawl_progress['success'] = success
            _daily_crawl_progress['failed'] = failed

    def _batch_worker():
        global _daily_crawl_progress
        try:
            crawler = TencentStockDailyCrawler()
            success, failed, df_list = crawler.fetch_batch(
                codes=codes,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
                progress_callback=_progress_callback,
            )
            success_stocks, fail_stocks, added, updated = save_daily_batch(df_list)

            crawl_time = datetime.now()
            status = 'success' if failed == 0 else 'partial'
            total_records = sum(len(df) for df in df_list)
            record_crawl_status(
                crawl_type='daily',
                status=status,
                crawl_time=crawl_time,
                success_count=success,
                fail_count=failed,
                error_message=f'新增{added}条，更新{updated}条' if failed == 0 else f'{failed}只股票失败',
            )

            with _daily_crawl_lock:
                _daily_crawl_progress['success'] = success
                _daily_crawl_progress['failed'] = failed
                _daily_crawl_progress['added'] = added
                _daily_crawl_progress['updated'] = updated
                _daily_crawl_progress['running'] = False
        except Exception as e:
            with _daily_crawl_lock:
                _daily_crawl_progress['running'] = False
                _daily_crawl_progress['error'] = str(e)
            record_crawl_status(
                crawl_type='daily',
                status='failed',
                crawl_time=datetime.now(),
                success_count=0,
                fail_count=len(codes),
                error_message=str(e),
            )

    with _daily_crawl_lock:
        _daily_crawl_progress = {
            'running': True,
            'current': 0,
            'total': len(codes),
            'current_code': '',
            'success': 0,
            'failed': 0,
            'added': 0,
            'updated': 0,
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': None,
        }

    thread = threading.Thread(target=_batch_worker, daemon=True)
    thread.start()

    return jsonify({
        'message': f'批量日线爬取已启动，共 {len(codes)} 只股票',
        'total': len(codes),
        'start_date': start_date,
        'end_date': end_date,
    })


@api.route('/crawler/progress/daily', methods=['GET'])
def get_daily_progress():
    """获取日线批量爬取进度"""
    with _daily_crawl_lock:
        progress = dict(_daily_crawl_progress)
    return jsonify(progress)


@api.route('/crawl_status', methods=['GET'])
def get_crawl_status():
    db = next(get_db())
    limit = request.args.get('limit', 10, type=int)
    crawl_type = request.args.get('crawl_type', None)

    query = db.query(CrawlStatus).order_by(CrawlStatus.crawl_time.desc())

    if crawl_type:
        query = query.filter(CrawlStatus.crawl_type == crawl_type)

    statuses = query.limit(limit).all()

    result = [{
        'id': s.id,
        'crawl_type': s.crawl_type,
        'status': s.status,
        'crawl_time': s.crawl_time.strftime('%Y-%m-%d %H:%M:%S'),
        'success_count': s.success_count,
        'fail_count': s.fail_count,
        'error_message': s.error_message
    } for s in statuses]

    db.close()
    return jsonify(result)


@api.route('/scheduler/info', methods=['GET'])
def get_scheduler_info():
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs_info()
    return jsonify({
        'running': scheduler.scheduler.running,
        'jobs': jobs
    })


@api.route('/scheduler/pause', methods=['POST'])
def pause_scheduler():
    scheduler = get_scheduler()
    scheduler.pause()
    return jsonify({'message': '调度器已暂停'})


@api.route('/scheduler/resume', methods=['POST'])
def resume_scheduler():
    scheduler = get_scheduler()
    scheduler.resume()
    return jsonify({'message': '调度器已恢复'})


@api.route('/scheduler/run/<job_id>', methods=['POST'])
def run_job(job_id):
    scheduler = get_scheduler()
    scheduler.run_job(job_id)
    return jsonify({'message': f'任务 {job_id} 已立即执行'})

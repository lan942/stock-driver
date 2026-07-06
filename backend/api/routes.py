from flask import Blueprint, request, jsonify
import time
import threading
from datetime import date, datetime
from sqlalchemy import func
from backend.services.analysis import StockAnalysis
from backend.services.indicator_engine import IndicatorEngine
from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.models.crawl_status import CrawlStatus
from backend.services.crawler.base import CrawlerError
from backend.services.crawler.stock_list import StockListCrawler, DEFAULT_SOURCES as STOCK_LIST_SOURCES
from backend.services.crawler.stock_realtime import StockRealtimeCrawler
from backend.services.crawler.stock_daily import TencentStockDailyCrawler
from backend.services.stock_service import (
    save_stock_list,
    save_realtime_quotes,
    save_daily_batch,
    record_crawl_status,
    has_today_success_record,
    get_daily_summary,
)
from backend.services.scheduler import get_scheduler
from backend.services.portfolio_service import (
    get_portfolio_overview,
    get_holdings,
    add_holding,
    update_holding,
    delete_holding,
    get_transactions,
    add_transaction,
    clear_all_transactions,
    update_cash_balance,
)
from backend.services.backtest_service import (
    get_portfolio_overview as backtest_get_overview,
    get_holdings as backtest_get_holdings,
    add_holding as backtest_add_holding,
    update_holding as backtest_update_holding,
    delete_holding as backtest_delete_holding,
    get_transactions as backtest_get_transactions,
    add_transaction as backtest_add_transaction,
    clear_all_transactions as backtest_clear_transactions,
    update_cash as backtest_update_cash,
)
from backend.services.strategy_config import StrategyConfigService
from backend.services.position_manager import PositionManager
from backend.services.strategy_engine import StrategyEngine
from backend.services.strategy_backtest import StrategyBacktest

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


@api.route('/stocks/search', methods=['GET'])
def search_stocks():
    """搜索股票基本信息（Stock 表，每只股票一条记录）"""
    db = next(get_db())
    query_str = request.args.get('q', '').strip()

    if not query_str:
        db.close()
        return jsonify({'data': []})

    results = []
    if query_str.isdigit():
        results = db.query(Stock).filter(Stock.code.like(f'%{query_str}%')).limit(20).all()
    if not results:
        results = db.query(Stock).filter(Stock.name.like(f'%{query_str}%')).limit(20).all()

    data = [{'code': s.code, 'name': s.name} for s in results]
    db.close()
    return jsonify({'data': data})


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


@api.route('/stocks/<code>/indicators', methods=['GET'])
def get_stock_indicators(code):
    """获取股票技术指标（Backtrader 计算）"""
    days = request.args.get('days', 120, type=int)
    indicators_str = request.args.get('indicators', '')
    params_str = request.args.get('params', '{}')

    # 解析指标列表
    if indicators_str:
        indicator_names = [name.strip() for name in indicators_str.split(',') if name.strip()]
    else:
        indicator_names = ['MA', 'EMA', 'MACD', 'RSI', 'BOLL', 'KDJ', 'ATR', 'ADX']

    # 解析自定义参数
    import json as _json
    try:
        custom_params = _json.loads(params_str)
    except (ValueError, TypeError):
        custom_params = {}

    # 构建指标配置
    configs = []
    for name in indicator_names:
        cfg = {'type': name, 'params': custom_params.get(name, {})}
        configs.append(cfg)

    try:
        result = IndicatorEngine.compute(code, configs, days)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    if result is None:
        # 检查股票是否存在
        db = next(get_db())
        stock = db.query(Stock).filter(Stock.code == code).first()
        db.close()
        if not stock:
            return jsonify({'error': '股票不存在'}), 404
        return jsonify({'error': '没有找到数据'}), 404

    return jsonify(result)


@api.route('/stocks/<code>/indicators/list', methods=['GET'])
def get_stock_indicators_list(code):
    """返回可用的技术指标清单"""
    return jsonify({'indicators': IndicatorEngine.get_indicator_list()})


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


@api.route('/stocks/daily_summary', methods=['GET'])
def get_stocks_daily_summary():
    start_date_str = request.args.get('start_date', None)
    end_date_str = request.args.get('end_date', None)

    start_date = None
    end_date = None

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': '起始日期格式错误，应为 YYYY-MM-DD'}), 400

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': '结束日期格式错误，应为 YYYY-MM-DD'}), 400

    summary = get_daily_summary(start_date, end_date)
    return jsonify(summary)


@api.route('/crawler/update_list', methods=['POST'])
def update_stock_list():
    start_time = time.time()
    sources_tried = [s.get("name", "unknown") for s in STOCK_LIST_SOURCES]
    crawler = StockListCrawler()
    try:
        df = crawler.fetch_stock_list_df()
    except CrawlerError as e:
        elapsed = round(time.time() - start_time, 1)
        record_crawl_status(
            crawl_type="list",
            status="failed",
            success_count=0,
            fail_count=0,
            error_message=str(e),
        )
        return jsonify({
            'message': '获取股票列表失败',
            'error': str(e),
            'sources_tried': sources_tried,
            'success_count': 0,
            'fail_count': 0,
            'elapsed': elapsed,
        }), 503

    elapsed = round(time.time() - start_time, 1)
    if df.empty:
        record_crawl_status(
            crawl_type="list",
            status="failed",
            success_count=0,
            fail_count=0,
            error_message="返回空数据",
        )
        return jsonify({
            'message': '获取股票列表为空',
            'error': '返回空数据',
            'sources_tried': sources_tried,
            'success_count': 0,
            'fail_count': 0,
            'elapsed': elapsed,
        }), 503

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


@api.route('/portfolio/overview', methods=['GET'])
def portfolio_overview():
    overview = get_portfolio_overview()
    return jsonify(overview)


@api.route('/portfolio/holdings', methods=['GET'])
def portfolio_holdings():
    holdings = get_holdings()
    return jsonify(holdings)


@api.route('/portfolio/holdings', methods=['POST'])
def portfolio_add_holding():
    data = request.get_json(silent=True) or {}
    code = data.get('code')
    quantity = data.get('quantity')
    cost_price = data.get('cost_price')

    if not code or quantity is None or cost_price is None:
        return jsonify({'error': '缺少必要参数: code, quantity, cost_price'}), 400

    result = add_holding(code, quantity, cost_price)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result), 201


@api.route('/portfolio/holdings/<int:holding_id>', methods=['PUT'])
def portfolio_update_holding(holding_id):
    data = request.get_json(silent=True) or {}
    quantity = data.get('quantity')
    cost_price = data.get('cost_price')

    result = update_holding(holding_id, quantity, cost_price)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@api.route('/portfolio/holdings/<int:holding_id>', methods=['DELETE'])
def portfolio_delete_holding(holding_id):
    result = delete_holding(holding_id)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@api.route('/portfolio/transactions', methods=['GET'])
def portfolio_transactions():
    limit = request.args.get('limit', 50, type=int)
    transactions = get_transactions(limit)
    return jsonify(transactions)


@api.route('/portfolio/transactions', methods=['POST'])
def portfolio_add_transaction():
    data = request.get_json(silent=True) or {}
    tx_type = data.get('type')
    code = data.get('code')
    quantity = data.get('quantity')
    price = data.get('price')
    trade_date = data.get('trade_date')

    if not tx_type or not code or quantity is None or price is None:
        return jsonify({'error': '缺少必要参数: type, code, quantity, price'}), 400

    result = add_transaction(tx_type, code, quantity, price, trade_date)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result), 201


@api.route('/portfolio/transactions', methods=['DELETE'])
def portfolio_clear_transactions():
    result = clear_all_transactions()
    return jsonify(result)


@api.route('/portfolio/cash', methods=['POST'])
def portfolio_update_cash():
    data = request.get_json(silent=True) or {}
    amount = data.get('amount')

    if amount is None:
        return jsonify({'error': '缺少必要参数: amount'}), 400

    result = update_cash_balance(amount)
    return jsonify(result)


@api.route('/backtest/overview', methods=['GET'])
def backtest_overview():
    overview = backtest_get_overview()
    return jsonify(overview)


@api.route('/backtest/holdings', methods=['GET'])
def backtest_holdings():
    holdings = backtest_get_holdings()
    return jsonify(holdings)


@api.route('/backtest/holdings', methods=['POST'])
def backtest_add_holding_route():
    data = request.get_json(silent=True) or {}
    code = data.get('code')
    quantity = data.get('quantity')
    cost_price = data.get('cost_price')

    if not code or quantity is None or cost_price is None:
        return jsonify({'error': '缺少必要参数: code, quantity, cost_price'}), 400

    result = backtest_add_holding(code, quantity, cost_price)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result), 201


@api.route('/backtest/holdings/<int:holding_id>', methods=['PUT'])
def backtest_update_holding_route(holding_id):
    data = request.get_json(silent=True) or {}
    quantity = data.get('quantity')
    cost_price = data.get('cost_price')

    result = backtest_update_holding(holding_id, quantity, cost_price)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@api.route('/backtest/holdings/<int:holding_id>', methods=['DELETE'])
def backtest_delete_holding_route(holding_id):
    result = backtest_delete_holding(holding_id)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@api.route('/backtest/transactions', methods=['GET'])
def backtest_transactions():
    limit = request.args.get('limit', 50, type=int)
    transactions = backtest_get_transactions(limit)
    return jsonify(transactions)


@api.route('/backtest/transactions', methods=['POST'])
def backtest_add_transaction_route():
    data = request.get_json(silent=True) or {}
    tx_type = data.get('type')
    code = data.get('code')
    quantity = data.get('quantity')
    price = data.get('price')
    trade_date = data.get('trade_date')

    if not tx_type or not code or quantity is None or price is None:
        return jsonify({'error': '缺少必要参数: type, code, quantity, price'}), 400

    result = backtest_add_transaction(tx_type, code, quantity, price, trade_date)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result), 201


@api.route('/backtest/transactions', methods=['DELETE'])
def backtest_clear_transactions():
    result = backtest_clear_transactions()
    return jsonify(result)


@api.route('/backtest/cash', methods=['POST'])
def backtest_update_cash_route():
    data = request.get_json(silent=True) or {}
    amount = data.get('amount')

    if amount is None:
        return jsonify({'error': '缺少必要参数: amount'}), 400

    result = backtest_update_cash(amount)
    return jsonify(result)


# ─── 策略 API ───────────────────────────────────────────

@api.route('/strategy/config', methods=['GET'])
def strategy_get_config():
    """获取策略全部配置"""
    configs = StrategyConfigService.get_all()
    expected = StrategyConfigService.get_expected_return()
    return jsonify({'config': configs, 'expected_return': expected})


@api.route('/strategy/config', methods=['PUT'])
def strategy_update_config():
    """批量更新策略配置"""
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({'error': '请求体为空'}), 400

    for key, value in data.items():
        StrategyConfigService.set(key, value)

    return jsonify({'message': '配置更新成功', 'updated': list(data.keys())})


@api.route('/strategy/recommendations', methods=['GET'])
def strategy_recommendations():
    """获取每日买入推荐"""
    available_slots = PositionManager.get_available_slots()
    available_cash = PositionManager.get_available_cash()

    if available_slots <= 0:
        return jsonify({'data': [], 'available_slots': 0, 'message': '持仓已满'})

    recommendations = StrategyEngine.generate_recommendations(available_slots, available_cash)
    return jsonify({
        'data': recommendations,
        'available_slots': available_slots,
        'available_cash': available_cash,
    })


@api.route('/strategy/positions', methods=['GET'])
def strategy_positions():
    """获取持仓列表"""
    status = request.args.get('status', None)
    positions = PositionManager.get_positions(status)
    return jsonify({'data': positions})


@api.route('/strategy/transactions', methods=['GET'])
def strategy_transactions():
    """分页获取交易记录"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    code = request.args.get('code', None)
    result = PositionManager.get_transactions(code=code, page=page, page_size=page_size)
    return jsonify(result)


@api.route('/strategy/stats', methods=['GET'])
def strategy_stats():
    """获取策略绩效统计"""
    stats = PositionManager.get_stats()
    return jsonify(stats)


@api.route('/strategy/run', methods=['POST'])
def strategy_run():
    """手动触发策略执行"""
    today = date.today()
    data = request.get_json(silent=True) or {}
    run_date_str = data.get('date')
    if run_date_str:
        today = datetime.strptime(run_date_str, '%Y-%m-%d').date()

    # 1. 检测卖出条件
    sell_result = PositionManager.check_sell_conditions(today)

    # 2. 计算可用仓位
    available_slots = PositionManager.get_available_slots()
    available_cash = PositionManager.get_available_cash()

    # 3. 生成推荐
    recommendations = []
    if available_slots > 0:
        recommendations = StrategyEngine.generate_recommendations(available_slots, available_cash)

    return jsonify({
        'sold_count': len(sell_result['sold']),
        'sold_details': sell_result['sold'],
        'remaining_holding': sell_result['remaining_holding'],
        'available_slots': available_slots,
        'available_cash': available_cash,
        'recommendations_count': len(recommendations),
        'recommendations': recommendations,
        'run_date': today.strftime('%Y-%m-%d'),
    })


@api.route('/strategy/execute', methods=['POST'])
def strategy_execute():
    """执行买入推荐：同步写入 portfolio 和 strategy 两套系统"""
    data = request.get_json(silent=True) or {}
    code = data.get('code')
    name = data.get('name', '')
    quantity = data.get('quantity')
    buy_price = data.get('buy_price')
    suggested_buy_price = data.get('suggested_buy_price', buy_price)
    target_price = data.get('target_price')
    stop_price = data.get('stop_price')
    buy_date_str = data.get('buy_date')

    if not code or not quantity or not buy_price or not target_price or not stop_price:
        return jsonify({'error': '缺少必要参数: code, quantity, buy_price, target_price, stop_price'}), 400

    if buy_date_str:
        buy_date = datetime.strptime(buy_date_str, '%Y-%m-%d').date()
    else:
        buy_date = date.today()

    result = PositionManager.execute_recommendation(
        code=code,
        name=name,
        quantity=quantity,
        buy_price=buy_price,
        suggested_buy_price=suggested_buy_price,
        target_price=target_price,
        stop_price=stop_price,
        buy_date=buy_date,
    )
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result), 201


@api.route('/strategy/sell', methods=['POST'])
def strategy_sell():
    """手动卖出策略持仓：同步到 portfolio 系统"""
    data = request.get_json(silent=True) or {}
    position_id = data.get('position_id')
    sell_price = data.get('sell_price')

    if not position_id or not sell_price:
        return jsonify({'error': '缺少必要参数: position_id, sell_price'}), 400

    sell_date_str = data.get('sell_date')
    if sell_date_str:
        sell_date = datetime.strptime(sell_date_str, '%Y-%m-%d').date()
    else:
        sell_date = date.today()

    result = PositionManager.close_position(position_id, sell_price, sell_date)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@api.route('/strategy/backtest', methods=['POST'])
def strategy_backtest():
    """回测：在指定日期范围内按日迭代模拟策略"""
    data = request.get_json(silent=True) or {}
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')

    if not start_date_str or not end_date_str:
        return jsonify({'error': '缺少必要参数: start_date, end_date'}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': '日期格式错误，应为 YYYY-MM-DD'}), 400

    backtest = StrategyBacktest(
        start_date=start_date,
        end_date=end_date,
        initial_capital=data.get('initial_capital'),
        max_positions=data.get('max_positions'),
        stop_profit_pct=data.get('stop_profit_pct'),
        stop_loss_pct=data.get('stop_loss_pct'),
        max_hold_days=data.get('max_hold_days'),
        position_ratio=data.get('position_ratio'),
    )

    result = backtest.run()
    if 'error' in result:
        return jsonify(result), 400

    return jsonify(result)


@api.route('/strategy/backtest/clear', methods=['POST'])
def strategy_backtest_clear():
    """清空回测数据"""
    result = StrategyBacktest.clear_all()
    return jsonify({'message': '回测数据已清除', **result})

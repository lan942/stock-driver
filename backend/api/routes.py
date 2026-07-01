from flask import Blueprint, request, jsonify
from backend.services.analysis import StockAnalysis
from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily
from backend.services.crawler.stock_list import StockListCrawler
from backend.services.crawler.stock_realtime import StockRealtimeCrawler

api = Blueprint('api', __name__)

@api.route('/stocks', methods=['GET'])
def get_stocks():
    db = next(get_db())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    filters = {}
    if 'name' in request.args:
        filters['name'] = request.args['name']
    if 'code' in request.args:
        filters['code'] = request.args['code']
    if 'industry' in request.args:
        filters['industry'] = request.args['industry']
    if 'min_price' in request.args:
        filters['min_price'] = request.args['min_price']
    if 'max_price' in request.args:
        filters['max_price'] = request.args['max_price']
    
    stocks = StockAnalysis.filter_stocks(db, filters)
    
    total = len(stocks)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_stocks = stocks[start:end]
    
    result = [{
        'id': s.id,
        'code': s.code,
        'name': s.name,
        'industry': s.industry,
        'sector': s.sector,
        'price': s.price,
        'change_percent': s.change_percent,
        'volume': s.volume,
        'turnover': s.turnover,
        'pe': s.pe,
        'pb': s.pb,
        'market_cap': s.market_cap
    } for s in paginated_stocks]
    
    return jsonify({
        'data': result,
        'total': total,
        'page': page,
        'per_page': per_page
    })

@api.route('/stocks/<code>', methods=['GET'])
def get_stock(code):
    db = next(get_db())
    stock = db.query(Stock).filter(Stock.code == code).first()
    
    if not stock:
        return jsonify({'error': '股票不存在'}), 404
    
    return jsonify({
        'id': stock.id,
        'code': stock.code,
        'name': stock.name,
        'industry': stock.industry,
        'sector': stock.sector,
        'price': stock.price,
        'change_percent': stock.change_percent,
        'volume': stock.volume,
        'turnover': stock.turnover,
        'pe': stock.pe,
        'pb': stock.pb,
        'market_cap': stock.market_cap
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
    stocks = StockAnalysis.get_top_gainers(db, limit)
    
    result = [{
        'code': s.code,
        'name': s.name,
        'price': s.price,
        'change_percent': s.change_percent
    } for s in stocks]
    
    return jsonify(result)

@api.route('/stocks/top/losers', methods=['GET'])
def get_top_losers():
    db = next(get_db())
    limit = request.args.get('limit', 10, type=int)
    stocks = StockAnalysis.get_top_losers(db, limit)
    
    result = [{
        'code': s.code,
        'name': s.name,
        'price': s.price,
        'change_percent': s.change_percent
    } for s in stocks]
    
    return jsonify(result)

@api.route('/crawler/update_list', methods=['POST'])
def update_stock_list():
    db = next(get_db())
    crawler = StockListCrawler()
    df = crawler.fetch_stock_list_df()
    if df.empty:
        return jsonify({'message': '获取股票列表失败'}), 500
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
    return jsonify({'message': f'成功更新 {count} 只股票'})

@api.route('/crawler/update_realtime', methods=['POST'])
def update_realtime():
    db = next(get_db())
    crawler = StockRealtimeCrawler()
    df = crawler.fetch_realtime_df()
    if df.empty:
        return jsonify({'message': '获取实时行情失败'}), 500
    count = 0
    for _, row in df.iterrows():
        code = str(row['code'])
        stock = db.query(Stock).filter(Stock.code == code).first()
        if stock:
            stock.price = row.get('close', None)
            stock.change_percent = row.get('change_percent', None)
            stock.volume = row.get('volume', None)
            stock.turnover = row.get('turnover', None)
            count += 1
    db.commit()
    return jsonify({'message': f'成功更新 {count} 只股票实时数据'})

@api.route('/crawler/fetch_daily/<code>', methods=['POST'])
def fetch_daily(code):
    import akshare as ak
    from datetime import datetime
    db = next(get_db())
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20250601", end_date=datetime.now().strftime('%Y%m%d'), adjust="qfq")
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    if df.empty:
        return jsonify({'message': '没有获取到数据'}), 404
    count = 0
    for _, row in df.iterrows():
        date_str = str(row['日期'])
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        existing = db.query(StockDaily).filter(
            StockDaily.code == code, StockDaily.date == date
        ).first()
        if not existing:
            daily = StockDaily(
                code=code, date=date,
                open=row.get('开盘', None), high=row.get('最高', None),
                low=row.get('最低', None), close=row.get('收盘', None),
                volume=row.get('成交量', None), turnover=row.get('成交额', None),
                change_percent=row.get('涨跌幅', None)
            )
            db.add(daily)
            count += 1
    db.commit()
    return jsonify({'message': f'成功获取 {count} 条日线数据'})

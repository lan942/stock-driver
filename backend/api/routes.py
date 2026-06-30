from flask import Blueprint, request, jsonify
from backend.services.crawler import StockCrawler
from backend.services.analysis import StockAnalysis
from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily

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
    count = StockCrawler.save_stock_list(db)
    return jsonify({'message': f'成功更新 {count} 只股票'})

@api.route('/crawler/update_realtime', methods=['POST'])
def update_realtime():
    db = next(get_db())
    count = StockCrawler.update_stock_realtime(db)
    return jsonify({'message': f'成功更新 {count} 只股票实时数据'})

@api.route('/crawler/fetch_daily/<code>', methods=['POST'])
def fetch_daily(code):
    db = next(get_db())
    count = StockCrawler.save_stock_daily(db, code)
    return jsonify({'message': f'成功获取 {count} 条日线数据'})

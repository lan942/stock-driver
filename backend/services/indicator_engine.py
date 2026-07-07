"""基于 Backtrader 的技术指标计算引擎

通过轻量 Cerebro 实例动态计算任意 Backtrader 内置指标。
支持缓存、自定义参数、批量计算。
"""

import json
import time
import math
from typing import Optional

import pandas as pd
import backtrader as bt
from backend.utils.db import get_db
from backend.models.stock import Stock, StockDaily


class _IndicatorStrategy(bt.Strategy):
    """内部策略：仅用于在 __init__ 中声明指标，不执行交易"""

    params = (
        ('indicator_configs', []),  # [{"type": "MA", "params": {"period": 20}}, ...]
    )

    def __init__(self):
        self._indicators = {}
        for config in self.params.indicator_configs:
            ind_type = config['type']
            params = config.get('params', {})
            indicator = INDICATOR_REGISTRY[ind_type](self.data, **params)
            self._indicators[ind_type] = indicator

    def next(self):
        """不做任何交易，仅驱动 Cerebro 运行"""
        pass


# ─── 指标注册表 ───────────────────────────────────────────

def _create_ma(data, **kwargs):
    period = kwargs.get('period', 20)
    return bt.indicators.SimpleMovingAverage(data.close, period=period)


def _create_ema(data, **kwargs):
    period = kwargs.get('period', 20)
    return bt.indicators.ExponentialMovingAverage(data.close, period=period)


def _create_macd(data, **kwargs):
    period_me1 = kwargs.get('period_me1', 12)
    period_me2 = kwargs.get('period_me2', 26)
    period_signal = kwargs.get('period_signal', 9)
    return bt.indicators.MACD(
        data.close,
        period_me1=period_me1,
        period_me2=period_me2,
        period_signal=period_signal,
    )


def _create_rsi(data, **kwargs):
    period = kwargs.get('period', 14)
    return bt.indicators.RelativeStrengthIndex(data.close, period=period)


def _create_boll(data, **kwargs):
    period = kwargs.get('period', 20)
    devfactor = kwargs.get('devfactor', 2)
    return bt.indicators.BollingerBands(data.close, period=period, devfactor=devfactor)


def _create_kdj(data, **kwargs):
    """KDJ: 组合 Stochastic + SMA"""
    period = kwargs.get('period', 14)
    period_d = kwargs.get('period_d', 3)
    stoch = bt.indicators.StochasticFull(
        data,
        period=period,
        period_dfast=period,
        period_dslow=period_d,
    )
    # K=percK, D=percD, J=3K-2D
    # 用一个包装对象暴露 k, d, j 三条线
    class KDJWrapper:
        def __init__(self, stoch):
            self.k = stoch.percK
            self.d = stoch.percD
            self.j = 3 * stoch.percK - 2 * stoch.percD

    return KDJWrapper(stoch)


def _create_atr(data, **kwargs):
    period = kwargs.get('period', 14)
    return bt.indicators.AverageTrueRange(data, period=period)


def _create_adx(data, **kwargs):
    period = kwargs.get('period', 14)
    return bt.indicators.AverageDirectionalMovementIndex(data, period=period)


# 注册表：指标 ID → 创建函数
INDICATOR_REGISTRY = {
    'MA': _create_ma,
    'EMA': _create_ema,
    'MACD': _create_macd,
    'RSI': _create_rsi,
    'BOLL': _create_boll,
    'KDJ': _create_kdj,
    'ATR': _create_atr,
    'ADX': _create_adx,
}

# 指标元数据
INDICATOR_META = [
    {"id": "MA", "name": "移动平均线", "default_params": {"period": 20}, "description": "简单移动平均线"},
    {"id": "EMA", "name": "指数移动平均线", "default_params": {"period": 20}, "description": "指数加权移动平均线"},
    {"id": "MACD", "name": "MACD", "default_params": {"period_me1": 12, "period_me2": 26, "period_signal": 9}, "description": "异同移动平均线"},
    {"id": "RSI", "name": "相对强弱指标", "default_params": {"period": 14}, "description": "相对强弱指数"},
    {"id": "BOLL", "name": "布林带", "default_params": {"period": 20, "devfactor": 2}, "description": "布林带通道"},
    {"id": "KDJ", "name": "KDJ指标", "default_params": {"period": 14, "period_d": 3}, "description": "随机指标"},
    {"id": "ATR", "name": "平均真实波幅", "default_params": {"period": 14}, "description": "平均真实波幅"},
    {"id": "ADX", "name": "平均趋向指数", "default_params": {"period": 14}, "description": "平均趋向指数"},
]


# ─── 数据适配器 ───────────────────────────────────────────

def _stock_daily_to_dataframe(code: str, days: int = 120, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
    """从数据库提取日线数据，转为 Backtrader 兼容的 DataFrame"""
    db = next(get_db())
    query = db.query(StockDaily).filter(StockDaily.code == code)

    if start_date:
        query = query.filter(StockDaily.date >= start_date)
    if end_date:
        query = query.filter(StockDaily.date <= end_date)

    records = query.order_by(StockDaily.date.desc()).limit(days).all()
    db.close()

    if not records:
        return None

    records = list(reversed(records))  # 升序排列

    dates = [r.date for r in records]
    df = pd.DataFrame({
        'open': [r.open for r in records],
        'high': [r.high for r in records],
        'low': [r.low for r in records],
        'close': [r.close for r in records],
        'volume': [r.volume for r in records],
        'openinterest': [0.0] * len(records),
    }, index=pd.to_datetime(dates))

    return df


def _stock_daily_to_dicts(code: str, days: int = 120) -> tuple:
    """返回 (dates列表, prices字典, stock_name) 用于 API 响应"""
    db = next(get_db())
    query = db.query(StockDaily).filter(StockDaily.code == code)
    records = query.order_by(StockDaily.date.desc()).limit(days).all()
    db.close()

    if not records:
        return None, None, None

    records = list(reversed(records))

    dates = [r.date.strftime('%Y-%m-%d') for r in records]
    prices = {
        'open': [r.open for r in records],
        'high': [r.high for r in records],
        'low': [r.low for r in records],
        'close': [r.close for r in records],
        'volume': [r.volume for r in records],
    }
    return dates, prices


# ─── 结果序列化 ───────────────────────────────────────────

def _safe_float(value) -> Optional[float]:
    """安全转换 NaN/Inf 为 None"""
    if value is None:
        return None
    try:
        fv = float(value)
        if math.isnan(fv) or math.isinf(fv):
            return None
        return round(fv, 4)
    except (TypeError, ValueError):
        return None


def _extract_line_values(line, length: int) -> list:
    """从 backtrader Line 中提取值列表（oldest→newest）"""
    values = []
    for i in range(length - 1, -1, -1):
        try:
            values.append(_safe_float(line[-i]))
        except IndexError:
            values.append(None)
    return values


def _serialize_indicator(indicator, ind_type: str, data_length: int) -> dict:
    """将 Backtrader 指标对象序列化为 dict"""
    if ind_type == 'MA':
        return {'values': _extract_line_values(indicator.lines.sma, data_length)}
    elif ind_type == 'EMA':
        return {'values': _extract_line_values(indicator.lines.ema, data_length)}
    elif ind_type == 'MACD':
        macd_vals = _extract_line_values(indicator.lines.macd, data_length)
        signal_vals = _extract_line_values(indicator.lines.signal, data_length)
        histogram = []
        for m, s in zip(macd_vals, signal_vals):
            if m is not None and s is not None:
                histogram.append(round(m - s, 4))
            else:
                histogram.append(None)
        return {
            'macd': macd_vals,
            'signal': signal_vals,
            'histogram': histogram,
        }
    elif ind_type == 'RSI':
        return {'values': _extract_line_values(indicator.lines.rsi, data_length)}
    elif ind_type == 'BOLL':
        return {
            'upper': _extract_line_values(indicator.lines.top, data_length),
            'mid': _extract_line_values(indicator.lines.mid, data_length),
            'lower': _extract_line_values(indicator.lines.bot, data_length),
        }
    elif ind_type == 'KDJ':
        return {
            'k': _extract_line_values(indicator.k, data_length),
            'd': _extract_line_values(indicator.d, data_length),
            'j': _extract_line_values(indicator.j, data_length),
        }
    elif ind_type == 'ATR':
        return {'values': _extract_line_values(indicator.lines.atr, data_length)}
    elif ind_type == 'ADX':
        return {'values': _extract_line_values(indicator.lines.adx, data_length)}
    else:
        return {'values': []}


# ─── 缓存 ─────────────────────────────────────────────────

_cache: dict = {}
CACHE_MAX_SIZE = 100
CACHE_TTL = 300  # 5 分钟


def _cache_key(code: str, days: int, configs_json: str) -> str:
    return f"{code}_{days}_{configs_json}"


def _cache_get(code: str, days: int, configs_json: str) -> Optional[dict]:
    key = _cache_key(code, days, configs_json)
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry['time'] < CACHE_TTL:
            return entry['data']
        else:
            del _cache[key]
    return None


def _cache_set(code: str, days: int, configs_json: str, data: dict):
    """写入缓存，超出上限时淘汰最早条目"""
    key = _cache_key(code, days, configs_json)
    if len(_cache) >= CACHE_MAX_SIZE:
        oldest = min(_cache, key=lambda k: _cache[k]['time'])
        del _cache[oldest]
    _cache[key] = {'time': time.time(), 'data': data}


# ─── 引擎主体 ─────────────────────────────────────────────

class IndicatorEngine:
    """基于 Backtrader 的指标计算引擎"""

    @staticmethod
    def compute(code: str, configs: list, days: int = 120) -> dict:
        """计算指定股票的指标

        Args:
            code: 股票代码
            configs: 指标配置列表，如 [{"type": "MA", "params": {"period": 50}}, {"type": "RSI"}]
            days: 取最近多少天的数据

        Returns:
            dict: {
                "code": "000001",
                "name": "平安银行",
                "dates": [...],
                "prices": {"open": [...], ...},
                "indicators": {"ma": {"values": [...]}, ...}
            }
        """
        # 验证指标名
        for cfg in configs:
            if cfg['type'] not in INDICATOR_REGISTRY:
                raise ValueError(
                    f"不支持的指标: {cfg['type']}，支持: {', '.join(INDICATOR_REGISTRY)}"
                )

        # 检查缓存
        configs_json = json.dumps(configs, sort_keys=True)
        cached = _cache_get(code, days, configs_json)
        if cached:
            return cached

        # 从数据库取数据
        df = _stock_daily_to_dataframe(code, days)
        if df is None or df.empty:
            return None

        dates, prices = _stock_daily_to_dicts(code, days)
        data_length = len(dates)

        # 获取股票名
        db = next(get_db())
        stock = db.query(Stock).filter(Stock.code == code).first()
        db.close()
        name = stock.name if stock else ''

        # 创建 Backtrader 数据源并运行
        data_feed = bt.feeds.PandasData(dataname=df)

        cerebro = bt.Cerebro(stdstats=False)  # 关闭默认 observer 加速
        cerebro.adddata(data_feed)
        cerebro.addstrategy(_IndicatorStrategy, indicator_configs=configs)
        result = cerebro.run()

        strategy = result[0]
        indicator_results = {}
        for cfg in configs:
            ind_type = cfg['type']
            ind_obj = strategy._indicators.get(ind_type)
            if ind_obj is not None:
                indicator_results[ind_type.lower()] = _serialize_indicator(ind_obj, ind_type, data_length)

        response = {
            'code': code,
            'name': name,
            'dates': dates,
            'prices': prices,
            'indicators': indicator_results,
        }

        _cache_set(code, days, configs_json, response)
        return response

    @staticmethod
    def get_indicator_list() -> list:
        """返回可用指标清单"""
        return INDICATOR_META

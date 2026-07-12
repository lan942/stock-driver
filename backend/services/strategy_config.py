"""策略配置服务"""
import json
from typing import Any, Optional
from backend.utils.db import get_db
from backend.models.strategy import StrategyConfig


# 默认配置
DEFAULT_CONFIGS = {
    'target_annual_return': {'value': '0.15', 'description': '期望年化收益率'},
    'initial_capital': {'value': '100000', 'description': '初始资金（元）'},
    'max_positions': {'value': '5', 'description': '最大同时持仓只数'},
    'position_ratio': {'value': '0.2', 'description': '单只仓位占可用资金比例'},
    'stop_profit_pct': {'value': '0.06', 'description': '止盈比例（底线）'},
    'stop_loss_pct': {'value': '0.03', 'description': '止损比例（底线）'},
    'max_hold_days': {'value': '5', 'description': '最大持有天数'},
    'strategy_type': {'value': 'xgboost', 'description': '策略类型：xgboost'},
    'adaptive_score_threshold_behind': {'value': '0.50', 'description': '落后档选股最低分'},
    'adaptive_score_threshold_near': {'value': '0.35', 'description': '接近档选股最低分'},
    'adaptive_score_threshold_met': {'value': '0.15', 'description': '达标档选股最低分'},
    'adaptive_position_ratio_behind': {'value': '0.10', 'description': '落后档单只仓位比例'},
    'adaptive_position_ratio_near': {'value': '0.15', 'description': '接近档单只仓位比例'},
    'adaptive_position_ratio_met': {'value': '0.20', 'description': '达标档单只仓位比例'},
    'adaptive_min_days': {'value': '20', 'description': '动态调整预热交易日数'},
    'atr_period': {'value': '14', 'description': 'ATR计算周期'},
    'atr_profit_multiplier': {'value': '2.0', 'description': 'ATR止盈倍数（涨超N倍ATR卖出）'},
    'atr_loss_multiplier': {'value': '1.0', 'description': 'ATR止损倍数（跌超N倍ATR卖出）'},
    'dynamic_sell_enabled': {'value': 'true', 'description': '启用动态评分卖出（持仓期重新评分，分数恶化则卖出）'},
    'dynamic_sell_percentile_threshold': {'value': '0.30', 'description': '动态卖出百分位阈值（跌出全市场前N%则卖出）'},
    'dynamic_sell_score_decline_days': {'value': '2', 'description': '动态卖出连续下降天数（连续N天评分下降则卖出）'},
    'dynamic_sell_score_absolute_threshold': {'value': '0.30', 'description': '动态卖出绝对分阈值（评分低于此值则卖出）'},
    'dynamic_sell_min_hold_days': {'value': '2', 'description': '动态卖出最小持仓天数（买入后N天内不触发评分卖出）'},
}


class StrategyConfigService:
    """策略配置服务"""

    @staticmethod
    def _init_defaults(db) -> None:
        """初始化默认配置（如不存在）"""
        for key, cfg in DEFAULT_CONFIGS.items():
            existing = db.query(StrategyConfig).filter(StrategyConfig.key == key).first()
            if not existing:
                db.add(StrategyConfig(key=key, value=cfg['value'], description=cfg['description']))
        db.commit()

    @staticmethod
    def get(key: str) -> Optional[Any]:
        """获取单个配置值，自动类型转换"""
        db = next(get_db())
        config = db.query(StrategyConfig).filter(StrategyConfig.key == key).first()
        db.close()

        if config is None:
            return None

        raw = config.value
        if key in ('target_annual_return', 'initial_capital', 'stop_profit_pct', 'stop_loss_pct',
                    'max_hold_days', 'position_ratio',
                    'adaptive_score_threshold_behind', 'adaptive_score_threshold_near', 'adaptive_score_threshold_met',
                    'adaptive_position_ratio_behind', 'adaptive_position_ratio_near', 'adaptive_position_ratio_met',
                    'atr_profit_multiplier', 'atr_loss_multiplier',
                    'dynamic_sell_percentile_threshold', 'dynamic_sell_score_absolute_threshold'):
            try:
                return float(raw)
            except ValueError:
                return raw
        if key in ('max_positions', 'adaptive_min_days', 'atr_period', 'dynamic_sell_score_decline_days', 'dynamic_sell_min_hold_days'):
            try:
                return int(raw)
            except ValueError:
                return raw
        return raw

    @staticmethod
    def set(key: str, value: Any) -> None:
        """设置单个配置"""
        db = next(get_db())
        config = db.query(StrategyConfig).filter(StrategyConfig.key == key).first()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        else:
            value = str(value)
        if config:
            config.value = value
        else:
            db.add(StrategyConfig(key=key, value=value))
        db.commit()

        # 同步 initial_capital 到 StrategyCash 表
        if key == 'initial_capital':
            from backend.models.strategy import StrategyCash
            cash = db.query(StrategyCash).first()
            init_val = float(value)
            if cash:
                diff = init_val - cash.initial_capital
                cash.initial_capital = init_val
                cash.balance = round(cash.balance + diff, 2)
            else:
                db.add(StrategyCash(balance=init_val, initial_capital=init_val))
            db.commit()

        db.close()

    @staticmethod
    def get_all() -> dict:
        """获取所有配置"""
        db = next(get_db())
        StrategyConfigService._init_defaults(db)

        configs = db.query(StrategyConfig).all()
        db.close()

        result = {}
        for c in configs:
            result[c.key] = StrategyConfigService.get(c.key)

        # 计算预期年化收益
        stop_profit = result.get('stop_profit_pct', 0.06)
        stop_loss = result.get('stop_loss_pct', 0.03)
        win_rate_estimate = 0.45
        expected_per_trade = win_rate_estimate * stop_profit - (1 - win_rate_estimate) * stop_loss
        result['expected_per_trade'] = round(expected_per_trade, 4)
        result['risk_reward_ratio'] = round(stop_profit / stop_loss, 2) if stop_loss > 0 else 0

        return result

    @staticmethod
    def get_expected_return() -> dict:
        """获取预期收益信息"""
        stop_profit = StrategyConfigService.get('stop_profit_pct')
        stop_loss = StrategyConfigService.get('stop_loss_pct')
        target = StrategyConfigService.get('target_annual_return')

        win_rate_estimate = 0.45
        expected_per_trade = win_rate_estimate * float(stop_profit) - (1 - win_rate_estimate) * float(stop_loss)
        risk_reward_ratio = float(stop_profit) / float(stop_loss) if float(stop_loss) > 0 else 0

        return {
            'win_rate_estimate': win_rate_estimate,
            'expected_per_trade': round(expected_per_trade, 4),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'target_annual_return': float(target) if target else 0.15,
        }

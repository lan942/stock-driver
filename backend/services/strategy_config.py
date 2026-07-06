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
    'stop_profit_pct': {'value': '0.06', 'description': '止盈比例'},
    'stop_loss_pct': {'value': '0.03', 'description': '止损比例'},
    'max_hold_days': {'value': '5', 'description': '最大持有天数'},
    'factor_weights': {
        'value': json.dumps({"trend": 0.30, "momentum": 0.25, "volume": 0.20, "reversal": 0.15, "volatility": 0.10}),
        'description': '因子权重',
    },
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
                    'max_hold_days', 'position_ratio'):
            try:
                return float(raw)
            except ValueError:
                return raw
        if key == 'max_positions':
            try:
                return int(raw)
            except ValueError:
                return raw
        if key == 'factor_weights':
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
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

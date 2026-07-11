"""策略模块初始化

注册所有可用策略，提供统一的策略选择接口。
"""

from .base_strategy import IStrategy
from .ml_strategy import XGBoostStrategy


STRATEGY_REGISTRY = {
    'xgboost': XGBoostStrategy,
}


def get_all_strategies() -> dict:
    """获取所有可用策略"""
    return {
        name: {
            'name': strategy.STRATEGY_NAME,
            'description': strategy.STRATEGY_DESCRIPTION,
        }
        for name, strategy in STRATEGY_REGISTRY.items()
    }


def get_strategy(strategy_name: str) -> IStrategy:
    """获取指定策略实例

    Args:
        strategy_name: 策略名称

    Returns:
        策略实例

    Raises:
        ValueError: 策略不存在
    """
    if strategy_name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    return STRATEGY_REGISTRY[strategy_name]()

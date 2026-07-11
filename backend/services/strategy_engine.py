"""策略引擎（策略调度器）

根据配置选择不同的策略进行股票评分和推荐。
作为统一入口，保持向后兼容性。
"""

from typing import Optional

from backend.services.strategy_config import StrategyConfigService
from backend.services.strategies import get_strategy, get_all_strategies


class StrategyEngine:
    """策略引擎调度器"""

    @staticmethod
    def get_current_strategy():
        """获取当前配置的策略实例"""
        strategy_name = StrategyConfigService.get('strategy_type') or 'xgboost'
        return get_strategy(strategy_name)

    @staticmethod
    def score_stock(code: str) -> Optional[dict]:
        """对单只股票进行评分（委托给当前策略）"""
        strategy = StrategyEngine.get_current_strategy()
        return strategy.score_stock(code)

    @staticmethod
    def generate_recommendations(
        available_slots: int,
        available_cash: float,
    ) -> list:
        """生成买入推荐清单（委托给当前策略）"""
        strategy = StrategyEngine.get_current_strategy()
        return strategy.generate_recommendations(available_slots, available_cash)

    @staticmethod
    def get_all_strategies_info() -> dict:
        """获取所有可用策略信息"""
        return get_all_strategies()

    @staticmethod
    def get_strategy_by_name(name: str):
        """获取指定策略实例"""
        return get_strategy(name)

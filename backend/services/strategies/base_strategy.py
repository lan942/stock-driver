"""策略基类接口

定义统一的策略评分接口，所有具体策略必须实现此接口。
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class IStrategy(ABC):
    """策略接口基类"""

    STRATEGY_NAME: str = "base"
    STRATEGY_DESCRIPTION: str = "策略基类"

    @abstractmethod
    def score_stock(self, code: str) -> Optional[Dict[str, Any]]:
        """对单只股票进行评分

        Args:
            code: 股票代码

        Returns:
            评分结果字典，包含:
                - code: 股票代码
                - total_score: 综合评分 (0~1)
                - factor_scores: 各因子得分字典
                - latest_close: 最新收盘价
                - latest_volume: 最新成交量
                - latest_change_pct: 最新涨跌幅
            None: 股票不符合策略条件（如涨跌停、数据不足等）
        """
        pass

    @abstractmethod
    def generate_recommendations(
        self,
        available_slots: int,
        available_cash: float,
    ) -> list:
        """生成买入推荐清单

        Args:
            available_slots: 可用持仓位数
            available_cash: 可用资金

        Returns:
            推荐列表
        """
        pass

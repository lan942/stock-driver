from __future__ import annotations

import logging
from typing import Any, Callable, Optional

import pandas as pd

from backend.services.crawler.base import CrawlerBase, CrawlerError, CrawlerResult
from backend.services.crawler.normalizer import normalize_tencent_daily_df
from backend.services.crawler.rate_limiter import RateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)

DEFAULT_DAILY_SOURCES = [
    {
        "name": "tencent_akshare",
        "type": "akshare",
        "function": "stock_zh_a_daily",
        "max_retries": 3,
        "base_wait": 0.5,
        "max_wait": 30.0,
    },
]


class TencentStockDailyCrawler(CrawlerBase):
    """腾讯股票日线数据爬虫"""

    def __init__(
        self,
        sources: Optional[list[dict[str, Any]]] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        if rate_limiter is None:
            rate_limiter = RateLimiter(RateLimitConfig(
                max_retries=3,
                base_wait=0.5,
                max_wait=30.0,
                requests_per_window=300,
                window_seconds=60.0,
            ))
        super().__init__(
            sources=sources or DEFAULT_DAILY_SOURCES,
            rate_limiter=rate_limiter,
        )

    def _fetch_from_source(self, source: dict[str, Any], **kwargs: Any) -> pd.DataFrame:
        import akshare as ak

        source_type = source.get("type", "akshare")

        if source_type == "akshare":
            func_name = source.get("function", "stock_zh_a_daily")
            symbol = kwargs.get("symbol", "")
            start_date = kwargs.get("start_date", "")
            end_date = kwargs.get("end_date", "")
            adjust = kwargs.get("adjust", "qfq")

            try:
                func = getattr(ak, func_name)
                df = func(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )
            except AttributeError as e:
                raise CrawlerError(f"akshare function not found: {func_name}") from e
            except Exception as e:
                if self._is_rate_limit_error(e):
                    raise
                raise CrawlerError(f"Failed to fetch daily data: {e}") from e

            if df is None or df.empty:
                raise CrawlerError("Empty daily data")

            return df

        raise CrawlerError(f"Unsupported source type: {source_type}")

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        rate_limit_keywords = [
            "429",
            "rate limit",
            "too many requests",
            "请求过于频繁",
            "频率限制",
            "限流",
            "访问太频繁",
            "frequently",
            "blocked",
            "forbidden",
            "403",
        ]
        return any(keyword in msg for keyword in rate_limit_keywords)

    def _format_symbol(self, code: str) -> str:
        """将股票代码转换为腾讯格式：sh600519 / sz000001"""
        code_clean = str(code).strip().lower()
        if code_clean.startswith(("sh", "sz", "bj")):
            return code_clean
        if code_clean.startswith("6"):
            return f"sh{code_clean}"
        elif code_clean.startswith(("0", "3")):
            return f"sz{code_clean}"
        else:
            return f"sh{code_clean}"

    def fetch_single(
        self,
        code: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """
        获取单只股票的日线数据

        Args:
            code: 股票代码（支持 600519 或 sh600519 格式）
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD
            adjust: 复权类型：qfq-前复权, hfq-后复权, ""-不复权

        Returns:
            归一化后的 DataFrame，包含 code/date/open/high/low/close/volume/
            turnover/turnover_rate/change_percent/pe/pb/market_cap
        """
        symbol = self._format_symbol(code)
        code_clean = symbol[2:] if len(symbol) > 2 and symbol[:2] in ("sh", "sz", "bj") else symbol

        result = self.fetch(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

        if not result.success or result.data is None:
            raise CrawlerError(result.error or "Failed to fetch daily data")

        return normalize_tencent_daily_df(result.data, code_clean)

    def fetch_batch(
        self,
        codes: list[str],
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> tuple[int, int, list[pd.DataFrame]]:
        """
        批量获取多只股票的日线数据

        Args:
            codes: 股票代码列表
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD
            adjust: 复权类型
            progress_callback: 进度回调函数 (当前序号, 总数, 当前股票代码)

        Returns:
            (成功数, 失败数, 成功的DataFrame列表)
        """
        success_count = 0
        fail_count = 0
        result_dfs: list[pd.DataFrame] = []
        total = len(codes)

        for idx, code in enumerate(codes):
            try:
                df = self.fetch_single(code, start_date, end_date, adjust)
                result_dfs.append(df)
                success_count += 1
            except Exception as e:
                fail_count += 1
                logger.warning("Fetch daily failed for %s: %s", code, e)

            if progress_callback:
                try:
                    progress_callback(idx + 1, total, code)
                except Exception as cb_err:
                    logger.warning("Progress callback error: %s", cb_err)

        return success_count, fail_count, result_dfs

    def fetch_single_raw(
        self,
        code: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> CrawlerResult:
        """获取单只股票原始数据（不归一化）"""
        symbol = self._format_symbol(code)
        return self.fetch(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

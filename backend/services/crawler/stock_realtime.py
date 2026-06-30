from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd

from backend.services.crawler.base import CrawlerBase, CrawlerError, CrawlerResult
from backend.services.crawler.normalizer import normalize_stock_realtime_data
from backend.services.crawler.rate_limiter import RateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)

DEFAULT_REALTIME_SOURCES = [
    {
        "name": "akshare_em_spot",
        "type": "akshare",
        "function": "stock_zh_a_spot_em",
        "field_units": {
            "price": "yuan",
            "volume": "shares",
            "turnover": "yuan",
            "turnover_rate": "percent",
            "change_percent": "percent",
        },
        "max_retries": 3,
        "base_wait": 1.0,
        "max_wait": 60.0,
    },
    {
        "name": "akshare_sina_spot",
        "type": "akshare",
        "function": "stock_zh_a_spot",
        "field_units": {
            "price": "yuan",
            "volume": "shares",
            "turnover": "yuan",
            "turnover_rate": "percent",
            "change_percent": "percent",
        },
        "max_retries": 3,
        "base_wait": 1.0,
        "max_wait": 60.0,
    },
]


class StockRealtimeCrawler(CrawlerBase):
    def __init__(
        self,
        sources: Optional[list[dict[str, Any]]] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        if rate_limiter is None:
            rate_limiter = RateLimiter(RateLimitConfig(
                max_retries=3,
                base_wait=1.0,
                max_wait=60.0,
                requests_per_window=10,
                window_seconds=60.0,
            ))
        super().__init__(
            sources=sources or DEFAULT_REALTIME_SOURCES,
            rate_limiter=rate_limiter,
        )

    def _fetch_from_source(self, source: dict[str, Any], **kwargs: Any) -> list[dict[str, Any]]:
        import akshare as ak

        source_type = source.get("type", "akshare")
        field_units = source.get("field_units", {})
        func_name = source.get("function", "stock_zh_a_spot_em")

        if source_type == "akshare":
            try:
                df = getattr(ak, func_name)()
            except AttributeError as e:
                raise CrawlerError(f"akshare function not found: {func_name}") from e
            except Exception as e:
                if self._is_rate_limit_error(e):
                    raise
                raise CrawlerError(f"Failed to fetch realtime data: {e}") from e

            if df is None or df.empty:
                raise CrawlerError("Empty realtime data")

            return self._normalize_dataframe(df, field_units)

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
            "connection reset",
        ]
        return any(keyword in msg for keyword in rate_limit_keywords)

    def _normalize_dataframe(
        self, df: pd.DataFrame, field_units: dict[str, str]
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            try:
                normalized = normalize_stock_realtime_data(row.to_dict(), field_units)
                if normalized["code"]:
                    result.append(normalized)
            except Exception as e:
                logger.warning("Failed to normalize realtime row: %s", e)
                continue
        return result

    def fetch_realtime(self) -> list[dict[str, Any]]:
        result = self.fetch()
        if not result.success:
            raise CrawlerError(result.error or "Failed to fetch realtime data")
        return result.data or []

    def fetch_realtime_df(self) -> pd.DataFrame:
        data = self.fetch_realtime()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    def fetch_single_stock(self, code: str) -> Optional[dict[str, Any]]:
        all_data = self.fetch_realtime()
        for item in all_data:
            if item["code"] == code:
                return item
        return None

    def fetch_batch_stocks(self, codes: list[str]) -> list[dict[str, Any]]:
        code_set = set(codes)
        all_data = self.fetch_realtime()
        return [item for item in all_data if item["code"] in code_set]

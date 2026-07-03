from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd

from backend.services.crawler.base import CrawlerBase, CrawlerError, CrawlerResult
from backend.services.crawler.normalizer import normalize_stock_list_row
from backend.services.crawler.rate_limiter import RateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)

DEFAULT_SOURCES = [
    {
        "name": "akshare_sina",
        "type": "akshare",
        "function": "stock_info_a_code_name",
        "max_retries": 3,
        "base_wait": 1.0,
        "max_wait": 60.0,
    },
    {
        "name": "akshare_zh_a_spot",
        "type": "akshare_spot",
        "function": "stock_zh_a_spot",
        "max_retries": 3,
        "base_wait": 1.0,
        "max_wait": 60.0,
    },
    {
        "name": "akshare_em_spot",
        "type": "akshare_spot",
        "function": "stock_zh_a_spot_em",
        "max_retries": 3,
        "base_wait": 1.0,
        "max_wait": 60.0,
    },
    {
        "name": "akshare_sh_spot",
        "type": "akshare_spot",
        "function": "stock_sh_a_spot_em",
        "max_retries": 3,
        "base_wait": 1.0,
        "max_wait": 60.0,
    },
    {
        "name": "akshare_sz_spot",
        "type": "akshare_spot",
        "function": "stock_sz_a_spot_em",
        "max_retries": 3,
        "base_wait": 1.0,
        "max_wait": 60.0,
    },
]


class StockListCrawler(CrawlerBase):
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
            sources=sources or DEFAULT_SOURCES,
            rate_limiter=rate_limiter,
        )

    def _fetch_from_source(self, source: dict[str, Any], **kwargs: Any) -> list[dict[str, Any]]:
        import akshare as ak

        source_type = source.get("type", "akshare")

        if source_type == "akshare":
            func_name = source.get("function", "stock_info_a_code_name")
            try:
                df = getattr(ak, func_name)()
            except AttributeError as e:
                raise CrawlerError(f"akshare function not found: {func_name}") from e
            except Exception as e:
                if self._is_rate_limit_error(e):
                    raise
                raise CrawlerError(f"Failed to fetch stock list: {e}") from e

            if df is None or df.empty:
                raise CrawlerError("Empty stock list data")

            return self._normalize_dataframe(df)

        if source_type == "akshare_spot":
            func_name = source.get("function", "stock_zh_a_spot_em")
            try:
                df = getattr(ak, func_name)()
            except AttributeError as e:
                raise CrawlerError(f"akshare function not found: {func_name}") from e
            except Exception as e:
                if self._is_rate_limit_error(e):
                    raise
                raise CrawlerError(f"Failed to fetch stock list from spot: {e}") from e

            if df is None or df.empty:
                raise CrawlerError("Empty stock list data from spot")

            return self._normalize_spot_dataframe(df)

        raise CrawlerError(f"Unsupported source type: {source_type}")

    def _normalize_spot_dataframe(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """从东财实时行情快照中提取股票代码和名称"""
        result: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            try:
                code = str(row.get('代码', row.get('code', ''))).strip()
                name = str(row.get('名称', row.get('name', ''))).strip()
                if code and name:
                    result.append({"code": code, "name": name})
            except Exception as e:
                logger.warning("Failed to normalize spot stock list row: %s", e)
                continue
        return result

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
        ]
        return any(keyword in msg for keyword in rate_limit_keywords)

    def _normalize_dataframe(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            try:
                normalized = normalize_stock_list_row(row.to_dict())
                if normalized["code"] and normalized["name"]:
                    result.append(normalized)
            except Exception as e:
                logger.warning("Failed to normalize stock list row: %s", e)
                continue
        return result

    def fetch_stock_list(self) -> list[dict[str, Any]]:
        result = self.fetch()
        if not result.success:
            raise CrawlerError(result.error or "Failed to fetch stock list")
        return result.data or []

    def fetch_stock_list_df(self) -> pd.DataFrame:
        data = self.fetch_stock_list()
        if not data:
            return pd.DataFrame(columns=["code", "name"])
        return pd.DataFrame(data)

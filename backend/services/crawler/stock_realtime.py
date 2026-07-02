from __future__ import annotations

import logging
import time
from typing import Any, Optional

import pandas as pd
import requests

from backend.services.crawler.base import CrawlerBase, CrawlerError, CrawlerResult
from backend.services.crawler.normalizer import normalize_stock_realtime_data
from backend.services.crawler.rate_limiter import RateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)

# 主源：直连东方财富 push2 API；备用源：akshare 封装的东方财富接口
# 直连源失败时由 base.py 的多源切换逻辑自动切换到 akshare
DEFAULT_REALTIME_SOURCES = [
    {
        "name": "eastmoney_direct_http",
        "type": "direct_http",
        "url": "https://push2.eastmoney.com/api/qt/clist/get",
        "params": {
            "pn": 1,
            "pz": 100,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2,
            "invt": 2,
            "fid": "f12",
            "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
            "fields": "f2,f3,f5,f6,f8,f9,f12,f14,f15,f16,f17,f20,f23",
        },
        "field_mapping": {
            "f2": "close",
            "f3": "change_percent",
            "f5": "volume",
            "f6": "turnover",
            "f8": "turnover_rate",
            "f9": "pe",
            "f12": "code",
            "f14": "name",
            "f15": "high",
            "f16": "low",
            "f17": "open",
            "f20": "market_cap",
            "f23": "pb",
        },
        "field_units": {
            "price": "yuan",
            "volume": "shares",
            "turnover": "yuan",
            "turnover_rate": "percent",
            "change_percent": "percent",
            "market_cap": "yuan",
        },
        "max_retries": 3,
        "base_wait": 0.0,
        "max_wait": 60.0,
        "http_retries": 5,
        "http_retry_wait": 1.0,
        "timeout": 30,
        "page_sleep": 0.8,
    },
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
        "base_wait": 0.0,
        "max_wait": 60.0,
    },
]

_EASTMONEY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "http://quote.eastmoney.com/",
}


class StockRealtimeCrawler(CrawlerBase):
    def __init__(
        self,
        sources: Optional[list[dict[str, Any]]] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        if rate_limiter is None:
            rate_limiter = RateLimiter(RateLimitConfig(
                max_retries=3,
                base_wait=0.0,
                max_wait=60.0,
                requests_per_window=60,
                window_seconds=60.0,
            ))
        super().__init__(
            sources=sources or DEFAULT_REALTIME_SOURCES,
            rate_limiter=rate_limiter,
        )

    def _fetch_from_source(self, source: dict[str, Any], **kwargs: Any) -> list[dict[str, Any]]:
        source_type = source.get("type", "akshare")
        field_units = source.get("field_units", {})

        if source_type == "akshare":
            return self._fetch_from_akshare(source, field_units)
        if source_type == "direct_http":
            return self._fetch_direct_http(source, field_units)

        raise CrawlerError(f"Unsupported source type: {source_type}")

    def _fetch_from_akshare(
        self, source: dict[str, Any], field_units: dict[str, str]
    ) -> list[dict[str, Any]]:
        import akshare as ak

        func_name = source.get("function", "stock_zh_a_spot_em")
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

    def _fetch_direct_http(
        self, source: dict[str, Any], field_units: dict[str, str]
    ) -> list[dict[str, Any]]:
        url = source["url"]
        base_params = source["params"]
        field_mapping = source["field_mapping"]
        timeout = source.get("timeout", 30)
        http_retries = source.get("http_retries", 5)
        http_retry_wait = source.get("http_retry_wait", 1.0)
        page_sleep = source.get("page_sleep", 0.8)
        page_size = base_params.get("pz", 100)

        all_rows: list[dict[str, Any]] = []
        page_num = 1
        total: Optional[int] = None

        while True:
            params = {**base_params, "pn": page_num, "pz": page_size}
            payload = self._http_get_with_retry(
                url, params, timeout, http_retries, http_retry_wait
            )
            data = payload.get("data") if payload else None
            if not data:
                raise CrawlerError("Empty response from Eastmoney direct API")

            if total is None:
                total = data.get("total", 0)
                if total == 0:
                    raise CrawlerError("Empty realtime data from direct API")
                logger.info(
                    "Direct HTTP: fetching %d stocks across %d pages",
                    total, (total + page_size - 1) // page_size,
                )

            rows = data.get("diff") or []
            if not rows:
                break
            all_rows.extend(rows)

            if len(all_rows) >= total:
                break

            page_num += 1
            time.sleep(page_sleep)

        logger.info("Direct HTTP: fetched %d/%d rows", len(all_rows), total or 0)

        result: list[dict[str, Any]] = []
        for row in all_rows:
            code = row.get("f12")
            if code is None or code in ("", "-"):
                continue
            normalized_row = {
                field_mapping[k]: v for k, v in row.items() if k in field_mapping
            }
            try:
                normalized = normalize_stock_realtime_data(normalized_row, field_units)
                if normalized["code"]:
                    result.append(normalized)
            except Exception as e:
                logger.warning("Failed to normalize direct HTTP row: %s", e)
                continue
        return result

    def _http_get_with_retry(
        self,
        url: str,
        params: dict[str, Any],
        timeout: int,
        max_retries: int,
        retry_wait: float,
    ) -> dict[str, Any]:
        last_exc: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url, params=params, timeout=timeout, headers=_EASTMONEY_HEADERS
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                last_exc = e
                logger.warning(
                    "Direct HTTP attempt %d/%d failed: %s",
                    attempt + 1, max_retries, str(e),
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_wait * (2 ** attempt))
        raise CrawlerError(
            f"Direct HTTP fetch failed after {max_retries} retries: {last_exc}"
        )

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

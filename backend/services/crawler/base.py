from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CrawlerError(Exception):
    pass


class RateLimitError(CrawlerError):
    pass


@dataclass
class CrawlerResult:
    data: Any = None
    success: bool = False
    error: Optional[str] = None
    source: str = ""


class CrawlerBase(ABC):
    """爬虫基类：多源切换、限流退避、错误重试。"""

    _RATE_LIMIT_KEYWORDS = (
        "429",
        "rate limit",
        "too many requests",
        "请求过于频繁",
        "频率限制",
        "限流",
        "访问太频繁",
        "connection reset",
        "frequently",
        "blocked",
        "forbidden",
        "403",
    )

    def __init__(
        self,
        sources: Optional[list[dict[str, Any]]] = None,
        rate_limiter: Optional[Any] = None,
    ) -> None:
        self._sources = sources or []
        self._rate_limiter = rate_limiter
        self._current_source_idx = 0

    @abstractmethod
    def _fetch_from_source(self, source: dict[str, Any], **kwargs: Any) -> Any:
        pass

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(keyword in msg for keyword in self._RATE_LIMIT_KEYWORDS)

    def fetch(self, **kwargs: Any) -> CrawlerResult:
        if not self._sources:
            return CrawlerResult(success=False, error="No data sources configured")

        last_error: Optional[Exception] = None
        tried_sources: set[int] = set()

        while len(tried_sources) < len(self._sources):
            source_idx = self._current_source_idx
            tried_sources.add(source_idx)
            source = self._sources[source_idx]

            try:
                if self._rate_limiter:
                    self._rate_limiter.wait_for_slot()

                data = self._fetch_with_retry(source, **kwargs)
                return CrawlerResult(
                    data=data,
                    success=True,
                    source=source.get("name", "unknown"),
                )
            except RateLimitError as e:
                last_error = e
                logger.warning(
                    "Rate limit exhausted for source %s, switching to next",
                    source.get("name", "unknown"),
                )
                self._switch_to_next_source()
            except Exception as e:
                last_error = e
                logger.error(
                    "Fetch failed for source %s: %s",
                    source.get("name", "unknown"),
                    str(e),
                )
                self._switch_to_next_source()

        return CrawlerResult(
            success=False,
            error=str(last_error) if last_error else "All sources failed",
        )

    def _fetch_with_retry(self, source: dict[str, Any], **kwargs: Any) -> Any:
        max_retries = source.get("max_retries", 3)
        base_wait = source.get("base_wait", 1.0)
        max_wait = source.get("max_wait", 60.0)

        last_exc: Optional[Exception] = None

        for attempt_idx in range(max_retries):
            try:
                return self._fetch_from_source(source, **kwargs)
            except Exception as e:
                last_exc = e
                if not self._is_rate_limit_error(e):
                    raise
                wait_time = min(base_wait * (2 ** attempt_idx), max_wait)
                logger.warning(
                    "Rate limit hit, attempt %d/%d, waiting %.1fs",
                    attempt_idx + 1,
                    max_retries,
                    wait_time,
                )
                time.sleep(wait_time)

        raise RateLimitError(
            f"Max retries ({max_retries}) exceeded for source: {source.get('name', 'unknown')}"
        )

    def _switch_to_next_source(self) -> None:
        self._current_source_idx = (self._current_source_idx + 1) % len(self._sources)
        logger.info(
            "Switched to source: %s",
            self._sources[self._current_source_idx].get("name", "unknown"),
        )

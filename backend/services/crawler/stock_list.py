from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd

from backend.services.crawler.base import CrawlerBase, CrawlerError
from backend.services.crawler.normalizer import normalize_stock_list_row
from backend.services.crawler.rate_limiter import RateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)

# 沪深交易所直连接口参数
SH_SYMBOL_MAIN_A = "主板A股"
SH_SYMBOL_KCB = "科创板"
SZ_SYMBOL_A_LIST = "A股列表"
BJ_FETCH_TIMEOUT = 15

# 主源：沪深交易所直连合并（避开 akshare stock_info_a_code_name 对 BSE 的强依赖）
# 备用源：东方财富实时快照（akshare_em_spot）
DEFAULT_SOURCES = [
    {
        "name": "akshare_sh_sz",
        "type": "akshare_sh_sz",
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

        source_type = source.get("type", "akshare_sh_sz")
        source_name = source.get("name", source_type)

        if source_type == "akshare_sh_sz":
            logger.info("Source %s: 开始获取沪深 A 股列表", source_name)
            sh_rows: list[dict[str, Any]] = []
            sz_rows: list[dict[str, Any]] = []

            # SH 主板独立 try/except
            try:
                sh_df = ak.stock_info_sh_name_code(symbol=SH_SYMBOL_MAIN_A)
                if sh_df is None or sh_df.empty:
                    logger.warning("Source %s: SH 主板接口返回空数据", source_name)
                else:
                    sh_rows = self._normalize_sh_dataframe(sh_df)
                    logger.info(
                        "Source %s: SH 主板标准化后 %d 条", source_name, len(sh_rows)
                    )
            except Exception as e:
                if self._is_rate_limit_error(e):
                    raise
                logger.warning("Source %s: SH 主板接口失败: %s", source_name, e)

            # SH 科创板独立 try/except：单边失败不影响其他板块
            try:
                sh_kcb_df = ak.stock_info_sh_name_code(symbol=SH_SYMBOL_KCB)
                if sh_kcb_df is None or sh_kcb_df.empty:
                    logger.warning("Source %s: SH 科创板接口返回空数据", source_name)
                else:
                    sh_kcb_rows = self._normalize_sh_dataframe(sh_kcb_df)
                    logger.info(
                        "Source %s: SH 科创板标准化后 %d 条", source_name, len(sh_kcb_rows)
                    )
                    sh_rows.extend(sh_kcb_rows)
            except Exception as e:
                if self._is_rate_limit_error(e):
                    raise
                logger.warning("Source %s: SH 科创板接口失败: %s", source_name, e)

            # SZ 独立 try/except
            try:
                sz_df = ak.stock_info_sz_name_code(symbol=SZ_SYMBOL_A_LIST)
                if sz_df is None or sz_df.empty:
                    logger.warning("Source %s: SZ 接口返回空数据", source_name)
                else:
                    sz_rows = self._normalize_sz_dataframe(sz_df)
                    logger.info(
                        "Source %s: SZ 标准化后 %d 条", source_name, len(sz_rows)
                    )
            except Exception as e:
                if self._is_rate_limit_error(e):
                    raise
                logger.warning("Source %s: SZ 接口失败: %s", source_name, e)

            # 沪深都失败 → 主源失败，交给 CrawlerBase 切换备用源
            if not sh_rows and not sz_rows:
                raise CrawlerError(
                    f"Source {source_name}: SH 和 SZ 接口均失败或返回空"
                )

            # 合并去重（按 code）
            merged: dict[str, dict[str, Any]] = {}
            for row in sh_rows + sz_rows:
                if row["code"] and row["code"] not in merged:
                    merged[row["code"]] = row
            result = list(merged.values())
            logger.info(
                "Source %s: SH(主板+科创板)+SZ 合并去重后 %d 条", source_name, len(result)
            )

            # BJ 作为可选补充：失败仅 WARN，不影响主列表返回
            try:
                bj_df = ak.stock_info_bj_name_code()
                if bj_df is None or bj_df.empty:
                    logger.warning("Source %s: BJ 接口返回空数据", source_name)
                else:
                    bj_rows = self._normalize_bj_dataframe(bj_df)
                    added = 0
                    for row in bj_rows:
                        if row["code"] and row["code"] not in merged:
                            merged[row["code"]] = row
                            added += 1
                    result = list(merged.values())
                    logger.info(
                        "Source %s: BJ 补充 %d 条，最终 %d 条",
                        source_name,
                        added,
                        len(result),
                    )
            except Exception as e:
                # BJ 失败属于预期容错场景，仅 WARN 不抛错
                logger.warning(
                    "Source %s: BJ 接口不可用，跳过 BJ 股票: %s",
                    source_name,
                    e,
                )

            return result

        if source_type == "akshare_spot":
            func_name = source.get("function", "stock_zh_a_spot_em")
            logger.info("Source %s: 调用 %s", source_name, func_name)
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

            rows = self._normalize_spot_dataframe(df)
            logger.info(
                "Source %s: spot 标准化后 %d 条", source_name, len(rows)
            )
            return rows

        raise CrawlerError(f"Unsupported source type: {source_type}")

    def _normalize_sh_dataframe(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """上交所股票列表标准化：列 [证券代码, 证券简称, ...]"""
        result: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            try:
                row_dict = {
                    "code": row.get("证券代码", row.get("code", "")),
                    "name": row.get("证券简称", row.get("name", "")),
                }
                normalized = normalize_stock_list_row(row_dict)
                if normalized["code"] and normalized["name"]:
                    result.append(normalized)
            except Exception as e:
                logger.warning("Failed to normalize SH stock list row: %s", e)
                continue
        return result

    def _normalize_sz_dataframe(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """深交所股票列表标准化：列 [板块, A股代码, A股简称, ...]"""
        result: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            try:
                row_dict = {
                    "code": row.get("A股代码", row.get("code", "")),
                    "name": row.get("A股简称", row.get("name", "")),
                }
                normalized = normalize_stock_list_row(row_dict)
                if normalized["code"] and normalized["name"]:
                    result.append(normalized)
            except Exception as e:
                logger.warning("Failed to normalize SZ stock list row: %s", e)
                continue
        return result

    def _normalize_bj_dataframe(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """北交所股票列表标准化：列名与 SH 类似 [证券代码, 证券简称, ...]
        BJ 股票代码以 8/4 开头，仍属于 A 股范畴，纳入 a_share_prefixes 过滤。
        """
        result: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            try:
                row_dict = {
                    "code": row.get("证券代码", row.get("code", "")),
                    "name": row.get("证券简称", row.get("name", "")),
                }
                normalized = normalize_stock_list_row(row_dict)
                if normalized["code"] and normalized["name"]:
                    result.append(normalized)
            except Exception as e:
                logger.warning("Failed to normalize BJ stock list row: %s", e)
                continue
        return result

    def _normalize_spot_dataframe(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """从实时行情快照中提取股票代码和名称，清洗代码格式并过滤非A股"""
        result: list[dict[str, Any]] = []
        a_share_prefixes = ('6', '0', '3', '8', '68')
        for _, row in df.iterrows():
            try:
                code = str(row.get('代码', row.get('code', ''))).strip()
                name = str(row.get('名称', row.get('name', ''))).strip()

                code = code.lower().replace('sh', '').replace('sz', '').replace('bj', '')

                if not code.isdigit():
                    continue

                if not code.startswith(a_share_prefixes):
                    continue

                if code and name:
                    result.append({"code": code, "name": name})
            except Exception as e:
                logger.warning("Failed to normalize spot stock list row: %s", e)
                continue
        return result

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

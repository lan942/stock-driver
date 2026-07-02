from __future__ import annotations

import logging
from typing import Any, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

Number = Union[int, float, str, None]


def _strip_unit_chars(value: str) -> str:
    cleaned = value.strip().replace(",", "").replace("%", "").replace("+", "")
    for unit in ["亿", "万", "手", "股", "元", "倍"]:
        if cleaned.endswith(unit):
            cleaned = cleaned[: -len(unit)]
    return cleaned.strip()


def _to_float(value: Number) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = _strip_unit_chars(value)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            logger.warning("Cannot convert to float: %s", value)
            return None
    return None


def normalize_price(value: Number, unit: str = "yuan") -> Optional[float]:
    num = _to_float(value)
    if num is None:
        return None

    unit_lower = unit.lower().strip()
    if unit_lower in ("yuan", "元", ""):
        return round(num, 4)
    if unit_lower in ("wan_yuan", "万元", "wanyuan"):
        return round(num * 10000, 4)
    if unit_lower in ("yi_yuan", "亿元", "yiyuan"):
        return round(num * 100000000, 4)

    logger.warning("Unknown price unit: %s, using value as-is", unit)
    return round(num, 4)


def normalize_volume(value: Number, unit: str = "shares") -> Optional[float]:
    num = _to_float(value)
    if num is None:
        return None

    unit_lower = unit.lower().strip()
    if unit_lower in ("shares", "股", ""):
        return float(int(num))
    if unit_lower in ("hand", "手", "shou"):
        return float(int(num * 100))
    if unit_lower in ("wan_shou", "万手", "wanshou"):
        return float(int(num * 10000 * 100))
    if unit_lower in ("yi_shou", "亿手", "yishou"):
        return float(int(num * 100000000 * 100))

    logger.warning("Unknown volume unit: %s, using value as-is", unit)
    return float(int(num))


def normalize_turnover(value: Number, unit: str = "yuan") -> Optional[float]:
    num = _to_float(value)
    if num is None:
        return None

    unit_lower = unit.lower().strip()
    if unit_lower in ("yuan", "元", ""):
        return round(num, 2)
    if unit_lower in ("wan_yuan", "万元", "wanyuan"):
        return round(num * 10000, 2)
    if unit_lower in ("yi_yuan", "亿元", "yiyuan"):
        return round(num * 100000000, 2)

    logger.warning("Unknown turnover unit: %s, using value as-is", unit)
    return round(num, 2)


def normalize_turnover_rate(value: Number, unit: str = "percent") -> Optional[float]:
    num = _to_float(value)
    if num is None:
        return None

    unit_lower = unit.lower().strip()
    if unit_lower in ("percent", "%", "百分号", ""):
        return round(num, 4)
    if unit_lower in ("decimal", "小数"):
        if -1.0 <= num <= 1.0:
            return round(num * 100, 4)
        logger.warning(
            "Turnover rate value %s seems too large for decimal format", num
        )
        return round(num, 4)

    logger.warning("Unknown turnover rate unit: %s, using value as-is", unit)
    return round(num, 4)


def normalize_change_percent(value: Number, unit: str = "percent") -> Optional[float]:
    num = _to_float(value)
    if num is None:
        return None

    unit_lower = unit.lower().strip()
    if unit_lower in ("percent", "%", "百分号", ""):
        return round(num, 4)
    if unit_lower in ("decimal", "小数"):
        if -1.0 <= num <= 1.0:
            return round(num * 100, 4)
        return round(num, 4)

    logger.warning("Unknown change percent unit: %s, using value as-is", unit)
    return round(num, 4)


def detect_unit_from_value(value: Any, field_name: str) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        if "%" in value:
            return "percent"
        if "亿" in value and field_name in ("turnover", "price", "market_cap"):
            return "yi_yuan"
        if "万" in value and field_name in ("turnover", "volume", "price"):
            return "wan_yuan"
        if "手" in value and field_name == "volume":
            return "hand"

    if isinstance(value, (int, float)):
        if field_name == "turnover_rate" and abs(value) <= 1.0 and value != 0:
            return "decimal"
        if field_name == "change_percent" and abs(value) <= 1.0 and value != 0:
            return "decimal"

    return ""


def normalize_stock_code(code: Any) -> str:
    if code is None:
        return ""
    code_str = str(code).strip().lower()
    prefixes = ["sh", "sz", "bj"]
    for prefix in prefixes:
        if code_str.startswith(prefix):
            return code_str[len(prefix):]
    return code_str


def normalize_stock_realtime_data(
    row: dict[str, Any],
    field_units: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    field_units = field_units or {}

    result = {
        "code": normalize_stock_code(row.get("code", row.get("代码", ""))),
        "name": str(row.get("name", row.get("名称", ""))).strip(),
        "open": None,
        "close": None,
        "high": None,
        "low": None,
        "volume": None,
        "turnover": None,
        "turnover_rate": None,
        "change_percent": None,
        "pe": None,
        "pb": None,
        "market_cap": None,
    }

    price_unit = field_units.get("price", detect_unit_from_value(
        row.get("最新价", row.get("close", None)), "price"
    ))
    volume_unit = field_units.get("volume", detect_unit_from_value(
        row.get("成交量", row.get("volume", None)), "volume"
    ))
    turnover_unit = field_units.get("turnover", detect_unit_from_value(
        row.get("成交额", row.get("turnover", None)), "turnover"
    ))
    turnover_rate_unit = field_units.get("turnover_rate", detect_unit_from_value(
        row.get("换手率", row.get("turnover_rate", None)), "turnover_rate"
    ))
    change_percent_unit = field_units.get("change_percent", detect_unit_from_value(
        row.get("涨跌幅", row.get("change_percent", None)), "change_percent"
    ))
    market_cap_unit = field_units.get("market_cap", detect_unit_from_value(
        row.get("总市值", row.get("market_cap", None)), "market_cap"
    ))

    result["open"] = normalize_price(
        row.get("今开", row.get("open", None)), price_unit
    )
    result["close"] = normalize_price(
        row.get("最新价", row.get("close", None)), price_unit
    )
    result["high"] = normalize_price(
        row.get("最高", row.get("high", None)), price_unit
    )
    result["low"] = normalize_price(
        row.get("最低", row.get("low", None)), price_unit
    )
    result["volume"] = normalize_volume(
        row.get("成交量", row.get("volume", None)), volume_unit
    )
    result["turnover"] = normalize_turnover(
        row.get("成交额", row.get("turnover", None)), turnover_unit
    )
    result["turnover_rate"] = normalize_turnover_rate(
        row.get("换手率", row.get("turnover_rate", None)), turnover_rate_unit
    )
    result["change_percent"] = normalize_change_percent(
        row.get("涨跌幅", row.get("change_percent", None)), change_percent_unit
    )
    result["pe"] = _to_float(
        row.get("市盈率-动态", row.get("pe", row.get("市盈率", None)))
    )
    result["pb"] = _to_float(
        row.get("市净率", row.get("pb", None))
    )
    result["market_cap"] = normalize_price(
        row.get("总市值", row.get("market_cap", None)), market_cap_unit
    )

    return result


def normalize_tencent_daily_row(row: dict[str, Any], code: str) -> dict[str, Any]:
    """
    归一化腾讯日线数据（stock_zh_a_daily 接口返回的英文字段）

    Args:
        row: 腾讯接口返回的单行数据字典（英文字段名）
        code: 股票代码（不含sh/sz前缀）

    Returns:
        归一化后的字典，包含 code/date/open/high/low/close/volume/turnover/
        turnover_rate/change_percent/pe/pb/market_cap
    """
    result = {
        "code": normalize_stock_code(code),
        "date": row.get("date"),
        "open": normalize_price(row.get("open"), "yuan"),
        "high": normalize_price(row.get("high"), "yuan"),
        "low": normalize_price(row.get("low"), "yuan"),
        "close": normalize_price(row.get("close"), "yuan"),
        "volume": normalize_volume(row.get("volume"), "shares"),
        "turnover": normalize_turnover(row.get("amount"), "yuan"),
        "turnover_rate": normalize_turnover_rate(row.get("turnover"), "decimal"),
        "change_percent": None,
        "pe": None,
        "pb": None,
        "market_cap": None,
    }
    return result


def normalize_tencent_daily_df(df: pd.DataFrame, code: str) -> pd.DataFrame:
    """
    归一化腾讯日线DataFrame，增加涨跌幅计算

    Args:
        df: 腾讯接口返回的DataFrame
        code: 股票代码（不含sh/sz前缀）

    Returns:
        归一化后的DataFrame
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "code", "date", "open", "high", "low", "close",
            "volume", "turnover", "turnover_rate", "change_percent",
            "pe", "pb", "market_cap"
        ])

    df_sorted = df.sort_values("date").reset_index(drop=True)
    result_rows: list[dict[str, Any]] = []

    prev_close: Optional[float] = None
    for _, row in df_sorted.iterrows():
        normalized = normalize_tencent_daily_row(row.to_dict(), code)

        if prev_close is not None and normalized["close"] is not None and prev_close != 0:
            normalized["change_percent"] = round(
                (normalized["close"] - prev_close) / prev_close * 100, 4
            )

        result_rows.append(normalized)
        if normalized["close"] is not None:
            prev_close = normalized["close"]

    return pd.DataFrame(result_rows)


def normalize_stock_list_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": normalize_stock_code(row.get("code", row.get("代码", ""))),
        "name": str(row.get("name", row.get("名称", ""))).strip(),
    }

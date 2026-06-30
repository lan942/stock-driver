import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing normalizer imports...")
from backend.services.crawler.normalizer import (
    normalize_price,
    normalize_volume,
    normalize_turnover,
    normalize_turnover_rate,
    normalize_change_percent,
    detect_unit_from_value,
    normalize_stock_realtime_data,
    normalize_stock_list_row,
)
print("Normalizer imports OK")

print("\nTesting normalize_price...")
assert normalize_price(1850.50) == 1850.5, "price yuan default failed"
assert normalize_price(18.505, "wan_yuan") == 185050.0, "price wan_yuan failed"
assert normalize_price(1.0, "yi_yuan") == 100000000.0, "price yi_yuan failed"
assert normalize_price("1850.50") == 1850.5, "price string failed"
assert normalize_price(None) is None, "price None failed"
print("normalize_price OK")

print("\nTesting normalize_volume...")
assert normalize_volume(1000000) == 1000000.0, "volume default failed"
assert normalize_volume(10000, "hand") == 1000000.0, "volume hand failed"
print("normalize_volume OK")

print("\nTesting normalize_turnover_rate...")
assert normalize_turnover_rate(5.25) == 5.25, "rate percent failed"
assert normalize_turnover_rate("5.25%") == 5.25, "rate string percent failed"
assert normalize_turnover_rate(0.0525, "decimal") == 5.25, "rate decimal failed"
print("normalize_turnover_rate OK")

print("\nTesting normalize_change_percent...")
assert normalize_change_percent(5.25) == 5.25, "change positive failed"
assert normalize_change_percent(-3.2) == -3.2, "change negative failed"
assert normalize_change_percent("+5.25") == 5.25, "change sign string failed"
print("normalize_change_percent OK")

print("\nTesting detect_unit_from_value...")
assert detect_unit_from_value("5.25%", "turnover_rate") == "percent"
assert detect_unit_from_value(0.05, "turnover_rate") == "decimal"
print("detect_unit_from_value OK")

print("\nTesting normalize_stock_realtime_data...")
row = {
    "代码": "600519",
    "名称": "贵州茅台",
    "今开": 1800.0,
    "最新价": 1850.5,
    "成交量": 1000000,
    "成交额": 1850000000,
    "换手率": 0.5,
    "涨跌幅": 2.5,
}
result = normalize_stock_realtime_data(row)
assert result["code"] == "600519"
assert result["name"] == "贵州茅台"
assert result["open"] == 1800.0
assert result["close"] == 1850.5
assert result["volume"] == 1000000.0
print("normalize_stock_realtime_data OK")

print("\nTesting normalize_stock_list_row...")
row2 = {"代码": "600519", "名称": "贵州茅台"}
result2 = normalize_stock_list_row(row2)
assert result2["code"] == "600519"
assert result2["name"] == "贵州茅台"
print("normalize_stock_list_row OK")

print("\n" + "="*50)
print("All normalizer tests passed!")
print("="*50)

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
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


class TestNormalizePrice(unittest.TestCase):
    def test_price_yuan_default(self):
        self.assertEqual(normalize_price(1850.50), 1850.5)

    def test_price_yuan_explicit(self):
        self.assertEqual(normalize_price(1850.50, "yuan"), 1850.5)

    def test_price_wan_yuan(self):
        self.assertEqual(normalize_price(18.505, "wan_yuan"), 185050.0)

    def test_price_yi_yuan(self):
        self.assertEqual(normalize_price(1.0, "yi_yuan"), 100000000.0)

    def test_price_string(self):
        self.assertEqual(normalize_price("1850.50"), 1850.5)

    def test_price_none(self):
        self.assertIsNone(normalize_price(None))

    def test_price_empty_string(self):
        self.assertIsNone(normalize_price(""))


class TestNormalizeVolume(unittest.TestCase):
    def test_volume_shares_default(self):
        self.assertEqual(normalize_volume(1000000), 1000000.0)

    def test_volume_hand(self):
        self.assertEqual(normalize_volume(10000, "hand"), 1000000.0)

    def test_volume_wan_shou(self):
        self.assertEqual(normalize_volume(1, "wan_shou"), 1000000.0)

    def test_volume_none(self):
        self.assertIsNone(normalize_volume(None))


class TestNormalizeTurnover(unittest.TestCase):
    def test_turnover_yuan(self):
        self.assertEqual(normalize_turnover(1000000), 1000000.0)

    def test_turnover_wan_yuan(self):
        self.assertEqual(normalize_turnover(100, "wan_yuan"), 1000000.0)

    def test_turnover_yi_yuan(self):
        self.assertEqual(normalize_turnover(1, "yi_yuan"), 100000000.0)


class TestNormalizeTurnoverRate(unittest.TestCase):
    def test_turnover_rate_percent(self):
        self.assertEqual(normalize_turnover_rate(5.25), 5.25)

    def test_turnover_rate_percent_string(self):
        self.assertEqual(normalize_turnover_rate("5.25%"), 5.25)

    def test_turnover_rate_decimal(self):
        self.assertEqual(normalize_turnover_rate(0.0525, "decimal"), 5.25)

    def test_turnover_rate_none(self):
        self.assertIsNone(normalize_turnover_rate(None))


class TestNormalizeChangePercent(unittest.TestCase):
    def test_change_percent_positive(self):
        self.assertEqual(normalize_change_percent(5.25), 5.25)

    def test_change_percent_negative(self):
        self.assertEqual(normalize_change_percent(-3.20), -3.2)

    def test_change_percent_with_sign_string(self):
        self.assertEqual(normalize_change_percent("+5.25"), 5.25)

    def test_change_percent_decimal(self):
        self.assertEqual(normalize_change_percent(0.0525, "decimal"), 5.25)


class TestDetectUnit(unittest.TestCase):
    def test_detect_percent_from_string(self):
        self.assertEqual(detect_unit_from_value("5.25%", "turnover_rate"), "percent")

    def test_detect_decimal_turnover_rate(self):
        self.assertEqual(detect_unit_from_value(0.05, "turnover_rate"), "decimal")

    def test_detect_decimal_change_percent(self):
        self.assertEqual(detect_unit_from_value(-0.03, "change_percent"), "decimal")

    def test_detect_none_value(self):
        self.assertEqual(detect_unit_from_value(None, "price"), "")


class TestNormalizeStockRealtimeData(unittest.TestCase):
    def test_normalize_with_chinese_keys(self):
        row = {
            "代码": "600519",
            "名称": "贵州茅台",
            "今开": 1800.0,
            "最新价": 1850.5,
            "最高": 1860.0,
            "最低": 1790.0,
            "成交量": 1000000,
            "成交额": 1850000000,
            "换手率": 5.25,
            "涨跌幅": 2.5,
        }
        result = normalize_stock_realtime_data(row)
        self.assertEqual(result["code"], "600519")
        self.assertEqual(result["name"], "贵州茅台")
        self.assertEqual(result["open"], 1800.0)
        self.assertEqual(result["close"], 1850.5)
        self.assertEqual(result["high"], 1860.0)
        self.assertEqual(result["low"], 1790.0)
        self.assertEqual(result["volume"], 1000000.0)
        self.assertEqual(result["turnover"], 1850000000.0)
        self.assertEqual(result["turnover_rate"], 5.25)
        self.assertEqual(result["change_percent"], 2.5)

    def test_normalize_with_english_keys(self):
        row = {
            "code": "600519",
            "name": "贵州茅台",
            "open": 1800.0,
            "close": 1850.5,
            "high": 1860.0,
            "low": 1790.0,
            "volume": 1000000,
            "turnover": 1850000000,
            "turnover_rate": 0.5,
            "change_percent": 2.5,
        }
        result = normalize_stock_realtime_data(row)
        self.assertEqual(result["code"], "600519")
        self.assertEqual(result["close"], 1850.5)

    def test_normalize_with_missing_fields(self):
        row = {
            "代码": "600519",
            "名称": "贵州茅台",
        }
        result = normalize_stock_realtime_data(row)
        self.assertEqual(result["code"], "600519")
        self.assertIsNone(result["open"])
        self.assertIsNone(result["close"])


class TestNormalizeStockListRow(unittest.TestCase):
    def test_normalize_chinese_keys(self):
        row = {"代码": "600519", "名称": "贵州茅台"}
        result = normalize_stock_list_row(row)
        self.assertEqual(result["code"], "600519")
        self.assertEqual(result["name"], "贵州茅台")

    def test_normalize_english_keys(self):
        row = {"code": "000001", "name": "平安银行"}
        result = normalize_stock_list_row(row)
        self.assertEqual(result["code"], "000001")
        self.assertEqual(result["name"], "平安银行")


if __name__ == "__main__":
    unittest.main()

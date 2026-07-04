"""StockListCrawler 测试：覆盖沪深直连合并、BJ 失败容忍、备用源切换、整体失败抛错、路由 503。"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch, MagicMock

import pandas as pd

from backend.services.crawler.base import CrawlerError
from backend.services.crawler.stock_list import StockListCrawler


# 构造测试用 DataFrame
def _sh_df():
    return pd.DataFrame([
        {"证券代码": "600519", "证券简称": "贵州茅台"},
        {"证券代码": "000001", "证券简称": "平安银行"},
    ])

def _sz_df():
    return pd.DataFrame([
        {"A股代码": "000001", "A股简称": "平安银行"},  # 与 SH 重复，去重
        {"A股代码": "300750", "A股简称": "宁德时代"},
    ])

def _bj_df():
    return pd.DataFrame([
        {"证券代码": "830789", "证券简称": "长虹能源"},
    ])

def _empty_df():
    return pd.DataFrame(columns=["证券代码", "证券简称"])


class TestShSzMerge(unittest.TestCase):
    """用例 1：SH+SZ 都成功 → 返回合并去重后的列表"""

    def test_sh_sz_both_success_dedup(self):
        with patch("akshare.stock_info_sh_name_code", return_value=_sh_df()), \
             patch("akshare.stock_info_sz_name_code", return_value=_sz_df()), \
             patch("akshare.stock_info_bj_name_code", return_value=_empty_df()):
            crawler = StockListCrawler()
            data = crawler.fetch_stock_list()

        codes = [row["code"] for row in data]
        self.assertIn("600519", codes)
        self.assertIn("000001", codes)
        self.assertIn("300750", codes)
        # 去重：000001 同时出现在 SH/SZ，只保留一条
        self.assertEqual(codes.count("000001"), 1)
        self.assertEqual(len(codes), 3)


class TestShSuccessSzFail(unittest.TestCase):
    """用例 2：SH 成功 SZ 失败 → 仍返回 SH 列表"""

    def test_sh_success_sz_failure_returns_sh_only(self):
        with patch("akshare.stock_info_sh_name_code", return_value=_sh_df()), \
             patch("akshare.stock_info_sz_name_code", side_effect=ConnectionError("SZ down")), \
             patch("akshare.stock_info_bj_name_code", return_value=_empty_df()):
            crawler = StockListCrawler()
            data = crawler.fetch_stock_list()

        codes = [row["code"] for row in data]
        self.assertIn("600519", codes)
        self.assertIn("000001", codes)
        self.assertEqual(len(data), 2)


class TestBjFailureTolerated(unittest.TestCase):
    """用例 3：SH+SZ 都成功 + BJ 失败 → 仍返回 SH+SZ 列表，BJ WARN"""

    def test_bj_failure_does_not_break_main_list(self):
        with patch("akshare.stock_info_sh_name_code", return_value=_sh_df()), \
             patch("akshare.stock_info_sz_name_code", return_value=_sz_df()), \
             patch("akshare.stock_info_bj_name_code", side_effect=ConnectionError("BSE down")):
            crawler = StockListCrawler()
            data = crawler.fetch_stock_list()

        codes = [row["code"] for row in data]
        self.assertEqual(len(codes), 3)
        # BJ 失败不应导致抛错
        self.assertNotIn("830789", codes)


class TestBjSuccessAppended(unittest.TestCase):
    """用例 4：SH+SZ 都成功 + BJ 成功 → 返回 SH+SZ+BJ 合并列表"""

    def test_bj_success_appended(self):
        with patch("akshare.stock_info_sh_name_code", return_value=_sh_df()), \
             patch("akshare.stock_info_sz_name_code", return_value=_sz_df()), \
             patch("akshare.stock_info_bj_name_code", return_value=_bj_df()):
            crawler = StockListCrawler()
            data = crawler.fetch_stock_list()

        codes = [row["code"] for row in data]
        self.assertIn("830789", codes)
        self.assertEqual(len(codes), 4)  # 600519, 000001, 300750, 830789


class TestFallbackToSpot(unittest.TestCase):
    """用例 5：主源失败 + 备用源 akshare_em_spot 成功 → 切换备用源"""

    def test_primary_fails_fallback_to_spot(self):
        spot_df = pd.DataFrame([
            {"代码": "600519", "名称": "贵州茅台"},
            {"代码": "000001", "名称": "平安银行"},
        ])
        with patch("akshare.stock_info_sh_name_code", side_effect=ConnectionError("SH down")), \
             patch("akshare.stock_info_sz_name_code", side_effect=ConnectionError("SZ down")), \
             patch("akshare.stock_info_bj_name_code", side_effect=ConnectionError("BJ down")), \
             patch("akshare.stock_zh_a_spot_em", return_value=spot_df):
            crawler = StockListCrawler()
            data = crawler.fetch_stock_list()

        codes = [row["code"] for row in data]
        self.assertIn("600519", codes)
        self.assertIn("000001", codes)


class TestAllSourcesFail(unittest.TestCase):
    """用例 6：所有源失败 → fetch_stock_list() 抛 CrawlerError"""

    def test_all_sources_fail_raises(self):
        with patch("akshare.stock_info_sh_name_code", side_effect=ConnectionError("SH down")), \
             patch("akshare.stock_info_sz_name_code", side_effect=ConnectionError("SZ down")), \
             patch("akshare.stock_info_bj_name_code", side_effect=ConnectionError("BJ down")), \
             patch("akshare.stock_zh_a_spot_em", side_effect=ConnectionError("spot down")):
            crawler = StockListCrawler()
            with self.assertRaises(CrawlerError):
                crawler.fetch_stock_list()


class TestUpdateListRoute503(unittest.TestCase):
    """用例 7：update_stock_list 路由在 CrawlerError 时返回 503 + error 字段"""

    def setUp(self):
        # 用独立 Flask app 测试路由，避免触发 scheduler / DB 初始化
        from flask import Flask
        from backend.api.routes import api
        self.app = Flask(__name__)
        self.app.register_blueprint(api, url_prefix='/api')
        self.client = self.app.test_client()

    def test_route_returns_503_on_crawler_error(self):
        with patch("backend.api.routes.StockListCrawler") as MockCrawler, \
             patch("backend.api.routes.record_crawl_status") as mock_record:
            instance = MockCrawler.return_value
            instance.fetch_stock_list_df.side_effect = CrawlerError("all sources failed")
            resp = self.client.post('/api/crawler/update_list')

        self.assertEqual(resp.status_code, 503)
        body = resp.get_json()
        self.assertIn("error", body)
        self.assertIn("sources_tried", body)
        self.assertEqual(body["success_count"], 0)
        # 失败状态应被记录
        mock_record.assert_called()
        call_kwargs = mock_record.call_args.kwargs
        self.assertEqual(call_kwargs["status"], "failed")
        self.assertEqual(call_kwargs["crawl_type"], "list")


if __name__ == '__main__':
    unittest.main()

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import pandas as pd

print("=" * 80)
print("AkShare 实时行情接口全量调研")
print("=" * 80)

# 尝试各种可能的实时行情接口
interfaces = [
    ("stock_zh_a_spot_em", "东方财富实时行情"),
    ("stock_zh_a_spot", "新浪实时行情"),
    ("stock_zh_a_hist", "日线历史"),
    ("stock_zh_a_daily", "日线数据(sina)"),
    ("stock_hk_spot_em", "港股实时(东财)"),
    ("stock_zh_a_spot_tx", "腾讯实时行情"),
    ("stock_zh_a_spot_163", "网易实时行情"),
    ("stock_zh_a_spot_sina", "新浪实时行情2"),
]

print("\n--- 列出 akshare.stock 模块下所有 spot 相关函数 ---")
stock_module = dir(ak)
spot_funcs = [f for f in stock_module if 'spot' in f.lower() or 'realtime' in f.lower() or 'quote' in f.lower()]
for f in sorted(spot_funcs):
    print(f"  {f}")

print("\n--- 列出所有 stock_zh_a 开头的函数 ---")
zh_a_funcs = [f for f in stock_module if f.startswith('stock_zh_a')]
for f in sorted(zh_a_funcs):
    print(f"  {f}")

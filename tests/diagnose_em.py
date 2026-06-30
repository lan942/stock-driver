import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import time

print("=" * 60)
print("东方财富接口诊断")
print("=" * 60)

print("\n[1] 尝试 stock_zh_a_spot_em()...")
try:
    start = time.time()
    df = ak.stock_zh_a_spot_em()
    elapsed = time.time() - start
    print(f"  成功! 耗时: {elapsed:.2f}s")
    print(f"  数据量: {df.shape}")
    print(f"  列: {list(df.columns)}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n[2] 尝试 stock_info_a_code_name() (参考)...")
try:
    start = time.time()
    df = ak.stock_info_a_code_name()
    elapsed = time.time() - start
    print(f"  成功! 耗时: {elapsed:.2f}s")
    print(f"  数据量: {df.shape}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

print("\n[3] 尝试 stock_zh_a_hist() (日线)...")
try:
    start = time.time()
    df = ak.stock_zh_a_hist(symbol="600519", period="daily", start_date="20250625", end_date="20250630", adjust="qfq")
    elapsed = time.time() - start
    print(f"  成功! 耗时: {elapsed:.2f}s")
    print(f"  数据量: {df.shape}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

print("\n[4] akshare 版本...")
print(f"  akshare version: {ak.__version__}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)

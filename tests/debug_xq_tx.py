import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import traceback

print(f"akshare version: {ak.__version__}")
print(f"akshare path: {ak.__file__}")

print("\n" + "=" * 60)
print("1. 雪球接口 stock_individual_spot_xq 详细错误")
print("=" * 60)
try:
    df = ak.stock_individual_spot_xq(symbol="SH600519")
    print(f"  Success! Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
except Exception as e:
    print(f"  Error type: {type(e).__name__}")
    print(f"  Error: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("2. 腾讯日线接口 stock_zh_a_hist_tx 详细错误")
print("=" * 60)
try:
    df = ak.stock_zh_a_hist_tx(symbol="600519", start_date="20250625", end_date="20250630", adjust="qfq")
    print(f"  Success! Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
except Exception as e:
    print(f"  Error type: {type(e).__name__}")
    print(f"  Error: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("3. 查看雪球接口源码位置")
print("=" * 60)
import inspect
try:
    src = inspect.getsource(ak.stock_individual_spot_xq)
    print(src[:2000])
except Exception as e:
    print(f"  Error: {e}")

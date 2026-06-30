import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak

print("Testing akshare stock_zh_a_spot_em (东方财富)...")
try:
    df = ak.stock_zh_a_spot_em()
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
    print(df.head(2).to_string())
except Exception as e:
    print(f"  Error: {e}")

print("\nTesting akshare stock_zh_a_spot (新浪)...")
try:
    df2 = ak.stock_zh_a_spot()
    print(f"  Shape: {df2.shape}")
    print(f"  Columns: {list(df2.columns)}")
    print(df2.head(2).to_string())
except Exception as e:
    print(f"  Error: {e}")

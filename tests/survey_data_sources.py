import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import pandas as pd

print("=" * 80)
print("AkShare 数据接口字段和单位调研")
print("=" * 80)

# 1. 股票列表接口
print("\n" + "=" * 80)
print("1. stock_info_a_code_name() - 股票列表")
print("=" * 80)
try:
    df = ak.stock_info_a_code_name()
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Data types:\n{df.dtypes}")
    print(f"\nSample:\n{df.head(3).to_string()}")
except Exception as e:
    print(f"Error: {e}")

# 2. 实时行情接口 - 东方财富
print("\n" + "=" * 80)
print("2. stock_zh_a_spot_em() - 实时行情(东方财富)")
print("=" * 80)
try:
    df = ak.stock_zh_a_spot_em()
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Data types:\n{df.dtypes}")
    # 检查数值字段的范围
    for col in df.columns:
        if df[col].dtype in ['float64', 'int64']:
            sample = df[col].dropna()
            if len(sample) > 0:
                print(f"  {col}: min={sample.min()}, max={sample.max()}, sample={sample.iloc[0]}")
    print(f"\nSample (600519):\n{df[df['代码']=='600519'].iloc[0].to_string()}")
except Exception as e:
    print(f"Error: {e}")

# 3. 实时行情接口 - 新浪
print("\n" + "=" * 80)
print("3. stock_zh_a_spot() - 实时行情(新浪)")
print("=" * 80)
try:
    df = ak.stock_zh_a_spot()
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Data types:\n{df.dtypes}")
    # 检查数值字段的范围
    for col in df.columns:
        if df[col].dtype in ['float64', 'int64']:
            sample = df[col].dropna()
            if len(sample) > 0:
                print(f"  {col}: min={sample.min()}, max={sample.max()}, sample={sample.iloc[0]}")
    print(f"\nSample (600519):\n{df[df['代码']=='sh600519'].iloc[0].to_string()}")
except Exception as e:
    print(f"Error: {e}")

# 4. 日线数据接口
print("\n" + "=" * 80)
print("4. stock_zh_a_hist() - 日线数据(东方财富)")
print("=" * 80)
try:
    df = ak.stock_zh_a_hist(symbol="600519", period="daily", start_date="20250601", end_date="20250630", adjust="qfq")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Data types:\n{df.dtypes}")
    print(f"\nSample:\n{df.head(3).to_string()}")
except Exception as e:
    print(f"Error: {e}")

# 5. 实时行情接口 - 腾讯
print("\n" + "=" * 80)
print("5. stock_zh_a_spot_em() - 实时行情(腾讯)")
print("=" * 80)
try:
    df = ak.stock_zh_a_spot_tx()
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Data types:\n{df.dtypes}")
    print(f"\nSample:\n{df.head(3).to_string()}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 80)
print("调研完成")
print("=" * 80)

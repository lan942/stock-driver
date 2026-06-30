import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

print("=" * 80)
print("新浪日线接口 stock_zh_a_daily 详细分析")
print("=" * 80)

df = ak.stock_zh_a_daily(symbol="sh600519")
print(f"\nShape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"\nLast 5 rows:")
print(df.tail(5).to_string())
print(f"\nData types:")
print(df.dtypes)

print(f"\n关键字段样例 (最新一行):")
latest = df.iloc[-1]
for col in df.columns:
    print(f"  {col}: {latest[col]} (type: {type(latest[col]).__name__})")

print("\n" + "=" * 80)
print("测试单只新浪接口是否有换手率信息")
print("=" * 80)

# 看看有没有办法从新浪获取实时带换手率的数据
print("\n尝试 stock_zh_a_spot 详细字段...")
df_spot = ak.stock_zh_a_spot()
print(f"  列: {list(df_spot.columns)}")
# 找600519
row = df_spot[df_spot['代码'] == 'sh600519']
if not row.empty:
    print(f"  贵州茅台数据:")
    print(row.iloc[0].to_string())

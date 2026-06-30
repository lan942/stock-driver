import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import pandas as pd

print("=" * 80)
print("AkShare 实时行情接口字段对比")
print("=" * 80)

interfaces = [
    ("新浪 stock_zh_a_spot", lambda: ak.stock_zh_a_spot()),
    ("东方财富 stock_zh_a_spot_em", lambda: ak.stock_zh_a_spot_em()),
]

for name, fn in interfaces:
    print(f"\n{'='*60}")
    print(f"接口: {name}")
    print(f"{'='*60}")
    try:
        df = fn()
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"\nSample row:")
        if not df.empty:
            print(df.iloc[0].to_string())

        # 数值字段分析
        print(f"\n数值字段统计:")
        for col in df.columns:
            if df[col].dtype in ['float64', 'int64']:
                sample = df[col].dropna()
                if len(sample) > 0:
                    print(f"  {col}: min={sample.min():.2f}, max={sample.max():.2f}")

        # 关键字段检查
        print(f"\n关键字段检查:")
        key_fields = {
            '换手率': ['换手率', 'turnover_rate', 'TurnoverRate'],
            '市盈率': ['市盈率', 'pe', 'PE'],
            '市净率': ['市净率', 'pb', 'PB'],
            '总市值': ['总市值', 'market_cap', 'MarketCap'],
            '流通市值': ['流通市值', 'float_market_cap'],
        }
        for field_ch, field_variants in key_fields.items():
            for variant in field_variants:
                if variant in df.columns:
                    print(f"  {field_ch}: 有 (列名={variant})")
                    break
            else:
                print(f"  {field_ch}: 无")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

print("\n" + "=" * 80)
print("股票代码格式检查 (新浪)")
print("=" * 80)
df = ak.stock_zh_a_spot()
print(f"\n股票代码样例:")
for i in range(min(10, len(df))):
    code = df.iloc[i]['代码']
    print(f"  {code} -> normalize后: {code.replace('sh','').replace('sz','').replace('bj','')}")

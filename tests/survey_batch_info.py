import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak

print("=" * 60)
print("搜索 akshare 批量基本信息接口")
print("=" * 60)

# 搜所有 stock_zh_a 开头的函数
stock_funcs = [f for f in dir(ak) if f.startswith('stock_zh_a')]
print(f"\nstock_zh_a 开头的函数 ({len(stock_funcs)}个):")
for f in sorted(stock_funcs):
    print(f"  {f}")

# 搜可能含股本/基本信息的
info_funcs = [f for f in dir(ak) if 'share' in f.lower() or 'info' in f.lower() or 'basic' in f.lower() or 'profile' in f.lower()]
stock_info_funcs = [f for f in info_funcs if 'stock' in f.lower() and 'zh_a' in f.lower()]
print(f"\n可能含股本信息的 stock_zh_a 函数:")
for f in sorted(stock_info_funcs):
    print(f"  {f}")

# 试试 stock_zh_a_spot_em 恢复了吗
print("\n[1] 东方财富恢复了吗?")
try:
    df = ak.stock_zh_a_spot_em()
    print(f"  YES! Shape: {df.shape}, columns: {list(df.columns)}")
except Exception as e:
    print(f"  NO: {type(e).__name__}")

# 试试分市场接口
print("\n[2] stock_sh_a_spot_em (沪A)?")
try:
    df = ak.stock_sh_a_spot_em()
    print(f"  YES! Shape: {df.shape}")
except Exception as e:
    print(f"  NO: {type(e).__name__}")

# 看看有没有新股/次新股的批量接口（可能有基本信息）
print("\n[3] stock_zh_a_new_em (新股)?")
try:
    df = ak.stock_zh_a_new_em()
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
except Exception as e:
    print(f"  Error: {e}")

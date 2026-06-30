import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak

print("=" * 60)
print("搜索 akshare 批量基本信息接口")
print("=" * 60)

# 搜所有可能含股本/基本信息的函数
all_funcs = dir(ak)
info_funcs = [f for f in all_funcs if ('share' in f.lower() or 'basic' in f.lower() or 'profile' in f.lower() or 'indicator' in f.lower()) and 'stock' in f.lower()]
print(f"\n可能含股本信息的函数:")
for f in sorted(info_funcs):
    print(f"  {f}")

# 看看 stock_zh_a_hist (日线) 接口是否支持批量
import inspect
print(f"\n[1] stock_zh_a_hist 签名: {list(inspect.signature(ak.stock_zh_a_hist).parameters.keys())}")

# 试试看有没有板块接口含换手率
try:
    df = ak.stock_board_industry_spot_em()
    print(f"\n[2] stock_board_industry_spot_em (行业板块):")
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {str(e)[:100]}")

# 试试新浪日线接口能否快速返回单只
import time
print(f"\n[3] stock_zh_a_daily 速度测试 (600519)...")
start = time.time()
df = ak.stock_zh_a_daily(symbol="sh600519")
elapsed = time.time() - start
print(f"  Time: {elapsed:.2f}s, rows: {len(df)}")
print(f"  最新 outstanding_share: {df.iloc[-1]['outstanding_share']}")
print(f"  最新 turnover: {df.iloc[-1]['turnover']}")

print(f"\n[4] 如果5000只各跑一次，预估: {elapsed * 5000 / 3600:.1f} 小时")

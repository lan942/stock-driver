import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import inspect

print("=" * 60)
print("接口参数检查")
print("=" * 60)

# 查新浪接口签名
print("\n[1] stock_zh_a_spot (新浪) 函数签名:")
sig = inspect.signature(ak.stock_zh_a_spot)
print(f"  参数: {list(sig.parameters.keys())}")
# 看看有没有日期参数
src = inspect.getsource(ak.stock_zh_a_spot)
# 找参数行
for line in src.split('\n'):
    line_stripped = line.strip()
    if 'def ' in line_stripped or 'param ' in line_stripped.lower() or 'period' in line_stripped.lower() or 'date' in line_stripped.lower() or 'symbol' in line_stripped.lower():
        print(f"  {line_stripped[:120]}")

print("\n[2] stock_zh_a_spot_em (东方财富) 函数签名:")
sig2 = inspect.signature(ak.stock_zh_a_spot_em)
print(f"  参数: {list(sig2.parameters.keys())}")

# 实际调用看看返回多少条
print("\n[3] 实际调用 - 新浪接口...")
df = ak.stock_zh_a_spot()
print(f"  返回行数: {len(df)}")
print(f"  时间戳字段唯一值: {df['时间戳'].unique()[:5]}")
print(f"  日期列: {[c for c in df.columns if 'date' in c.lower() or 'time' in c.lower() or '日' in c or '期' in c]}")

print("\n[4] 接口文档摘要 (stock_zh_a_spot):")
try:
    doc = ak.stock_zh_a_spot.__doc__ or ""
    print(doc[:800])
except:
    pass

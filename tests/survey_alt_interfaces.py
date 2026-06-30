import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak

print("=" * 80)
print("备选实时行情接口字段对比")
print("=" * 80)

candidates = [
    ("stock_sh_a_spot_em", "沪A实时(东财)"),
    ("stock_sz_a_spot_em", "深A实时(东财)"),
    ("stock_kc_a_spot_em", "科创板实时(东财)"),
    ("stock_cy_a_spot_em", "创业板实时(东财)"),
    ("stock_bj_a_spot_em", "北交所实时(东财)"),
    ("stock_individual_spot_xq", "个股实时(雪球)"),
    ("stock_zh_a_daily", "日线数据(sina)"),
    ("stock_zh_a_hist_tx", "日线数据(腾讯)"),
]

key_fields = ['代码', '名称', '最新价', '涨跌幅', '换手率', '成交量', '成交额', '市盈率', '市净率', '总市值', '流通市值']

for func_name, desc in candidates:
    print(f"\n{'='*60}")
    print(f"接口: {func_name} ({desc})")
    print(f"{'='*60}")
    try:
        func = getattr(ak, func_name, None)
        if func is None:
            print("  不存在")
            continue

        if 'individual' in func_name:
            df = func(symbol="SH600519")
        elif 'daily' in func_name:
            df = func(symbol="sh600519")
        elif 'hist_tx' in func_name:
            df = func(symbol="600519", start_date="20250625", end_date="20250630", adjust="qfq")
        else:
            df = func()

        print(f"  Shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")

        if not df.empty:
            print(f"\n  关键字段检查:")
            cols_lower = {c.lower(): c for c in df.columns}
            for field in key_fields:
                found = field in df.columns or field.lower() in cols_lower
                actual_name = cols_lower.get(field.lower(), field if field in df.columns else None)
                if actual_name:
                    sample_val = df.iloc[0][actual_name]
                    print(f"    {field}: ✅ ({sample_val})")
                else:
                    print(f"    {field}: ❌")

            print(f"\n  第一行样例:")
            print(df.head(1).to_string())
    except Exception as e:
        print(f"  错误: {type(e).__name__}: {str(e)[:100]}")

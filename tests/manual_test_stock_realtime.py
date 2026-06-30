import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("Manual Test 7.4: Stock Realtime Crawler")
print("=" * 60)

from backend.services.crawler.stock_realtime import StockRealtimeCrawler

print("\n[1/5] Creating StockRealtimeCrawler...")
crawler = StockRealtimeCrawler()
print(f"  Sources: {len(crawler.available_sources)}")
for i, src in enumerate(crawler.available_sources):
    print(f"    {i+1}. {src['name']} - {src['function']}")
print(f"  Current source: {crawler.current_source.get('name', 'unknown')}")

print("\n[2/5] Fetching realtime data (this may take a while)...")
try:
    result = crawler.fetch()
    print(f"  Success: {result.success}")
    print(f"  Source used: {result.source}")
    if result.success:
        data = result.data
        print(f"  Total stocks fetched: {len(data)}")
        if data:
            print(f"\n  First 3 stocks:")
            for i, stock in enumerate(data[:3]):
                print(f"    {i+1}. {stock['code']} - {stock['name']}")
                print(f"       开:{stock['open']} 收:{stock['close']} 高:{stock['high']} 低:{stock['low']}")
                print(f"       量:{stock['volume']} 额:{stock['turnover']} 换手:{stock['turnover_rate']}% 涨跌:{stock['change_percent']}%")
    else:
        print(f"  Error: {result.error}")
except Exception as e:
    print(f"  Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n[3/5] Testing fetch_realtime_df()...")
try:
    df = crawler.fetch_realtime_df()
    print(f"  DataFrame shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
except Exception as e:
    print(f"  Exception: {e}")

print("\n[4/5] Testing fetch_single_stock (600519)...")
try:
    stock = crawler.fetch_single_stock("600519")
    if stock:
        print(f"  Found: {stock['code']} - {stock['name']}")
        print(f"  Close: {stock['close']}  Change%: {stock['change_percent']}")
        print(f"  Turnover: {stock['turnover']}  Turnover Rate: {stock['turnover_rate']}%")
    else:
        print("  Not found")
except Exception as e:
    print(f"  Exception: {e}")

print("\n[5/5] Testing fetch_batch_stocks...")
try:
    codes = ["600519", "000001", "000858"]
    batch = crawler.fetch_batch_stocks(codes)
    print(f"  Requested: {len(codes)} stocks")
    print(f"  Got: {len(batch)} stocks")
    for s in batch:
        print(f"    {s['code']} - {s['name']} - {s['close']} - {s['change_percent']}%")
except Exception as e:
    print(f"  Exception: {e}")

print("\n" + "=" * 60)
print("Test 7.4 Complete")
print("=" * 60)

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("Manual Test 7.3: Stock List Crawler")
print("=" * 60)

from backend.services.crawler.stock_list import StockListCrawler

print("\n[1/4] Creating StockListCrawler...")
crawler = StockListCrawler()
print(f"  Sources: {len(crawler.available_sources)}")
print(f"  Current source: {crawler.current_source.get('name', 'unknown')}")

print("\n[2/4] Fetching stock list (this may take a while)...")
try:
    result = crawler.fetch()
    print(f"  Success: {result.success}")
    print(f"  Source used: {result.source}")
    if result.success:
        data = result.data
        print(f"  Total stocks fetched: {len(data)}")
        if data:
            print(f"\n  First 5 stocks:")
            for i, stock in enumerate(data[:5]):
                print(f"    {i+1}. {stock['code']} - {stock['name']}")
    else:
        print(f"  Error: {result.error}")
except Exception as e:
    print(f"  Exception: {e}")

print("\n[3/4] Testing fetch_stock_list_df()...")
try:
    df = crawler.fetch_stock_list_df()
    print(f"  DataFrame shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
    print(f"\n  DataFrame head:")
    print(df.head(5).to_string())
except Exception as e:
    print(f"  Exception: {e}")

print("\n[4/4] Verifying data format...")
try:
    df = crawler.fetch_stock_list_df()
    has_code = 'code' in df.columns
    has_name = 'name' in df.columns
    print(f"  Has 'code' column: {has_code}")
    print(f"  Has 'name' column: {has_name}")
    if not df.empty:
        sample_code = df.iloc[0]['code']
        sample_name = df.iloc[0]['name']
        print(f"  Sample code: {sample_code} (type: {type(sample_code).__name__})")
        print(f"  Sample name: {sample_name} (type: {type(sample_name).__name__})")
    all_passed = has_code and has_name and not df.empty
    print(f"\n  Format check: {'PASSED' if all_passed else 'FAILED'}")
except Exception as e:
    print(f"  Exception: {e}")

print("\n" + "=" * 60)
print("Test 7.3 Complete")
print("=" * 60)

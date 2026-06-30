import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time, requests

token = "78d1f8d9cf4f42f48978e9c414bb5f68fee9fecb"
session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Cookie": f"xq_a_token={token}"
}

print("=" * 60)
print("Snowball API Test")
print("=" * 60)

# Test 1: single stock
print("\n[1] Testing SH600519...")
url = "https://stock.xueqiu.com/v5/stock/quote.json?symbol=SH600519&extend=detail"
r = session.get(url, headers=headers, timeout=15)
data = r.json()
if "data" in data and "quote" in data["data"]:
    q = data["data"]["quote"]
    print(f"  [OK] success!")
    print(f"  name: {q.get('name')}")
    print(f"  current: {q.get('current')}")
    print(f"  percent: {q.get('percent')}%")
    print(f"  market_capital: {q.get('market_capital')}")
    print(f"  float_market_capital: {q.get('float_market_capital')}")
    print(f"  pb: {q.get('pb')}")
    print(f"  pe_forecast: {q.get('pe_forecast')}")
    print(f"  pe_lyr: {q.get('pe_lyr')}")
    print(f"  volume: {q.get('volume')}")
    print(f"  amount: {q.get('amount')}")
    print(f"  turnover_rate: {q.get('turnover_rate')}%")
    print(f"  amplitude: {q.get('amplitude')}%")
    print(f"  high52w: {q.get('high52w')}")
    print(f"  low52w: {q.get('low52w')}")
    print(f"  all fields: {list(q.keys())}")
else:
    print(f"  [FAIL]: {str(data)[:200]}")

time.sleep(1)

# Test 2: 000001
print("\n[2] Testing SZ000001...")
url = "https://stock.xueqiu.com/v5/stock/quote.json?symbol=SZ000001&extend=detail"
r = session.get(url, headers=headers, timeout=15)
data = r.json()
if "data" in data and "quote" in data["data"]:
    q = data["data"]["quote"]
    print(f"  [OK] {q.get('name')} current:{q.get('current')} mcap:{q.get('market_capital')} PB:{q.get('pb')} turnover:{q.get('turnover_rate')}%")
else:
    print(f"  [FAIL]: {str(data)[:200]}")

print("\n" + "=" * 60)
print("Test complete")
print("=" * 60)

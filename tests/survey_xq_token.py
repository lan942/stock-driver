import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json

print("=" * 70)
print("雪球 token 获取方式调研")
print("=" * 70)

print("\n[1] 直接访问雪球主页，看能否拿到 cookie")
session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}
r = session.get("https://xueqiu.com", headers=headers, timeout=10)
print(f"  Status: {r.status_code}")
print(f"  Cookies: {dict(session.cookies)}")
has_token = 'xq_a_token' in session.cookies
print(f"  Has xq_a_token: {has_token}")
if has_token:
    print(f"  xq_a_token: {session.cookies['xq_a_token']}")

print("\n[2] 用这个 cookie 试试调用接口")
if has_token:
    url = "https://stock.xueqiu.com/v5/stock/quote.json?symbol=SH600519&extend=detail"
    r2 = session.get(url, headers=headers, timeout=10)
    print(f"  Status: {r2.status_code}")
    try:
        data = r2.json()
        print(f"  Has 'data' key: {'data' in data}")
        if 'data' in data:
            print(f"  数据正常! 字段: {list(data['data'].keys())}")
            if 'quote' in data['data']:
                quote = data['data']['quote']
                print(f"  股票: {quote.get('name')}")
                print(f"  现价: {quote.get('current')}")
                print(f"  总市值: {quote.get('market_capital')}")
                print(f"  流通值: {quote.get('float_market_capital')}")
                print(f"  PE: {quote.get('pe_forecast')}")
                print(f"  PB: {quote.get('pb')}")
        else:
            print(f"  返回内容: {str(data)[:300]}")
    except Exception as e:
        print(f"  JSON 解析失败: {e}")
        print(f"  Text: {r2.text[:300]}")
else:
    print("  没有 token，跳过")

print("\n[3] 检查 browser_cookie3 是否已安装")
try:
    import browser_cookie3
    print(f"  已安装: browser_cookie3 {browser_cookie3.__version__ if hasattr(browser_cookie3, '__version__') else 'unknown'}")
except ImportError:
    print("  未安装 browser_cookie3")

print("\n" + "=" * 70)
print("调研完成")
print("=" * 70)

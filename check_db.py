import sqlite3, os

db_path = "data/stock.db"
if not os.path.exists(db_path):
    print("Database file NOT found!")
else:
    conn = sqlite3.connect(db_path)
    tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"Tables: {tables}")
    for t in tables:
        count = conn.execute(f"SELECT count(*) FROM '{t}'").fetchone()[0]
        print(f"  {t}: {count} rows")
    conn.close()

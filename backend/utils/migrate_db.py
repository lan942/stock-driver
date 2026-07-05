"""数据库迁移脚本：创建crawl_status表和portfolio相关表"""
import os
import shutil
from datetime import datetime
from sqlalchemy import create_engine, text
from backend.config import Config


def backup_database(db_path: str, backup_path: str) -> None:
    """备份数据库文件"""
    if os.path.exists(db_path):
        print(f"备份数据库: {db_path} -> {backup_path}")
        shutil.copy2(db_path, backup_path)
        print("✓ 备份完成")
    else:
        print(f"数据库文件不存在: {db_path}，跳过备份")


def create_crawl_status_table(engine) -> None:
    """创建crawl_status表"""
    print("创建crawl_status表...")
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS crawl_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crawl_type VARCHAR(20) NOT NULL,
        status VARCHAR(20) NOT NULL,
        crawl_time DATETIME NOT NULL,
        success_count INTEGER DEFAULT 0,
        fail_count INTEGER DEFAULT 0,
        error_message TEXT
    );
    """
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
    print("✓ crawl_status表创建完成")


def verify_migration(engine) -> None:
    """验证迁移结果"""
    print("\n验证迁移结果...")

    # 检查crawl_status表是否存在
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='crawl_status';"))
        if result.fetchone():
            print("✓ crawl_status表存在")
        else:
            print("✗ crawl_status表不存在")
            return

        # 检查portfolio表是否存在
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio';"))
        if result.fetchone():
            print("✓ portfolio表存在")
        else:
            print("✗ portfolio表不存在")
            return

        # 检查transactions表是否存在
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions';"))
        if result.fetchone():
            print("✓ transactions表存在")
        else:
            print("✗ transactions表不存在")
            return

        # 检查cash_balance表是否存在
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='cash_balance';"))
        if result.fetchone():
            print("✓ cash_balance表存在")
        else:
            print("✗ cash_balance表不存在")
            return

        # 检查backtest_portfolio表是否存在
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_portfolio';"))
        if result.fetchone():
            print("✓ backtest_portfolio表存在")
        else:
            print("✗ backtest_portfolio表不存在")
            return

        # 检查backtest_transactions表是否存在
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_transactions';"))
        if result.fetchone():
            print("✓ backtest_transactions表存在")
        else:
            print("✗ backtest_transactions表不存在")
            return

        # 检查backtest_cash表是否存在
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_cash';"))
        if result.fetchone():
            print("✓ backtest_cash表存在")
        else:
            print("✗ backtest_cash表不存在")
            return

    print("✓ 迁移验证成功")


def create_portfolio_tables(engine) -> None:
    """创建持仓相关的表"""
    print("创建portfolio表...")
    create_portfolio_sql = """
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(20) NOT NULL,
        quantity INTEGER NOT NULL,
        cost_price FLOAT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    with engine.connect() as conn:
        conn.execute(text(create_portfolio_sql))
        conn.commit()
    print("✓ portfolio表创建完成")

    print("创建transactions表...")
    create_transactions_sql = """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type VARCHAR(10) NOT NULL,
        code VARCHAR(20) NOT NULL,
        quantity INTEGER NOT NULL,
        price FLOAT NOT NULL,
        amount FLOAT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    with engine.connect() as conn:
        conn.execute(text(create_transactions_sql))
        conn.commit()
    print("✓ transactions表创建完成")

    print("创建cash_balance表...")
    create_cash_sql = """
    CREATE TABLE IF NOT EXISTS cash_balance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        balance FLOAT NOT NULL DEFAULT 0.0,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    with engine.connect() as conn:
        conn.execute(text(create_cash_sql))
        conn.commit()
    print("✓ cash_balance表创建完成")


def add_trade_date_column(engine) -> None:
    """为transactions表添加trade_date列"""
    print("为transactions表添加trade_date列...")
    with engine.connect() as conn:
        # 检查列是否已存在
        result = conn.execute(text("PRAGMA table_info(transactions);"))
        columns = [row[1] for row in result.fetchall()]
        if 'trade_date' in columns:
            print("✓ trade_date列已存在，跳过")
            return

        conn.execute(text("ALTER TABLE transactions ADD COLUMN trade_date DATE;"))
        conn.commit()

        # 回填已有数据：将created_at的日期部分设为trade_date
        conn.execute(text("""
            UPDATE transactions 
            SET trade_date = date(created_at) 
            WHERE trade_date IS NULL;
        """))
        conn.commit()
    print("✓ trade_date列添加完成，已有记录已回填")


def create_backtest_tables(engine) -> None:
    """创建回测相关表"""
    print("创建回测相关表...")
    
    create_portfolio_sql = """
    CREATE TABLE IF NOT EXISTS backtest_portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(20) NOT NULL,
        quantity INTEGER NOT NULL,
        cost_price FLOAT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(code)
    );
    """
    
    create_transactions_sql = """
    CREATE TABLE IF NOT EXISTS backtest_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type VARCHAR(10) NOT NULL,
        code VARCHAR(20) NOT NULL,
        quantity INTEGER NOT NULL,
        price FLOAT NOT NULL,
        amount FLOAT,
        trade_date DATE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_cash_sql = """
    CREATE TABLE IF NOT EXISTS backtest_cash (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        balance FLOAT NOT NULL DEFAULT 0.0,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_portfolio_sql))
        conn.execute(text(create_transactions_sql))
        conn.execute(text(create_cash_sql))
        conn.commit()
    print("✓ backtest_portfolio 表创建完成")
    print("✓ backtest_transactions 表创建完成")
    print("✓ backtest_cash 表创建完成")


def add_stock_daily_columns(engine) -> None:
    """为stock_daily表添加pe/pb/market_cap列（如果缺失）"""
    print("为stock_daily表添加pe/pb/market_cap列...")
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info('stock_daily')"))
        existing_cols = {row[1] for row in result.fetchall()}
        for col_name, col_type in [
            ('pe', 'FLOAT'),
            ('pb', 'FLOAT'),
            ('market_cap', 'FLOAT'),
        ]:
            if col_name not in existing_cols:
                conn.execute(text(
                    f"ALTER TABLE stock_daily ADD COLUMN {col_name} {col_type}"
                ))
                conn.commit()
                print(f"  ✓ Added column {col_name} to stock_daily")
            else:
                print(f"  - {col_name}列已存在，跳过")
    print("✓ stock_daily列检查完成")


def add_stock_daily_unique_constraint(engine) -> None:
    """为stock_daily表添加(code, date)唯一约束"""
    print("为stock_daily表添加(code, date)唯一约束...")
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA index_list(stock_daily);"))
        indexes = [row[1] for row in result.fetchall()]
        if 'uq_stock_daily_code_date' in indexes:
            print("✓ 唯一约束已存在，跳过")
            return

        conn.execute(text("BEGIN TRANSACTION"))
        try:
            conn.execute(text("""
                CREATE TABLE stock_daily_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code VARCHAR(20) NOT NULL,
                    date DATE NOT NULL,
                    open FLOAT,
                    high FLOAT,
                    low FLOAT,
                    close FLOAT,
                    volume FLOAT,
                    turnover FLOAT,
                    turnover_rate FLOAT,
                    change_percent FLOAT,
                    pe FLOAT,
                    pb FLOAT,
                    market_cap FLOAT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(code, date)
                );
            """))
            conn.execute(text("""
                INSERT OR REPLACE INTO stock_daily_new 
                SELECT id, code, date, open, high, low, close, volume, 
                       turnover, turnover_rate, change_percent, pe, pb, market_cap, created_at
                FROM stock_daily;
            """))
            conn.execute(text("DROP TABLE stock_daily;"))
            conn.execute(text("ALTER TABLE stock_daily_new RENAME TO stock_daily;"))
            conn.commit()
            print("✓ 唯一约束添加完成")
        except Exception as e:
            conn.execute(text("ROLLBACK"))
            print(f"✗ 添加约束失败: {e}")
            raise


def migrate() -> None:
    """执行完整的数据库迁移"""
    print("=" * 50)
    print("开始数据库迁移")
    print("=" * 50)

    # 获取数据库路径
    db_uri = Config.SQLALCHEMY_DATABASE_URI
    db_path = db_uri.replace('sqlite:///', '')

    # 步骤1: 备份数据库
    backup_path = db_path + '.backup'
    backup_database(db_path, backup_path)

    # 创建数据库引擎
    engine = create_engine(db_uri)

    # 步骤2: 创建crawl_status表
    create_crawl_status_table(engine)

    # 步骤3: 创建持仓相关的表
    create_portfolio_tables(engine)

    # 步骤4: 为stock_daily表添加pe/pb/market_cap列
    add_stock_daily_columns(engine)

    # 步骤5: 为stock_daily表添加唯一约束
    add_stock_daily_unique_constraint(engine)

    # 步骤6: 为transactions表添加trade_date列
    add_trade_date_column(engine)

    # 步骤7: 验证迁移
    verify_migration(engine)

    # 步骤8: 创建回测相关表
    create_backtest_tables(engine)

    print("\n" + "=" * 50)
    print("迁移完成")
    print("=" * 50)
    print(f"备份文件: {backup_path}")
    print("若迁移失败，可删除 {} 并恢复备份".format(db_path))


if __name__ == "__main__":
    migrate()
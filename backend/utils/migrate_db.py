"""数据库迁移脚本：为stocks表增加price_date字段，创建crawl_status表"""
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


def add_price_date_column(engine) -> None:
    """为stocks表增加price_date列"""
    print("为stocks表增加price_date列...")
    alter_table_sql = "ALTER TABLE stocks ADD COLUMN price_date DATE;"
    try:
        with engine.connect() as conn:
            conn.execute(text(alter_table_sql))
            conn.commit()
        print("✓ price_date列添加完成")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("price_date列已存在，跳过添加")
        else:
            raise


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

        # 检查stocks表的列
        result = conn.execute(text("PRAGMA table_info(stocks);"))
        columns = [row[1] for row in result.fetchall()]
        if 'price_date' in columns:
            print("✓ stocks表包含price_date列")
        else:
            print("✗ stocks表缺少price_date列")
            return

    print("✓ 迁移验证成功")


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

    # 步骤3: 为stocks表增加price_date列
    add_price_date_column(engine)

    # 步骤4: 为stock_daily表添加唯一约束
    add_stock_daily_unique_constraint(engine)

    # 步骤5: 验证迁移
    verify_migration(engine)

    print("\n" + "=" * 50)
    print("迁移完成")
    print("=" * 50)
    print(f"备份文件: {backup_path}")
    print("若迁移失败，可删除 {} 并恢复备份".format(db_path))


if __name__ == "__main__":
    migrate()
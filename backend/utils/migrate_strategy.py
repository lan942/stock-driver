"""数据库迁移脚本：创建策略相关表"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from backend.config import Config


def create_strategy_tables(engine) -> None:
    """创建策略相关的四张表"""
    print("创建策略相关表...")

    # 策略持仓表
    create_positions_sql = """
    CREATE TABLE IF NOT EXISTS strategy_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR(20) NOT NULL,
        name VARCHAR(100),
        quantity INTEGER NOT NULL,
        buy_price FLOAT NOT NULL,
        target_price FLOAT NOT NULL,
        stop_price FLOAT NOT NULL,
        suggested_buy_price FLOAT,
        buy_date DATE NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'holding',
        sell_price FLOAT,
        sell_date DATE,
        profit_pct FLOAT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """

    # 策略交易记录表
    create_transactions_sql = """
    CREATE TABLE IF NOT EXISTS strategy_transactions (
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

    # 策略现金余额表
    create_cash_sql = """
    CREATE TABLE IF NOT EXISTS strategy_cash (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        balance FLOAT NOT NULL DEFAULT 0.0,
        initial_capital FLOAT NOT NULL DEFAULT 0.0,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """

    # 策略配置表
    create_config_sql = """
    CREATE TABLE IF NOT EXISTS strategy_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key VARCHAR(50) UNIQUE NOT NULL,
        value VARCHAR(500) NOT NULL,
        description VARCHAR(200),
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """

    with engine.connect() as conn:
        conn.execute(text(create_positions_sql))
        conn.execute(text(create_transactions_sql))
        conn.execute(text(create_cash_sql))
        conn.execute(text(create_config_sql))
        conn.commit()

    print("[OK] strategy_positions 表创建完成")
    print("[OK] strategy_transactions 表创建完成")
    print("[OK] strategy_cash 表创建完成")
    print("[OK] strategy_config 表创建完成")


def init_default_config(engine) -> None:
    """初始化默认策略配置"""
    import json
    print("初始化默认策略配置...")

    defaults = [
        ('target_annual_return', '0.15', '期望年化收益率'),
        ('initial_capital', '100000', '初始资金（元）'),
        ('max_positions', '5', '最大同时持仓只数'),
        ('position_ratio', '0.2', '单只仓位占可用资金比例'),
        ('stop_profit_pct', '0.06', '止盈比例'),
        ('stop_loss_pct', '0.03', '止损比例'),
        ('max_hold_days', '5', '最大持有天数'),
        ('factor_weights', json.dumps({"trend": 0.30, "momentum": 0.25, "volume": 0.20, "reversal": 0.15, "volatility": 0.10}), '因子权重'),
    ]

    with engine.connect() as conn:
        for key, value, desc in defaults:
            # 检查是否已存在
            result = conn.execute(text("SELECT id FROM strategy_config WHERE key = :key"), {"key": key})
            if result.fetchone() is None:
                conn.execute(text(
                    "INSERT INTO strategy_config (key, value, description) VALUES (:key, :value, :desc)"
                ), {"key": key, "value": value, "desc": desc})
        conn.commit()

    print("[OK] 默认策略配置初始化完成")


def verify_strategy_tables(engine) -> None:
    """验证策略表"""
    print("\n验证策略表...")
    tables = ['strategy_positions', 'strategy_transactions', 'strategy_cash', 'strategy_config']
    with engine.connect() as conn:
        for table in tables:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=:name"
            ), {"name": table})
            if result.fetchone():
                print(f"[OK] {table} 表存在")
            else:
                print(f"[FAIL] {table} 表不存在")
    print("[OK] 策略表验证完成")


def migrate() -> None:
    """执行策略模块数据库迁移"""
    print("=" * 50)
    print("开始策略模块数据库迁移")
    print("=" * 50)

    db_uri = Config.SQLALCHEMY_DATABASE_URI
    engine = create_engine(db_uri)

    create_strategy_tables(engine)
    init_default_config(engine)
    verify_strategy_tables(engine)

    print("\n" + "=" * 50)
    print("策略模块迁移完成")
    print("=" * 50)


if __name__ == "__main__":
    migrate()

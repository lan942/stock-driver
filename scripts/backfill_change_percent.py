"""一次性回填脚本：补全 stock_daily 中 change_percent 为 NULL 的记录。

根因：腾讯 stock_zh_a_daily 接口不返回涨跌幅，normalizer 只能从 df 内部
prev_close 计算；单日补爬时 df 仅有 1 行，change_percent 必然为 NULL。
此脚本基于数据库内上一交易日 close 回填历史数据。

用法:
    py scripts/backfill_change_percent.py          # 默认回填
    py scripts/backfill_change_percent.py --dry-run # 只统计，不写入
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "stock.db"


def backfill(dry_run: bool = False) -> None:
    if not DB_PATH.exists():
        print(f"[ERROR] 数据库不存在: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()

    # 先看有多少条需要回填
    cur.execute(
        "SELECT COUNT(*) FROM stock_daily "
        "WHERE change_percent IS NULL AND close IS NOT NULL"
    )
    total_pending = cur.fetchone()[0]
    print(f"待回填记录数（change_percent IS NULL 且 close IS NOT NULL）: {total_pending}")

    if total_pending == 0:
        con.close()
        print("无可回填数据，退出。")
        return

    # 用 LAG 窗口函数一次性算出每条记录的 prev_close
    cur.execute(
        """
        WITH ranked AS (
            SELECT id, close, change_percent,
                   LAG(close) OVER (PARTITION BY code ORDER BY date) AS prev_close
            FROM stock_daily
            WHERE close IS NOT NULL
        )
        SELECT id, close, prev_close
        FROM ranked
        WHERE change_percent IS NULL
          AND prev_close IS NOT NULL
          AND prev_close != 0
        """
    )
    rows = cur.fetchall()

    updatable = len(rows)
    skipped = total_pending - updatable
    print(f"可回填（能找到前一日 close）: {updatable}")
    print(f"跳过（找不到前一日 close）  : {skipped}")

    if dry_run:
        print("[dry-run] 未写入数据库。")
        con.close()
        return

    # 批量 UPDATE
    updated = 0
    for rec_id, close, prev_close in rows:
        pct = round((close - prev_close) / prev_close * 100, 4)
        cur.execute(
            "UPDATE stock_daily SET change_percent = ? WHERE id = ?",
            (pct, rec_id),
        )
        updated += 1

    con.commit()
    con.close()
    print(f"回填完成: 已更新 {updated} 条记录。")


def main() -> None:
    parser = argparse.ArgumentParser(description="回填 stock_daily.change_percent")
    parser.add_argument(
        "--dry-run", action="store_true", help="只统计不写入"
    )
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

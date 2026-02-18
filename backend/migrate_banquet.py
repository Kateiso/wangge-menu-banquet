"""独立迁移脚本：为已有数据库添加宴会模式所需字段。

用法: python backend/migrate_banquet.py [menu.db]
"""
import sqlite3
import sys


def migrate(db_path: str = "menu.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # dish.min_price
    cols = {row[1] for row in cur.execute("PRAGMA table_info(dish)").fetchall()}
    if "min_price" not in cols:
        cur.execute("ALTER TABLE dish ADD COLUMN min_price REAL DEFAULT 0.0")
        cur.execute("UPDATE dish SET min_price = ROUND(cost * 1.3, 2) WHERE min_price = 0")
        print("dish.min_price: added + backfilled")
    else:
        print("dish.min_price: already exists")

    # menu.mode
    cols = {row[1] for row in cur.execute("PRAGMA table_info(menu)").fetchall()}
    if "mode" not in cols:
        cur.execute("ALTER TABLE menu ADD COLUMN mode TEXT DEFAULT 'retail'")
        print("menu.mode: added")
    else:
        print("menu.mode: already exists")

    # menuitem.min_price
    cols = {row[1] for row in cur.execute("PRAGMA table_info(menuitem)").fetchall()}
    if "min_price" not in cols:
        cur.execute("ALTER TABLE menuitem ADD COLUMN min_price REAL DEFAULT 0.0")
        print("menuitem.min_price: added")
    else:
        print("menuitem.min_price: already exists")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "menu.db"
    migrate(path)

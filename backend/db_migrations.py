import sqlite3
from pathlib import Path

from sqlalchemy.engine import Engine


def run_sqlite_compat_migrations(engine: Engine) -> None:
    db_path = engine.url.database
    if engine.url.get_backend_name() != "sqlite" or not db_path or db_path == ":memory:":
        return

    path = Path(db_path)
    if not path.exists():
        return

    conn = sqlite3.connect(path)
    cur = conn.cursor()

    package_item_cols = {row[1] for row in cur.execute("PRAGMA table_info(packageitem)").fetchall()}
    if "override_price" not in package_item_cols:
        cur.execute("ALTER TABLE packageitem ADD COLUMN override_price REAL")

    menu_item_cols = {row[1] for row in cur.execute("PRAGMA table_info(menuitem)").fetchall()}
    if "additive_price" not in menu_item_cols:
        cur.execute("ALTER TABLE menuitem ADD COLUMN additive_price REAL DEFAULT 0.0")
        cur.execute(
            """
            UPDATE menuitem
            SET additive_price = CASE
                WHEN adjusted_price > 0 THEN adjusted_price
                ELSE price
            END
            WHERE additive_price = 0
            """
        )

    conn.commit()
    conn.close()

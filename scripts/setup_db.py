
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "docs" / "schema.sql"
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "employee_performance.db"


def setup_database():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        connection.executescript(schema_sql)

        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        print(f"Database: {DB_PATH}")
        print(f"Tables created: {len(tables)}")
        for (table_name,) in tables:
            print(f"  - {table_name}")

        if foreign_key_errors:
            raise RuntimeError(
                f"Foreign-key validation failed: {foreign_key_errors}"
            )

        if integrity != "ok":
            raise RuntimeError(f"Integrity check failed: {integrity}")

        print("Foreign-key check: PASSED")
        print("Integrity check: PASSED")
        print("Database setup completed successfully.")


if __name__ == "__main__":
    setup_database()
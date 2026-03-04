"""Migrate a plain SQLite database to SQLCipher encryption.

Usage:
    .venv/bin/python scripts/migrate_to_sqlcipher.py --dry-run
    .venv/bin/python scripts/migrate_to_sqlcipher.py --db-path ./kinfolk.db
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sqlite3
import sys

# Allow standalone execution from backend/ root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings  # noqa: E402
from app.utils.crypto import (  # noqa: E402
    derive_sqlcipher_key_from_settings,
    sqlcipher_hex_literal,
)

try:
    from sqlcipher3 import dbapi2 as sqlcipher_dbapi
except ModuleNotFoundError as exc:
    raise RuntimeError("sqlcipher3 must be installed for migration") from exc

sqlcipher_connect = getattr(sqlcipher_dbapi, "connect")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help=("Path to source SQLite DB. Defaults to configured database_url path."),  # noqa: E501
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect DB state only. Do not write any files.",
    )
    return parser.parse_args()


def resolve_db_path(explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        return explicit_path.resolve()

    db_url = settings.database_url
    if not db_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// database URLs are supported")
    configured_path = db_url.removeprefix("sqlite:///")
    return Path(configured_path).resolve()


def is_plain_sqlite(db_path: Path) -> bool:
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sqlite_master")
        cur.fetchone()
        cur.close()
        conn.close()
        return True
    except sqlite3.DatabaseError:
        return False


def is_sqlcipher_with_key(db_path: Path, key_hex: str) -> bool:
    conn = sqlcipher_connect(str(db_path))
    try:
        cur = conn.cursor()
        key_literal = sqlcipher_hex_literal(key_hex)
        cur.execute(f'PRAGMA key = "{key_literal}"')
        cur.execute("SELECT COUNT(*) FROM sqlite_master")
        cur.fetchone()
        cur.close()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def is_sqlcipher_with_legacy_secret(db_path: Path, legacy_secret: str) -> bool:
    conn = sqlcipher_connect(str(db_path))
    try:
        cur = conn.cursor()
        escaped_secret = legacy_secret.replace("'", "''")
        cur.execute(f"PRAGMA key = '{escaped_secret}'")
        cur.execute("SELECT COUNT(*) FROM sqlite_master")
        cur.fetchone()
        cur.close()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def table_row_counts_sqlite(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cur.fetchall()]
        counts: dict[str, int] = {}
        for table in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            counts[table] = int(cur.fetchone()[0])
        cur.close()
        return counts
    finally:
        conn.close()


def table_row_counts_sqlcipher(db_path: Path, key_hex: str) -> dict[str, int]:
    conn = sqlcipher_connect(str(db_path))
    try:
        cur = conn.cursor()
        key_literal = sqlcipher_hex_literal(key_hex)
        cur.execute(f'PRAGMA key = "{key_literal}"')
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cur.fetchall()]
        counts: dict[str, int] = {}
        for table in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            counts[table] = int(cur.fetchone()[0])
        cur.close()
        return counts
    finally:
        conn.close()


def table_row_counts_sqlcipher_with_secret(
    db_path: Path,
    secret: str,
) -> dict[str, int]:
    conn = sqlcipher_connect(str(db_path))
    try:
        cur = conn.cursor()
        escaped_secret = secret.replace("'", "''")
        cur.execute(f"PRAGMA key = '{escaped_secret}'")
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cur.fetchall()]
        counts: dict[str, int] = {}
        for table in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            counts[table] = int(cur.fetchone()[0])
        cur.close()
        return counts
    finally:
        conn.close()


def migrate_plain_to_sqlcipher(db_path: Path, key_hex: str) -> None:
    tmp_path = db_path.with_suffix(db_path.suffix + ".sqlcipher.tmp")
    backup_path = db_path.with_suffix(db_path.suffix + ".backup")

    if tmp_path.exists():
        tmp_path.unlink()

    conn = sqlcipher_connect(str(db_path))
    cur = conn.cursor()
    try:
        attached_key = sqlcipher_hex_literal(key_hex)
        cur.execute(  # noqa: E501
            f"ATTACH DATABASE '{tmp_path}' AS encrypted KEY \"{attached_key}\""
        )
        cur.execute("SELECT sqlcipher_export('encrypted')")
        cur.execute("DETACH DATABASE encrypted")
        conn.commit()
    finally:
        cur.close()
        conn.close()

    source_counts = table_row_counts_sqlite(db_path)
    encrypted_counts = table_row_counts_sqlcipher(tmp_path, key_hex)
    if source_counts != encrypted_counts:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(
            "Row count verification failed. "
            f"source={source_counts}, encrypted={encrypted_counts}"
        )

    shutil.copy2(db_path, backup_path)
    shutil.move(str(tmp_path), str(db_path))


def rekey_legacy_sqlcipher(
    db_path: Path,
    legacy_secret: str,
    key_hex: str,
) -> None:
    backup_path = db_path.with_suffix(db_path.suffix + ".backup")
    escaped_secret = legacy_secret.replace("'", "''")
    key_literal = sqlcipher_hex_literal(key_hex)

    before_counts = table_row_counts_sqlcipher_with_secret(
        db_path,
        legacy_secret,
    )
    shutil.copy2(db_path, backup_path)

    conn = sqlcipher_connect(str(db_path))
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA key = '{escaped_secret}'")
        cur.execute(f'PRAGMA rekey = "{key_literal}"')
        conn.commit()
    finally:
        cur.close()
        conn.close()

    after_counts = table_row_counts_sqlcipher(db_path, key_hex)
    if before_counts != after_counts:
        raise RuntimeError(
            "Legacy SQLCipher rekey verification failed. "
            f"before={before_counts}, after={after_counts}"
        )


def main() -> int:
    args = parse_args()
    db_path = resolve_db_path(args.db_path)
    key_hex = derive_sqlcipher_key_from_settings()
    legacy_secret = settings.database_encryption_key

    if not db_path.exists():
        print(f"[FAIL] Database path does not exist: {db_path}")
        return 1

    plain = is_plain_sqlite(db_path)
    encrypted = is_sqlcipher_with_key(db_path, key_hex)
    encrypted_legacy = is_sqlcipher_with_legacy_secret(db_path, legacy_secret)

    if encrypted:
        print(f"[OK] Already SQLCipher-encrypted with current key: {db_path}")
        return 0

    if encrypted_legacy:
        if args.dry_run:
            print(f"[WARN] DB uses legacy SQLCipher passphrase key: {db_path}")
            print("[INFO] Dry-run mode: no migration/rekey performed")
            return 0

        print(f"[WORK] Rekeying legacy SQLCipher database: {db_path}")
        rekey_legacy_sqlcipher(db_path, legacy_secret, key_hex)
        print(f"[OK] Rekey completed. Backup created at: {db_path}.backup")
        return 0

    if not plain:
        print(
            "[FAIL] Database is not plain SQLite and cannot be opened with "
            "current key. It may be encrypted with a different key "
            "or corrupted."
        )
        return 1

    if args.dry_run:
        print(f"[OK] Plain SQLite database detected: {db_path}")
        print("[INFO] Dry-run mode: no migration performed")
        return 0

    print(f"[WORK] Migrating plain SQLite -> SQLCipher: {db_path}")
    migrate_plain_to_sqlcipher(db_path, key_hex)
    if not is_sqlcipher_with_key(db_path, key_hex):
        print("[FAIL] Post-migration verification failed")
        return 1

    print(f"[OK] Migration completed. Backup created at: {db_path}.backup")
    return 0


if __name__ == "__main__":
    sys.exit(main())

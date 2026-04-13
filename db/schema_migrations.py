from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

MIGRATIONS_TABLE = "schema_migrations"
BASE_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BASE_DIR / "migrations"


def ensure_schema_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
            name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def list_migration_paths() -> list[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(
        path
        for path in MIGRATIONS_DIR.glob("*.py")
        if path.is_file() and not path.name.startswith("__")
    )


def list_migration_names() -> list[str]:
    return [path.stem for path in list_migration_paths()]


def get_applied_migration_names(conn: sqlite3.Connection) -> list[str]:
    ensure_schema_migrations_table(conn)
    rows = conn.execute(
        f"""
        SELECT name
        FROM {MIGRATIONS_TABLE}
        ORDER BY name ASC
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


def get_pending_migration_names(conn: sqlite3.Connection) -> list[str]:
    applied = set(get_applied_migration_names(conn))
    return [name for name in list_migration_names() if name not in applied]


def _load_migration_module(path: Path):
    spec = importlib.util.spec_from_file_location(f"schema_migration_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nao foi possivel carregar a migration {path.name}.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_pending_migrations(conn: sqlite3.Connection) -> list[str]:
    ensure_schema_migrations_table(conn)
    applied = set(get_applied_migration_names(conn))
    executed = []

    for path in list_migration_paths():
        migration_name = path.stem
        if migration_name in applied:
            continue

        module = _load_migration_module(path)
        upgrade = getattr(module, "upgrade", None)
        if not callable(upgrade):
            raise RuntimeError(f"Migration {path.name} nao expoe upgrade(conn).")

        upgrade(conn)
        conn.execute(
            f"""
            INSERT OR IGNORE INTO {MIGRATIONS_TABLE} (name, applied_at)
            VALUES (?, datetime('now'))
            """,
            (migration_name,),
        )
        conn.commit()
        executed.append(migration_name)
        applied.add(migration_name)

    return executed


def _configure_db_path_env(db_path: str | None) -> None:
    if not db_path:
        return
    os.environ["DB_PATH"] = str(Path(db_path).expanduser())


def _resolve_db_path(db_path: str | None = None) -> Path:
    if db_path:
        return Path(db_path).expanduser()
    env_path = os.getenv("DB_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    return BASE_DIR.parent / "sistema-impress-data" / "impressao.db"


def _open_connection(db_path: str | None = None) -> sqlite3.Connection:
    resolved_path = _resolve_db_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved_path))
    return conn


def _import_database_module(*, reload_module: bool = False):
    if "database" in sys.modules:
        if reload_module:
            return importlib.reload(sys.modules["database"])
        return sys.modules["database"]
    return importlib.import_module("database")


def upgrade_database(db_path: str | None = None) -> list[str]:
    _configure_db_path_env(db_path)
    database = _import_database_module(reload_module=db_path is not None)

    before = set()
    conn = _open_connection(db_path)
    try:
        before = set(get_applied_migration_names(conn))
    finally:
        conn.close()

    database.criar_tabelas()

    conn = _open_connection(db_path)
    try:
        after = set(get_applied_migration_names(conn))
    finally:
        conn.close()

    return sorted(after - before)


def get_migration_status(db_path: str | None = None) -> dict[str, list[str]]:
    conn = _open_connection(db_path)
    try:
        applied = get_applied_migration_names(conn)
        pending = get_pending_migration_names(conn)
    finally:
        conn.close()
    return {
        "applied": applied,
        "pending": pending,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gerencia migrations versionadas do schema SQLite."
    )
    parser.add_argument(
        "action",
        choices=["upgrade", "status"],
        help="upgrade aplica bootstrap + migrations pendentes; status lista o estado atual.",
    )
    parser.add_argument(
        "--db",
        default=os.getenv("DB_PATH", "").strip() or None,
        help="Caminho opcional para o banco SQLite.",
    )
    args = parser.parse_args()

    if args.action == "upgrade":
        executed = upgrade_database(args.db)
        if executed:
            print("Migrations aplicadas:")
            for migration_name in executed:
                print(f"- {migration_name}")
        else:
            print("Nenhuma migration pendente.")
        return

    status = get_migration_status(args.db)
    print("Applied:")
    for migration_name in status["applied"]:
        print(f"- {migration_name}")

    print("Pending:")
    for migration_name in status["pending"]:
        print(f"- {migration_name}")


if __name__ == "__main__":
    main()

import importlib.util
import sqlite3
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def load_blog_migration(filename: str):
    path = MIGRATIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(f"test_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nao foi possivel carregar a migration {filename}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_blog_migrations(conn: sqlite3.Connection) -> None:
    load_blog_migration("20260812_create_blog_module.py").upgrade(conn)
    load_blog_migration("20260813_add_blog_tags.py").upgrade(conn)

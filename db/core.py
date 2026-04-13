from ._proxy import get_database_attr, proxy

DB_PATH = get_database_attr("DB_PATH")
get_connection = proxy("get_connection")

__all__ = [
    "DB_PATH",
    "get_connection",
]

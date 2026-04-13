import importlib


def get_database_attr(name: str):
    return getattr(importlib.import_module("database"), name)


def proxy(name: str):
    def wrapper(*args, **kwargs):
        return get_database_attr(name)(*args, **kwargs)

    wrapper.__name__ = name
    wrapper.__qualname__ = name
    wrapper.__module__ = __name__
    return wrapper

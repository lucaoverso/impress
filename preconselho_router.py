"""Legacy compatibility shim for the pre-conselho module.

The real implementation now lives in ``modules.preconselho.router``.
This file remains only to preserve compatibility with older imports and
tests while the broader refactor is still in progress.
"""

import importlib

from fastapi import HTTPException

_module_router = importlib.import_module("modules.preconselho.router")

router = _module_router.router


def __getattr__(name: str):
    return getattr(_module_router, name)


__all__ = ["router", "HTTPException"]

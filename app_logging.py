from __future__ import annotations

import logging
import os


def _resolver_log_level() -> int:
    nome_nivel = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    return getattr(logging, nome_nivel, logging.INFO)


def setup_logging() -> None:
    if getattr(setup_logging, "_configured", False):
        return

    logging.basicConfig(
        level=_resolver_log_level(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    setup_logging._configured = True

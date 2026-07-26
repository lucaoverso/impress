import logging
import time

from db.bootstrap import criar_tabelas

from . import delivery_repository
from .apc_integration import reconcile_all_apc
from .push import process_one_delivery

logger = logging.getLogger(__name__)


def worker_loop():
    criar_tabelas()
    last_reconcile = 0.0
    last_cleanup = 0.0
    logger.info("Worker de notificacoes iniciado")
    while True:
        now = time.monotonic()
        try:
            if now - last_reconcile >= 60:
                reconcile_all_apc()
                last_reconcile = now
            if now - last_cleanup >= 3600:
                delivery_repository.purge_old(180)
                last_cleanup = now
            processed = False
            for _ in range(20):
                if not process_one_delivery():
                    break
                processed = True
            time.sleep(1 if processed else 5)
        except Exception:
            logger.exception("Falha no ciclo do worker de notificacoes")
            time.sleep(5)

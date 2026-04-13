import logging

from app_logging import setup_logging
from db.bootstrap import criar_tabelas
from services.worker import worker_loop

setup_logging()
logger = logging.getLogger(__name__)


def main():
    logger.info("Inicializando worker externo")
    criar_tabelas()
    worker_loop()


if __name__ == "__main__":
    main()

from app_logging import setup_logging
from modules.notifications.worker import worker_loop


def main():
    setup_logging()
    worker_loop()


if __name__ == "__main__":
    main()

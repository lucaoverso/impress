from database import criar_tabelas
from services.worker import worker_loop

def main():
    criar_tabelas()
    worker_loop()

if __name__ == "__main__":
    main()

PYTHON ?= $(shell if [ -x venv/bin/python ]; then echo venv/bin/python; elif [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
PIP ?= $(PYTHON) -m pip
RUFF ?= $(shell if [ -x venv/bin/ruff ]; then echo venv/bin/ruff; elif [ -x .venv/bin/ruff ]; then echo .venv/bin/ruff; else echo ruff; fi)

.PHONY: install install-dev test lint format check migrate migrations-status seed-demo

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

test:
	$(PYTHON) -m unittest discover -s tests -q

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

check: lint test

migrate:
	$(PYTHON) -m db.schema_migrations upgrade

migrations-status:
	$(PYTHON) -m db.schema_migrations status

seed-demo:
	$(PYTHON) -m db.demo_seed

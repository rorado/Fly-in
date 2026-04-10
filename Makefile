
PYTHON = python3
VENV   := .venv
PIP    := $(VENV)/bin/pip
PYBIN  := $(VENV)/bin/python

.PHONY: install run debug clean lint lint-strict

install:
@$(PYTHON) -m venv $(VENV)
@$(PIP) install --upgrade pip --quiet
@$(PIP) install flake8 mypy --quiet
@echo "Dependencies installed."

run:
@$(PYBIN) main.py map.txt

debug:
@$(PYBIN) -m pdb main.py map.txt

clean:
@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
@rm -rf .mypy_cache
@echo "Cleaned."

lint:
@flake8 .
@mypy . \
--warn-return-any \
--warn-unused-ignores \
--ignore-missing-imports \
--disallow-untyped-defs \
--check-untyped-defs

lint-strict:
@flake8 .
@mypy . --strict


PYTHON = python3
VENV := .venv


install:
	@$(PYTHON) -m venv $(VENV)
	@$(PYTHON) 
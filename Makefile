
PYTHON      = python3
MAIN        = main.py
CONFIG      = map.txt


run:
	@$(PYTHON) $(MAIN) $(CONFIG)

install:
	@pip install --upgrade pip
	@pip install flake8 mypy webcolors pygame pydantic

debug:
	@$(PYTHON) -m pdb $(MAIN) $(CONFIG)

clean:
	@rm -rf __pycache__ .mypy_cache


lint:
	-@$(PYTHON) -m flake8 .
	-@$(PYTHON) -m mypy . \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs || true

lint-strict:
	-@$(PYTHON) -m flake8 .
	-@$(PYTHON) -m mypy . --strict

PYTHON ?= .venv/Scripts/python

.DEFAULT_GOAL := help
.PHONY: help grammars unit e2e black flake8 ruff

help:
	@echo "Usage: make <target> [PYTHON=path/to/python]"
	@echo ""
	@echo "Tests:"
	@echo "  grammars Download the tree-sitter grammars the packs use, so tests stay offline"
	@echo "  unit     Run the fast tests and fail if coverage drops below 90%"
	@echo "  e2e      Run the deep tests that start the tool as a real process"
	@echo ""
	@echo "Code style:"
	@echo "  black    Reformat jev_gate and tests in place"
	@echo "  flake8   Check jev_gate and tests with flake8"
	@echo "  ruff     Check jev_gate and tests with ruff"
	@echo ""
	@echo "PYTHON defaults to $(PYTHON)"

grammars:
	$(PYTHON) -c "import glob, yaml, tree_sitter_language_pack as t; t.download(sorted({n for f in glob.glob('jev_gate/packs/*.yml') for n in yaml.safe_load(open(f))['grammars'].values()}))"

unit: grammars
	$(PYTHON) -m pytest -m "not deep and not online" --cov --cov-report=term-missing --cov-fail-under=90

e2e: grammars
	$(PYTHON) -m pytest -m deep

black:
	$(PYTHON) -m black jev_gate tests

flake8:
	$(PYTHON) -m flake8 jev_gate tests

ruff:
	$(PYTHON) -m ruff check jev_gate tests

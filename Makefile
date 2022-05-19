PYTHON ?= python
LINT_TARGETS := ./magnit_calc ./tests

PYCODESTYLE ?= pycodestyle
PYCODESTYLE_CMD ?= $(PYCODESTYLE) $(LINT_TARGETS)

pycodestyle:
	$(PYCODESTYLE_CMD)

MYPY ?= mypy
MYPY_CMD ?= $(MYPY) $(LINT_TARGETS)

mypy:
	$(MYPY_CMD)


FLAKE8 ?= flake8
FLAKE8_CMD ?= $(FLAKE8) $(LINT_TARGETS)

flake8:
	$(FLAKE8_CMD)

CPUCOUNT=$(shell $(PYTHON) -c 'from multiprocessing import cpu_count ; print(cpu_count() or 1)')
PYLINT ?= pylint
PYLINT_CMD ?= $(PYLINT) --jobs=$(CPUCOUNT) $(LINT_TARGETS)

pylint:
	$(PYLINT_CMD)


lint: pycodestyle flake8 pylint mypy

PYTEST ?= pytest

test:
	$(PYTEST)


.coverage: test

COVERAGE ?= coverage

coverage-repot: .coverage
	$(COVERAGE) report -m

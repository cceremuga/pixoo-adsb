PYTHON = venv/bin/python
BLACK  = venv/bin/black

.PHONY: setup run format test

setup:
	bash setup.sh

run:
	$(PYTHON) main.py

format:
	$(BLACK) *.py
	venv/bin/isort *.py
	venv/bin/pylint *.py
	venv/bin/mdformat *.md

test:
	venv/bin/pytest tests.py -v

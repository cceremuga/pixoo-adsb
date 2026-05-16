PYTHON = venv/bin/python
BLACK  = venv/bin/black

.PHONY: setup run run-debug emulate format test sample

setup:
	bash setup.sh

run:
	$(PYTHON) main.py

run-debug:
	$(PYTHON) main.py --debug

emulate:
	$(PYTHON) emulate.py --debug

format:
	$(BLACK) *.py
	venv/bin/isort *.py
	venv/bin/pylint *.py
	venv/bin/mdformat *.md

test:
	venv/bin/pytest tests.py -v

sample:
	$(PYTHON) generate_sample.py

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
	$(BLACK) *.py enrichers/*.py
	venv/bin/isort *.py enrichers/*.py
	venv/bin/pylint *.py enrichers/*.py
	venv/bin/mdformat *.md
	$(PYTHON) -m json.tool --indent 2 sample.config.json > sample.config.json.tmp && mv sample.config.json.tmp sample.config.json

test:
	venv/bin/pytest tests.py -v

sample:
	$(PYTHON) generate_sample.py

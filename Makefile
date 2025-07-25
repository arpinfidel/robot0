.PHONY: setup run

setup:
	python3 -m venv venv
	chmod +x venv/bin/activate
	. venv/bin/activate && pip install -r requirements.txt

install:
	. venv/bin/activate && pip install -r requirements.txt

run:
	. venv/bin/activate && python3 main.py

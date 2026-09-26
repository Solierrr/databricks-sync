PYTHON ?= python
VENV := .venv

ifeq ($(OS),Windows_NT)
VENV_PYTHON := $(VENV)/Scripts/python.exe
else
VENV_PYTHON := $(VENV)/bin/python
endif

.PHONY: setup run

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -r requirements.txt

run:
	$(VENV_PYTHON) -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

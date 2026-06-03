SHELL := /bin/bash
PYTHON ?= python3
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
THREE_VERSION := 0.160.0
PORT ?= 8000

.PHONY: install vendor serve serve-static test-unit test-backend test-e2e test record-demo clean

install: $(VENV)/bin/activate vendor
	$(PY) -m playwright install --with-deps chromium

$(VENV)/bin/activate: pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .
	touch $(VENV)/bin/activate

vendor:
	mkdir -p static/vendor
	curl -fsSL "https://unpkg.com/three@$(THREE_VERSION)/build/three.module.js" -o static/vendor/three.module.js
	curl -fsSL "https://unpkg.com/three@$(THREE_VERSION)/examples/jsm/controls/PointerLockControls.js" -o static/vendor/PointerLockControls.js

serve: $(VENV)/bin/activate vendor
	$(PY) -m uvicorn server.main:app --host 127.0.0.1 --port $(PORT)

serve-static: vendor
	$(PYTHON) -m http.server $(PORT) --directory static

test-unit:
	npm test

test-backend: $(VENV)/bin/activate
	$(PY) -m pytest tests/backend

test-e2e: $(VENV)/bin/activate vendor
	$(PY) -m pytest tests/e2e

test: test-unit test-backend test-e2e

record-demo: $(VENV)/bin/activate vendor
	$(PY) tests/e2e/record_demo.py

clean:
	rm -rf .pytest_cache test-results

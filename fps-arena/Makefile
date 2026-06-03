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
	$(PYTHON) -c "import ensurepip" >/dev/null 2>&1 && $(PYTHON) -m venv $(VENV) || ( $(PYTHON) -m pip install --user virtualenv && $(PYTHON) -m virtualenv $(VENV) )
	$(PIP) install --upgrade pip
	$(PIP) install -e .
	touch $(VENV)/bin/activate

vendor:
	mkdir -p static/vendor
	test -s static/vendor/three.module.js || ( curl --retry 4 --retry-delay 2 --retry-all-errors -fsSL "https://unpkg.com/three@$(THREE_VERSION)/build/three.module.js" -o static/vendor/three.module.js || curl --retry 4 --retry-delay 2 --retry-all-errors -fsSL "https://cdn.jsdelivr.net/npm/three@$(THREE_VERSION)/build/three.module.js" -o static/vendor/three.module.js || ( npm pack three@$(THREE_VERSION) --silent && tar -xzf three-$(THREE_VERSION).tgz package/build/three.module.js && mv package/build/three.module.js static/vendor/three.module.js && rm -rf package three-$(THREE_VERSION).tgz ) )
	test -s static/vendor/PointerLockControls.js || ( curl --retry 4 --retry-delay 2 --retry-all-errors -fsSL "https://unpkg.com/three@$(THREE_VERSION)/examples/jsm/controls/PointerLockControls.js" -o static/vendor/PointerLockControls.js || curl --retry 4 --retry-delay 2 --retry-all-errors -fsSL "https://cdn.jsdelivr.net/npm/three@$(THREE_VERSION)/examples/jsm/controls/PointerLockControls.js" -o static/vendor/PointerLockControls.js || ( npm pack three@$(THREE_VERSION) --silent && tar -xzf three-$(THREE_VERSION).tgz package/examples/jsm/controls/PointerLockControls.js && mv package/examples/jsm/controls/PointerLockControls.js static/vendor/PointerLockControls.js && rm -rf package three-$(THREE_VERSION).tgz ) )

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

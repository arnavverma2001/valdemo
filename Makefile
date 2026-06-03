.PHONY: install lint test demo video

install:
	python3 -m pip install -e ".[dev]"
	python3 -m playwright install --with-deps chromium

lint:
	python3 -m ruff format --check .
	python3 -m ruff check .
	python3 -m mypy app

test:
	python3 -m pytest

demo:
	@echo "Serving Tactical Shooter at http://127.0.0.1:8000/?autoplay=1&seed=42&quick=1&speed=fast"
	python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000

video:
	python3 scripts/record_demo.py

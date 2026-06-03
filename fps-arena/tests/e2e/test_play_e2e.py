import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture()
def game_server(tmp_path):
    port = free_port()
    env = os.environ.copy()
    env["FPS_ARENA_SCORE_FILE"] = str(tmp_path / "scores.json")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 20
    while time.time() < deadline:
      try:
        with urlopen(url, timeout=1) as response:
          if response.status == 200:
            break
      except Exception:
        time.sleep(0.2)
    else:
      output = process.stdout.read() if process.stdout else ""
      process.terminate()
      raise RuntimeError(f"server failed to start:\n{output}")
    yield url
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def test_autoplay_reaches_terminal_state(game_server):
    page_errors = []
    console_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--use-gl=swiftshader",
                "--enable-unsafe-swiftshader",
                "--ignore-gpu-blocklist",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.goto(f"{game_server}/?autoplay=1&seed=42&waves=3", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => window.__fpsArenaState && window.__fpsArenaState.kills > 0 && window.__fpsArenaState.score > 0",
            timeout=60000,
        )
        page.locator("#result-banner.visible").wait_for(timeout=120000)
        banner = page.locator("#result-banner").inner_text(timeout=1000)
        state = page.evaluate("window.__fpsArenaState")
        browser.close()

    assert state["score"] > 0
    assert state["kills"] > 0
    assert "VICTORY" in banner or "GAME OVER" in banner
    assert page_errors == []
    assert console_errors == []

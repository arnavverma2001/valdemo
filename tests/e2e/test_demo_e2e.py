from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Generator

import pytest
from playwright.sync_api import Page, expect, sync_playwright


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def server_url() -> Generator[str]:
    port = free_port()
    process = subprocess.Popen(
        [
            "python3",
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.1)
        else:
            raise RuntimeError("uvicorn did not start")
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_autoplay_match_reaches_winner(server_url: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page: Page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{server_url}/?autoplay=1&seed=42&quick=1&speed=fast")
        banner = page.locator("#winner-banner")
        expect(banner).to_be_visible(timeout=120_000)
        expect(banner).to_contain_text("WINNER")
        browser.close()

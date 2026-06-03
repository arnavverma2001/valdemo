from __future__ import annotations

import shutil
import socket
import subprocess
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_port(port: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError("uvicorn did not start")


def main() -> None:
    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
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
    try:
        wait_for_port(port)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                record_video_dir=str(artifacts),
                record_video_size={"width": 1280, "height": 900},
            )
            page = context.new_page()
            page.goto(f"http://127.0.0.1:{port}/?autoplay=1&seed=42&quick=1&speed=fast")
            banner = page.locator("#winner-banner")
            expect(banner).to_be_visible(timeout=120_000)
            expect(banner).to_contain_text("WINNER")
            video = page.video
            context.close()
            browser.close()
            if video is None:
                raise RuntimeError("Playwright did not produce a video")
            source = Path(video.path())
            target = artifacts / f"demo-{int(time.time())}.webm"
            shutil.move(str(source), target)
            if target.stat().st_size <= 0:
                raise RuntimeError(f"video is empty: {target}")
            print(f"Recorded demo video: {target} ({target.stat().st_size} bytes)")
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == "__main__":
    main()

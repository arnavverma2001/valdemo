from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path("/opt/cursor/artifacts/assets")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    output = process.stdout.read() if process.stdout else ""
    raise RuntimeError(f"server failed to start:\n{output}")


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    port = free_port()
    env = os.environ.copy()
    env["FPS_ARENA_SCORE_FILE"] = str(Path(tempfile.mkdtemp()) / "scores.json")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        wait_for_server(url, process)
        with tempfile.TemporaryDirectory() as video_dir:
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
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    record_video_dir=video_dir,
                    record_video_size={"width": 1280, "height": 720},
                )
                page = context.new_page()
                page.goto(f"{url}/?autoplay=1&seed=42&waves=3", wait_until="domcontentloaded")
                page.locator("#result-banner.visible").wait_for(timeout=120000)
                banner = page.locator("#result-banner").inner_text()
                video = page.video
                context.close()
                browser.close()
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                output = ARTIFACTS / f"fps-arena-demo-{timestamp}.webm"
                if video is not None:
                    shutil.copyfile(video.path(), output)
                print(f"Recorded {output}")
                print(banner)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
DEFAULT_SCORE_FILE = Path(__file__).with_name("scores.json")


class ScoreIn(BaseModel):
    name: str = Field(min_length=1, max_length=24)
    score: int = Field(ge=0, le=1_000_000)
    wave: int = Field(ge=0, le=999)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name cannot be blank")
        return cleaned


app = FastAPI(title="FPS Arena")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


def score_file() -> Path:
    return Path(os.environ.get("FPS_ARENA_SCORE_FILE", DEFAULT_SCORE_FILE))


def read_scores() -> list[dict[str, Any]]:
    path = score_file()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]", encoding="utf-8")
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        path.write_text("[]", encoding="utf-8")
        return []
    if not isinstance(data, list):
        path.write_text("[]", encoding="utf-8")
        return []
    valid: list[dict[str, Any]] = []
    for item in data:
        if (
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and isinstance(item.get("score"), int)
            and isinstance(item.get("wave"), int)
        ):
            valid.append({"name": item["name"], "score": item["score"], "wave": item["wave"]})
    return sort_scores(valid)


def write_scores(scores: list[dict[str, Any]]) -> None:
    path = score_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sort_scores(scores)[:10], indent=2), encoding="utf-8")


def sort_scores(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(scores, key=lambda item: (-int(item["score"]), -int(item["wave"]), str(item["name"])))[:10]


@app.get("/api/scores")
def get_scores() -> dict[str, list[dict[str, Any]]]:
    return {"scores": read_scores()}


@app.post("/api/scores")
def post_score(score: ScoreIn) -> dict[str, list[dict[str, Any]]]:
    try:
        scores = read_scores()
        scores.append(score.model_dump())
        write_scores(scores)
        return {"scores": read_scores()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="static-assets")
app.mount("/src", StaticFiles(directory=STATIC_DIR / "src"), name="src")
app.mount("/vendor", StaticFiles(directory=STATIC_DIR / "vendor"), name="vendor")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{path:path}")
def static_fallback(path: str) -> FileResponse:
    file_path = STATIC_DIR / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(STATIC_DIR / "index.html")

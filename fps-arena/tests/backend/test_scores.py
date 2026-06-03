import importlib
import json

from fastapi.testclient import TestClient


def make_client(tmp_path, monkeypatch):
    score_file = tmp_path / "scores.json"
    monkeypatch.setenv("FPS_ARENA_SCORE_FILE", str(score_file))
    module = importlib.import_module("server.main")
    return TestClient(module.app), score_file


def test_get_scores_recreates_missing_file(tmp_path, monkeypatch):
    client, score_file = make_client(tmp_path, monkeypatch)
    response = client.get("/api/scores")
    assert response.status_code == 200
    assert response.json() == {"scores": []}
    assert score_file.exists()


def test_post_score_validates_and_persists(tmp_path, monkeypatch):
    client, score_file = make_client(tmp_path, monkeypatch)
    response = client.post("/api/scores", json={"name": "Ace", "score": 300, "wave": 3})
    assert response.status_code == 200
    assert response.json()["scores"][0] == {"name": "Ace", "score": 300, "wave": 3}
    assert json.loads(score_file.read_text())[0]["score"] == 300


def test_scores_are_sorted(tmp_path, monkeypatch):
    client, _ = make_client(tmp_path, monkeypatch)
    client.post("/api/scores", json={"name": "Low", "score": 100, "wave": 2})
    client.post("/api/scores", json={"name": "High", "score": 500, "wave": 1})
    assert [item["name"] for item in client.get("/api/scores").json()["scores"][:2]] == ["High", "Low"]


def test_invalid_input_returns_400(tmp_path, monkeypatch):
    client, _ = make_client(tmp_path, monkeypatch)
    response = client.post("/api/scores", json={"name": "", "score": -1, "wave": "bad"})
    assert response.status_code == 400


def test_corrupt_score_file_recovers(tmp_path, monkeypatch):
    client, score_file = make_client(tmp_path, monkeypatch)
    score_file.write_text("{not json")
    response = client.get("/api/scores")
    assert response.status_code == 200
    assert response.json() == {"scores": []}
    assert score_file.read_text() == "[]"

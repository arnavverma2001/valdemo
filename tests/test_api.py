from fastapi.testclient import TestClient

from app.api import GAMES
from app.main import app


def test_create_get_start_and_ai_step_routes() -> None:
    GAMES.clear()
    client = TestClient(app)
    created = client.post("/api/game", json={"seed": 123, "quick": True, "match_to": 2}).json()
    assert created["game_id"] == "game-123"
    assert created["phase"] == "BUY"

    got = client.get("/api/game/game-123")
    assert got.status_code == 200
    assert got.json()["seed"] == 123

    stepped = client.post("/api/game/game-123/ai_step")
    assert stepped.status_code == 200
    assert stepped.json()["phase"] in {"ACTION", "ROUND_END", "MATCH_END"}


def test_illegal_action_returns_400_and_does_not_mutate() -> None:
    GAMES.clear()
    client = TestClient(app)
    client.post("/api/game", json={"seed": 1, "quick": True})
    before = client.get("/api/game/game-1").json()
    response = client.post(
        "/api/game/game-1/action",
        json={"type": "end_activation", "unit_id": "A1"},
    )
    after = client.get("/api/game/game-1").json()
    assert response.status_code == 400
    assert before == after


def test_buy_route_shape_and_illegal_buy_400() -> None:
    GAMES.clear()
    client = TestClient(app)
    client.post("/api/game", json={"seed": 2, "quick": True})
    response = client.post("/api/game/game-2/buy", json={"unit_id": "A1", "weapon": "rifle"})
    assert response.status_code == 400
    assert "insufficient" in response.json()["detail"]

    response = client.post("/api/game/game-2/buy", json={"unit_id": "A1", "weapon": "pistol"})
    assert response.status_code == 200
    assert response.json()["units"][0]["weapon"] == "pistol"


def test_static_index_served() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Tactical Shooter" in response.text

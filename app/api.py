from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException

from app.engine.ai import choose_action
from app.engine.game import (
    GameSession,
    IllegalAction,
    apply_action,
    apply_buy,
    auto_buy,
    new_session,
    start_round,
)
from app.engine.schema import (
    ActionRequest,
    BuyRequest,
    GameConfig,
    GameCreateRequest,
    GameState,
    Phase,
)

router = APIRouter(prefix="/api")
GAMES: dict[str, GameSession] = {}


def _session(game_id: str) -> GameSession:
    if game_id not in GAMES:
        raise HTTPException(status_code=404, detail="game not found")
    return GAMES[game_id]


def _bad_request_without_mutation(
    session: GameSession, func: Callable[..., None], *args: Any
) -> GameState:
    before = session.state.model_copy(deep=True)
    try:
        func(session.state, *args)
    except IllegalAction as exc:
        session.state = before
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return session.state


@router.post("/game")
def create_game(request: GameCreateRequest) -> GameState:
    config = GameConfig(
        team_size=request.team_size,
        match_to=request.match_to,
        seed=request.seed,
        quick=request.quick,
        difficulty=request.difficulty,
    )
    session = new_session(config)
    GAMES[session.state.game_id] = session
    return session.state


@router.get("/game/{game_id}")
def get_game(game_id: str) -> GameState:
    return _session(game_id).state


@router.post("/game/{game_id}/buy")
def buy(game_id: str, request: BuyRequest) -> GameState:
    session = _session(game_id)
    return _bad_request_without_mutation(session, apply_buy, request)


@router.post("/game/{game_id}/start_round")
def api_start_round(game_id: str) -> GameState:
    session = _session(game_id)
    return _bad_request_without_mutation(session, start_round)


@router.post("/game/{game_id}/action")
def action(game_id: str, request: ActionRequest) -> GameState:
    session = _session(game_id)
    before = session.state.model_copy(deep=True)
    try:
        apply_action(session.state, session.rng, request)
    except IllegalAction as exc:
        session.state = before
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return session.state


@router.post("/game/{game_id}/ai_step")
def ai_step(game_id: str) -> GameState:
    session = _session(game_id)
    state = session.state
    if state.phase is Phase.BUY:
        auto_buy(state)
        start_round(state)
    elif state.phase is Phase.ROUND_END:
        start_round(state)
    elif state.phase is Phase.ACTION:
        request = choose_action(state, session.rng)
        apply_action(state, session.rng, request)
    return state

from random import Random

import pytest

from app.engine.combat import calculate_hit_chance
from app.engine.game import _end_round_turn, apply_action, new_game, start_round
from app.engine.grid import has_los
from app.engine.schema import ActionRequest, ActionType, GameConfig, Team, Vec2


def started_game(seed: int = 1):
    state = new_game(GameConfig(seed=seed, match_to=2))
    start_round(state)
    return state


def test_smoke_blocks_los_expires_after_two_round_turns_and_costs_ap() -> None:
    state = started_game()
    unit = state.unit("A1")
    enemy = state.unit("D1")
    unit.pos = Vec2(x=0, y=0)
    enemy.pos = Vec2(x=4, y=0)
    state.active_unit_id = "A1"
    unit.ap = 2
    apply_action(
        state,
        Random(1),
        ActionRequest(type=ActionType.ABILITY, unit_id="A1", target=Vec2(x=2, y=0)),
    )
    assert unit.ap == 1
    assert unit.ability_used
    assert not has_los(state.map, unit.pos, enemy.pos, state.smokes)
    _end_round_turn(state)
    assert state.smokes
    _end_round_turn(state)
    assert not state.smokes
    assert has_los(state.map, unit.pos, enemy.pos, state.smokes)


def test_ability_once_per_round() -> None:
    state = started_game()
    state.active_unit_id = "A1"
    state.unit("A1").ap = 2
    action = ActionRequest(type=ActionType.ABILITY, unit_id="A1", target=Vec2(x=2, y=0))
    apply_action(state, Random(1), action)
    with pytest.raises(ValueError, match=r"not that unit|already used"):
        apply_action(state, Random(1), action)


def test_flash_sets_flashed_and_applies_hit_penalty() -> None:
    state = started_game()
    flasher = state.unit("A2")
    target = state.unit("D1")
    flasher.pos = Vec2(x=1, y=1)
    target.pos = Vec2(x=2, y=1)
    state.active_unit_id = "A2"
    flasher.ap = 2
    apply_action(
        state,
        Random(1),
        ActionRequest(type=ActionType.ABILITY, unit_id="A2", target=Vec2(x=2, y=1)),
    )
    assert target.flashed
    target.weapon = "rifle"
    shooter_chance = calculate_hit_chance(state, target, flasher)
    target.flashed = False
    assert shooter_chance == pytest.approx(calculate_hit_chance(state, target, flasher) - 0.40)


def test_reveal_sets_revealed_and_expires_next_round_turn() -> None:
    state = started_game()
    recon = state.unit("A3")
    state.active_unit_id = "A3"
    recon.ap = 2
    apply_action(
        state,
        Random(1),
        ActionRequest(type=ActionType.ABILITY, unit_id="A3", target=recon.pos),
    )
    assert all(unit.revealed for unit in state.living_units(Team.DEFENDERS))
    _end_round_turn(state)
    assert not any(unit.revealed for unit in state.living_units(Team.DEFENDERS))

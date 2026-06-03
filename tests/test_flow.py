from random import Random

import pytest

from app.engine.game import (
    IllegalAction,
    _check_round_end,
    _end_round_turn,
    apply_action,
    new_game,
    start_round,
)
from app.engine.schema import ActionRequest, ActionType, GameConfig, Phase, Team, Vec2


def test_phase_transitions_and_match_end_at_match_to() -> None:
    state = new_game(GameConfig(seed=1, match_to=1))
    assert state.phase is Phase.BUY
    start_round(state)
    assert state.phase is Phase.ACTION
    for defender in state.living_units(Team.DEFENDERS):
        defender.alive = False
    _check_round_end(state)
    assert state.phase is Phase.MATCH_END
    assert state.winner is Team.ATTACKERS


def test_round_end_can_start_next_round_and_side_swaps_after_half() -> None:
    state = new_game(GameConfig(seed=1, match_to=3, swap_after=1))
    start_round(state)
    state.unit("D1").alive = False
    state.unit("D2").alive = False
    state.unit("D3").alive = False
    _check_round_end(state)
    assert state.phase is Phase.ROUND_END
    start_round(state)
    assert state.round_number == 2
    assert state.side_swapped
    assert state.unit("A1").pos == state.map.defender_spawns[0]


def test_all_defenders_eliminated_attackers_win_round() -> None:
    state = new_game(GameConfig(seed=1, match_to=2))
    start_round(state)
    for defender in state.living_units(Team.DEFENDERS):
        defender.alive = False
    _check_round_end(state)
    assert state.round_winner is Team.ATTACKERS


def test_all_attackers_eliminated_defenders_win_round() -> None:
    state = new_game(GameConfig(seed=1, match_to=2))
    start_round(state)
    for attacker in state.living_units(Team.ATTACKERS):
        attacker.alive = False
    _check_round_end(state)
    assert state.round_winner is Team.DEFENDERS


def test_spike_plant_detonate_and_defuse_conditions() -> None:
    detonate = new_game(GameConfig(seed=1, match_to=2, spike_timer=1))
    start_round(detonate)
    planter = detonate.unit("A1")
    planter.pos = detonate.map.site_a[0]
    planter.ap = 2
    detonate.active_unit_id = "A1"
    apply_action(detonate, Random(1), ActionRequest(type=ActionType.PLANT, unit_id="A1"))
    _end_round_turn(detonate)
    assert detonate.round_winner is Team.ATTACKERS

    defuse = new_game(GameConfig(seed=2, match_to=2))
    start_round(defuse)
    planter = defuse.unit("A1")
    planter.pos = defuse.map.site_a[0]
    planter.ap = 2
    defuse.active_unit_id = "A1"
    apply_action(defuse, Random(1), ActionRequest(type=ActionType.PLANT, unit_id="A1"))
    defender = defuse.unit("D1")
    defender.pos = Vec2(x=planter.pos.x + 1, y=planter.pos.y)
    defender.ap = 2
    defuse.active_unit_id = "D1"
    apply_action(defuse, Random(1), ActionRequest(type=ActionType.DEFUSE, unit_id="D1"))
    assert defuse.round_winner is Team.DEFENDERS


def test_round_turn_cap_defenders_win_if_unplanted() -> None:
    state = new_game(GameConfig(seed=1, match_to=2, round_turn_cap=1))
    start_round(state)
    _end_round_turn(state)
    assert state.round_winner is Team.DEFENDERS


def test_illegal_action_wrong_active_unit() -> None:
    state = new_game(GameConfig(seed=1))
    start_round(state)
    with pytest.raises(IllegalAction, match="not that unit"):
        apply_action(
            state,
            Random(1),
            ActionRequest(type=ActionType.END_ACTIVATION, unit_id="D1"),
        )

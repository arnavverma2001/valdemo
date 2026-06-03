from __future__ import annotations

from dataclasses import dataclass
from random import Random

from app.engine import content
from app.engine.abilities import AbilityError, use_ability
from app.engine.combat import calculate_hit_chance, shoot
from app.engine.economy import (
    EconomyError,
    award_kill,
    award_plant,
    bot_buy_requests,
    settle_round_economy,
)
from app.engine.economy import apply_buy as economy_apply_buy
from app.engine.grid import chebyshev_distance, in_bounds, is_site_tile, tile_at
from app.engine.movement import validate_move
from app.engine.schema import (
    ActionRequest,
    ActionType,
    BuyRequest,
    GameConfig,
    GameState,
    Phase,
    Team,
    Unit,
    Vec2,
)


class IllegalAction(ValueError):
    pass


@dataclass
class GameSession:
    state: GameState
    rng: Random


def new_session(config: GameConfig | None = None) -> GameSession:
    config = config or GameConfig()
    state = new_game(config)
    return GameSession(state=state, rng=Random(config.seed))


def new_game(config: GameConfig | None = None) -> GameState:
    config = config or GameConfig()
    game_map = content.default_map()
    units: list[Unit] = []
    agents = content.agent_names_for_team_size(config.team_size)
    for index, agent in enumerate(agents):
        units.append(
            Unit(
                id=f"A{index + 1}",
                team=Team.ATTACKERS,
                agent=agent,
                pos=game_map.attacker_spawns[index],
                has_spike=index == 0,
            )
        )
        units.append(
            Unit(
                id=f"D{index + 1}",
                team=Team.DEFENDERS,
                agent=agent,
                pos=game_map.defender_spawns[index],
            )
        )
    return GameState(
        game_id=f"game-{config.seed}",
        config=config,
        seed=config.seed,
        map=game_map,
        units=units,
        log=[f"Created game seed={config.seed}"],
    )


def apply_buy(state: GameState, request: BuyRequest) -> None:
    if state.phase is not Phase.BUY:
        raise IllegalAction("buys are only allowed during BUY phase")
    try:
        economy_apply_buy(state, request)
    except EconomyError as exc:
        raise IllegalAction(str(exc)) from exc


def auto_buy(state: GameState) -> None:
    if state.phase is not Phase.BUY:
        return
    for team in (Team.ATTACKERS, Team.DEFENDERS):
        for request in bot_buy_requests(state, team):
            apply_buy(state, request)


def _spawn_for_unit(state: GameState, unit: Unit, index: int) -> Vec2:
    attacker_spawns = state.map.defender_spawns if state.side_swapped else state.map.attacker_spawns
    defender_spawns = state.map.attacker_spawns if state.side_swapped else state.map.defender_spawns
    return (attacker_spawns if unit.team is Team.ATTACKERS else defender_spawns)[index]


def start_round(state: GameState) -> None:
    if state.phase is Phase.MATCH_END:
        raise IllegalAction("match already ended")
    if state.phase is Phase.ROUND_END:
        state.round_number += 1
        state.phase = Phase.BUY
    if state.phase is not Phase.BUY:
        raise IllegalAction("round can only start from BUY phase")
    state.side_swapped = state.round_number > state.config.swap_after
    state.smokes.clear()
    state.spike.planted = False
    state.spike.pos = None
    state.spike.turns_to_detonate = 0
    state.spike.defused = False
    state.acted_unit_ids.clear()
    state.round_winner = None
    state.round_turn = 0
    state.reveal_turns_left = 0
    by_team_index = {Team.ATTACKERS: 0, Team.DEFENDERS: 0}
    for unit in state.units:
        index = by_team_index[unit.team]
        by_team_index[unit.team] += 1
        unit.pos = _spawn_for_unit(state, unit, index)
        unit.hp = 100
        unit.alive = True
        unit.ap = 0
        unit.flashed = False
        unit.ability_used = False
        unit.revealed = False
        unit.has_spike = unit.team is Team.ATTACKERS and index == 0
    state.phase = Phase.ACTION
    _select_next_unit(state, preferred_team=Team.ATTACKERS)
    state.log.append(f"Round {state.round_number} started")


def _living_not_acted(state: GameState, team: Team | None = None) -> list[Unit]:
    acted = set(state.acted_unit_ids)
    return [u for u in state.living_units(team) if u.id not in acted]


def _select_next_unit(state: GameState, preferred_team: Team | None = None) -> None:
    if state.phase is not Phase.ACTION:
        state.active_unit_id = None
        return
    candidates: list[Unit] = []
    if preferred_team is not None:
        candidates = _living_not_acted(state, preferred_team)
    if not candidates:
        other = Team.DEFENDERS if preferred_team is Team.ATTACKERS else Team.ATTACKERS
        candidates = _living_not_acted(state, other)
    if not candidates:
        _end_round_turn(state)
        if state.phase is not Phase.ACTION:
            return
        candidates = _living_not_acted(state, Team.ATTACKERS) or _living_not_acted(
            state, Team.DEFENDERS
        )
    if not candidates:
        state.active_unit_id = None
        return
    unit = sorted(candidates, key=lambda u: u.id)[0]
    unit.ap = state.config.activation_ap
    state.active_unit_id = unit.id
    state.active_team = unit.team


def _end_round_turn(state: GameState) -> None:
    state.round_turn += 1
    state.acted_unit_ids.clear()
    for smoke in state.smokes:
        smoke.turns_left -= 1
    state.smokes = [smoke for smoke in state.smokes if smoke.turns_left > 0]
    if state.reveal_turns_left:
        state.reveal_turns_left -= 1
        if state.reveal_turns_left <= 0:
            for unit in state.units:
                unit.revealed = False
    if state.spike.planted and not state.spike.defused:
        state.spike.turns_to_detonate -= 1
        state.log.append(f"Spike timer: {state.spike.turns_to_detonate}")
    _check_round_end(state)


def _finish_activation(state: GameState) -> None:
    if state.active_unit_id is None:
        return
    unit = state.unit(state.active_unit_id)
    unit.ap = 0
    unit.flashed = False
    if unit.id not in state.acted_unit_ids:
        state.acted_unit_ids.append(unit.id)
    next_team = Team.DEFENDERS if unit.team is Team.ATTACKERS else Team.ATTACKERS
    _select_next_unit(state, preferred_team=next_team)


def _validate_active_unit(state: GameState, action: ActionRequest) -> Unit:
    if state.phase is not Phase.ACTION:
        raise IllegalAction("actions are only allowed during ACTION phase")
    if state.active_unit_id != action.unit_id:
        raise IllegalAction("it is not that unit's activation")
    unit = state.unit(action.unit_id)
    if not unit.alive:
        raise IllegalAction("unit is dead")
    if unit.ap < 1 and action.type is not ActionType.END_ACTIVATION:
        raise IllegalAction("not enough AP")
    return unit


def is_legal_action(state: GameState, action: ActionRequest) -> bool:
    clone = state.model_copy(deep=True)
    try:
        apply_action(clone, Random(0), action)
    except IllegalAction:
        return False
    return True


def apply_action(state: GameState, rng: Random, action: ActionRequest) -> None:
    unit = _validate_active_unit(state, action)
    if action.type is ActionType.MOVE:
        if action.target is None:
            raise IllegalAction("move target is required")
        try:
            path = validate_move(state, unit.id, action.target)
        except ValueError as exc:
            raise IllegalAction(str(exc)) from exc
        unit.pos = action.target
        unit.ap -= 1
        state.log.append(f"{unit.id} moved {len(path) - 1} tiles to ({unit.pos.x},{unit.pos.y})")
    elif action.type is ActionType.SHOOT:
        if action.target_unit_id is None:
            raise IllegalAction("target_unit_id is required")
        try:
            result = shoot(state, rng, unit.id, action.target_unit_id)
        except ValueError as exc:
            raise IllegalAction(str(exc)) from exc
        unit.ap -= 1
        target = state.unit(action.target_unit_id)
        if result.killed:
            unit.kills += 1
            award_kill(state, unit.team)
        state.log.append(
            f"{unit.id} shot {target.id}: {'hit' if result.hit else 'miss'} "
            f"({result.hit_chance:.2f})"
        )
    elif action.type is ActionType.ABILITY:
        try:
            line = use_ability(state, unit, action.target)
        except AbilityError as exc:
            raise IllegalAction(str(exc)) from exc
        state.log.append(line)
    elif action.type is ActionType.PLANT:
        _plant(state, unit)
    elif action.type is ActionType.DEFUSE:
        _defuse(state, unit)
    elif action.type is ActionType.END_ACTIVATION:
        state.log.append(f"{unit.id} ended activation")
    _check_round_end(state)
    if state.phase is Phase.ACTION and (unit.ap <= 0 or action.type is ActionType.END_ACTIVATION):
        _finish_activation(state)


def _plant(state: GameState, unit: Unit) -> None:
    if unit.team is not Team.ATTACKERS:
        raise IllegalAction("only attackers can plant")
    if not unit.has_spike:
        raise IllegalAction("unit does not carry the spike")
    if state.spike.planted:
        raise IllegalAction("spike is already planted")
    if not is_site_tile(tile_at(state.map, unit.pos)):
        raise IllegalAction("spike can only be planted on a site")
    state.spike.planted = True
    state.spike.pos = unit.pos
    state.spike.turns_to_detonate = state.config.spike_timer
    unit.has_spike = False
    unit.ap -= 1
    award_plant(state, unit.team)
    state.log.append(f"{unit.id} planted the spike")


def _defuse(state: GameState, unit: Unit) -> None:
    if unit.team is not Team.DEFENDERS:
        raise IllegalAction("only defenders can defuse")
    if not state.spike.planted or state.spike.defused or state.spike.pos is None:
        raise IllegalAction("no planted spike to defuse")
    if unit.ap < 2:
        raise IllegalAction("defuse requires 2 AP in one activation")
    if chebyshev_distance(unit.pos, state.spike.pos) > 1:
        raise IllegalAction("defuser must be adjacent to the spike")
    unit.ap -= 2
    state.spike.defused = True
    state.log.append(f"{unit.id} defused the spike")


def _check_round_end(state: GameState) -> None:
    if state.phase is not Phase.ACTION:
        return
    winner: Team | None = None
    if not state.living_units(Team.DEFENDERS):
        winner = Team.ATTACKERS
    elif not state.living_units(Team.ATTACKERS) or state.spike.defused:
        winner = Team.DEFENDERS
    elif state.spike.planted and state.spike.turns_to_detonate <= 0:
        winner = Team.ATTACKERS
    elif not state.spike.planted and state.round_turn >= state.config.round_turn_cap:
        winner = Team.DEFENDERS
    if winner is not None:
        _finish_round(state, winner)


def _finish_round(state: GameState, winner: Team) -> None:
    state.round_winner = winner
    state.scores.add(winner)
    settle_round_economy(state, winner)
    state.log.append(f"{winner.value} win round {state.round_number}")
    if state.scores.get(winner) >= state.config.match_to:
        state.phase = Phase.MATCH_END
        state.winner = winner
        state.active_unit_id = None
        state.log.append(f"WINNER: {winner.value}")
    else:
        state.phase = Phase.ROUND_END
        state.active_unit_id = None


def visible_enemies(state: GameState, unit: Unit) -> list[Unit]:
    enemies = Team.DEFENDERS if unit.team is Team.ATTACKERS else Team.ATTACKERS
    out: list[Unit] = []
    for target in state.living_units(enemies):
        try:
            calculate_hit_chance(state, unit, target)
        except ValueError:
            continue
        out.append(target)
    return sorted(out, key=lambda u: u.id)


def can_plant(state: GameState, unit: Unit) -> bool:
    return (
        unit.team is Team.ATTACKERS
        and unit.has_spike
        and not state.spike.planted
        and unit.ap >= 1
        and is_site_tile(tile_at(state.map, unit.pos))
    )


def can_defuse(state: GameState, unit: Unit) -> bool:
    return (
        unit.team is Team.DEFENDERS
        and state.spike.planted
        and not state.spike.defused
        and state.spike.pos is not None
        and unit.ap >= 2
        and chebyshev_distance(unit.pos, state.spike.pos) <= 1
    )


def nearest_site_tile(state: GameState, unit: Unit) -> Vec2:
    sites = state.map.site_a + state.map.site_b
    return min(sites, key=lambda p: (chebyshev_distance(unit.pos, p), p.y, p.x))


def assert_invariants(state: GameState) -> None:
    assert state.config.match_to >= state.scores.ATTACKERS
    assert state.config.match_to >= state.scores.DEFENDERS
    assert state.credits.ATTACKERS >= 0 and state.credits.DEFENDERS >= 0
    occupied: set[tuple[int, int]] = set()
    for unit in state.units:
        assert unit.hp >= 0
        assert 0 <= unit.ap <= state.config.activation_ap
        if unit.alive:
            assert in_bounds(state.map, unit.pos)
            assert tile_at(state.map, unit.pos).value != "WALL"
            assert unit.pos.as_tuple() not in occupied
            occupied.add(unit.pos.as_tuple())

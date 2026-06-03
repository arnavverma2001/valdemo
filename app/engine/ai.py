from __future__ import annotations

from random import Random

from app.engine import content
from app.engine.combat import calculate_hit_chance
from app.engine.game import (
    can_defuse,
    can_plant,
    is_legal_action,
    nearest_site_tile,
    visible_enemies,
)
from app.engine.grid import chebyshev_distance, has_los, target_has_cover
from app.engine.movement import reachable_tiles
from app.engine.schema import ActionRequest, ActionType, AIDifficulty, GameState, Team, Unit, Vec2


def enumerate_legal_actions(state: GameState, unit_id: str) -> list[ActionRequest]:
    actions: list[ActionRequest] = [ActionRequest(type=ActionType.END_ACTIVATION, unit_id=unit_id)]
    if state.active_unit_id != unit_id:
        return actions
    unit = state.unit(unit_id)
    if not unit.alive:
        return actions
    if unit.ap >= 1:
        for tile in sorted(reachable_tiles(state, unit_id), key=lambda p: (p.y, p.x)):
            if tile != unit.pos:
                actions.append(ActionRequest(type=ActionType.MOVE, unit_id=unit_id, target=tile))
        for enemy in visible_enemies(state, unit):
            actions.append(
                ActionRequest(type=ActionType.SHOOT, unit_id=unit_id, target_unit_id=enemy.id)
            )
        if not unit.ability_used:
            actions.extend(_ability_candidates(state, unit))
        if can_plant(state, unit):
            actions.append(ActionRequest(type=ActionType.PLANT, unit_id=unit_id))
    if can_defuse(state, unit):
        actions.append(ActionRequest(type=ActionType.DEFUSE, unit_id=unit_id))
    legal: list[ActionRequest] = []
    seen: set[str] = set()
    for action in actions:
        key = action.model_dump_json()
        if key not in seen and is_legal_action(state, action):
            seen.add(key)
            legal.append(action)
    return sorted(legal, key=lambda a: a.model_dump_json())


def _ability_candidates(state: GameState, unit: Unit) -> list[ActionRequest]:
    ability = content.AGENTS[unit.agent].ability
    targets: list[Vec2] = []
    if ability == "reveal":
        targets = [unit.pos]
    elif ability == "flash":
        enemies = Team.DEFENDERS if unit.team is Team.ATTACKERS else Team.ATTACKERS
        targets = [enemy.pos for enemy in state.living_units(enemies)]
    elif ability == "smoke":
        enemies = Team.DEFENDERS if unit.team is Team.ATTACKERS else Team.ATTACKERS
        for enemy in state.living_units(enemies):
            if has_los(state.map, unit.pos, enemy.pos, state.smokes):
                midpoint = Vec2(
                    x=(unit.pos.x + enemy.pos.x) // 2, y=(unit.pos.y + enemy.pos.y) // 2
                )
                targets.append(midpoint)
        targets.append(nearest_site_tile(state, unit))
    return [
        ActionRequest(type=ActionType.ABILITY, unit_id=unit.id, target=target)
        for target in sorted(set(targets), key=lambda p: (p.y, p.x))
    ]


def score_action(state: GameState, action: ActionRequest) -> float:
    unit = state.unit(action.unit_id)
    score = 0.0
    if action.type is ActionType.SHOOT and action.target_unit_id is not None:
        target = state.unit(action.target_unit_id)
        chance = calculate_hit_chance(state, unit, target)
        score += chance * content.WEAPONS[unit.weapon].damage
        if target.hp + target.armor <= content.WEAPONS[unit.weapon].damage:
            score += 35.0
    elif action.type is ActionType.PLANT:
        score += 120.0
    elif action.type is ActionType.DEFUSE:
        score += 140.0
    elif action.type is ActionType.ABILITY:
        score += _score_ability(state, unit, action)
    elif action.type is ActionType.MOVE and action.target is not None:
        score += _score_move(state, unit, action.target)
    elif action.type is ActionType.END_ACTIVATION:
        score -= 5.0 if unit.ap > 0 else 0.0
    return score


def _score_ability(state: GameState, unit: Unit, action: ActionRequest) -> float:
    ability = content.AGENTS[unit.agent].ability
    if ability == "reveal":
        return 22.0
    if ability == "flash" and action.target is not None:
        enemies = Team.DEFENDERS if unit.team is Team.ATTACKERS else Team.ATTACKERS
        affected = sum(
            1
            for enemy in state.living_units(enemies)
            if chebyshev_distance(enemy.pos, action.target) <= 2
        )
        return 18.0 * affected
    if ability == "smoke":
        return 16.0
    return 0.0


def _score_move(state: GameState, unit: Unit, target: Vec2) -> float:
    score = 0.0
    if unit.team is Team.ATTACKERS and not state.spike.planted:
        score -= chebyshev_distance(target, nearest_site_tile(state, unit)) * 2.5
        if unit.has_spike:
            score += 10.0
    elif state.spike.planted and state.spike.pos is not None:
        score -= chebyshev_distance(target, state.spike.pos) * (
            3.0 if unit.team is Team.DEFENDERS else 1.0
        )
    else:
        enemies = Team.DEFENDERS if unit.team is Team.ATTACKERS else Team.ATTACKERS
        living = state.living_units(enemies)
        if living:
            score -= min(chebyshev_distance(target, enemy.pos) for enemy in living)
    if target_has_cover(state.map, _nearest_enemy_pos(state, unit), target):
        score += 6.0
    risk = 0
    for enemy in state.living_units(
        Team.DEFENDERS if unit.team is Team.ATTACKERS else Team.ATTACKERS
    ):
        if has_los(state.map, enemy.pos, target, state.smokes):
            risk += 1
    score -= risk * 4.0
    return score


def _nearest_enemy_pos(state: GameState, unit: Unit) -> Vec2:
    enemies = state.living_units(Team.DEFENDERS if unit.team is Team.ATTACKERS else Team.ATTACKERS)
    if not enemies:
        return unit.pos
    return min(enemies, key=lambda e: (chebyshev_distance(unit.pos, e.pos), e.id)).pos


def choose_action(
    state: GameState, rng: Random, difficulty: AIDifficulty | None = None
) -> ActionRequest:
    difficulty = difficulty or state.config.difficulty
    unit_id = state.active_unit_id
    if unit_id is None:
        return ActionRequest(type=ActionType.END_ACTIVATION, unit_id="")
    try:
        actions = enumerate_legal_actions(state, unit_id)
        if difficulty is AIDifficulty.EASY:
            actions = [a for a in actions if a.type is not ActionType.ABILITY] or actions
        if not actions:
            return ActionRequest(type=ActionType.END_ACTIVATION, unit_id=unit_id)
        scored: list[tuple[float, str, ActionRequest]] = []
        for action in actions:
            score = score_action(state, action)
            if difficulty is AIDifficulty.EASY:
                score += rng.uniform(-10.0, 10.0)
            scored.append((score, action.model_dump_json(), action))
        best_score = max(score for score, _, _ in scored)
        best = [item for item in scored if item[0] == best_score]
        best.sort(key=lambda item: item[1])
        return rng.choice([item[2] for item in best])
    except Exception as exc:
        state.log.append(f"AI fallback for {unit_id}: {type(exc).__name__}: {exc}")
        return ActionRequest(type=ActionType.END_ACTIVATION, unit_id=unit_id)

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from app.engine import content
from app.engine.grid import chebyshev_distance, has_los, target_has_cover
from app.engine.schema import GameState, Unit


@dataclass(frozen=True)
class ShotResult:
    hit_chance: float
    hit: bool
    damage: int
    killed: bool


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def calculate_hit_chance(state: GameState, shooter: Unit, target: Unit) -> float:
    if not shooter.alive or not target.alive:
        raise ValueError("shooter and target must be alive")
    if shooter.team is target.team:
        raise ValueError("cannot shoot a teammate")
    if not has_los(state.map, shooter.pos, target.pos, state.smokes):
        raise ValueError("line of sight is blocked")
    weapon = content.WEAPONS[shooter.weapon]
    distance = chebyshev_distance(shooter.pos, target.pos)
    falloff = weapon.falloff_per_tile * max(0, distance - weapon.optimal_range)
    cover_penalty = 0.25 if target_has_cover(state.map, shooter.pos, target.pos) else 0.0
    flash_penalty = 0.40 if shooter.flashed else 0.0
    return clamp(weapon.base_accuracy - falloff - cover_penalty - flash_penalty, 0.05, 0.95)


def apply_damage(target: Unit, damage: int) -> int:
    remaining = damage
    if target.armor:
        absorbed = min(target.armor, remaining)
        target.armor -= absorbed
        remaining -= absorbed
    if remaining:
        target.hp = max(0, target.hp - remaining)
    if target.hp <= 0:
        target.alive = False
        target.ap = 0
    return remaining


def shoot(state: GameState, rng: Random, shooter_id: str, target_id: str) -> ShotResult:
    shooter = state.unit(shooter_id)
    target = state.unit(target_id)
    chance = calculate_hit_chance(state, shooter, target)
    hit = rng.random() < chance
    damage = content.WEAPONS[shooter.weapon].damage if hit else 0
    killed_before = target.alive
    if hit:
        apply_damage(target, damage)
    killed = killed_before and not target.alive
    return ShotResult(hit_chance=chance, hit=hit, damage=damage, killed=killed)

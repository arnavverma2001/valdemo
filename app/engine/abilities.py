from __future__ import annotations

from app.engine import content
from app.engine.grid import chebyshev_distance, has_los, in_bounds, tile_at
from app.engine.schema import GameState, SmokeZone, Team, TileType, Unit, Vec2


class AbilityError(ValueError):
    pass


def radius_tiles(state: GameState, center: Vec2, radius: int) -> list[Vec2]:
    tiles: list[Vec2] = []
    for y in range(center.y - radius, center.y + radius + 1):
        for x in range(center.x - radius, center.x + radius + 1):
            pos = Vec2(x=x, y=y)
            if in_bounds(state.map, pos) and chebyshev_distance(center, pos) <= radius:
                if tile_at(state.map, pos) is not TileType.WALL:
                    tiles.append(pos)
    return sorted(tiles)


def validate_ability_common(state: GameState, unit: Unit, ability_name: str, target: Vec2 | None) -> None:
    if target is None:
        raise AbilityError("ability target is required")
    if unit.ability_used:
        raise AbilityError("ability already used this round")
    if unit.ap < 1:
        raise AbilityError("not enough AP")
    if ability_name not in content.ABILITIES:
        raise AbilityError(f"unknown ability {ability_name}")
    if chebyshev_distance(unit.pos, target) > content.ABILITIES[ability_name].range:
        raise AbilityError("ability target is out of range")
    if not in_bounds(state.map, target):
        raise AbilityError("ability target is out of bounds")


def use_ability(state: GameState, unit: Unit, target: Vec2 | None) -> str:
    ability_name = content.AGENTS[unit.agent].ability
    validate_ability_common(state, unit, ability_name, target)
    assert target is not None
    if ability_name == "smoke":
        return use_smoke(state, unit, target)
    if ability_name == "flash":
        return use_flash(state, unit, target)
    if ability_name == "reveal":
        return use_reveal(state, unit, target)
    raise AbilityError(f"unhandled ability {ability_name}")


def use_smoke(state: GameState, unit: Unit, target: Vec2) -> str:
    data = content.ABILITIES["smoke"]
    state.smokes.append(SmokeZone(tiles=radius_tiles(state, target, data.radius), turns_left=data.duration))
    unit.ap -= 1
    unit.ability_used = True
    return f"{unit.id} smoked ({target.x},{target.y})"


def use_flash(state: GameState, unit: Unit, target: Vec2) -> str:
    data = content.ABILITIES["flash"]
    flashed: list[str] = []
    for other in state.living_units():
        if chebyshev_distance(other.pos, target) <= data.radius and has_los(
            state.map, other.pos, target, state.smokes
        ):
            other.flashed = True
            flashed.append(other.id)
    unit.ap -= 1
    unit.ability_used = True
    return f"{unit.id} flashed {', '.join(sorted(flashed)) or 'nobody'}"


def use_reveal(state: GameState, unit: Unit, target: Vec2) -> str:
    del target
    enemy = Team.DEFENDERS if unit.team is Team.ATTACKERS else Team.ATTACKERS
    for other in state.living_units(enemy):
        other.revealed = True
    state.reveal_turns_left = content.ABILITIES["reveal"].duration
    unit.ap -= 1
    unit.ability_used = True
    return f"{unit.id} revealed enemies"

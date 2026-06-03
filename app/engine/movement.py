from __future__ import annotations

from collections import deque

from app.engine.grid import in_bounds, is_walkable_tile, neighbors4, tile_at
from app.engine.schema import GameState, Vec2


def occupied_positions(state: GameState, excluding_unit_id: str | None = None) -> set[tuple[int, int]]:
    return {
        unit.pos.as_tuple()
        for unit in state.units
        if unit.alive and unit.id != excluding_unit_id
    }


def reachable_tiles(state: GameState, unit_id: str, max_range: int | None = None) -> set[Vec2]:
    unit = state.unit(unit_id)
    max_steps = state.config.move_range if max_range is None else max_range
    occupied = occupied_positions(state, excluding_unit_id=unit_id)
    seen: set[tuple[int, int]] = {unit.pos.as_tuple()}
    reached: set[Vec2] = {unit.pos}
    queue: deque[tuple[Vec2, int]] = deque([(unit.pos, 0)])
    while queue:
        pos, distance = queue.popleft()
        if distance >= max_steps:
            continue
        for nxt in sorted(neighbors4(state.map, pos)):
            if nxt.as_tuple() in seen or nxt.as_tuple() in occupied:
                continue
            if not is_walkable_tile(tile_at(state.map, nxt)):
                continue
            seen.add(nxt.as_tuple())
            reached.add(nxt)
            queue.append((nxt, distance + 1))
    return reached


def shortest_path(state: GameState, unit_id: str, target: Vec2) -> list[Vec2] | None:
    unit = state.unit(unit_id)
    if not in_bounds(state.map, target) or not is_walkable_tile(tile_at(state.map, target)):
        return None
    occupied = occupied_positions(state, excluding_unit_id=unit_id)
    if target.as_tuple() in occupied:
        return None
    queue: deque[Vec2] = deque([unit.pos])
    parent: dict[tuple[int, int], tuple[int, int] | None] = {unit.pos.as_tuple(): None}
    while queue:
        pos = queue.popleft()
        if pos == target:
            break
        for nxt in sorted(neighbors4(state.map, pos)):
            key = nxt.as_tuple()
            if key in parent or key in occupied:
                continue
            if not is_walkable_tile(tile_at(state.map, nxt)):
                continue
            parent[key] = pos.as_tuple()
            queue.append(nxt)
    if target.as_tuple() not in parent:
        return None
    path_rev = [target]
    current = parent[target.as_tuple()]
    while current is not None:
        pos = Vec2(x=current[0], y=current[1])
        path_rev.append(pos)
        current = parent[current]
    return list(reversed(path_rev))


def validate_move(state: GameState, unit_id: str, target: Vec2) -> list[Vec2]:
    path = shortest_path(state, unit_id, target)
    if path is None:
        raise ValueError("target is unreachable")
    if len(path) - 1 > state.config.move_range:
        raise ValueError("target is beyond move range")
    return path

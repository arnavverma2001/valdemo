from __future__ import annotations

from math import ceil

from app.engine.schema import MapData, SmokeZone, TileType, Vec2


def in_bounds(map_data: MapData, pos: Vec2) -> bool:
    return 0 <= pos.x < map_data.width and 0 <= pos.y < map_data.height


def tile_at(map_data: MapData, pos: Vec2) -> TileType:
    if not in_bounds(map_data, pos):
        raise ValueError(f"position out of bounds: {pos}")
    return map_data.tiles[pos.y][pos.x]


def is_walkable_tile(tile_type: TileType) -> bool:
    return tile_type is not TileType.WALL


def is_site_tile(tile_type: TileType) -> bool:
    return tile_type in (TileType.SITE_A, TileType.SITE_B)


def neighbors4(map_data: MapData, pos: Vec2) -> list[Vec2]:
    candidates = [
        Vec2(x=pos.x + 1, y=pos.y),
        Vec2(x=pos.x - 1, y=pos.y),
        Vec2(x=pos.x, y=pos.y + 1),
        Vec2(x=pos.x, y=pos.y - 1),
    ]
    return [p for p in candidates if in_bounds(map_data, p)]


def chebyshev_distance(a: Vec2, b: Vec2) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


def manhattan_distance(a: Vec2, b: Vec2) -> int:
    return abs(a.x - b.x) + abs(a.y - b.y)


def line_tiles(a: Vec2, b: Vec2) -> list[Vec2]:
    """Return all tiles crossed by the segment from cell center to cell center.

    The implementation samples enough points along the line to behave like a conservative
    supercover check for this small grid. It is deterministic and includes endpoints.
    """

    dx = b.x - a.x
    dy = b.y - a.y
    steps = max(abs(dx), abs(dy)) * 4
    if steps == 0:
        return [a]
    seen: set[tuple[int, int]] = set()
    out: list[Vec2] = []
    for i in range(steps + 1):
        t = i / steps
        x = int(ceil(a.x + dx * t - 0.5))
        y = int(ceil(a.y + dy * t - 0.5))
        pos = Vec2(x=x, y=y)
        if pos.as_tuple() not in seen:
            seen.add(pos.as_tuple())
            out.append(pos)
    if out[-1] != b:
        out.append(b)
    return out


def smoke_tiles(smokes: list[SmokeZone] | tuple[SmokeZone, ...]) -> set[tuple[int, int]]:
    active: set[tuple[int, int]] = set()
    for smoke in smokes:
        if smoke.turns_left > 0:
            active.update(tile.as_tuple() for tile in smoke.tiles)
    return active


def has_los(
    map_data: MapData,
    a: Vec2,
    b: Vec2,
    smokes: list[SmokeZone] | tuple[SmokeZone, ...] = (),
) -> bool:
    if not in_bounds(map_data, a) or not in_bounds(map_data, b):
        return False
    smoked = smoke_tiles(smokes)
    for pos in line_tiles(a, b)[1:-1]:
        if tile_at(map_data, pos) is TileType.WALL:
            return False
        if pos.as_tuple() in smoked:
            return False
    return True


def target_has_cover(map_data: MapData, shooter: Vec2, target: Vec2) -> bool:
    """Half-cover counts if adjacent to target on the shooter's side of the target."""

    dx = 0 if shooter.x == target.x else (1 if shooter.x > target.x else -1)
    dy = 0 if shooter.y == target.y else (1 if shooter.y > target.y else -1)
    candidates = {Vec2(x=target.x + dx, y=target.y), Vec2(x=target.x, y=target.y + dy)}
    if dx and dy:
        candidates.add(Vec2(x=target.x + dx, y=target.y + dy))
    for pos in candidates:
        if in_bounds(map_data, pos) and tile_at(map_data, pos) is TileType.HALF_COVER:
            return True
    return False

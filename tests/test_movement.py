import pytest

from app.engine.movement import reachable_tiles, shortest_path, validate_move
from app.engine.schema import GameConfig, GameState, MapData, Team, TileType, Unit, Vec2


def map_from_rows(rows: list[str]) -> MapData:
    lookup = {".": TileType.FLOOR, "#": TileType.WALL}
    return MapData(
        width=len(rows[0]),
        height=len(rows),
        tiles=[[lookup[ch] for ch in row] for row in rows],
        site_a=[],
        site_b=[],
        attacker_spawns=[Vec2(x=0, y=0)],
        defender_spawns=[Vec2(x=len(rows[0]) - 1, y=len(rows) - 1)],
    )


def state_for(rows: list[str], move_range: int = 4) -> GameState:
    return GameState(
        game_id="g",
        config=GameConfig(move_range=move_range),
        seed=1,
        map=map_from_rows(rows),
        units=[
            Unit(id="a", team=Team.ATTACKERS, agent="Smoker", pos=Vec2(x=0, y=0)),
            Unit(id="block", team=Team.DEFENDERS, agent="Recon", pos=Vec2(x=1, y=0)),
        ],
    )


def test_reachable_tiles_respects_range_walls_and_occupancy() -> None:
    state = state_for(["...", ".#.", "..."], move_range=2)
    reached = {p.as_tuple() for p in reachable_tiles(state, "a")}
    assert (0, 0) in reached
    assert (1, 0) not in reached
    assert (1, 1) not in reached
    assert (2, 2) not in reached
    assert (0, 2) in reached


def test_shortest_path_returns_shortest_route_around_wall() -> None:
    state = state_for(["....", ".##.", "...."], move_range=10)
    state.unit("block").alive = False
    path = shortest_path(state, "a", Vec2(x=3, y=0))
    assert path is not None
    assert [p.as_tuple() for p in path] == [(0, 0), (1, 0), (2, 0), (3, 0)]


def test_validate_move_rejects_unreachable_and_over_range() -> None:
    state = state_for([".#.", ".#.", "..."], move_range=2)
    with pytest.raises(ValueError, match="beyond move range"):
        validate_move(state, "a", Vec2(x=2, y=0))
    with pytest.raises(ValueError, match="unreachable"):
        validate_move(state, "a", Vec2(x=1, y=0))

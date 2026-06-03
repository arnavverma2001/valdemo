from app.engine.grid import has_los, line_tiles, target_has_cover
from app.engine.schema import GameConfig, GameState, MapData, SmokeZone, TileType, Unit, Vec2


def small_map(rows: list[str]) -> MapData:
    lookup = {".": TileType.FLOOR, "#": TileType.WALL, "c": TileType.HALF_COVER}
    return MapData(
        width=len(rows[0]),
        height=len(rows),
        tiles=[[lookup[ch] for ch in row] for row in rows],
        site_a=[],
        site_b=[],
        attacker_spawns=[Vec2(x=0, y=0)],
        defender_spawns=[Vec2(x=len(rows[0]) - 1, y=len(rows) - 1)],
    )


def test_los_clear_and_blocked_by_wall() -> None:
    map_data = small_map([".....", "..#..", "....."])
    assert has_los(map_data, Vec2(x=0, y=0), Vec2(x=4, y=0))
    assert not has_los(map_data, Vec2(x=0, y=1), Vec2(x=4, y=1))


def test_los_blocked_by_smoke() -> None:
    map_data = small_map(["....."])
    smoke = SmokeZone(tiles=[Vec2(x=2, y=0)], turns_left=2)
    assert not has_los(map_data, Vec2(x=0, y=0), Vec2(x=4, y=0), [smoke])
    smoke.turns_left = 0
    assert has_los(map_data, Vec2(x=0, y=0), Vec2(x=4, y=0), [smoke])


def test_line_tiles_includes_endpoints_and_middle() -> None:
    tiles = line_tiles(Vec2(x=0, y=0), Vec2(x=3, y=3))
    assert tiles[0] == Vec2(x=0, y=0)
    assert tiles[-1] == Vec2(x=3, y=3)
    assert Vec2(x=1, y=1) in tiles


def test_directional_half_cover_detection() -> None:
    map_data = small_map([".....", ".c...", "....."])
    assert target_has_cover(map_data, Vec2(x=0, y=1), Vec2(x=2, y=1))
    assert not target_has_cover(map_data, Vec2(x=4, y=1), Vec2(x=2, y=1))


def test_schema_fixture_constructs() -> None:
    map_data = small_map([".."])
    state = GameState(
        game_id="g",
        config=GameConfig(),
        seed=1,
        map=map_data,
        units=[
            Unit(id="a", team="ATTACKERS", agent="Smoker", pos=Vec2(x=0, y=0)),
            Unit(id="d", team="DEFENDERS", agent="Recon", pos=Vec2(x=1, y=0)),
        ],
    )
    assert state.unit("a").agent == "Smoker"

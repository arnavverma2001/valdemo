from random import Random

import pytest

from app.engine.combat import apply_damage, calculate_hit_chance, shoot
from app.engine.schema import GameConfig, GameState, MapData, Team, TileType, Unit, Vec2


def map_from_rows(rows: list[str]) -> MapData:
    lookup = {".": TileType.FLOOR, "c": TileType.HALF_COVER}
    return MapData(
        width=len(rows[0]),
        height=len(rows),
        tiles=[[lookup[ch] for ch in row] for row in rows],
        site_a=[],
        site_b=[],
        attacker_spawns=[Vec2(x=0, y=0)],
        defender_spawns=[Vec2(x=len(rows[0]) - 1, y=0)],
    )


def state_with_positions(shooter: Vec2, target: Vec2, rows: list[str] | None = None) -> GameState:
    return GameState(
        game_id="g",
        config=GameConfig(),
        seed=1,
        map=map_from_rows(rows or ["............"]),
        units=[
            Unit(id="a", team=Team.ATTACKERS, agent="Smoker", pos=shooter, weapon="rifle"),
            Unit(id="d", team=Team.DEFENDERS, agent="Recon", pos=target, weapon="pistol"),
        ],
    )


def test_hit_chance_exact_formula_distance_cover_and_flash() -> None:
    state = state_with_positions(Vec2(x=0, y=0), Vec2(x=8, y=0))
    assert calculate_hit_chance(state, state.unit("a"), state.unit("d")) == pytest.approx(0.72)

    covered = state_with_positions(Vec2(x=0, y=0), Vec2(x=3, y=0), ["..c...."])
    assert calculate_hit_chance(covered, covered.unit("a"), covered.unit("d")) == pytest.approx(
        0.55
    )

    covered.unit("a").flashed = True
    assert calculate_hit_chance(covered, covered.unit("a"), covered.unit("d")) == pytest.approx(
        0.15
    )


def test_hit_chance_clamps_min_and_max() -> None:
    far = state_with_positions(Vec2(x=0, y=0), Vec2(x=20, y=0), ["." * 21])
    far.unit("a").weapon = "shotgun"
    far.unit("a").flashed = True
    assert calculate_hit_chance(far, far.unit("a"), far.unit("d")) == pytest.approx(0.05)

    close = state_with_positions(Vec2(x=0, y=0), Vec2(x=1, y=0), [".."])
    close.unit("a").weapon = "shotgun"
    assert calculate_hit_chance(close, close.unit("a"), close.unit("d")) == pytest.approx(0.85)


def test_seeded_shots_are_deterministic() -> None:
    state1 = state_with_positions(Vec2(x=0, y=0), Vec2(x=1, y=0), [".."])
    state2 = state_with_positions(Vec2(x=0, y=0), Vec2(x=1, y=0), [".."])
    rng1 = Random(3)
    rng2 = Random(3)
    assert [shoot(state1, rng1, "a", "d").hit for _ in range(2)] == [
        shoot(state2, rng2, "a", "d").hit for _ in range(2)
    ]


def test_damage_applies_to_armor_then_hp_and_kills() -> None:
    target = Unit(id="d", team=Team.DEFENDERS, agent="Recon", pos=Vec2(x=0, y=0), armor=25)
    apply_damage(target, 39)
    assert target.armor == 0
    assert target.hp == 86
    assert target.alive
    apply_damage(target, 100)
    assert target.hp == 0
    assert not target.alive

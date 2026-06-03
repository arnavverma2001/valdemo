from __future__ import annotations

from app.engine.schema import AbilityData, AgentData, MapData, TileType, Vec2, WeaponData

LIGHT_ARMOR_COST = 1000
LIGHT_ARMOR_VALUE = 25
STARTING_CREDITS = 800
WIN_BONUS = 3000
LOSS_BONUS_BASE = 1900
LOSS_BONUS_STEP = 500
LOSS_BONUS_CAP = 2900
KILL_REWARD = 200
PLANT_REWARD = 300


WEAPONS: dict[str, WeaponData] = {
    "pistol": WeaponData(
        name="pistol", cost=0, base_accuracy=0.75, optimal_range=3, falloff_per_tile=0.06, damage=26
    ),
    "rifle": WeaponData(
        name="rifle", cost=2900, base_accuracy=0.80, optimal_range=6, falloff_per_tile=0.04, damage=39
    ),
    "sniper": WeaponData(
        name="sniper", cost=4700, base_accuracy=0.70, optimal_range=10, falloff_per_tile=0.02, damage=90
    ),
    "shotgun": WeaponData(
        name="shotgun",
        cost=1500,
        base_accuracy=0.85,
        optimal_range=2,
        falloff_per_tile=0.18,
        damage=60,
    ),
}

ABILITIES: dict[str, AbilityData] = {
    "smoke": AbilityData(name="smoke", range=6, radius=1, duration=2),
    "flash": AbilityData(name="flash", range=6, radius=2, duration=1),
    "reveal": AbilityData(name="reveal", range=99, radius=0, duration=1),
}

AGENTS: dict[str, AgentData] = {
    "Smoker": AgentData(name="Smoker", ability="smoke"),
    "Flasher": AgentData(name="Flasher", ability="flash"),
    "Recon": AgentData(name="Recon", ability="reveal"),
}


def _tile(ch: str) -> TileType:
    return {
        ".": TileType.FLOOR,
        "#": TileType.WALL,
        "c": TileType.HALF_COVER,
        "A": TileType.SITE_A,
        "B": TileType.SITE_B,
    }[ch]


# A compact two-site 14x14 map. Attackers spawn on the west edge; defenders on the east.
# Chokes through the middle wall create two lanes, with half-cover around sites and mid.
_MAP_ROWS = [
    "..............",
    "..c..##..c.BB.",
    "...A.##....BB.",
    "..AA....#..c..",
    "..c..##.#.....",
    ".....##....c..",
    "...c....##....",
    "....##....c...",
    "..c....##.....",
    ".....#.##..c..",
    "..c..#....AA..",
    ".BB....##.A...",
    ".BB.c..##..c..",
    "..............",
]


def default_map() -> MapData:
    tiles = [[_tile(ch) for ch in row] for row in _MAP_ROWS]
    site_a: list[Vec2] = []
    site_b: list[Vec2] = []
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if tile is TileType.SITE_A:
                site_a.append(Vec2(x=x, y=y))
            elif tile is TileType.SITE_B:
                site_b.append(Vec2(x=x, y=y))
    return MapData(
        width=14,
        height=14,
        tiles=tiles,
        site_a=site_a,
        site_b=site_b,
        attacker_spawns=[
            Vec2(x=0, y=5),
            Vec2(x=0, y=6),
            Vec2(x=0, y=7),
            Vec2(x=1, y=5),
            Vec2(x=1, y=7),
        ],
        defender_spawns=[
            Vec2(x=13, y=5),
            Vec2(x=13, y=6),
            Vec2(x=13, y=7),
            Vec2(x=12, y=5),
            Vec2(x=12, y=7),
        ],
    )


def agent_names_for_team_size(team_size: int) -> list[str]:
    base = ["Smoker", "Flasher", "Recon", "Smoker", "Flasher"]
    return base[:team_size]

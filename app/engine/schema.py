from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Team(str, Enum):
    ATTACKERS = "ATTACKERS"
    DEFENDERS = "DEFENDERS"


class TileType(str, Enum):
    FLOOR = "FLOOR"
    WALL = "WALL"
    HALF_COVER = "HALF_COVER"
    SITE_A = "SITE_A"
    SITE_B = "SITE_B"


class Phase(str, Enum):
    BUY = "BUY"
    ACTION = "ACTION"
    ROUND_END = "ROUND_END"
    MATCH_END = "MATCH_END"


class ActionType(str, Enum):
    MOVE = "move"
    SHOOT = "shoot"
    ABILITY = "ability"
    PLANT = "plant"
    DEFUSE = "defuse"
    END_ACTIVATION = "end_activation"


class AIDifficulty(str, Enum):
    EASY = "easy"
    NORMAL = "normal"


class Vec2(BaseModel):
    model_config = ConfigDict(frozen=True)

    x: int
    y: int

    def as_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)

    def __lt__(self, other: "Vec2") -> bool:
        return self.as_tuple() < other.as_tuple()


class MapData(BaseModel):
    width: int
    height: int
    tiles: list[list[TileType]]
    site_a: list[Vec2]
    site_b: list[Vec2]
    attacker_spawns: list[Vec2]
    defender_spawns: list[Vec2]

    @field_validator("tiles")
    @classmethod
    def validate_tiles(cls, tiles: list[list[TileType]]) -> list[list[TileType]]:
        if not tiles or not tiles[0]:
            raise ValueError("map tiles cannot be empty")
        width = len(tiles[0])
        if any(len(row) != width for row in tiles):
            raise ValueError("map rows must all have the same width")
        return tiles

    @model_validator(mode="after")
    def validate_dimensions(self) -> "MapData":
        if len(self.tiles) != self.height or len(self.tiles[0]) != self.width:
            raise ValueError("map dimensions must match tile matrix")
        return self


class WeaponData(BaseModel):
    name: str
    cost: int
    base_accuracy: float
    optimal_range: int
    falloff_per_tile: float
    damage: int


class AbilityData(BaseModel):
    name: str
    range: int
    radius: int = 0
    duration: int = 0


class AgentData(BaseModel):
    name: str
    ability: str


class GameConfig(BaseModel):
    team_size: int = 3
    match_to: int = 7
    seed: int = 42
    quick: bool = False
    swap_after: int = 6
    round_turn_cap: int = 12
    spike_timer: int = 4
    move_range: int = 4
    activation_ap: int = 2
    difficulty: AIDifficulty = AIDifficulty.NORMAL

    @model_validator(mode="after")
    def apply_quick_defaults(self) -> "GameConfig":
        if self.quick:
            self.match_to = min(self.match_to, 2)
            self.swap_after = min(self.swap_after, 2)
            self.round_turn_cap = min(self.round_turn_cap, 8)
        if self.team_size not in (3, 5):
            raise ValueError("team_size must be 3 or 5")
        if self.match_to < 1:
            raise ValueError("match_to must be positive")
        return self


class Unit(BaseModel):
    id: str
    team: Team
    agent: str
    pos: Vec2
    hp: int = 100
    armor: int = 0
    weapon: str = "pistol"
    ap: int = 0
    alive: bool = True
    flashed: bool = False
    ability_used: bool = False
    revealed: bool = False
    has_spike: bool = False
    kills: int = 0


class SmokeZone(BaseModel):
    tiles: list[Vec2]
    turns_left: int


class SpikeState(BaseModel):
    planted: bool = False
    pos: Vec2 | None = None
    turns_to_detonate: int = 0
    defused: bool = False


class Scores(BaseModel):
    ATTACKERS: int = 0
    DEFENDERS: int = 0

    def get(self, team: Team) -> int:
        return self.ATTACKERS if team is Team.ATTACKERS else self.DEFENDERS

    def add(self, team: Team, amount: int = 1) -> None:
        if team is Team.ATTACKERS:
            self.ATTACKERS += amount
        else:
            self.DEFENDERS += amount


class TeamCredits(BaseModel):
    ATTACKERS: int = 800
    DEFENDERS: int = 800

    def get(self, team: Team) -> int:
        return self.ATTACKERS if team is Team.ATTACKERS else self.DEFENDERS

    def set(self, team: Team, amount: int) -> None:
        if amount < 0:
            raise ValueError("credits cannot be negative")
        if team is Team.ATTACKERS:
            self.ATTACKERS = amount
        else:
            self.DEFENDERS = amount

    def add(self, team: Team, amount: int) -> None:
        self.set(team, self.get(team) + amount)


class LossStreaks(BaseModel):
    ATTACKERS: int = 0
    DEFENDERS: int = 0

    def get(self, team: Team) -> int:
        return self.ATTACKERS if team is Team.ATTACKERS else self.DEFENDERS

    def set(self, team: Team, value: int) -> None:
        if team is Team.ATTACKERS:
            self.ATTACKERS = value
        else:
            self.DEFENDERS = value


class GameState(BaseModel):
    game_id: str
    config: GameConfig
    seed: int
    map: MapData
    units: list[Unit]
    smokes: list[SmokeZone] = Field(default_factory=list)
    phase: Phase = Phase.BUY
    active_team: Team = Team.ATTACKERS
    active_unit_id: str | None = None
    spike: SpikeState = Field(default_factory=SpikeState)
    round_number: int = 1
    scores: Scores = Field(default_factory=Scores)
    round_turn: int = 0
    log: list[str] = Field(default_factory=list)
    winner: Team | None = None
    credits: TeamCredits = Field(default_factory=TeamCredits)
    loss_streaks: LossStreaks = Field(default_factory=LossStreaks)
    acted_unit_ids: list[str] = Field(default_factory=list)
    reveal_turns_left: int = 0
    side_swapped: bool = False
    round_winner: Team | None = None

    def unit(self, unit_id: str) -> Unit:
        for unit in self.units:
            if unit.id == unit_id:
                return unit
        raise ValueError(f"unknown unit {unit_id}")

    def living_units(self, team: Team | None = None) -> list[Unit]:
        return [u for u in self.units if u.alive and (team is None or u.team is team)]


class BuyRequest(BaseModel):
    unit_id: str
    weapon: str | None = None
    armor: bool = False


class ActionRequest(BaseModel):
    type: ActionType
    unit_id: str
    target: Vec2 | None = None
    target_unit_id: str | None = None
    ability: str | None = None


class GameCreateRequest(BaseModel):
    team_size: int = 3
    match_to: int = 7
    seed: int = 42
    quick: bool = False
    difficulty: AIDifficulty = AIDifficulty.NORMAL


ActionLiteral = Literal["move", "shoot", "ability", "plant", "defuse", "end_activation"]

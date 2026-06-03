import pytest

from app.engine import content
from app.engine.economy import (
    EconomyError,
    apply_buy,
    award_kill,
    award_plant,
    loss_bonus_for_streak,
    settle_round_economy,
)
from app.engine.schema import BuyRequest, GameConfig, GameState, MapData, Team, TileType, Unit, Vec2


def economy_state() -> GameState:
    return GameState(
        game_id="g",
        config=GameConfig(),
        seed=1,
        map=MapData(
            width=2,
            height=1,
            tiles=[[TileType.FLOOR, TileType.FLOOR]],
            site_a=[],
            site_b=[],
            attacker_spawns=[Vec2(x=0, y=0)],
            defender_spawns=[Vec2(x=1, y=0)],
        ),
        units=[
            Unit(id="a", team=Team.ATTACKERS, agent="Smoker", pos=Vec2(x=0, y=0)),
            Unit(id="d", team=Team.DEFENDERS, agent="Recon", pos=Vec2(x=1, y=0)),
        ],
    )


def test_starting_credits_and_illegal_buy_rejected() -> None:
    state = economy_state()
    assert state.credits.ATTACKERS == content.STARTING_CREDITS
    before = state.model_dump_json()
    with pytest.raises(EconomyError, match="insufficient"):
        apply_buy(state, BuyRequest(unit_id="a", weapon="rifle", armor=True))
    assert state.model_dump_json() == before


def test_legal_buy_updates_weapon_armor_and_never_negative() -> None:
    state = economy_state()
    state.credits.ATTACKERS = 4000
    apply_buy(state, BuyRequest(unit_id="a", weapon="rifle", armor=True))
    assert state.unit("a").weapon == "rifle"
    assert state.unit("a").armor == content.LIGHT_ARMOR_VALUE
    assert state.credits.ATTACKERS == 100


def test_rewards_and_loss_streak_escalation_cap() -> None:
    state = economy_state()
    award_kill(state, Team.ATTACKERS)
    award_plant(state, Team.ATTACKERS)
    assert state.credits.ATTACKERS == 1300
    assert loss_bonus_for_streak(0) == 1900
    assert loss_bonus_for_streak(1) == 2400
    assert loss_bonus_for_streak(99) == 2900
    settle_round_economy(state, Team.DEFENDERS)
    assert state.credits.DEFENDERS == 3800
    assert state.credits.ATTACKERS == 3200
    assert state.loss_streaks.ATTACKERS == 1
    assert state.loss_streaks.DEFENDERS == 0

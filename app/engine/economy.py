from __future__ import annotations

from app.engine import content
from app.engine.schema import BuyRequest, GameState, Team


class EconomyError(ValueError):
    pass


def buy_cost(request: BuyRequest) -> int:
    cost = 0
    if request.weapon is not None:
        if request.weapon not in content.WEAPONS:
            raise EconomyError(f"unknown weapon {request.weapon}")
        cost += content.WEAPONS[request.weapon].cost
    if request.armor:
        cost += content.LIGHT_ARMOR_COST
    return cost


def apply_buy(state: GameState, request: BuyRequest) -> None:
    unit = state.unit(request.unit_id)
    if not unit.alive:
        raise EconomyError("dead units cannot buy")
    cost = buy_cost(request)
    credits = state.credits.get(unit.team)
    if cost > credits:
        raise EconomyError("insufficient credits")
    if request.weapon is not None:
        unit.weapon = request.weapon
    if request.armor:
        unit.armor = content.LIGHT_ARMOR_VALUE
    state.credits.set(unit.team, credits - cost)
    state.log.append(f"{unit.id} bought {request.weapon or 'nothing'}{' + armor' if request.armor else ''}")


def bot_buy_requests(state: GameState, team: Team) -> list[BuyRequest]:
    requests: list[BuyRequest] = []
    credits = state.credits.get(team)
    living = [u for u in state.units if u.team is team]
    for unit in living:
        weapon: str | None = None
        armor = False
        if credits >= content.WEAPONS["rifle"].cost + content.LIGHT_ARMOR_COST:
            weapon = "rifle"
            armor = True
        elif credits >= content.WEAPONS["shotgun"].cost + content.LIGHT_ARMOR_COST:
            weapon = "shotgun"
            armor = True
        elif credits >= content.LIGHT_ARMOR_COST and unit.armor <= 0:
            armor = True
        request = BuyRequest(unit_id=unit.id, weapon=weapon, armor=armor)
        credits -= buy_cost(request)
        if request.weapon is not None or request.armor:
            requests.append(request)
        if credits <= 0:
            break
    return requests


def award_kill(state: GameState, killer_team: Team) -> None:
    state.credits.add(killer_team, content.KILL_REWARD)


def award_plant(state: GameState, planter_team: Team) -> None:
    state.credits.add(planter_team, content.PLANT_REWARD)


def loss_bonus_for_streak(streak: int) -> int:
    return min(content.LOSS_BONUS_CAP, content.LOSS_BONUS_BASE + content.LOSS_BONUS_STEP * streak)


def settle_round_economy(state: GameState, winner: Team) -> None:
    loser = Team.DEFENDERS if winner is Team.ATTACKERS else Team.ATTACKERS
    state.credits.add(winner, content.WIN_BONUS)
    state.credits.add(loser, loss_bonus_for_streak(state.loss_streaks.get(loser)))
    state.loss_streaks.set(winner, 0)
    state.loss_streaks.set(loser, state.loss_streaks.get(loser) + 1)

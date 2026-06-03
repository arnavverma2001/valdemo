from random import Random

from app.engine.ai import choose_action, enumerate_legal_actions
from app.engine.game import apply_action, assert_invariants, auto_buy, new_game, start_round
from app.engine.schema import GameConfig, Phase


def test_ai_returns_only_legal_actions_across_many_seeds() -> None:
    for seed in range(20):
        state = new_game(GameConfig(seed=seed, quick=True))
        auto_buy(state)
        start_round(state)
        rng = Random(seed)
        for _ in range(20):
            if state.phase is not Phase.ACTION:
                break
            action = choose_action(state, rng)
            assert action in enumerate_legal_actions(state, action.unit_id)
            apply_action(state, rng, action)
            assert_invariants(state)


def test_ai_never_raises_when_no_active_unit() -> None:
    state = new_game(GameConfig(seed=1, quick=True))
    action = choose_action(state, Random(1))
    assert action.type.value == "end_activation"

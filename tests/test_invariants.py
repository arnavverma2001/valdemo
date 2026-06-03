from random import Random

from app.engine.ai import choose_action
from app.engine.game import apply_action, assert_invariants, auto_buy, new_game, start_round
from app.engine.schema import GameConfig, Phase


def run_match(seed: int):
    state = new_game(GameConfig(seed=seed, quick=True))
    rng = Random(seed)
    steps = 0
    while state.phase is not Phase.MATCH_END and steps < 2000:
        if state.phase is Phase.BUY:
            auto_buy(state)
            start_round(state)
        elif state.phase is Phase.ROUND_END:
            start_round(state)
        elif state.phase is Phase.ACTION:
            action = choose_action(state, rng)
            apply_action(state, rng, action)
        assert_invariants(state)
        steps += 1
    assert steps < 2000
    return state


def test_fifty_bot_matches_terminate_and_invariants_hold() -> None:
    for seed in range(50):
        state = run_match(seed)
        assert state.winner is not None
        assert state.scores.get(state.winner) == state.config.match_to


def test_same_seed_reproducible_final_state_and_log() -> None:
    first = run_match(42)
    second = run_match(42)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")

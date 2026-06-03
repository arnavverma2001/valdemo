# Turn-Based Tactical Shooter

A deterministic single-player tactical shooter against bots: tactical agents, weapons, economy,
spike plant/defuse, and a short browser demo mode. The backend is FastAPI over a pure Python
engine; the frontend is one dependency-free HTML/JS/canvas page.

## Run

```bash
make install
make lint
make test
make demo
```

Open:

```text
http://127.0.0.1:8000/?autoplay=1&seed=42&quick=1&speed=fast
```

Record a demo video:

```bash
make video
```

The generated `.webm` lands in `artifacts/`.

## Game defaults and rules

- Default teams: 3v3; 5v5 is supported by config.
- Regulation: first to 7 rounds, side-spawn swap after 6 rounds, round-turn cap 12.
- Quick/demo: first to 2, swap after 2, round-turn cap 8.
- Each activation gives 2 AP. Move/shoot/ability/plant cost 1 AP.
- Defuse costs 2 AP in a single defender activation and requires adjacency to the spike.
- Movement uses 4-way BFS, max 4 tiles per move action, blocked by walls and living units.
- Shooting uses Chebyshev distance and this exact hit chance:

```text
falloff        = falloff_per_tile * max(0, distance - weapon.optimal_range)
cover_penalty  = 0.25 if target has adjacent directional half-cover else 0
flash_penalty  = 0.40 if shooter is flashed else 0
hit_chance     = clamp(base_accuracy - falloff - cover_penalty - flash_penalty, 0.05, 0.95)
```

- LOS is blocked by walls and active smoke tiles.
- Smoke lasts 2 round-turns; flash affects units with LOS to the flash tile for their next
  activation; reveal marks enemies for 1 round-turn.
- The spike detonates after 4 round-turns once planted.
- Economy: start 800 credits; +3000 win, +1900 loss escalating by +500 to +2900, +200 kill,
  +300 plant. Bots buy rifle+armor if affordable, else shotgun+armor, else armor/save.

## Determinism

All game randomness is passed through a per-session seeded `random.Random`. The engine never calls
module-level `random`. Same seed plus same action stream produces identical state and log.

## API

- `POST /api/game`
- `GET /api/game/{id}`
- `POST /api/game/{id}/buy`
- `POST /api/game/{id}/start_round`
- `POST /api/game/{id}/action`
- `POST /api/game/{id}/ai_step`

Illegal actions return HTTP 400 and do not mutate state.

## Tests

`make test` runs unit, integration, invariant, and Playwright E2E tests with engine coverage
threshold `>=85%`. Runtime network access is not used except Playwright driving localhost.

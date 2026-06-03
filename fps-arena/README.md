# FPS Arena

A browser first-person wave-survival shooter built with vanilla JavaScript and locally vendored Three.js. Move with WASD, aim with the mouse, and clear bot waves in a compact arena.

## Requirements

- Node 22+
- Python 3.11+
- `curl`

## Install

```bash
make install
```

This creates `.venv/`, installs the Python tools, installs Playwright Chromium, and vendors:

- `static/vendor/three.module.js`
- `static/vendor/PointerLockControls.js`

The running game imports Three.js from those local files; there is no CDN dependency at play time.

## Run

```bash
make serve
```

Open <http://127.0.0.1:8000>.

Static-only mode also works:

```bash
make serve-static
```

## Controls

- Click the overlay to lock the pointer and start
- WASD: move
- Mouse: look
- Left click/hold: fire
- R: reload
- Shift: sprint
- Space: jump
- Esc: release pointer lock

## Autoplay

The bot-player mode controls the player automatically:

```text
/?autoplay=1&seed=42&waves=3
```

URL parameters:

- `autoplay=1`: enable automated player
- `seed=VALUE`: deterministic match seed
- `waves=N`: waves required to win

## Gameplay defaults

- Arena: 40×40 units, perimeter walls, 10 cover boxes
- Player: 100 HP, 5 u/s walk, 8 u/s sprint, gravity/jump, wall/cover collision
- Rifle: 25 damage, 9 shots/s, 30-round magazine, 1.5s reload
- Grunt: 50 HP, 3.5 u/s, 10 melee damage, 1.0s cooldown
- Shooter: 40 HP, 2.5 u/s, holds range, 8 ranged damage, 1.5s cooldown
- Default match: 5 waves
- Score: enemy kill points plus wave/victory bonuses

All gameplay randomness goes through the seeded PRNG in `static/src/engine/rng.js`.

## Tests

```bash
make test-unit      # Node built-in runner for pure game logic
make test-backend   # FastAPI score API tests
make test-e2e       # Playwright headless autoplay full match
make test           # all of the above
```

The E2E test launches Chromium with software WebGL, runs `/?autoplay=1&seed=42&waves=3`, verifies kills/score increase, and waits for `#result-banner` to show `VICTORY` or `GAME OVER`.

## Backend

The optional FastAPI backend serves the static game and exposes:

- `GET /api/scores`
- `POST /api/scores` with `{ "name": "Ace", "score": 1200, "wave": 5 }`

Scores persist to `server/scores.json`. Missing or corrupt score files are recreated.

## Record a demo

```bash
make record-demo
```

This records an autoplay match to `/opt/cursor/artifacts/assets/` when running in the cloud environment.

const canvas = document.querySelector("#game");
const ctx = canvas.getContext("2d");
const hud = document.querySelector("#hud");
const logEl = document.querySelector("#log");
const winnerBanner = document.querySelector("#winner-banner");
const speedSelect = document.querySelector("#speed");

let state = null;
let autoplay = false;
let autoplayTimer = null;
let lastLogLength = 0;
let effect = null;

const params = new URLSearchParams(window.location.search);
const delays = { slow: 650, normal: 300, fast: 120 };

function delay() {
  return delays[speedSelect.value] ?? 120;
}

async function api(path, body = null) {
  const options = body
    ? {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    : { method: "GET" };
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

function gamePath(suffix) {
  return `/api/game/${state.game_id}${suffix}`;
}

async function newMatch() {
  const seed = Number(params.get("seed") || 42);
  const quick = params.get("quick") === "1" || params.get("quick") === "true";
  state = await api("/api/game", {
    seed,
    quick,
    match_to: quick ? 2 : 7,
    team_size: 3,
  });
  lastLogLength = state.log.length;
  winnerBanner.hidden = true;
  render();
}

async function startRound() {
  if (!state) return;
  state = await api(gamePath("/start_round"), {});
  render();
}

function activeUnit() {
  if (!state || !state.active_unit_id) return null;
  return state.units.find((unit) => unit.id === state.active_unit_id);
}

async function aiStep() {
  if (!state || state.phase === "MATCH_END") {
    stopAutoplay();
    return;
  }
  state = await api(gamePath("/ai_step"), {});
  updateEffect();
  render();
  if (state.phase === "MATCH_END") {
    stopAutoplay();
    showWinner();
    return;
  }
  autoplayTimer = window.setTimeout(aiStep, delay());
}

function startAutoplay() {
  autoplay = true;
  document.querySelector("#autoplay").textContent = "Stop Spectating";
  if (autoplayTimer === null) {
    autoplayTimer = window.setTimeout(aiStep, 80);
  }
}

function stopAutoplay() {
  autoplay = false;
  document.querySelector("#autoplay").textContent = "Spectate (AI vs AI)";
  if (autoplayTimer !== null) {
    window.clearTimeout(autoplayTimer);
    autoplayTimer = null;
  }
}

async function endActivation() {
  const unit = activeUnit();
  if (!unit) return;
  state = await api(gamePath("/action"), { type: "end_activation", unit_id: unit.id });
  render();
}

function showWinner() {
  if (state?.phase === "MATCH_END") {
    winnerBanner.textContent = `WINNER: ${state.winner} — ${state.scores.ATTACKERS}-${state.scores.DEFENDERS}`;
    winnerBanner.hidden = false;
  }
}

function updateEffect() {
  const newest = state.log.at(-1) || "";
  if (state.log.length === lastLogLength) return;
  lastLogLength = state.log.length;
  effect = { text: newest, until: performance.now() + 360 };
}

function tileColor(tile) {
  return {
    FLOOR: "#26241e",
    WALL: "#070605",
    HALF_COVER: "#716c5e",
    SITE_A: "rgba(245, 78, 0, 0.42)",
    SITE_B: "rgba(85, 170, 255, 0.34)",
  }[tile];
}

function drawGrid(cell) {
  for (let y = 0; y < state.map.height; y += 1) {
    for (let x = 0; x < state.map.width; x += 1) {
      const tile = state.map.tiles[y][x];
      ctx.fillStyle = tileColor(tile);
      ctx.fillRect(x * cell, y * cell, cell, cell);
      ctx.strokeStyle = "rgba(237,236,236,0.08)";
      ctx.strokeRect(x * cell, y * cell, cell, cell);
      if (tile === "HALF_COVER") {
        ctx.fillStyle = "#9d9684";
        ctx.fillRect(x * cell + 12, y * cell + 18, cell - 24, cell - 36);
      }
      if (tile === "SITE_A" || tile === "SITE_B") {
        ctx.fillStyle = "#edecec";
        ctx.font = "bold 18px system-ui";
        ctx.fillText(tile === "SITE_A" ? "A" : "B", x * cell + 17, y * cell + 32);
      }
    }
  }
}

function drawSmokes(cell) {
  for (const smoke of state.smokes) {
    for (const tile of smoke.tiles) {
      ctx.beginPath();
      ctx.fillStyle = "rgba(190,190,185,0.74)";
      ctx.arc(tile.x * cell + cell / 2, tile.y * cell + cell / 2, cell * 0.44, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

function drawSpike(cell) {
  if (!state.spike.planted || !state.spike.pos) return;
  const { x, y } = state.spike.pos;
  ctx.fillStyle = "#f54e00";
  ctx.beginPath();
  ctx.moveTo(x * cell + cell / 2, y * cell + 7);
  ctx.lineTo(x * cell + cell - 8, y * cell + cell / 2);
  ctx.lineTo(x * cell + cell / 2, y * cell + cell - 7);
  ctx.lineTo(x * cell + 8, y * cell + cell / 2);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#14120b";
  ctx.font = "bold 14px system-ui";
  ctx.fillText(String(state.spike.turns_to_detonate), x * cell + 20, y * cell + 30);
}

function unitVisible(unit) {
  if (autoplay) return true;
  if (unit.team === state.active_team) return true;
  return unit.revealed || state.phase === "MATCH_END";
}

function drawUnits(cell) {
  for (const unit of state.units) {
    if (!unit.alive || !unitVisible(unit)) continue;
    const cx = unit.pos.x * cell + cell / 2;
    const cy = unit.pos.y * cell + cell / 2;
    const active = unit.id === state.active_unit_id;
    ctx.beginPath();
    ctx.fillStyle = unit.team === "ATTACKERS" ? "#f54e00" : "#4aa7ff";
    ctx.strokeStyle = active ? "#ffffff" : "#14120b";
    ctx.lineWidth = active ? 4 : 2;
    ctx.arc(cx, cy, active ? 18 : 16, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "#edecec";
    ctx.font = "bold 12px system-ui";
    ctx.textAlign = "center";
    ctx.fillText(`${unit.id}:${unit.agent[0]}`, cx, cy + 4);

    const barWidth = 34;
    ctx.fillStyle = "#321";
    ctx.fillRect(cx - barWidth / 2, cy + 21, barWidth, 5);
    ctx.fillStyle = "#48d17a";
    ctx.fillRect(cx - barWidth / 2, cy + 21, barWidth * (unit.hp / 100), 5);
    if (unit.armor > 0) {
      ctx.fillStyle = "#9cc8ff";
      ctx.fillRect(cx - barWidth / 2, cy + 28, barWidth * (unit.armor / 25), 4);
    }
    if (unit.flashed) {
      ctx.strokeStyle = "#fff47a";
      ctx.beginPath();
      ctx.arc(cx, cy, 24, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
  ctx.textAlign = "left";
}

function drawEffect(cell) {
  if (!effect || performance.now() > effect.until) return;
  ctx.save();
  ctx.globalAlpha = 0.75;
  ctx.fillStyle = effect.text.includes("shot") ? "#fff47a" : "#f54e00";
  ctx.font = "bold 26px system-ui";
  ctx.fillText(effect.text.slice(0, 44), 20, canvas.height - 26);
  if (effect.text.includes("flashed")) {
    ctx.strokeStyle = "#fff47a";
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.arc(canvas.width / 2, canvas.height / 2, cell * 2, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.restore();
  requestAnimationFrame(() => render());
}

function renderHud() {
  if (!state) return;
  const active = activeUnit();
  hud.innerHTML = `
    <div class="hud-card"><b>Round</b> ${state.round_number} / phase ${state.phase}</div>
    <div class="hud-card"><b>Score</b> ATT ${state.scores.ATTACKERS} — DEF ${state.scores.DEFENDERS}</div>
    <div class="hud-card"><b>Credits</b> ATT ${state.credits.ATTACKERS} — DEF ${state.credits.DEFENDERS}</div>
    <div class="hud-card"><b>Active</b> ${active ? `${active.id} ${active.agent}, AP ${active.ap}` : "none"}</div>
    <div class="hud-card"><b>Spike</b> ${
      state.spike.planted ? `planted, detonates in ${state.spike.turns_to_detonate}` : "not planted"
    }</div>
  `;
  logEl.innerHTML = state.log
    .slice(-8)
    .map((line) => `<li>${line.replaceAll("<", "&lt;")}</li>`)
    .join("");
  showWinner();
}

function render() {
  if (!state) return;
  const cell = canvas.width / state.map.width;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawGrid(cell);
  drawSmokes(cell);
  drawSpike(cell);
  drawUnits(cell);
  drawEffect(cell);
  renderHud();
}

canvas.addEventListener("click", async (event) => {
  if (!state || autoplay || state.phase !== "ACTION") return;
  const rect = canvas.getBoundingClientRect();
  const cell = canvas.width / state.map.width;
  const x = Math.floor(((event.clientX - rect.left) / rect.width) * state.map.width);
  const y = Math.floor(((event.clientY - rect.top) / rect.height) * state.map.height);
  const unit = activeUnit();
  if (!unit) return;
  const target = state.units.find((other) => other.alive && other.pos.x === x && other.pos.y === y);
  try {
    if (target && target.team !== unit.team) {
      state = await api(gamePath("/action"), {
        type: "shoot",
        unit_id: unit.id,
        target_unit_id: target.id,
      });
    } else {
      state = await api(gamePath("/action"), { type: "move", unit_id: unit.id, target: { x, y } });
    }
  } catch (error) {
    state.log.push(`Rejected: ${error.message}`);
  }
  updateEffect();
  render();
});

document.querySelector("#new-match").addEventListener("click", async () => {
  stopAutoplay();
  await newMatch();
});
document.querySelector("#start-round").addEventListener("click", startRound);
document.querySelector("#end-activation").addEventListener("click", endActivation);
document.querySelector("#autoplay").addEventListener("click", () => {
  if (autoplay) stopAutoplay();
  else startAutoplay();
});

(async function boot() {
  if (params.get("speed")) speedSelect.value = params.get("speed");
  await newMatch();
  if (params.get("autoplay") === "1" || params.get("autoplay") === "true") {
    startAutoplay();
  }
})();

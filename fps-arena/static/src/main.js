import * as THREE from "three";
import { createWorld } from "./world.js";
import { Player } from "./player.js";
import { Hud } from "./hud.js";
import { Game, GAME_STATES } from "./game.js";
import { AutoplayController } from "./autoplay.js";

function parseConfig() {
  const params = new URLSearchParams(window.location.search);
  const seed = params.get("seed") ?? "42";
  const waves = Number.parseInt(params.get("waves") ?? "5", 10);
  return {
    seed,
    wavesToWin: Number.isFinite(waves) && waves > 0 ? waves : 5,
    autoplay: params.get("autoplay") === "1"
  };
}

const config = parseConfig();
const canvas = document.querySelector("#game-canvas");
const startOverlay = document.querySelector("#start-overlay");
const startButton = document.querySelector("#start-button");

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(74, window.innerWidth / window.innerHeight, 0.05, 120);
const world = createWorld(scene);
const hud = new Hud();
const player = new Player(camera, document.body, world, hud, scene);
const game = new Game({ scene, world, player, hud, seed: config.seed, wavesToWin: config.wavesToWin });
const autoplay = config.autoplay ? new AutoplayController(player, config.seed) : null;

if (config.autoplay) {
  startOverlay.classList.add("hidden");
  game.start(0);
} else {
  startButton.addEventListener("click", () => {
    player.requestLock();
    game.start(performance.now() / 1000);
  });
  player.controls.addEventListener("lock", () => {
    startOverlay.classList.add("hidden");
    if (game.state === GAME_STATES.READY) {
      game.start(performance.now() / 1000);
    }
  });
  player.controls.addEventListener("unlock", () => {
    if (game.state !== GAME_STATES.RESULT) {
      startOverlay.classList.remove("hidden");
    }
  });
}

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

let last = performance.now() / 1000;
function animate() {
  requestAnimationFrame(animate);
  const now = performance.now() / 1000;
  const dt = Math.min(0.05, Math.max(0.001, now - last));
  last = now;
  if (autoplay && game.state === GAME_STATES.PLAYING) {
    autoplay.update(dt, game);
    game.updateWithExternalPlayer(dt, now);
  } else {
    game.update(dt, now);
  }
  renderer.render(scene, camera);
}

game.publishState();
animate();

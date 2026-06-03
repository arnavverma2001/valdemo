import { createRng, randomFloat } from "./engine/rng.js";
import { DEFAULT_WAVE_CONFIG, getWaveSpec } from "./engine/waves.js";
import { createEnemy, updateEnemies, ENEMY_STATS } from "./enemy.js";

export const GAME_STATES = Object.freeze({
  READY: "READY",
  PLAYING: "PLAYING",
  RESULT: "RESULT"
});

export class Game {
  constructor({ scene, world, player, hud, seed = 42, wavesToWin = DEFAULT_WAVE_CONFIG.wavesToWin }) {
    this.scene = scene;
    this.world = world;
    this.player = player;
    this.hud = hud;
    this.seed = seed;
    this.rng = createRng(seed);
    this.waveConfig = { ...DEFAULT_WAVE_CONFIG, wavesToWin };
    this.state = GAME_STATES.READY;
    this.wave = 0;
    this.score = 0;
    this.kills = 0;
    this.enemies = [];
    this.nextWaveAt = 0;
    this.startedAt = 0;
    this.terminalReason = "";
    this.scorePosted = false;
  }

  start(now = 0) {
    if (this.state !== GAME_STATES.READY) return;
    this.state = GAME_STATES.PLAYING;
    this.startedAt = now;
    this.queueNextWave(now, 0.1);
  }

  update(dt, now) {
    if (this.state !== GAME_STATES.PLAYING) {
      this.publishState();
      return;
    }
    if (this.player.dead || this.player.hp <= 0) {
      this.finish("GAME OVER", now);
      return;
    }
    this.player.update(dt, now, this.enemies, false);
    this.updateWorld(dt, now);
  }

  updateWithExternalPlayer(dt, now) {
    if (this.state !== GAME_STATES.PLAYING) {
      this.publishState();
      return;
    }
    if (this.player.dead || this.player.hp <= 0) {
      this.finish("GAME OVER", now);
      return;
    }
    this.player.update(dt, now, this.enemies, true);
    this.updateWorld(dt, now);
  }

  updateWorld(dt, now) {
    updateEnemies(this.enemies, this.player, this.world, dt, now, this.rng);
    const newlyDead = this.enemies.filter((enemy) => enemy.dead && !enemy.scored);
    for (const enemy of newlyDead) {
      enemy.scored = true;
      this.score += ENEMY_STATS[enemy.type].score;
      this.kills += 1;
    }
    this.enemies = this.enemies.filter((enemy) => !enemy.despawn);
    const living = this.enemies.filter((enemy) => !enemy.dead);
    if (living.length === 0) {
      if (this.wave >= this.waveConfig.wavesToWin) {
        this.score += 500;
        this.finish("VICTORY", now);
      } else if (this.nextWaveAt === 0) {
        this.score += this.wave * 75;
        this.queueNextWave(now, 1.3);
      }
    }
    if (this.nextWaveAt > 0 && now >= this.nextWaveAt) {
      this.spawnWave();
      this.nextWaveAt = 0;
    }
    this.publishState();
  }

  queueNextWave(now, delay) {
    this.nextWaveAt = now + delay;
  }

  spawnWave() {
    this.wave += 1;
    const spec = getWaveSpec(this.wave, this.rng, this.waveConfig, this.world.spawnPoints.length);
    for (const enemyPlan of spec.enemies) {
      const spawn = this.world.spawnPoints[enemyPlan.spawnIndex];
      const offset = {
        x: randomFloat(this.rng, -1.1, 1.1),
        z: randomFloat(this.rng, -1.1, 1.1)
      };
      const enemy = createEnemy(
        this.scene,
        enemyPlan.type,
        { x: spawn.x + offset.x, z: spawn.z + offset.z },
        enemyPlan.id
      );
      this.enemies.push(enemy);
    }
  }

  finish(reason, now) {
    if (this.state === GAME_STATES.RESULT) return;
    this.state = GAME_STATES.RESULT;
    this.terminalReason = reason;
    const elapsed = Math.max(0, now - this.startedAt);
    const text = `${reason}\nScore ${this.score} · Wave ${this.wave}/${this.waveConfig.wavesToWin} · Kills ${this.kills} · Time ${elapsed.toFixed(1)}s`;
    this.hud.showResult(text);
    this.publishState();
    this.postScore(reason);
  }

  async postScore(reason) {
    if (this.scorePosted || !window.location.protocol.startsWith("http")) return;
    this.scorePosted = true;
    try {
      const response = await fetch("/api/scores", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: reason === "VICTORY" ? "Survivor" : "Fighter", score: this.score, wave: this.wave })
      });
      if (!response.ok && response.status !== 404) {
        console.info(`Score API returned ${response.status}`);
      }
    } catch (error) {
      console.info(`Score API unavailable: ${error.message}`);
    }
  }

  publishState() {
    const status = this.state === GAME_STATES.PLAYING
      ? this.nextWaveAt > 0 ? "Intermission" : `Wave ${this.wave}`
      : this.state;
    this.hud.update({
      health: this.player.hp,
      ammo: this.player.weapon.ammo,
      magazine: this.player.weapon.magazine,
      wave: this.wave,
      wavesToWin: this.waveConfig.wavesToWin,
      score: this.score,
      kills: this.kills,
      status
    });
    window.__fpsArenaState = {
      state: this.state,
      wave: this.wave,
      wavesToWin: this.waveConfig.wavesToWin,
      score: this.score,
      kills: this.kills,
      enemies: this.enemies.filter((enemy) => !enemy.dead).length,
      hp: this.player.hp,
      result: this.terminalReason
    };
  }
}

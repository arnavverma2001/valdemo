import test from "node:test";
import assert from "node:assert/strict";
import { createRng } from "../../static/src/engine/rng.js";
import { enemyCountForWave, getWaveSpec, shooterRatioForWave } from "../../static/src/engine/waves.js";

test("enemy counts follow base plus wave scale", () => {
  assert.equal(enemyCountForWave(1), 4);
  assert.equal(enemyCountForWave(3), 8);
  assert.equal(enemyCountForWave(5), 12);
});

test("shooter ratio ramps in later waves", () => {
  assert.equal(shooterRatioForWave(1), 0);
  assert.ok(shooterRatioForWave(3) > shooterRatioForWave(2));
  assert.ok(shooterRatioForWave(10) <= 0.45);
});

test("wave specs are deterministic for fixed seed", () => {
  const a = getWaveSpec(4, createRng(42), undefined, 8);
  const b = getWaveSpec(4, createRng(42), undefined, 8);
  assert.deepEqual(a, b);
  assert.equal(a.enemies.length, a.count);
  assert.ok(a.enemies.every((enemy) => enemy.spawnIndex >= 0 && enemy.spawnIndex < 8));
});

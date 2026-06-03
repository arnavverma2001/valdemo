import test from "node:test";
import assert from "node:assert/strict";
import { applyDamage, computeDamage, HIT_ZONES, isDead, selectHitscanTarget } from "../../static/src/engine/combat.js";

test("damage subtracts hp and marks death", () => {
  const hurt = applyDamage({ id: "a", hp: 30 }, 10);
  assert.equal(hurt.hp, 20);
  assert.equal(isDead(hurt), false);
  const dead = applyDamage(hurt, 50);
  assert.equal(dead.hp, 0);
  assert.equal(dead.dead, true);
  assert.equal(isDead(dead), true);
});

test("headshots apply multiplier", () => {
  assert.equal(computeDamage(25, HIT_ZONES.BODY), 25);
  assert.equal(computeDamage(25, HIT_ZONES.HEAD), 50);
});

test("hitscan selects nearest valid living target", () => {
  const origin = { x: 0, y: 1, z: 0 };
  const direction = { x: 0, y: 0, z: 1 };
  const enemies = [
    { id: "far", hp: 10, position: { x: 0, y: 1, z: 8 }, hitRadius: 0.5 },
    { id: "dead", hp: 0, position: { x: 0, y: 1, z: 2 }, hitRadius: 0.5 },
    { id: "near", hp: 10, position: { x: 0, y: 1, z: 4 }, hitRadius: 0.5 }
  ];
  assert.equal(selectHitscanTarget(origin, direction, enemies).enemy.id, "near");
});

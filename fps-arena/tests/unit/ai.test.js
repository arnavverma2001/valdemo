import test from "node:test";
import assert from "node:assert/strict";
import { createRng, randomFloat } from "../../static/src/engine/rng.js";
import { decideEnemyAction, ENEMY_ACTIONS, selectNearestLivingEnemy, computeAutoplayAim, computeAutoplayMove, computeAutoplayWeapon } from "../../static/src/engine/ai.js";

test("enemy decisions are legal across many states", () => {
  const rng = createRng(99);
  const legal = new Set(Object.values(ENEMY_ACTIONS));
  for (let i = 0; i < 200; i += 1) {
    const enemy = {
      type: i % 2 === 0 ? "grunt" : "shooter",
      position: { x: randomFloat(rng, -20, 20), z: randomFloat(rng, -20, 20) },
      nextAttackAt: randomFloat(rng, 0, 10)
    };
    const player = { position: { x: randomFloat(rng, -20, 20), z: randomFloat(rng, -20, 20) } };
    const decision = decideEnemyAction(enemy, player, randomFloat(rng, 0, 10));
    assert.ok(legal.has(decision.action));
    assert.ok(Number.isFinite(decision.move.x));
    assert.ok(Number.isFinite(decision.move.z));
  }
});

test("autoplay chooses nearest living enemy", () => {
  const target = selectNearestLivingEnemy({ x: 0, z: 0 }, [
    { id: "dead", hp: 0, position: { x: 1, z: 1 } },
    { id: "far", hp: 10, position: { x: 9, z: 0 } },
    { id: "near", hp: 10, position: { x: 2, z: 0 } }
  ]);
  assert.equal(target.id, "near");
});

test("autoplay helper outputs safe controls", () => {
  const player = { position: { x: 0, y: 1.7, z: 0 }, yaw: 0, pitch: 0 };
  const enemy = { hp: 40, position: { x: 0, y: 0, z: 5 }, aimPoint: { x: 0, y: 1.1, z: 5 } };
  const aim = computeAutoplayAim(player, enemy);
  assert.ok(Number.isFinite(aim.yaw));
  assert.ok(Number.isFinite(aim.pitch));
  const move = computeAutoplayMove(player, enemy, createRng(1));
  assert.ok(move.forward >= -1 && move.forward <= 1);
  assert.ok(move.strafe >= -1 && move.strafe <= 1);
  assert.deepEqual(computeAutoplayWeapon({ ammo: 0 }, aim), { fire: false, reload: true });
});

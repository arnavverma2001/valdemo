import { distance2D, yawPitchToTarget, isAimWithinTolerance, normalize2D, clamp } from "./vecmath.js";
import { randomFloat } from "./rng.js";

export const ENEMY_ACTIONS = Object.freeze({
  SEEK: "seek",
  RETREAT: "retreat",
  HOLD: "hold",
  ATTACK: "attack"
});

export function selectNearestLivingEnemy(playerPosition, enemies) {
  let best = null;
  let bestDistance = Infinity;
  for (const enemy of enemies ?? []) {
    if (!enemy || enemy.dead || enemy.hp <= 0) continue;
    const d = distance2D(playerPosition, enemy.position);
    if (d < bestDistance) {
      best = enemy;
      bestDistance = d;
    }
  }
  return best;
}

export function decideEnemyAction(enemy, player, now = 0) {
  if (!enemy || !player) {
    throw new Error("decideEnemyAction requires enemy and player");
  }
  const d = distance2D(enemy.position, player.position);
  const cooldownReady = (enemy.nextAttackAt ?? 0) <= now;
  if (enemy.type === "shooter") {
    if (d <= 13 && cooldownReady) {
      return { action: ENEMY_ACTIONS.ATTACK, move: { x: 0, z: 0 }, wantsFire: true };
    }
    if (d < 6) {
      const away = normalize2D({ x: enemy.position.x - player.position.x, z: enemy.position.z - player.position.z });
      return { action: ENEMY_ACTIONS.RETREAT, move: away, wantsFire: false };
    }
    if (d > 9) {
      const toward = normalize2D({ x: player.position.x - enemy.position.x, z: player.position.z - enemy.position.z });
      return { action: ENEMY_ACTIONS.SEEK, move: toward, wantsFire: false };
    }
    return { action: ENEMY_ACTIONS.HOLD, move: { x: 0, z: 0 }, wantsFire: false };
  }
  if (d <= 1.15 && cooldownReady) {
    return { action: ENEMY_ACTIONS.ATTACK, move: { x: 0, z: 0 }, wantsFire: false };
  }
  const toward = normalize2D({ x: player.position.x - enemy.position.x, z: player.position.z - enemy.position.z });
  return { action: ENEMY_ACTIONS.SEEK, move: toward, wantsFire: false };
}

export function separationVector(self, others, desiredDistance = 1.1) {
  let x = 0;
  let z = 0;
  for (const other of others ?? []) {
    if (!other || other === self || other.dead || other.hp <= 0) continue;
    const d = distance2D(self.position, other.position);
    if (d <= 1e-6 || d >= desiredDistance) continue;
    x += (self.position.x - other.position.x) / d * (desiredDistance - d);
    z += (self.position.z - other.position.z) / d * (desiredDistance - d);
  }
  return normalize2D({ x, z });
}

export function computeAutoplayAim(playerPose, target) {
  if (!target) {
    return { yaw: playerPose.yaw ?? 0, pitch: playerPose.pitch ?? 0, onTarget: false };
  }
  const aimPoint = target.aimPoint ?? {
    x: target.position.x,
    y: (target.position.y ?? 0) + 1.15,
    z: target.position.z
  };
  const desired = yawPitchToTarget(playerPose.position, aimPoint);
  const onTarget = isAimWithinTolerance(
    { yaw: playerPose.yaw ?? 0, pitch: playerPose.pitch ?? 0 },
    desired,
    0.11
  );
  return { ...desired, onTarget };
}

export function computeAutoplayMove(playerPose, target, rng, arenaHalfSize = 19) {
  if (!target) {
    return { forward: 0, strafe: 0, sprint: false };
  }
  const d = distance2D(playerPose.position, target.position);
  let forward = d > 9 ? 1 : d < 4.5 ? -0.65 : 0.2;
  const dodge = randomFloat(rng, -1, 1);
  let strafe = Math.abs(dodge) < 0.2 ? 0 : Math.sign(dodge) * 0.75;
  const margin = arenaHalfSize - 2;
  if (playerPose.position.x > margin) strafe = -1;
  if (playerPose.position.x < -margin) strafe = 1;
  if (playerPose.position.z > margin) forward = -1;
  if (playerPose.position.z < -margin) forward = 1;
  return {
    forward: clamp(forward, -1, 1),
    strafe: clamp(strafe, -1, 1),
    sprint: d > 12
  };
}

export function computeAutoplayWeapon(playerWeapon, aim) {
  if ((playerWeapon.ammo ?? 0) <= 0) {
    return { fire: false, reload: true };
  }
  if (playerWeapon.reloading) {
    return { fire: false, reload: false };
  }
  return { fire: Boolean(aim?.onTarget), reload: false };
}

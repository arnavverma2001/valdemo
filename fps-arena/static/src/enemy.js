import * as THREE from "three";
import { decideEnemyAction, separationVector } from "./engine/ai.js";
import { distance2D } from "./engine/vecmath.js";
import { randomFloat } from "./engine/rng.js";
import { resolveCircleWorld } from "./world.js";

export const ENEMY_STATS = Object.freeze({
  grunt: { hp: 50, speed: 3.5, damage: 10, cooldown: 1.0, score: 100, radius: 0.45 },
  shooter: { hp: 40, speed: 2.5, damage: 8, cooldown: 1.5, score: 150, radius: 0.45 }
});

export function createEnemy(scene, type, position, id) {
  const stats = ENEMY_STATS[type] ?? ENEMY_STATS.grunt;
  const material = new THREE.MeshStandardMaterial({
    color: type === "shooter" ? 0x8cc9ff : 0xf54e00,
    roughness: 0.55,
    emissive: type === "shooter" ? 0x082033 : 0x361000
  });
  const group = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.42, 1.0, 5, 10), material);
  body.position.y = 0.85;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.28, 14, 10), material);
  head.position.y = 1.55;
  group.add(body, head);
  group.position.set(position.x, 0, position.z);
  scene.add(group);
  return {
    id,
    type,
    hp: stats.hp,
    maxHp: stats.hp,
    dead: false,
    despawn: false,
    position: { x: position.x, y: 0, z: position.z },
    aimPoint: { x: position.x, y: 1.1, z: position.z },
    hitRadius: 0.7,
    nextAttackAt: 0,
    flashTimer: 0,
    deathTimer: 0.35,
    mesh: group,
    material
  };
}

export function updateEnemies(enemies, player, world, dt, now, rng) {
  let deaths = 0;
  for (const enemy of enemies) {
    if (enemy.despawn) continue;
    if (enemy.dead) {
      enemy.deathTimer -= dt;
      enemy.mesh.scale.multiplyScalar(Math.max(0.86, 1 - dt * 4));
      enemy.mesh.position.y += dt * 0.8;
      if (enemy.deathTimer <= 0) {
        enemy.despawn = true;
        enemy.mesh.parent?.remove(enemy.mesh);
        enemy.material.dispose();
        deaths += 1;
      }
      continue;
    }
    enemy.flashTimer = Math.max(0, enemy.flashTimer - dt);
    enemy.material.emissive.setHex(enemy.flashTimer > 0 ? 0xffffff : enemy.type === "shooter" ? 0x082033 : 0x361000);
    const stats = ENEMY_STATS[enemy.type];
    const decision = decideEnemyAction(enemy, player, now);
    if (decision.action === "attack") {
      attackPlayer(enemy, player, now, rng);
    }

    const sep = separationVector(enemy, enemies, 1.2);
    const move = {
      x: (decision.move.x ?? 0) + sep.x * 0.8,
      z: (decision.move.z ?? 0) + sep.z * 0.8
    };
    const length = Math.hypot(move.x, move.z);
    if (length > 1e-6 && decision.action !== "hold") {
      enemy.position.x += (move.x / length) * stats.speed * dt;
      enemy.position.z += (move.z / length) * stats.speed * dt;
      const resolved = resolveCircleWorld(enemy.position, stats.radius, world.obstacles, world.arenaHalfSize);
      enemy.position.x = resolved.x;
      enemy.position.z = resolved.z;
    }
    enemy.aimPoint = { x: enemy.position.x, y: 1.1, z: enemy.position.z };
    enemy.mesh.position.set(enemy.position.x, 0, enemy.position.z);
    const dx = player.position.x - enemy.position.x;
    const dz = player.position.z - enemy.position.z;
    enemy.mesh.rotation.y = Math.atan2(dx, dz);
  }
  return deaths;
}

function attackPlayer(enemy, player, now, rng) {
  const stats = ENEMY_STATS[enemy.type];
  if (now < enemy.nextAttackAt || player.dead) return;
  const d = distance2D(enemy.position, player.position);
  if (enemy.type === "grunt") {
    if (d <= 1.25) {
      player.takeDamage(stats.damage);
      enemy.nextAttackAt = now + stats.cooldown;
    }
    return;
  }
  if (d <= 14) {
    const spread = Math.abs(randomFloat(rng, -0.08, 0.08));
    const hit = spread < 0.062 || d < 5;
    if (hit) {
      player.takeDamage(stats.damage);
    }
    enemy.nextAttackAt = now + stats.cooldown;
  }
}

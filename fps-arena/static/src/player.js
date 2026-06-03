import * as THREE from "three";
import { PointerLockControls } from "three/addons/controls/PointerLockControls.js";
import { applyDamage, computeDamage, selectHitscanTarget, HIT_ZONES } from "./engine/combat.js";
import { resolveCircleWorld } from "./world.js";

const PLAYER_RADIUS = 0.35;
const EYE_HEIGHT = 1.7;
const GRAVITY = -18;

export class Player {
  constructor(camera, domElement, world, hud, scene) {
    this.camera = camera;
    this.domElement = domElement;
    this.world = world;
    this.hud = hud;
    this.scene = scene;
    this.controls = new PointerLockControls(camera, domElement);
    this.position = { x: 0, y: 0, z: 0 };
    this.velocityY = 0;
    this.grounded = true;
    this.hp = 100;
    this.dead = false;
    this.yaw = 0;
    this.pitch = 0;
    this.input = {
      forward: 0,
      strafe: 0,
      sprint: false,
      jump: false,
      fire: false,
      reload: false
    };
    this.keys = new Set();
    this.weapon = {
      damage: 25,
      fireRate: 9,
      magazine: 30,
      ammo: 30,
      reloadSeconds: 1.5,
      reloading: false,
      reloadDoneAt: 0,
      nextShotAt: 0
    };
    this.effects = [];
    this.camera.position.set(0, EYE_HEIGHT, 0);
    this.camera.rotation.order = "YXZ";
    this.bindInput();
  }

  bindInput() {
    window.addEventListener("keydown", (event) => {
      this.keys.add(event.code);
      if (event.code === "KeyR") this.input.reload = true;
    });
    window.addEventListener("keyup", (event) => this.keys.delete(event.code));
    window.addEventListener("mousedown", (event) => {
      if (event.button === 0) this.input.fire = true;
    });
    window.addEventListener("mouseup", (event) => {
      if (event.button === 0) this.input.fire = false;
    });
  }

  syncKeyboardInput() {
    this.input.forward = (this.keys.has("KeyW") ? 1 : 0) + (this.keys.has("KeyS") ? -1 : 0);
    this.input.strafe = (this.keys.has("KeyD") ? 1 : 0) + (this.keys.has("KeyA") ? -1 : 0);
    this.input.sprint = this.keys.has("ShiftLeft") || this.keys.has("ShiftRight");
    this.input.jump = this.keys.has("Space");
    if (this.keys.has("KeyR")) this.input.reload = true;
  }

  requestLock() {
    this.controls.lock();
  }

  setAutoplayControls(command) {
    this.input.forward = command.forward ?? 0;
    this.input.strafe = command.strafe ?? 0;
    this.input.sprint = Boolean(command.sprint);
    this.input.jump = false;
    this.input.fire = Boolean(command.fire);
    this.input.reload = Boolean(command.reload);
    if (Number.isFinite(command.yaw) && Number.isFinite(command.pitch)) {
      this.yaw = command.yaw;
      this.pitch = command.pitch;
      const dir = new THREE.Vector3(Math.sin(this.yaw) * Math.cos(this.pitch), Math.sin(this.pitch), Math.cos(this.yaw) * Math.cos(this.pitch));
      this.camera.lookAt(this.camera.position.clone().add(dir));
    }
  }

  update(dt, now, enemies, autoplay = false) {
    if (this.dead) return;
    if (!autoplay) {
      this.syncKeyboardInput();
    }
    if (this.weapon.reloading && now >= this.weapon.reloadDoneAt) {
      this.weapon.reloading = false;
      this.weapon.ammo = this.weapon.magazine;
    }
    if (this.input.reload) {
      this.reload(now);
      this.input.reload = false;
    }
    this.move(dt);
    if (this.input.fire) {
      this.tryFire(now, enemies);
    }
    this.updateEffects(dt);
  }

  move(dt) {
    const speed = this.input.sprint ? 8 : 5;
    const forward = new THREE.Vector3();
    this.camera.getWorldDirection(forward);
    forward.y = 0;
    if (forward.lengthSq() < 1e-8) forward.set(0, 0, 1);
    forward.normalize();
    const right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(0, 1, 0)).multiplyScalar(-1).normalize();
    const desired = new THREE.Vector3();
    desired.addScaledVector(forward, this.input.forward);
    desired.addScaledVector(right, this.input.strafe);
    if (desired.lengthSq() > 1) desired.normalize();
    this.position.x += desired.x * speed * dt;
    this.position.z += desired.z * speed * dt;

    if (this.input.jump && this.grounded) {
      this.velocityY = 7;
      this.grounded = false;
    }
    this.velocityY += GRAVITY * dt;
    this.position.y += this.velocityY * dt;
    if (this.position.y <= 0) {
      this.position.y = 0;
      this.velocityY = 0;
      this.grounded = true;
    }

    const resolved = resolveCircleWorld(this.position, PLAYER_RADIUS, this.world.obstacles, this.world.arenaHalfSize);
    this.position.x = resolved.x;
    this.position.z = resolved.z;
    this.camera.position.set(this.position.x, this.position.y + EYE_HEIGHT, this.position.z);
  }

  reload(now) {
    if (this.weapon.reloading || this.weapon.ammo === this.weapon.magazine) return;
    this.weapon.reloading = true;
    this.weapon.reloadDoneAt = now + this.weapon.reloadSeconds;
  }

  tryFire(now, enemies) {
    if (this.weapon.reloading) return;
    if (this.weapon.ammo <= 0) {
      this.reload(now);
      return;
    }
    if (now < this.weapon.nextShotAt) return;
    this.weapon.nextShotAt = now + 1 / this.weapon.fireRate;
    this.weapon.ammo -= 1;

    const origin = this.camera.position;
    const direction = new THREE.Vector3();
    this.camera.getWorldDirection(direction).normalize();
    const hit = selectHitscanTarget(
      { x: origin.x, y: origin.y, z: origin.z },
      { x: direction.x, y: direction.y, z: direction.z },
      enemies,
      { maxDistance: 70 }
    );
    const end = hit
      ? new THREE.Vector3(hit.enemy.position.x, hit.enemy.position.y + 1, hit.enemy.position.z)
      : origin.clone().add(direction.multiplyScalar(45));
    this.spawnTracer(origin, end, hit ? 0xf54e00 : 0xedecec);
    if (hit) {
      const zone = hit.distance < 35 && hit.enemy.type === "grunt" ? HIT_ZONES.BODY : hit.hitZone;
      const updated = applyDamage(hit.enemy, computeDamage(this.weapon.damage, zone));
      hit.enemy.hp = updated.hp;
      hit.enemy.dead = updated.dead;
      hit.enemy.flashTimer = 0.12;
      this.hud.showHitMarker();
    }
  }

  spawnTracer(origin, end, color) {
    const geometry = new THREE.BufferGeometry().setFromPoints([origin.clone(), end.clone()]);
    const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.86 });
    const line = new THREE.Line(geometry, material);
    this.scene.add(line);
    this.effects.push({ object: line, ttl: 0.07 });

    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(0.08, 8, 8),
      new THREE.MeshBasicMaterial({ color: 0xffd166 })
    );
    marker.position.copy(end);
    this.scene.add(marker);
    this.effects.push({ object: marker, ttl: 0.12 });
  }

  updateEffects(dt) {
    for (const effect of this.effects) {
      effect.ttl -= dt;
      if (effect.object.material) {
        effect.object.material.opacity = Math.max(0, effect.ttl / 0.12);
      }
    }
    const deadEffects = this.effects.filter((effect) => effect.ttl <= 0);
    this.effects = this.effects.filter((effect) => effect.ttl > 0);
    for (const effect of deadEffects) {
      this.scene.remove(effect.object);
      effect.object.geometry?.dispose();
      effect.object.material?.dispose();
    }
  }

  takeDamage(amount) {
    if (this.dead) return;
    this.hp = Math.max(0, this.hp - amount);
    this.hud.showDamage();
    if (this.hp <= 0) {
      this.dead = true;
    }
  }
}

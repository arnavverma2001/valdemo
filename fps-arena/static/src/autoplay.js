import { createRng } from "./engine/rng.js";
import { computeAutoplayAim, computeAutoplayMove, computeAutoplayWeapon, selectNearestLivingEnemy } from "./engine/ai.js";
import { clamp, lerpAngle } from "./engine/vecmath.js";

export class AutoplayController {
  constructor(player, seed = 42) {
    this.player = player;
    this.rng = createRng(`autoplay-${seed}`);
    this.yaw = 0;
    this.pitch = 0;
  }

  update(dt, game) {
    const target = selectNearestLivingEnemy(this.player.position, game.enemies);
    const pose = {
      position: {
        x: this.player.position.x,
        y: this.player.position.y + 1.7,
        z: this.player.position.z
      },
      yaw: this.yaw,
      pitch: this.pitch
    };
    const aim = computeAutoplayAim(pose, target);
    const turnSpeed = Math.min(1, dt * 9);
    this.yaw = lerpAngle(this.yaw, aim.yaw, turnSpeed);
    this.pitch = clamp(this.pitch + (aim.pitch - this.pitch) * turnSpeed, -1.25, 1.25);
    const refinedAim = computeAutoplayAim({ ...pose, yaw: this.yaw, pitch: this.pitch }, target);
    const move = computeAutoplayMove(this.player.position, target, this.rng, game.world.arenaHalfSize);
    const weapon = computeAutoplayWeapon(this.player.weapon, refinedAim);
    this.player.setAutoplayControls({
      ...move,
      ...weapon,
      yaw: this.yaw,
      pitch: this.pitch
    });
  }
}

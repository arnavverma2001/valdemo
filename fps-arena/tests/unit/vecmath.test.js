import test from "node:test";
import assert from "node:assert/strict";
import { distance2D, distance3D, yawPitchToTarget, directionFromYawPitch, isAimWithinTolerance } from "../../static/src/engine/vecmath.js";

test("distance helpers use x/z and x/y/z correctly", () => {
  assert.equal(distance2D({ x: 0, z: 0 }, { x: 3, z: 4 }), 5);
  assert.equal(distance3D({ x: 0, y: 0, z: 0 }, { x: 2, y: 3, z: 6 }), 7);
});

test("yaw and pitch to target are predictable", () => {
  const forward = yawPitchToTarget({ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: 10 });
  assert.ok(Math.abs(forward.yaw) < 1e-9);
  assert.ok(Math.abs(forward.pitch) < 1e-9);

  const right = yawPitchToTarget({ x: 0, y: 0, z: 0 }, { x: 10, y: 10, z: 0 });
  assert.ok(Math.abs(right.yaw - Math.PI / 2) < 1e-9);
  assert.ok(Math.abs(right.pitch - Math.PI / 4) < 1e-9);
});

test("direction and aim tolerance match expected values", () => {
  const dir = directionFromYawPitch(Math.PI / 2, 0);
  assert.ok(Math.abs(dir.x - 1) < 1e-9);
  assert.ok(Math.abs(dir.y) < 1e-9);
  assert.ok(Math.abs(dir.z) < 1e-9);
  assert.equal(isAimWithinTolerance({ yaw: 0, pitch: 0 }, { yaw: 0.05, pitch: -0.04 }, 0.06), true);
  assert.equal(isAimWithinTolerance({ yaw: 0, pitch: 0 }, { yaw: 0.07, pitch: 0 }, 0.06), false);
});

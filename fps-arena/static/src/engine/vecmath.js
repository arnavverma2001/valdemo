export const TAU = Math.PI * 2;

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export function distance2D(a, b) {
  const dx = (a.x ?? 0) - (b.x ?? 0);
  const dz = (a.z ?? 0) - (b.z ?? 0);
  return Math.hypot(dx, dz);
}

export function distance3D(a, b) {
  const dx = (a.x ?? 0) - (b.x ?? 0);
  const dy = (a.y ?? 0) - (b.y ?? 0);
  const dz = (a.z ?? 0) - (b.z ?? 0);
  return Math.hypot(dx, dy, dz);
}

export function normalizeAngle(angle) {
  let out = (angle + Math.PI) % TAU;
  if (out < 0) out += TAU;
  return out - Math.PI;
}

export function angleDelta(from, to) {
  return normalizeAngle(to - from);
}

export function lerpAngle(from, to, t) {
  return normalizeAngle(from + angleDelta(from, to) * clamp(t, 0, 1));
}

export function yawPitchToTarget(from, to) {
  const dx = (to.x ?? 0) - (from.x ?? 0);
  const dy = (to.y ?? 0) - (from.y ?? 0);
  const dz = (to.z ?? 0) - (from.z ?? 0);
  const ground = Math.hypot(dx, dz);
  return {
    yaw: Math.atan2(dx, dz),
    pitch: Math.atan2(dy, ground)
  };
}

export function directionFromYawPitch(yaw, pitch) {
  const cp = Math.cos(pitch);
  return {
    x: Math.sin(yaw) * cp,
    y: Math.sin(pitch),
    z: Math.cos(yaw) * cp
  };
}

export function normalize2D(v) {
  const length = Math.hypot(v.x ?? 0, v.z ?? 0);
  if (length <= 1e-9) {
    return { x: 0, z: 0 };
  }
  return { x: (v.x ?? 0) / length, z: (v.z ?? 0) / length };
}

export function isAimWithinTolerance(current, target, toleranceRadians) {
  return (
    Math.abs(angleDelta(current.yaw ?? 0, target.yaw ?? 0)) <= toleranceRadians &&
    Math.abs((target.pitch ?? 0) - (current.pitch ?? 0)) <= toleranceRadians
  );
}

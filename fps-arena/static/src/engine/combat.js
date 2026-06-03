export const HIT_ZONES = Object.freeze({
  BODY: "body",
  HEAD: "head"
});

export function computeDamage(baseDamage, hitZone = HIT_ZONES.BODY, headshotMultiplier = 2) {
  if (!Number.isFinite(baseDamage) || baseDamage < 0) {
    throw new Error(`Invalid damage: ${baseDamage}`);
  }
  return hitZone === HIT_ZONES.HEAD ? baseDamage * headshotMultiplier : baseDamage;
}

export function applyDamage(entity, amount) {
  if (!entity || !Number.isFinite(entity.hp)) {
    throw new Error("applyDamage requires an entity with hp");
  }
  if (!Number.isFinite(amount) || amount < 0) {
    throw new Error(`Invalid damage amount: ${amount}`);
  }
  const hp = Math.max(0, entity.hp - amount);
  return {
    ...entity,
    hp,
    dead: hp <= 0
  };
}

export function isDead(entity) {
  return !entity || entity.dead === true || (Number.isFinite(entity.hp) && entity.hp <= 0);
}

export function raySphereIntersection(origin, direction, center, radius) {
  const ox = origin.x - center.x;
  const oy = origin.y - center.y;
  const oz = origin.z - center.z;
  const b = 2 * (ox * direction.x + oy * direction.y + oz * direction.z);
  const c = ox * ox + oy * oy + oz * oz - radius * radius;
  const disc = b * b - 4 * c;
  if (disc < 0) return null;
  const root = Math.sqrt(disc);
  const t1 = (-b - root) / 2;
  const t2 = (-b + root) / 2;
  const t = t1 >= 0 ? t1 : t2 >= 0 ? t2 : null;
  return t === null ? null : t;
}

export function selectHitscanTarget(origin, direction, enemies, options = {}) {
  const maxDistance = options.maxDistance ?? 100;
  let best = null;
  for (const enemy of enemies) {
    if (isDead(enemy)) continue;
    const center = enemy.aimPoint ?? enemy.position;
    const radius = enemy.hitRadius ?? 0.55;
    const distance = raySphereIntersection(origin, direction, center, radius);
    if (distance === null || distance > maxDistance) continue;
    if (!best || distance < best.distance) {
      best = {
        enemy,
        distance,
        hitZone: center.y - origin.y > 0.8 ? HIT_ZONES.HEAD : HIT_ZONES.BODY
      };
    }
  }
  return best;
}

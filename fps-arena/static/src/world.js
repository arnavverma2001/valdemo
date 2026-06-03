import * as THREE from "three";

export const ARENA_HALF_SIZE = 20;

const COVER_SPECS = [
  { x: -10, z: -8, w: 4, d: 2.5, h: 2.2 },
  { x: -3, z: -12, w: 2.5, d: 5, h: 1.8 },
  { x: 8, z: -9, w: 5, d: 2, h: 2.5 },
  { x: 12, z: -1, w: 2.5, d: 5, h: 1.9 },
  { x: 5, z: 7, w: 4, d: 2.4, h: 2.2 },
  { x: -8, z: 7, w: 3, d: 5, h: 2.4 },
  { x: 0, z: 0, w: 3.2, d: 3.2, h: 1.5 },
  { x: -14, z: 2, w: 2, d: 4.5, h: 2.2 },
  { x: 14, z: 12, w: 4.4, d: 2.2, h: 2.0 },
  { x: -1, z: 13.5, w: 5.2, d: 2, h: 1.8 }
];

export const SPAWN_POINTS = [
  { x: -17, z: -17 }, { x: 0, z: -18 }, { x: 17, z: -17 },
  { x: 18, z: 0 }, { x: 17, z: 17 }, { x: 0, z: 18 },
  { x: -17, z: 17 }, { x: -18, z: 0 }
];

export function coverToAabb(spec) {
  return {
    minX: spec.x - spec.w / 2,
    maxX: spec.x + spec.w / 2,
    minZ: spec.z - spec.d / 2,
    maxZ: spec.z + spec.d / 2,
    height: spec.h
  };
}

export function createWorld(scene) {
  scene.background = new THREE.Color(0x14120b);
  scene.fog = new THREE.Fog(0x14120b, 45, 88);

  const ambient = new THREE.AmbientLight(0xfff4e0, 1.25);
  scene.add(ambient);
  const sun = new THREE.DirectionalLight(0xffd7af, 1.6);
  sun.position.set(10, 22, 8);
  scene.add(sun);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(ARENA_HALF_SIZE * 2, ARENA_HALF_SIZE * 2),
    new THREE.MeshStandardMaterial({ color: 0x242118, roughness: 0.86 })
  );
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);

  const wallMaterial = new THREE.MeshStandardMaterial({ color: 0x3b3528, roughness: 0.8 });
  const wallHeight = 4;
  const wallThickness = 0.8;
  const wallGeoH = new THREE.BoxGeometry(ARENA_HALF_SIZE * 2 + wallThickness, wallHeight, wallThickness);
  const wallGeoV = new THREE.BoxGeometry(wallThickness, wallHeight, ARENA_HALF_SIZE * 2 + wallThickness);
  for (const [x, z, geo] of [
    [0, -ARENA_HALF_SIZE - wallThickness / 2, wallGeoH],
    [0, ARENA_HALF_SIZE + wallThickness / 2, wallGeoH],
    [-ARENA_HALF_SIZE - wallThickness / 2, 0, wallGeoV],
    [ARENA_HALF_SIZE + wallThickness / 2, 0, wallGeoV]
  ]) {
    const wall = new THREE.Mesh(geo, wallMaterial);
    wall.position.set(x, wallHeight / 2, z);
    scene.add(wall);
  }

  const coverMaterial = new THREE.MeshStandardMaterial({ color: 0x5a4b38, roughness: 0.82 });
  const obstacles = [];
  for (const spec of COVER_SPECS) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(spec.w, spec.h, spec.d), coverMaterial);
    mesh.position.set(spec.x, spec.h / 2, spec.z);
    mesh.castShadow = false;
    scene.add(mesh);
    obstacles.push(coverToAabb(spec));
  }

  const grid = new THREE.GridHelper(ARENA_HALF_SIZE * 2, 40, 0x5c4d3c, 0x302a20);
  grid.position.y = 0.012;
  scene.add(grid);

  return {
    arenaHalfSize: ARENA_HALF_SIZE,
    obstacles,
    spawnPoints: SPAWN_POINTS.map((p) => ({ ...p }))
  };
}

export function resolveCircleWorld(position, radius, obstacles, halfSize = ARENA_HALF_SIZE) {
  const out = { x: position.x, z: position.z };
  out.x = Math.max(-halfSize + radius, Math.min(halfSize - radius, out.x));
  out.z = Math.max(-halfSize + radius, Math.min(halfSize - radius, out.z));

  for (const box of obstacles) {
    const nearestX = Math.max(box.minX, Math.min(out.x, box.maxX));
    const nearestZ = Math.max(box.minZ, Math.min(out.z, box.maxZ));
    const dx = out.x - nearestX;
    const dz = out.z - nearestZ;
    const distSq = dx * dx + dz * dz;
    if (distSq > radius * radius) continue;

    if (distSq > 1e-8) {
      const dist = Math.sqrt(distSq);
      const push = radius - dist;
      out.x += (dx / dist) * push;
      out.z += (dz / dist) * push;
    } else {
      const pushes = [
        { x: box.minX - radius - out.x, z: 0, m: Math.abs(box.minX - radius - out.x) },
        { x: box.maxX + radius - out.x, z: 0, m: Math.abs(box.maxX + radius - out.x) },
        { x: 0, z: box.minZ - radius - out.z, m: Math.abs(box.minZ - radius - out.z) },
        { x: 0, z: box.maxZ + radius - out.z, m: Math.abs(box.maxZ + radius - out.z) }
      ].sort((a, b) => a.m - b.m);
      out.x += pushes[0].x;
      out.z += pushes[0].z;
    }
  }
  out.x = Math.max(-halfSize + radius, Math.min(halfSize - radius, out.x));
  out.z = Math.max(-halfSize + radius, Math.min(halfSize - radius, out.z));
  return out;
}

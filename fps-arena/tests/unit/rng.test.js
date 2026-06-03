import test from "node:test";
import assert from "node:assert/strict";
import { createRng, randomFloat, randomInt, choice } from "../../static/src/engine/rng.js";

test("seeded PRNG is reproducible", () => {
  const a = createRng(42);
  const b = createRng(42);
  assert.deepEqual(
    Array.from({ length: 8 }, () => a.next()),
    Array.from({ length: 8 }, () => b.next())
  );
});

test("different seeds produce different sequences", () => {
  const a = createRng("a");
  const b = createRng("b");
  assert.notDeepEqual(
    Array.from({ length: 5 }, () => a.next()),
    Array.from({ length: 5 }, () => b.next())
  );
});

test("helpers are bounded and deterministic", () => {
  const rng = createRng(7);
  const floats = Array.from({ length: 50 }, () => randomFloat(rng, -2, 4));
  assert.ok(floats.every((value) => value >= -2 && value < 4));

  const rng2 = createRng(7);
  Array.from({ length: 50 }, () => randomFloat(rng2, -2, 4));
  assert.equal(randomInt(rng, 1, 3), randomInt(rng2, 1, 3));
  assert.ok(["x", "y"].includes(choice(createRng(3), ["x", "y"])));
});

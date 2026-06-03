export function hashSeed(seed) {
  const text = String(seed ?? 1);
  let h = 2166136261 >>> 0;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function createRng(seed = 1) {
  let state = hashSeed(seed);
  return {
    get state() {
      return state >>> 0;
    },
    next() {
      state = (state + 0x6d2b79f5) >>> 0;
      let t = state;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    }
  };
}

export function randomFloat(rng, min = 0, max = 1) {
  if (max < min) {
    throw new Error(`randomFloat invalid range: ${min}..${max}`);
  }
  return min + (max - min) * rng.next();
}

export function randomInt(rng, min, maxInclusive) {
  if (!Number.isInteger(min) || !Number.isInteger(maxInclusive) || maxInclusive < min) {
    throw new Error(`randomInt invalid range: ${min}..${maxInclusive}`);
  }
  return Math.floor(randomFloat(rng, min, maxInclusive + 1));
}

export function choice(rng, values) {
  if (!Array.isArray(values) || values.length === 0) {
    throw new Error("choice requires a non-empty array");
  }
  return values[randomInt(rng, 0, values.length - 1)];
}

export function weightedChoice(rng, weightedValues) {
  if (!Array.isArray(weightedValues) || weightedValues.length === 0) {
    throw new Error("weightedChoice requires values");
  }
  const total = weightedValues.reduce((sum, item) => sum + Math.max(0, item.weight), 0);
  if (total <= 0) {
    throw new Error("weightedChoice requires positive weights");
  }
  let roll = randomFloat(rng, 0, total);
  for (const item of weightedValues) {
    roll -= Math.max(0, item.weight);
    if (roll <= 0) {
      return item.value;
    }
  }
  return weightedValues[weightedValues.length - 1].value;
}

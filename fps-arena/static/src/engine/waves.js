import { weightedChoice, randomInt } from "./rng.js";

export const DEFAULT_WAVE_CONFIG = Object.freeze({
  baseEnemies: 2,
  scaleEnemies: 2,
  wavesToWin: 5,
  shooterStartWave: 2,
  maxShooterRatio: 0.45
});

export function enemyCountForWave(waveNumber, config = DEFAULT_WAVE_CONFIG) {
  if (!Number.isInteger(waveNumber) || waveNumber < 1) {
    throw new Error(`Invalid wave number: ${waveNumber}`);
  }
  return config.baseEnemies + waveNumber * config.scaleEnemies;
}

export function shooterRatioForWave(waveNumber, config = DEFAULT_WAVE_CONFIG) {
  if (waveNumber < config.shooterStartWave) return 0;
  const ramp = (waveNumber - config.shooterStartWave + 1) * 0.14;
  return Math.min(config.maxShooterRatio, ramp);
}

export function getWaveSpec(waveNumber, rng, config = DEFAULT_WAVE_CONFIG, spawnPointCount = 1) {
  const count = enemyCountForWave(waveNumber, config);
  const shooterRatio = shooterRatioForWave(waveNumber, config);
  const enemies = [];
  for (let i = 0; i < count; i += 1) {
    const type = weightedChoice(rng, [
      { value: "grunt", weight: 1 - shooterRatio },
      { value: "shooter", weight: shooterRatio }
    ]);
    enemies.push({
      id: `w${waveNumber}-e${i}`,
      type,
      spawnIndex: randomInt(rng, 0, Math.max(0, spawnPointCount - 1))
    });
  }
  return {
    waveNumber,
    count,
    shooterRatio,
    enemies
  };
}

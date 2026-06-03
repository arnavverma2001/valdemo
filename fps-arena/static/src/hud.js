export class Hud {
  constructor(documentRef = document) {
    this.healthValue = documentRef.querySelector("#health-value");
    this.healthFill = documentRef.querySelector("#health-fill");
    this.ammoValue = documentRef.querySelector("#ammo-value");
    this.waveValue = documentRef.querySelector("#wave-value");
    this.scoreValue = documentRef.querySelector("#score-value");
    this.killsValue = documentRef.querySelector("#kills-value");
    this.statusText = documentRef.querySelector("#status-text");
    this.resultBanner = documentRef.querySelector("#result-banner");
    this.hitMarker = documentRef.querySelector("#hit-marker");
    this.damageFlash = documentRef.querySelector("#damage-flash");
    this.hudRoot = documentRef.querySelector("#hud");
  }

  update(snapshot) {
    this.healthValue.textContent = String(Math.max(0, Math.round(snapshot.health)));
    this.healthFill.style.width = `${Math.max(0, Math.min(100, snapshot.health))}%`;
    this.ammoValue.textContent = `${snapshot.ammo}/${snapshot.magazine}`;
    this.waveValue.textContent = `${snapshot.wave}/${snapshot.wavesToWin}`;
    this.scoreValue.textContent = String(snapshot.score);
    this.killsValue.textContent = String(snapshot.kills);
    this.statusText.textContent = snapshot.status;
  }

  showHitMarker() {
    this.hitMarker.classList.remove("visible");
    void this.hitMarker.offsetWidth;
    this.hitMarker.classList.add("visible");
  }

  showDamage() {
    this.damageFlash.classList.remove("visible");
    this.hudRoot.classList.remove("shake");
    void this.damageFlash.offsetWidth;
    this.damageFlash.classList.add("visible");
    this.hudRoot.classList.add("shake");
    window.setTimeout(() => this.hudRoot.classList.remove("shake"), 90);
  }

  showResult(text) {
    this.resultBanner.textContent = text;
    this.resultBanner.classList.add("visible");
  }
}

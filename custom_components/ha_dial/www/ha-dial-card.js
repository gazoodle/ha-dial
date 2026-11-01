import { renderScene } from "./scene.js";

import { dialNames } from "./editor.js";

const ZOOM_KEY = "ha-dial-preview-zoom";
const ZOOM_MIN = 100, ZOOM_MAX = 400, ZOOM_STEP = 25;
// One Dial pixel per CSS pixel is the point where hard edges start being honest rather than ragged.
const SCREEN_PIXELS = 240;

// Per browser, because a phone and a Mac want different sizes, and kept apart for the panel's preview and
// for each Dial's cards, so a size chosen in one never turns up in another. Storage can be blocked or empty, and the preview must still work, so
// this only ever falls back to 100%.
function storedZoom(key) {
  try {
    const value = Number(localStorage.getItem(key));
    return value >= ZOOM_MIN && value <= ZOOM_MAX ? Math.round(value / ZOOM_STEP) * ZOOM_STEP : ZOOM_MIN;
  } catch { return ZOOM_MIN; }
}

class HaDialCard extends HTMLElement {
  constructor() {
    super();
    this.draftDevice = "preview_" + Array.from(crypto.getRandomValues(new Uint32Array(2))).join("_");
    this.configVersion = 0;
    this.lastRevision = -1;
  }

  connectedCallback() { this.load(); }

  disconnectedCallback() {
    this.unsubscribe?.();
    this.unsubscribe = undefined;
    this.subscribedDevice = undefined;
    this.configKey = this.attemptedKey = undefined;
    this.configVersion++;
  }

  // A dashboard card views and operates one Dial, so that's all its configuration holds. Anything else an
  // older card has saved, including its own pages, is dropped here.
  setConfig(config) {
    const device = String(config?.device || "").replaceAll("-", "_");
    if (device && !/^[a-z0-9_]{1,64}$/.test(device)) throw new Error("Invalid HA Dial device name");
    const next = { device: device === "preview" ? "" : device, ...(config?.follow === false ? { follow: false } : {}) };
    if (JSON.stringify(next) !== JSON.stringify(this.config)) this.configVersion++;
    this.config = next;
    this._build();
    this.applyZoom(storedZoom(this._zoomKey()));
    this.load();
  }

  _zoomKey() { return this.draftDefinition ? ZOOM_KEY : `${ZOOM_KEY}-${this.config.device}`; }

  // The panel's preview, showing a draft on a device of its own. Nothing else calls this.
  setDraft(definition) {
    if (JSON.stringify(definition) !== JSON.stringify(this.draftDefinition)) this.configVersion++;
    this.draftDefinition = definition;
    this.config = { device: "" };
    this._build();
    this.applyZoom(storedZoom(this._zoomKey()));
    this.load();
  }

  _build() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.innerHTML = `<style>${HaDialCard.styles}</style><ha-card><p class="live-banner" role="alert" hidden>Warning: changes made here are live</p><label class="zoom"><span>Zoom</span><input type="range" min="${ZOOM_MIN}" max="${ZOOM_MAX}" step="${ZOOM_STEP}" aria-label="Preview zoom"><output></output></label><div class="viewport"><div class="stage"><div class="dial"><img class="frame" src="/ha_dial/dial-frame.png" alt="" draggable="false"><canvas width="240" height="240" tabindex="0" aria-label="HA Dial preview"></canvas><button class="click-chip" data-action="press" aria-label="Click dial"><span>CLICK</span></button></div><button class="spin left" data-action="rotate_left" aria-label="Rotate left"><svg viewBox="0 0 100 100" aria-hidden="true"><path class="sweep" d="M75 79A37 37 0 1 1 86 42"/><path class="head" d="M74 39L96 39L85 59Z"/></svg></button><button class="spin right" data-action="rotate_right" aria-label="Rotate right"><svg viewBox="0 0 100 100" aria-hidden="true"><path class="sweep" d="M75 79A37 37 0 1 1 86 42"/><path class="head" d="M74 39L96 39L85 59Z"/></svg></button><p role="alert" hidden></p></div></div></ha-card>`;
      this.shadowRoot.addEventListener("click", (event) => {
        const action = event.target.closest("button")?.dataset.action;
        if (action) this.input(action);
      });
      this.shadowRoot.querySelector(".zoom input").addEventListener("input", (event) => {
        this.applyZoom(Number(event.target.value));
        try { localStorage.setItem(this._zoomKey(), String(this.zoom)); } catch { /* Remembering is a convenience. */ }
      });
      const canvas = this.shadowRoot.querySelector("canvas");
      canvas.addEventListener("click", (event) => this.touch(event));
      canvas.addEventListener("keydown", (event) => {
        const action = { ArrowLeft: "rotate_left", ArrowRight: "rotate_right", Enter: "press", Escape: "back", Home: "home" }[event.key];
        if (action) { event.preventDefault(); this.input(action); }
      });
    }
  }

  // Enlarges the whole rectangle. The viewport scrolls, so a phone pans around what no longer fits.
  applyZoom(zoom) {
    this.zoom = zoom;
    const width = 360 * zoom / 100, card = this.shadowRoot.querySelector("ha-card");
    card.style.setProperty("--dial-zoom", String(zoom / 100));
    card.style.setProperty("--dial-card-width", `${width}px`);
    // At 100% the card still shrinks to fit a narrow phone; past that it deliberately doesn't.
    card.style.setProperty("--dial-stage-width", zoom === ZOOM_MIN ? "100%" : `${width}px`);
    // A layout around the card, such as the panel, can make room for it.
    this.style.setProperty("--dial-preview-width", zoom === ZOOM_MIN ? "" : `${width}px`);
    this.shadowRoot.querySelector(".zoom input").value = String(zoom);
    this.shadowRoot.querySelector(".zoom output").textContent = `${zoom}%`;
    const canvas = this.shadowRoot.querySelector("canvas");
    canvas.style.imageRendering = (canvas.getBoundingClientRect?.().width ?? 0) >= SCREEN_PIXELS ? "pixelated" : "auto";
  }

  set hass(hass) { this._hass = hass; this.load(); }

  _device() {
    if (this.draftDefinition || this._isBeingEdited() || this.config.follow === false) return this.draftDevice;
    return this.config.device;
  }

  // Being added or edited on a dashboard: it shows the Dial on a device of its own, so trying it is safe.
  _isBeingEdited() {
    for (let node = this; node; node = node.parentNode || node.getRootNode?.().host) {
      if (["HUI-DIALOG-EDIT-CARD", "HUI-DIALOG-CREATE-CARD"].includes(node.tagName) ||
          (["HUI-CARD", "HUI-SECTION"].includes(node.tagName) && (node.preview || node.hasAttribute?.("preview"))))
        return true;
    }
    return false;
  }

  // Follow Dial off: its own screen on the Dial's pages, still operating real devices.
  _isBrowsing() { return !this.draftDefinition && this.config.follow === false && !this._isBeingEdited(); }

  async _savedPages() {
    const saved = (await this._hass.callWS({ type: "ha_dial/definitions" }))[this.config.device];
    if (!saved) throw new Error("This Dial has no saved pages yet. Add them in the HA Dial panel.");
    return { ...saved, preview_of: this.config.device };
  }

  // Set by the panel only. It travels with each input, so nothing in HA can stay switched on.
  setLive(live) {
    this.live = live;
    this.shadowRoot.querySelector(".live-banner").hidden = !live;
    this.render();
    // The screen may be showing a simulated result, so start again from what's really there.
    if (this.configKey) this.input("ready");
  }

  accept(result) {
    if (result.error) { this.error = result.error; this.render(); return; }
    if (result.revision < this.lastRevision) return;
    this.lastRevision = result.revision;
    this.deployment = result.deployment;
    this.scene = result.scene;
    this.frames = result.frames || {};
    this.frameError = result.frame_error || "";
    this.error = undefined;
    this.render();
  }

  async load() {
    if (!this.isConnected || !this._hass || !this.config) return;
    if (this.loading) { this.needsLoad = true; return; }
    this.loading = true;
    try {
      do {
        this.needsLoad = false;
        if (!this.draftDefinition && !this.config.device) {
          this.error = "Choose a Dial in this card's settings.";
          this.render();
          continue;
        }
        const device = this._device(), version = this.configVersion, real = !device.startsWith("preview_");
        const browsing = this._isBrowsing();
        const key = this.draftDefinition ? `${device}:${JSON.stringify(this.draftDefinition)}` : `${device}:${this.config.device}:${browsing}`;
        if (key === this.attemptedKey) continue;
        this.attemptedKey = key;
        try {
          const definition = real || browsing ? undefined : this.draftDefinition || await this._savedPages();
          const result = real
            ? await this._hass.callWS({ type: "ha_dial/view", device })
            : browsing ? await this._hass.callWS({ type: "ha_dial/browse", device, dial: this.config.device })
            : await this._hass.callWS({ type: "ha_dial/configure", device, definition });
          if (!this.isConnected || version !== this.configVersion) { this.needsLoad = true; continue; }
          if (this.subscribedDevice !== device) {
            this.unsubscribe?.();
            this.lastRevision = -1;
            this.subscribedDevice = device;
            const unsubscribe = await this._hass.connection.subscribeMessage((event) => {
              if (this.isConnected && this._device() === device) this.accept(event);
            }, { type: "ha_dial/subscribe", device, ...(definition ? { definition } : {}) });
            if (!this.isConnected || this._device() !== device) { unsubscribe(); continue; }
            this.unsubscribe = unsubscribe;
          }
          this.configKey = key;
          this.accept(result);
        } catch (error) {
          if (version === this.configVersion) { this.error = error.message || String(error); this.render(); }
        }
      } while (this.needsLoad && this.isConnected);
    } finally { this.loading = false; }
  }

  input(action, item) {
    this.inputQueue = (this.inputQueue || Promise.resolve()).then(async () => {
      if (!this._hass || !this.configKey || this.error) return;
      const device = this._device();
      try {
        const result = await this._hass.callWS({ type: "ha_dial/input", device, action, ...(item ? { item } : {}), ...(this.live ? { live: true } : {}) });
        if (this.isConnected && device === this._device()) this.accept(result);
      } catch (error) { this.error = error.message || String(error); this.render(); }
    });
    return this.inputQueue;
  }

  touch(event) {
    if (!this.scene) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) * 240 / rect.width, y = (event.clientY - rect.top) * 240 / rect.height;
    const hit = this.scene.regions.find((region) => (x - region.x) ** 2 + (y - region.y) ** 2 <= region.r ** 2);
    if (hit) this.input(["back", "home"].includes(hit.id) ? hit.id : hit.id === "control" ? "press" : "touch", hit.id);
  }

  render() {
    if (!this.shadowRoot) return;
    const error = this.shadowRoot.querySelector("[role=alert]");
    error.hidden = !this.error;
    error.textContent = this.error || "";
    let status = this.shadowRoot.querySelector("[role=status]");
    if (!status) {
      status = document.createElement("p");
      status.setAttribute("role", "status");
      this.shadowRoot.querySelector(".stage").append(status);
    }
    status.textContent = this.frameError ? `Dial image: ${this.frameError}` : this.live ? "Operating your live house" : this._isBrowsing() ? "Browsing separately from the Dial" : ({ preview: "Local preview", waiting: "Waiting for ESPHome device", sent: "Scene sent · awaiting device", applied: "Scene applied on device", failed: "Device deployment failed" })[this.deployment] || "";
    if (this.scene) {
      const canvas = this.shadowRoot.querySelector("canvas");
      canvas.setAttribute("aria-label", this.scene.label || "HA Dial preview");
      renderScene(canvas, this.scene, this.frames);
    }
  }

  getCardSize() { return 5; }
  static getConfigElement() { return document.createElement("ha-dial-card-editor"); }
  static getStubConfig(hass) {
    const [device] = dialNames(hass);
    return device ? { device } : {};
  }

  static styles = `
    ha-card { display:block; width:min(100%,var(--dial-card-width,360px)); margin-inline:auto; overflow:hidden; background:radial-gradient(circle at 50% 24%,#3d4248,#16181b 70%); }
    .live-banner { margin:0; padding:8px 14px; font:600 13px/18px system-ui,sans-serif; text-align:center; color:#fff; background:#c2412d; overflow-wrap:anywhere; }
    .live-banner[hidden] { display:none; }
    .zoom { display:grid; grid-template-columns:auto minmax(0,1fr) 44px; align-items:center; gap:10px; padding:8px 14px; font:500 12px/16px system-ui,sans-serif; color:#ff8b2d; background:#16181b; }
    .zoom input { width:100%; accent-color:#ff8b2d; cursor:pointer; }
    .zoom output { text-align:right; font-variant-numeric:tabular-nums; }
    .viewport { overflow:auto; max-height:85dvh; overscroll-behavior:contain; }
    /* Every measure scales, so the whole rectangle grows rather than only the Dial inside it. */
    .stage { position:relative; width:var(--dial-stage-width,100%); aspect-ratio:1; margin-inline:auto; display:grid; place-items:center; padding:calc(22px * var(--dial-zoom,1)) calc(22px * var(--dial-zoom,1)) calc(48px * var(--dial-zoom,1)); box-sizing:border-box; }
    [role=status] { position:absolute; bottom:calc(20px * var(--dial-zoom,1)); left:calc(80px * var(--dial-zoom,1)); right:calc(80px * var(--dial-zoom,1)); margin:0; text-align:center; font-size:calc(11px * var(--dial-zoom,1)); line-height:calc(16px * var(--dial-zoom,1)); overflow-wrap:anywhere; }
    .dial { position:relative; width:86%; aspect-ratio:472/475; }
    /* Visible artwork bounds at alpha > 8: (37,1)–(509,476) in the 512 px asset. */
    .frame { position:absolute; left:-7.839%; top:-.211%; display:block; width:108.475%; height:auto; pointer-events:none; }
    canvas { position:absolute; left:15.148%; top:15.263%; display:block; width:69.703%; height:auto; aspect-ratio:1; border-radius:50%; }
    .spin { position:absolute; bottom:calc(16px * var(--dial-zoom,1)); width:calc(64px * var(--dial-zoom,1)); height:calc(64px * var(--dial-zoom,1)); padding:calc(8px * var(--dial-zoom,1)); box-sizing:border-box; border:0; border-radius:50%; background:none; color:#ff8b2d; opacity:.38; cursor:pointer; transition:opacity .15s,filter .15s; }
    .spin.left { left:calc(16px * var(--dial-zoom,1)); transform:scaleX(-1); }.spin.right { right:calc(16px * var(--dial-zoom,1)); }
    .spin svg { display:block; width:100%; height:100%; overflow:visible; }
    .spin .sweep { fill:none; stroke:currentColor; stroke-width:9; stroke-linecap:butt; }
    .spin .head { fill:currentColor; }
    .spin:hover,.spin:focus-visible { opacity:.95; filter:drop-shadow(0 0 4px #ff8b2d60); }
    /* Casa Mia cm-chip dimensions; orange translucent treatment over the M5 mark. */
    .click-chip { position:absolute; left:50%; top:90.316%; transform:translate(-50%,-50%); display:inline-flex; align-items:center; justify-content:center; gap:4px; box-sizing:border-box; border:0; border-radius:calc(12px * var(--dial-zoom,1)); padding:calc(3px * var(--dial-zoom,1)) calc(10px * var(--dial-zoom,1)); box-shadow:inset 0 0 0 1px currentColor; color:#ff8b2d; background:transparent; opacity:.55; font:500 calc(10px * var(--dial-zoom,1))/calc(16px * var(--dial-zoom,1)) system-ui,sans-serif; letter-spacing:.04em; text-transform:uppercase; white-space:nowrap; cursor:pointer; transition:opacity .15s,box-shadow .15s,filter .15s; }
    .click-chip span { opacity:0; }
    .click-chip:hover span,.click-chip:focus-visible span { opacity:1; }
    .click-chip:hover,.click-chip:focus-visible { opacity:.95; background:color-mix(in srgb,#ff8b2d 28%,#15110f 72%); box-shadow:inset 0 0 0 1px currentColor,0 0 0 3px #ff8b2d59; filter:brightness(1.08); }
    .spin:active,.click-chip:active { opacity:1; }
    @media (prefers-reduced-motion:reduce) { .spin,.click-chip { transition:none; } }
    canvas:focus-visible,button:focus-visible { outline:3px solid #65bfff; outline-offset:3px; }
    [role=alert] { color:var(--error-color,#ff8080); overflow-wrap:anywhere; max-width:100%; }
  `;
}

customElements.define("ha-dial-card", HaDialCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "ha-dial-card", name: "HA Dial", description: "Shows a Dial and operates it", preview: true });

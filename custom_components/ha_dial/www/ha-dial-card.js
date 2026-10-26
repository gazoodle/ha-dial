const ICONS = {
  "mdi:lightbulb": "💡",
};

const escapeHtml = (value) => String(value).replace(
  /[&<>"']/g,
  (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character],
);

class HaDialCard extends HTMLElement {
  setConfig(config) {
    const device = String(config.device || "preview").replaceAll("-", "_");
    if (!/^[a-z0-9_]{1,64}$/.test(device)) throw new Error("Invalid HA Dial device name");
    this.config = { ...config, device };
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.innerHTML = `<style>${HaDialCard.styles}</style><ha-card><div class="stage"><div class="dial" aria-label="HA Dial preview"></div><div class="controls"><button data-action="rotate_left" aria-label="Rotate left">↶</button><button data-action="press" aria-label="Press dial">●</button><button data-action="rotate_right" aria-label="Rotate right">↷</button></div></div></ha-card>`;
      this.shadowRoot.addEventListener("click", (event) => {
        const button = event.target.closest("button");
        if (button?.dataset.action) this.input(button.dataset.action, button.dataset.item);
      });
    }
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.view) {
      this.load();
    } else if (this.view.kind === "control") {
      const state = hass.states[this.view.entity_id];
      const available = Boolean(state) && !["unknown", "unavailable"].includes(state.state);
      const active = available && state.state === "on";
      const brightness = state?.attributes.brightness;
      const value = available ? (Number.isFinite(brightness) ? Math.round(brightness * 100 / 255) : (active ? 100 : 0)) : 0;
      this.view = { ...this.view, value, active, available };
      this.render();
    }
  }

  async load() {
    if (!this._hass || this.loading) return;
    this.loading = true;
    try {
      this.view = await this._hass.callWS({ type: "ha_dial/view", device: this.config.device });
      this.render();
    } finally {
      this.loading = false;
    }
  }

  async input(action, item) {
    if (!this._hass) return;
    this.view = await this._hass.callWS({
      type: "ha_dial/input",
      device: this.config.device,
      action,
      ...(item ? { item } : {}),
    });
    this.render();
  }

  render() {
    const dial = this.shadowRoot?.querySelector(".dial");
    if (!dial) return;
    const view = this.view || {
      kind: "menu",
      title: "HA Dial",
      selected: 0,
      back: false,
      items: [
        { id: "lights", label: "Lights", icon: "mdi:lightbulb" },
      ],
    };
    const items = view.items || [];
    const radial = items.map((item, index) => {
      const angle = -90 + (360 * index) / Math.max(items.length, 1);
      const x = 50 + Math.cos((angle * Math.PI) / 180) * 38;
      const y = 50 + Math.sin((angle * Math.PI) / 180) * 38;
      const selected = index === view.selected ? " selected" : "";
      return `<button class="item${selected}" style="left:${x}%;top:${y}%" data-action="touch" data-item="${escapeHtml(item.id)}" aria-label="${escapeHtml(item.label)}"><span>${ICONS[item.icon] || "•"}</span><small>${escapeHtml(item.label)}</small></button>`;
    }).join("");
    const centreAction = view.back ? "back" : "press";
    const centreIcon = view.back ? "‹" : (ICONS[view.icon] || "●");
    const selectedLabel = view.kind === "control" && view.available === false
      ? "Unavailable"
      : view.kind === "control" && view.value != null
      ? `${view.value}${view.unit || ""}`
      : items[view.selected]?.label || view.profile || "Turn to choose";
    dial.innerHTML = `<div class="face"><div class="title">${escapeHtml(view.title)}</div>${radial}<button class="centre" data-action="${centreAction}" aria-label="${view.back ? "Back" : "Press"}"><b>${centreIcon}</b><span>${escapeHtml(selectedLabel)}</span></button><div class="notch"></div></div>`;
  }

  getCardSize() { return 5; }
  static getStubConfig() { return { device: "preview" }; }

  static styles = `
    ha-card { overflow:hidden; background:radial-gradient(circle at 50% 24%,#3d4248,#16181b 70%); }
    .stage { min-height:390px; display:grid; place-items:center; padding:22px; box-sizing:border-box; }
    .dial { width:min(78vw,310px); aspect-ratio:1; border-radius:50%; padding:12px; background:linear-gradient(135deg,#ff9d32,#ee5b12 52%,#9f2e08); box-shadow:0 18px 35px #0009,0 0 0 3px #632406,inset 0 2px 4px #ffd49a; box-sizing:border-box; }
    .face { position:relative; width:100%; height:100%; border-radius:50%; overflow:hidden; background:radial-gradient(circle at 45% 38%,#303238 0,#111215 56%,#050505 100%); box-shadow:inset 0 0 0 4px #060606,inset 0 0 28px #000; color:#f7f4ef; }
    .title { position:absolute; z-index:2; top:18%; left:25%; width:50%; text-align:center; font:600 15px/1.2 system-ui,sans-serif; color:#f3a15e; letter-spacing:.08em; text-transform:uppercase; }
    .item { position:absolute; z-index:3; width:58px; height:58px; translate:-50% -50%; border:1px solid #ffffff20; border-radius:50%; background:#24272dcc; color:white; display:grid; place-items:center; cursor:pointer; box-shadow:0 3px 9px #0009; }
    .item span { font-size:23px; line-height:1; pointer-events:none; }
    .item small { position:absolute; top:61px; white-space:nowrap; color:#bbb; font:11px system-ui,sans-serif; pointer-events:none; }
    .item.selected { background:#e96821; border-color:#ffbc75; box-shadow:0 0 0 3px #ff7a2c44,0 5px 12px #000b; transform:scale(1.08); }
    .item.selected small { color:#fff; }
    .centre { position:absolute; z-index:4; left:50%; top:52%; translate:-50% -50%; width:112px; height:112px; border:0; border-radius:50%; background:radial-gradient(circle at 40% 32%,#34373c,#17191c 65%); color:#f7f4ef; box-shadow:inset 0 0 0 1px #ffffff18,0 5px 14px #000b; cursor:pointer; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:7px; }
    .centre b { color:#f47a28; font:300 45px/30px system-ui,sans-serif; }
    .centre span { max-width:90px; font:600 13px/1.15 system-ui,sans-serif; }
    .notch { position:absolute; bottom:3px; left:50%; translate:-50%; width:8px; height:19px; border-radius:5px; background:#ff862f; box-shadow:0 0 10px #f66; }
    .controls { display:flex; gap:16px; margin-top:22px; }
    .controls button { width:52px; height:42px; border:1px solid #ffffff20; border-radius:21px; background:#24272d; color:#f47a28; font:24px system-ui,sans-serif; cursor:pointer; box-shadow:0 4px 10px #0006; }
    button:focus-visible { outline:3px solid #65bfff; outline-offset:3px; }
  `;
}

customElements.define("ha-dial-card", HaDialCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "ha-dial-card", name: "HA Dial", description: "HA-managed Dial navigation and preview" });

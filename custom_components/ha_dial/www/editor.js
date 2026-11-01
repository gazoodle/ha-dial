export function defaultConfig() {
  return { theme: "ember", pages: [{ id: "home", title: "Home", parent: "", lights: [] }], template: "" };
}

// What the panel's editor builds on: a page tree in memory, and moving things around in it.
export class PagesEditor extends HTMLElement {
  setConfig(config) {
    this.config = { ...defaultConfig(), ...config };
    this.render();
  }

  set hass(hass) { this._hass = hass; this.render(); }

  changed(config) {
    this.config = config;
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config }, bubbles: true, composed: true,
    }));
  }

  entities(pageId) {
    const page = this.config.pages.find((page) => page.id === pageId);
    return [...(page?.lights || []), ...(page?.entities || [])];
  }

  setEntities(pageId, entities) {
    this.changed({ ...this.config, pages: this.config.pages.map((page) => {
      if (page.id !== pageId) return page;
      const updated = { ...page, entities }; delete updated.lights; return updated;
    }) });
    this.renderTree();
  }

  move(source, target, position) {
    if (source.kind !== target.kind || source.id === target.id) return false;
    if (source.kind === "entity") {
      if (source.page !== target.page) return false;
      const all = this.entities(source.page);
      const moved = all.find((item) => (typeof item === 'string' ? item : item.entity_id) === source.id);
      const entities = all.filter((item) => (typeof item === 'string' ? item : item.entity_id) !== source.id);
      const index = entities.findIndex((item) => (typeof item === 'string' ? item : item.entity_id) === target.id);
      if (index < 0) return false;
      entities.splice(index + (position === "after" ? 1 : 0), 0, moved);
      this.setEntities(source.page, entities);
    } else {
      const pages = this.config.pages, page = pages.find((page) => page.id === source.id), destination = pages.find((page) => page.id === target.id);
      if (!page?.parent || !destination) return false;
      const parent = position === "inside" ? destination.id : destination.parent;
      if (!parent) return false;
      const seen = new Set([page.id]);
      for (let ancestor = parent; ancestor; ancestor = pages.find((page) => page.id === ancestor)?.parent) {
        if (seen.has(ancestor)) return false;
        seen.add(ancestor);
      }
      const updated = pages.filter((candidate) => candidate.id !== page.id);
      updated.splice(updated.findIndex((candidate) => candidate.id === destination.id) + (position === "before" ? 0 : 1), 0, { ...page, parent });
      this.changed({ ...this.config, pages: updated }); this.renderTree();
    }
    this.querySelector("[role=status]").textContent = "Moved " + source.id;
    this.querySelector(`[data-kind="${source.kind}"][data-id="${CSS.escape(source.id)}"] .grab`)?.focus();
    return true;
  }

  handle(source, label) {
    const handle = document.createElement("button"); handle.type = "button"; handle.className = "grab";
    handle.textContent = "⠿"; handle.setAttribute("aria-label", label); handle.title = label;
    handle.addEventListener("click", (event) => { event.preventDefault(); event.stopPropagation(); });
    handle.addEventListener("keydown", (event) => {
      const page = this.config.pages.find((page) => page.id === (source.kind === "page" ? source.id : source.page));
      const siblings = source.kind === "page" ? this.config.pages.filter((candidate) => candidate.parent === page.parent).map((candidate) => candidate.id) : this.entities(source.page).map((item) => typeof item === "string" ? item : item.entity_id);
      const index = siblings.indexOf(source.id);
      let target, position;
      if (event.key === "ArrowUp") { target = siblings[index - 1]; position = "before"; }
      if (event.key === "ArrowDown") { target = siblings[index + 1]; position = "after"; }
      if (source.kind === "page" && event.key === "ArrowRight") { target = siblings[index - 1]; position = "inside"; }
      if (source.kind === "page" && event.key === "ArrowLeft") { target = page.parent; position = "after"; }
      if (position) {
        event.preventDefault(); event.stopPropagation();
        if (target) this.move(source, { ...source, id: target }, position);
      }
    });
    handle.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      event.preventDefault(); event.stopPropagation();
      handle.focus({ preventScroll: true });
      handle.setPointerCapture(event.pointerId);
      const tree = this.querySelector(".tree"); tree.classList.add("dragging");
      let drop, position;
      const clear = () => { drop?.classList.remove("drop-before", "drop-inside", "drop-after"); };
      const move = (next) => {
        clear();
        // HA embeds the editor in shadow roots; document hit-testing stops at their hosts.
        let root = this.getRootNode(), hit;
        while (root?.elementFromPoint) {
          const candidate = root.elementFromPoint(next.clientX, next.clientY);
          if (!candidate || candidate === hit) break;
          hit = candidate; root = candidate.shadowRoot;
        }
        drop = hit?.closest("[data-kind]");
        if (!drop || !this.contains(drop) || drop.dataset.kind !== source.kind) { drop = undefined; return; }
        const rect = drop.getBoundingClientRect(), offset = (next.clientY - rect.top) / rect.height;
        position = offset < .3 ? "before" : offset > .7 ? "after" : source.kind === "page" ? "inside" : "after";
        drop.classList.add("drop-" + position);
      };
      const end = (next) => {
        clear(); tree.classList.remove("dragging");
        handle.removeEventListener("pointermove", move); handle.removeEventListener("pointerup", end); handle.removeEventListener("pointercancel", end); handle.removeEventListener("lostpointercapture", end);
        if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
        if (next.type === "pointerup" && drop) this.move(source, { ...drop.dataset }, position);
      };
      handle.addEventListener("pointermove", move); handle.addEventListener("pointerup", end); handle.addEventListener("pointercancel", end); handle.addEventListener("lostpointercapture", end);
    });
    return handle;
  }
}

// A dashboard card views and operates a Dial, so the choices are which one, and whether to share its
// screen. Saving this also clears anything an older card still holds, such as its own copy of the pages.
class HaDialCardEditor extends HTMLElement {
  setConfig(config) {
    this.config = config;
    this.render();
  }

  set hass(hass) { this._hass = hass; this.render(); }

  render() {
    if (!this.config || !this._hass) return;
    if (!this.initialised) {
      this.initialised = true;
      this.innerHTML = `<ha-form class="settings"></ha-form><p class="hint">Pages are edited in the HA Dial panel. Operating this card operates the real Dial.</p>`;
      const form = this.querySelector(".settings");
      form.computeLabel = (field) => ({ device: "Dial", follow: "Follow the Dial's screen" })[field.name];
      form.computeHelper = (field) => field.name === "follow" ? "On, this card and the Dial show the same screen. Off, this card browses on its own, and still operates real devices." : undefined;
      form.addEventListener("value-changed", (event) => {
        event.stopPropagation();
        const config = { ...(this.config.type ? { type: this.config.type } : {}), device: event.detail.value.device, ...(event.detail.value.follow === false ? { follow: false } : {}) };
        this.config = config;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
      });
    }
    const form = this.querySelector(".settings"), services = this._hass.services?.esphome, device = this.config.device === "preview" ? "" : this.config.device || "";
    form.hass = this._hass; form.data = { device, follow: this.config.follow !== false };
    if (!form.schema || services !== this.deviceServices || device !== this.deviceSelection) {
      const selected = device.replaceAll("-", "_");
      const devices = dialNames(this._hass);
      const options = devices.map((name) => ({ value: name === selected ? device : name, label: name.replaceAll("_", "-") }));
      if (selected && !devices.includes(selected)) options.push({ value: device, label: `${device} (unavailable)` });
      form.schema = [{ name: "device", required: true, selector: { select: { mode: "dropdown", options } } }, { name: "follow", selector: { boolean: {} } }];
      this.deviceServices = services;
      this.deviceSelection = device;
    }
  }
}

export function dialNames(hass) {
  const suffix = "_ha_dial_show_view";
  return Object.keys(hass?.services?.esphome || {}).filter((name) => name.endsWith(suffix))
    .map((name) => name.slice(0, -suffix.length)).filter((name) => /^[a-z0-9_]{1,64}$/.test(name) && name !== "preview" && !name.startsWith("preview_")).sort();
}

customElements.define("ha-dial-card-editor", HaDialCardEditor);

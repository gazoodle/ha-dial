import { openOptions } from './editor/options.js';
import { DOMAINS } from './editor/catalogue.js';

export function defaultConfig() {
  return { device: "preview", zoom: 100, theme: "ember", pages: [{ id: "home", title: "Home", parent: "", lights: [] }], template: "" };
}

const THEMES = ["ember", "verdant", "cobalt", "rose", "acid", "alloy"];
const THEME_SELECTOR = { select: { options: THEMES } };

class HaDialEditor extends HTMLElement {
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

  addPage(parent) {
    const id = "page_" + Array.from(crypto.getRandomValues(new Uint32Array(2))).join("_");
    this.changed({ ...this.config, pages: [...this.config.pages, { id, title: "New page", parent, entities: [] }] });
    this.renderTree(parent);
  }

  render() {
    if (!this.config || !this._hass) return;
    if (!this.initialised) {
      this.initialised = true;
      this.innerHTML = `<style>
        .options-dialog{color:var(--primary-text-color);background:var(--card-background-color,#1c1c1c);border:1px solid var(--divider-color);border-radius:12px;max-width:600px;width:calc(100vw - 48px);max-height:85vh;box-sizing:border-box;overflow:auto}
        .options-dialog::backdrop{background:#0009}.options-dialog textarea{box-sizing:border-box;width:100%;font:inherit;color:inherit;background:var(--secondary-background-color);padding:12px}.options-dialog [role=alert]{color:var(--error-color);overflow-wrap:anywhere}
        details{margin:12px 0}summary{cursor:pointer;padding:10px 0}
        .children{padding-left:16px;border-left:2px solid var(--divider-color,#8884)}
        button{font:inherit;padding:8px 12px;margin:8px 8px 8px 0;cursor:pointer;color:var(--primary-text-color);background:var(--secondary-background-color);border:1px solid var(--divider-color);border-radius:8px}
        .hint{color:var(--secondary-text-color);line-height:1.4}
        .grab{cursor:grab;touch-action:none;user-select:none;-webkit-user-select:none;border:0;background:transparent;padding:8px;margin:0;min-width:44px;min-height:44px}
        .tree.dragging,.tree.dragging *{user-select:none;-webkit-user-select:none;cursor:grabbing}
        .entity{display:flex;align-items:center;gap:8px}.entity span{flex:1;overflow-wrap:anywhere}
        .drop-before{box-shadow:0 -3px var(--primary-color)}.drop-after{box-shadow:0 3px var(--primary-color)}
        .drop-inside{outline:2px solid var(--primary-color);border-radius:8px}
        .sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
        button:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
      </style><ha-form class="settings"></ha-form><p class="hint">Add subpages to build your tree. Add controls or read-only entities on any page. Open Appearance & conditions or Edit for detailed options. Changes stay local until you save.</p><p class="hint">Drag a page above/below another to reorder, or onto its title to nest it. On a handle, arrow keys move; Left/Right change nesting.</p><p class="sr-only" role="status"></p><div class="tree"></div><details><summary>Advanced Jinja template</summary><ha-form class="advanced"></ha-form></details>`;
      this.querySelector(".settings").addEventListener("value-changed", (event) => {
        event.stopPropagation(); this.changed({ ...this.config, ...event.detail.value });
      });
      this.querySelector(".advanced").addEventListener("value-changed", (event) => {
        event.stopPropagation(); this.changed({ ...this.config, ...event.detail.value });
      });
    }
    const settings = this.querySelector(".settings"), advanced = this.querySelector(".advanced");
    for (const form of [settings, advanced]) {
      form.hass = this._hass; form.data = this.config;
      form.computeLabel = (field) => ({ device: "Dial device", theme: "Default page theme", zoom: "Preview zoom (%)", template: "Template" })[field.name] || field.name;
      form.computeHelper = (field) => ({ device: "Choose an installed Dial, or Preview for local simulation. Add new Dials through the ESPHome integration.", zoom: "Enlarge the dashboard preview within the available width. The device screen is unchanged.", template: "Return a tree object or JSON. Jinja macros and HA custom_templates are supported; pages and theme are available as variables." })[field.name];
    }
    const services = this._hass.services?.esphome;
    if (!this.settingsSchema || services !== this.deviceServices || this.config.device !== this.deviceSelection) {
      const suffix = "_ha_dial_show_view";
      const selected = this.config.device.replaceAll("-", "_");
      const devices = Object.keys(services || {}).filter((name) => name.endsWith(suffix))
        .map((name) => name.slice(0, -suffix.length)).filter((device) => /^[a-z0-9_]{1,64}$/.test(device) && device !== "preview" && !device.startsWith("preview_")).sort();
      const options = [{ value: "preview", label: "Preview" }, ...devices.map((device) => ({
        value: device === selected ? this.config.device : device, label: device.replaceAll("_", "-"),
      }))];
      if (selected !== "preview" && !devices.includes(selected))
        options.push({ value: this.config.device, label: `${this.config.device} (unavailable)` });
      this.settingsSchema = [
        { name: "device", selector: { select: { mode: "dropdown", options } } },
        { name: "theme", selector: THEME_SELECTOR },
        { name: "zoom", selector: { number: { min: 100, max: 300, step: 25, mode: "slider" } } },
      ];
      this.deviceServices = services;
      this.deviceSelection = this.config.device;
    }
    settings.schema = this.settingsSchema;
    advanced.schema = [{ name: "template", selector: { template: {} } }];
    const key = this.config.pages === this.treePages ? this.treeKey : JSON.stringify(this.config.pages);
    if (key !== this.treeKey) this.renderTree();
    else for (const form of this.querySelectorAll(".tree ha-form")) form.hass = this._hass;
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

  renderTree(openPage) {
    const tree = this.querySelector(".tree");
    const pages = this.config.pages;
    const byId = new Map(pages.map((page) => [page.id, page]));
    const childrenByParent = new Map();
    for (const page of pages) {
      if (!childrenByParent.has(page.parent)) childrenByParent.set(page.parent, []);
      childrenByParent.get(page.parent).push(page);
    }
    this.openPages ||= new Set(pages.filter((page) => !page.parent).map((page) => page.id));
    for (const node of tree.querySelectorAll("details")) {
      if (node.open) this.openPages.add(node.dataset.id);
      else this.openPages.delete(node.dataset.id);
    }
    if (openPage) this.openPages.add(openPage);
    for (const id of this.openPages) if (!byId.has(id)) this.openPages.delete(id);
    tree.replaceChildren();
    const button = (label, callback) => {
      const node = document.createElement("button"); node.type = "button";
      node.textContent = label; node.addEventListener("click", callback); return node;
    };
    const rendered = new Set();
    const row = (page, container) => {
      page = byId.get(page.id);
      if (rendered.has(page.id)) return;
      rendered.add(page.id);
      const details = document.createElement("details"), summary = document.createElement("summary");
      details.dataset.id = page.id; details.open = this.openPages.has(page.id);
      summary.textContent = page.title || "Untitled page";
      summary.dataset.kind = "page"; summary.dataset.id = page.id;
      if (page.parent) summary.append(this.handle({ kind: "page", id: page.id }, "Move " + page.title));
      details.append(summary);
      const body = document.createElement("div");
      const populate = () => {
        const form = document.createElement("ha-form");
        form.hass = this._hass; form.data = { ...page, entities: [...(page.lights || []), ...(page.entities || [])] };
        form.schema = [
          { name: "title", required: true, selector: { text: {} } },
        ];
        form.computeLabel = (field) => ({ title: "Page title", parent: "Parent page", theme: "Page theme", entities: "Controls" })[field.name];
        form.computeHelper = (field) => field.name === "theme" ? "Leave empty to use the default theme." : undefined;
        form.addEventListener("value-changed", (event) => {
          event.stopPropagation();
          const updated = { ...page, ...event.detail.value }; delete updated.lights;
          if (!updated.theme) delete updated.theme;
          this.changed({ ...this.config, pages: this.config.pages.map((item) => item.id === page.id ? updated : item) });
          page = updated;
          byId.set(page.id, updated);
          summary.firstChild.textContent = updated.title || "Untitled page";
          this.treeKey = JSON.stringify(this.config.pages);
          this.treePages = this.config.pages;
        });
        const controls = document.createElement("div");
        for (const entry of [...(page.lights || []), ...(page.entities || [])]) {
          const entity = typeof entry === "string" ? entry : entry.entity_id;
          const control = document.createElement("div"); control.className = "entity";
          control.dataset.kind = "entity"; control.dataset.page = page.id; control.dataset.id = entity;
          const label = document.createElement("span"); label.textContent = entry.label || this._hass.states?.[entity]?.attributes.friendly_name || entity;
          control.append(this.handle({ kind: "entity", page: page.id, id: entity }, "Move " + label.textContent), label,
            button("Edit", () => openOptions(this, page.id, entity)),
            button("Remove", () => this.setEntities(page.id, this.entities(page.id).filter((item) => (typeof item === "string" ? item : item.entity_id) !== entity))));
          controls.append(control);
        }
        const add = document.createElement("ha-form");
        add.hass = this._hass; add.data = {};
        add.schema = [{ name: "entity", selector: { entity: { filter: { domain: DOMAINS } } } }];
        add.computeLabel = () => "Add control";
        add.addEventListener("value-changed", (event) => {
          event.stopPropagation();
          const entity = event.detail.value.entity;
          if (entity && !this.entities(page.id).some((item) => (typeof item === "string" ? item : item.entity_id) === entity)) this.setEntities(page.id, [...this.entities(page.id), entity]);
        });
        body.append(form, button("Appearance & conditions", () => openOptions(this, page.id)), controls, add, button("Add subpage", () => { details.open = true; this.addPage(page.id); }));
        if (page.parent) body.append(button("Remove page", () => {
          const currentPages = this.config.pages;
          const children = currentPages.filter((candidate) => candidate.parent === page.id);
          this.changed({ ...this.config, pages: currentPages.filter((candidate) => candidate.id !== page.id).map((candidate) => children.includes(candidate) ? { ...candidate, parent: page.parent } : candidate) });
          this.renderTree();
        }));
        const children = document.createElement("div"); children.className = "children";
        for (const child of childrenByParent.get(page.id) || []) row(child, children);
        body.append(children);
        details.append(body);
      };
      details.addEventListener("toggle", () => {
        if (!tree.contains(details)) return;
        if (details.open) {
          this.openPages.add(page.id);
          if (!body.children.length) populate();
        } else {
          this.openPages.delete(page.id);
          for (const nested of body.querySelectorAll("details")) rendered.delete(nested.dataset.id);
          body.replaceChildren();
          body.remove();
        }
      });
      container.append(details);
      if (details.open) populate();
    };
    if (!pages.length) tree.append(button("Add Home page", () => {
      this.changed({ ...this.config, pages: defaultConfig().pages });
      this.renderTree();
    }));
    // Find disconnected roots without mounting descendants of collapsed pages.
    const reachable = new Set();
    const roots = [];
    const visit = (page) => {
      if (reachable.has(page.id)) return;
      reachable.add(page.id);
      for (const child of childrenByParent.get(page.id) || []) visit(child);
    };
    for (const page of pages) if (!page.parent || !byId.has(page.parent)) { roots.push(page); visit(page); }
    for (const page of pages) if (!reachable.has(page.id)) { roots.push(page); visit(page); }
    for (const page of roots) row(page, tree);
    this.treeKey = JSON.stringify(pages);
    this.treePages = pages;
  }
}

customElements.define("ha-dial-card-editor", HaDialEditor);

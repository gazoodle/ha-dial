import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

class Element {
  constructor(tag = "div") { this.tag = tag; this.isConnected = false; this.elements = {}; this.children = []; this.dataset = {}; this.events = {}; this.classes = new Set(); this.classList = { add: (...names) => names.forEach((name) => this.classes.add(name)), remove: (...names) => names.forEach((name) => this.classes.delete(name)), contains: (name) => this.classes.has(name) }; }
  set textContent(value) { this.firstChild = { textContent: value }; }
  get textContent() { return this.firstChild?.textContent; }
  focus() {}
  set innerHTML(value) { this.html = value; }
  get innerHTML() { return this.html; }
  addEventListener(name, callback) { this.events[name] = callback; }
  removeEventListener(name, callback) { if (this.events[name] === callback) delete this.events[name]; }
  setPointerCapture(id) { this.pointer = id; }
  hasPointerCapture(id) { return this.pointer === id; }
  releasePointerCapture() { this.pointer = undefined; }
  setAttribute(name, value) { this[name] = value; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren() { this.children = []; }
  querySelectorAll(selector) {
    const result = [];
    const visit = (node) => {
      if ((selector === "details[open]" && node.tag === "details" && node.open) || (selector === "ha-form" && node.tag === "ha-form")) result.push(node);
      for (const child of node.children) visit(child);
    };
    visit(this); return result;
  }
  querySelector(selector) { return this.elements[selector] ||= new Element(); }
  getRootNode() { return {}; }
  attachShadow() { this.shadowRoot = new Element(); }
}
const classes = new Map();
globalThis.HTMLElement = Element;
globalThis.document = { createElement: (tag) => new Element(tag) };
globalThis.window = {};
globalThis.CSS = { escape: (value) => value };
globalThis.CustomEvent = class { constructor(name, properties) { this.type = name; Object.assign(this, properties); } };
Element.prototype.dispatchEvent = function(event) { this.lastEvent = event; };
globalThis.customElements = { define: (name, type) => classes.set(name, type) };
globalThis.renderScene = () => {};
vm.runInThisContext(fs.readFileSync("custom_components/ha_dial/www/editor.js", "utf8").replace(/^export /gm, ""));
vm.runInThisContext(fs.readFileSync("custom_components/ha_dial/www/ha-dial-card.js", "utf8").replace(/^import .*;\n/gm, ""));
const Editor = classes.get("ha-dial-card-editor"), Card = classes.get("ha-dial-card");
const editor = new Editor(); editor.setConfig({}); editor.hass = {};
assert.equal(editor.config.pages.length, 1);
editor.addPage("home");
const child = editor.config.pages[1];
assert.equal(child.parent, "home");
assert(child.id.startsWith("page_"));
editor.addPage(child.id);
const treeForms = editor.querySelector(".tree").querySelectorAll("ha-form");
assert.equal(treeForms.length, 6);
assert(treeForms.every((form) => !form.schema.some((field) => field.name === "parent")));
assert.deepEqual(treeForms[1].schema[0].selector.entity.filter.domain, ["light", "switch", "cover"]);
const grandchild = editor.config.pages[2];
assert.equal(editor.move({kind:"page",id:child.id}, {kind:"page",id:grandchild.id}, "inside"), false, "reject cycles");
assert.equal(editor.move({kind:"page",id:grandchild.id}, {kind:"page",id:child.id}, "after"), true);
assert.equal(editor.config.pages.find((page) => page.id === grandchild.id).parent, "home");
assert.equal(editor.move({kind:"page",id:grandchild.id}, {kind:"page",id:child.id}, "inside"), true);
editor.setEntities(child.id, ["light.demo", "cover.demo", "switch.demo"]);
assert.equal(editor.move({kind:"entity",page:child.id,id:"switch.demo"}, {kind:"entity",page:child.id,id:"light.demo"}, "before"), true);
assert.deepEqual(editor.entities(child.id), ["switch.demo", "light.demo", "cover.demo"]);
assert.equal(editor.move({kind:"entity",page:child.id,id:"switch.demo"}, {kind:"entity",page:"home",id:"cover.demo"}, "after"), false);
// Exercise pointer handlers in an HA-style shadow root, rather than only the move model.
const drop = editor.querySelector(".tree").children[0].children[0];
drop.closest = () => drop;
drop.getBoundingClientRect = () => ({top: 0, height: 40});
const host = {shadowRoot: {elementFromPoint: () => drop}};
editor.getRootNode = () => ({elementFromPoint: () => host});
editor.contains = (node) => node === drop;
document.elementFromPoint = () => { throw new Error("document hit-testing cannot reach the editor"); };
const grip = editor.handle({kind:"page",id:grandchild.id}, "Move child");
let prevented = false;
grip.events.pointerdown({button:0,pointerId:7,preventDefault:()=>{prevented=true},stopPropagation(){}});
assert(prevented, "pointer-down must prevent native text selection");
assert(editor.querySelector(".tree").classList.contains("dragging"));
grip.events.pointermove({clientX:20,clientY:20});
assert(drop.classList.contains("drop-inside"));
grip.events.pointerup({type:"pointerup"});
assert.equal(editor.config.pages.find((page)=>page.id===grandchild.id).parent,"home");
assert(!editor.querySelector(".tree").classList.contains("dragging"));
assert.equal(grip.pointer, undefined);
assert.equal(grip.events.pointermove, undefined);
editor.move({kind:"page",id:grandchild.id},{kind:"page",id:child.id},"inside");
const cancelled = editor.handle({kind:"page",id:grandchild.id}, "Move child");
const beforeCancel = JSON.stringify(editor.config);
cancelled.events.pointerdown({button:0,pointerId:8,preventDefault(){},stopPropagation(){}});
cancelled.events.pointermove({clientX:20,clientY:20});
cancelled.events.pointercancel({type:"pointercancel"});
assert.equal(JSON.stringify(editor.config),beforeCancel);
assert(!editor.querySelector(".tree").classList.contains("dragging"));
assert.equal(window.customCards[0].preview, true);
assert(Card.styles.includes(".frame"));
// Removing a page preserves its children by moving them up one level.
const childRow = editor.querySelector(".tree").children[0].children.at(-1).children[0];
childRow.children.find((node) => node.textContent === "Remove page").events.click();
assert.equal(editor.config.pages.length, 2);
assert.equal(editor.config.pages[1].parent, "home");

const card = new Card(); card.setConfig({ device: "demo_dial" });
assert(!card.shadowRoot.innerHTML.includes('class="controls"'));
assert(card.shadowRoot.innerHTML.includes('class="click-chip"'));
assert(card.shadowRoot.innerHTML.includes('<svg'));
card.parentNode = { tagName: "HUI-CARD", preview: true, parentNode: { tagName: "HUI-DIALOG-EDIT-CARD" } };
assert(card._device().startsWith("preview_"));
assert.notEqual(card._device(), new Card().draftDevice);
card.parentNode = { tagName: "HUI-CARD-EDIT-MODE" };
assert.equal(card._device(), "demo_dial");
card.parentNode = { tagName: "HUI-DIALOG-CREATE-CARD" };
assert(card._device().startsWith("preview_"));
const calls = [];
let subscriber, released = 0, revision = 0;
const result = (label = "Home") => ({ scene: { label }, revision: ++revision, deployment: "preview" });
card.isConnected = true;
card.hass = {
  callWS: async (request) => { calls.push(request); return result(); },
  connection: { subscribeMessage: async (callback) => { subscriber = callback; return () => released++; } },
};
const tick = () => new Promise((resolve) => setImmediate(resolve));
while (card.loading) await tick();
assert.equal(calls.length, 1);
assert.equal(calls[0].device, card.draftDevice);
for (let n = 0; n < 20; n++) card.hass = card._hass;
while (card.loading) await tick();
assert.equal(calls.length, 1, "unrelated HA updates must not poll scenes");
subscriber(result("Fresh"));
card.accept({ scene: { label: "Stale" }, revision: 0 });
assert.equal(card.scene.label, "Fresh");
await Promise.all([card.input("rotate_right"), card.input("press")]);
assert.deepEqual(calls.slice(1).map((request) => request.action), ["rotate_right", "press"]);
card.disconnectedCallback();
assert.equal(released, 1);

const racing = new Card(); racing.setConfig({ device: "preview", pages: [{ id: "home", title: "Old" }] });
racing.isConnected = true;
const pending = [];
racing.hass = { callWS: (request) => new Promise((resolve) => pending.push({ request, resolve })),
  connection: { subscribeMessage: async () => () => {} } };
racing.setConfig({ device: "preview", pages: [{ id: "home", title: "New" }] });
pending[0].resolve(result("Old"));
while (pending.length < 2) await tick();
assert.equal(pending[1].request.definition.pages[0].title, "New");
pending[1].resolve(result("New"));
while (racing.loading) await tick();
assert.equal(racing.scene.label, "New");
console.log("Editor, draft isolation, push updates, ordering and config race checks passed");

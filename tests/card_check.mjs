import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { webcrypto } from "node:crypto";

// Ordinary HTTP exposes getRandomValues but not randomUUID.
Object.defineProperty(globalThis, "crypto", { configurable: true, value: { getRandomValues: webcrypto.getRandomValues.bind(webcrypto) } });

class Element {
  constructor(tag = "div") { this.style = { setProperty(name, value) { this[name] = value; } }; this.tag = tag; this.isConnected = false; this.elements = {}; this.children = []; this.dataset = {}; this.events = {}; this.classes = new Set(); this.classList = { add: (...names) => names.forEach((name) => this.classes.add(name)), remove: (...names) => names.forEach((name) => this.classes.delete(name)), contains: (name) => this.classes.has(name) }; }
  set textContent(value) { this.firstChild = { textContent: value }; }
  get textContent() { return this.firstChild?.textContent; }
  focus() {}
  showModal() { this.open = true; }
  close() { this.open = false; }
  set innerHTML(value) { this.html = value; }
  get innerHTML() { return this.html; }
  addEventListener(name, callback) { this.events[name] = callback; }
  removeEventListener(name, callback) { if (this.events[name] === callback) delete this.events[name]; }
  setPointerCapture(id) { this.pointer = id; }
  hasPointerCapture(id) { return this.pointer === id; }
  releasePointerCapture() { this.pointer = undefined; }
  setAttribute(name, value) { this[name] = value; }
  append(...nodes) { for (const node of nodes) { node.parentNode = this; this.children.push(node); } }
  prepend(node) { node.parentNode = this; this.children.unshift(node); }
  contains(node) { return this === node || this.children.some((child) => child.contains(node)); }
  remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter((node) => node !== this); this.parentNode = undefined; }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  click() { this.events.click?.(); }
  querySelectorAll(selector) {
    if (selector === ".tree ha-form") return this.querySelector(".tree").querySelectorAll("ha-form");
    const result = [];
    const visit = (node) => {
      if (((selector === "details" || selector === "details[open]" && node.open) && node.tag === "details") || (selector === "ha-form" && node.tag === "ha-form")) result.push(node);
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
globalThis.customElements = { define: (name, type) => classes.set(name, type), get: (name) => classes.get(name) };
globalThis.renderScene = () => {};
for (const path of ['editor/catalogue.js','editor/conditions.js','editor/options.js','editor.js']) vm.runInThisContext(fs.readFileSync(`custom_components/ha_dial/www/${path}`, 'utf8').replace(/^import .*;\n/gm, '').replace(/^export /gm,''));
vm.runInThisContext(fs.readFileSync("custom_components/ha_dial/www/ha-dial-card.js", "utf8").replace(/^import .*;\n/gm, ""));
vm.runInThisContext(fs.readFileSync("custom_components/ha_dial/www/panel-editor.js", "utf8").replace(/^import .*;\n/gm, ""));
const Editor = classes.get("ha-dial-card-editor"), Card = classes.get("ha-dial-card");
const Workspace = classes.get("ha-dial-panel-editor");
let editedConditions;
const conditionUI = conditionsEditor({}, [], value => { editedConditions = value; });
const addCondition = conditionUI.children[2];
addCondition.children[1].children.find(node => node.textContent === 'Time').events.click();
assert.equal(editedConditions[0].condition, 'time');
const timeRow = conditionUI.children[2];
timeRow.children[1].events['value-changed']({stopPropagation(){},detail:{value:{after:'22:00:00',before:'06:00:00',weekday:['fri']}}});
assert.equal(editedConditions[0].before, '06:00:00');
assert(timeRow.children[0].children[1].textContent.includes('22:00:00'));
let notifyCondition, stopped = false;
const liveUI = conditionsEditor({callWS: async () => '{{ true }}', connection: {subscribeMessage: async callback => { notifyCondition = callback; return () => { stopped = true; }; }}}, [{condition:'state',entity_id:'select.mode',state:'Home'}], () => {});
await new Promise(resolve => setTimeout(resolve,0));
notifyCondition({result:'false'});
assert.equal(liveUI.children[1].textContent, 'Currently hidden');
assert.equal(liveUI.children[2].children[0].children[2].textContent, 'Does not pass');
notifyCondition({result:'true'});
assert.equal(liveUI.children[1].textContent, 'Currently visible');
liveUI.destroy(); assert(stopped);
const workspace = new Workspace(); workspace.setConfig({}); workspace.hass = {states:{}};
assert.equal(workspace.selectedPage, 'home');
workspace.addPage('home');
assert.equal(workspace.config.pages.length, 2);
assert.equal(workspace.config.pages[1].parent, 'home');
assert.equal(workspace.selectedPage, workspace.config.pages[1].id);
workspace.setEntities(workspace.selectedPage, ['light.demo']);
assert.deepEqual(workspace.entities(workspace.selectedPage), ['light.demo']);
const removal = new Workspace(); removal.setConfig({pages:[{id:'home',title:'Home'},{id:'parent',title:'Parent',parent:'home'},{id:'child',title:'Child',parent:'parent'},{id:'grandchild',title:'Grandchild',parent:'child'}]}); removal.hass = {states:{}}; removal.renderTree = () => {};
removal.removePage(removal.config.pages[1]);
let removeDialog = removal.children.at(-1), options = removeDialog.children[1].children[1].children;
assert(options[2].children[1].children[0].textContent.includes('2 subpages'));
removeDialog.children[2].children[0].events.click();
assert.equal(removal.config.pages.length, 4, 'cancel leaves the draft intact');
removal.removePage(removal.config.pages[1]); removeDialog = removal.children.at(-1);
removeDialog.children[2].children[1].events.click();
assert.deepEqual(removal.config.pages.map(page=>[page.id,page.parent]), [['home',undefined],['child','home'],['grandchild','child']]);
removal.setConfig({pages:[{id:'home',title:'Home'},{id:'parent',title:'Parent',parent:'home'},{id:'child',title:'Child',parent:'parent'},{id:'grandchild',title:'Grandchild',parent:'child'}]});
removal.removePage(removal.config.pages[1]); removeDialog = removal.children.at(-1); options = removeDialog.children[1].children[1].children;
options[2].children[0].events.change(); removeDialog.children[2].children[1].events.click();
assert.deepEqual(removal.config.pages.map(page=>page.id), ['home'], 'remove includes nested descendants');
const editor = new Editor(); editor.setConfig({}); editor.hass = {};
assert.equal(editor.config.pages.length, 1);
const deviceOptions = () => editor.querySelector(".settings").schema[0].selector.select.options;
assert.deepEqual(deviceOptions(), [{value:"preview",label:"Preview"}]);
const dialServices = { demo_dial_ha_dial_show_view: {}, other_dial_ha_dial_show_view: {}, unrelated_restart: {} };
editor.hass = { services: { esphome: dialServices } };
assert.deepEqual(deviceOptions(), [
  {value:"preview",label:"Preview"}, {value:"demo_dial",label:"demo-dial"}, {value:"other_dial",label:"other-dial"},
]);
const deviceSchema = editor.querySelector(".settings").schema;
editor.hass = { services: { esphome: dialServices }, states: {} };
assert.equal(editor.querySelector(".settings").schema, deviceSchema, "unrelated state changes do not rebuild the selector");
editor.setConfig({device:"demo-dial"});
assert.equal(deviceOptions()[1].value, "demo-dial", "existing hyphenated device names remain selected");
editor.hass = { services: { esphome: {other_dial_ha_dial_show_view:{}} } };
assert.deepEqual(deviceOptions().at(-1), {value:"demo-dial",label:"demo-dial (unavailable)"});
assert.equal(editor.config.device, "demo-dial", "discovery changes must not retarget the card");
editor.querySelector(".settings").events["value-changed"]({stopPropagation(){},detail:{value:{device:"other_dial"}}});
assert.equal(editor.lastEvent.detail.config.device, "other_dial");
editor.setConfig({});
editor.querySelector(".tree").children[0].children[1].children.find((node) => node.textContent === "Add subpage").events.click();
const child = editor.config.pages[1];
assert.equal(child.parent, "home");
assert(child.id.startsWith("page_"));
assert.equal(editor.lastEvent.detail.config.pages[1].id, child.id);
editor.addPage(child.id);
const treeForms = editor.querySelector(".tree").querySelectorAll("ha-form");
assert.equal(treeForms.length, 4, "a closed grandchild has no controls");
assert(treeForms.every((form) => !form.schema.some((field) => field.name === "parent")));
assert(treeForms[1].schema[0].selector.entity.filter.domain.includes("climate"));
assert(treeForms[1].schema[0].selector.entity.filter.domain.includes("sensor"));
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
const childRow = editor.querySelector(".tree").children[0].children[1].children.at(-1).children[0];
childRow.children[1].children.find((node) => node.textContent === "Remove page").events.click();
assert.equal(editor.config.pages.length, 2);
assert.equal(editor.config.pages[1].parent, "home");

// The complete four-level definition stays data; only expanded pages mount forms.
const large = new Editor();
const pages = [{id:"home",title:"Home",parent:""}];
const branch = (parent, depth) => {
  if (depth === 4) return;
  for (let n = 1; n <= [5,6,5,6][depth]; n++) {
    const id = `${parent}_${n}`;
    pages.push({id,title:id,parent}); branch(id, depth + 1);
  }
};
branch("home", 0);
assert.equal(pages.length, 1086);
large.setConfig({pages}); large.hass = {states:{}};
const largeTree = large.querySelector(".tree");
assert.equal(largeTree.querySelectorAll("ha-form").length, 2);
assert.equal(largeTree.querySelectorAll("details").length, 6);
const toggle = (row, open) => { row.open = open; row.events.toggle(); };
const first = largeTree.querySelectorAll("details")[1];
toggle(first, true);
assert.equal(largeTree.querySelectorAll("ha-form").length, 4);
assert.equal(largeTree.querySelectorAll("details").length, 12);
const nested = first.querySelectorAll("details")[1];
toggle(nested, true);
const titleForm = nested.querySelectorAll("ha-form")[0];
titleForm.events["value-changed"]({stopPropagation(){},detail:{value:{title:"Edited"}}});
toggle(first, false);
assert.equal(largeTree.querySelectorAll("ha-form").length, 2);
const hiddenHass = titleForm.hass;
large.hass = {states:{"light.example":{}}};
assert.equal(titleForm.hass, hiddenHass, "unmounted forms receive no HA updates");
toggle(first, true);
assert.equal(largeTree.querySelectorAll("ha-form").length, 6, "descendant expansion survives collapse");
assert.equal(first.querySelectorAll("ha-form")[2].data.title, "Edited");
large.renderTree();
assert.equal(largeTree.querySelectorAll("ha-form").length, 6, "rebuild preserves expansion");
toggle(largeTree.children[0], false);
large.renderTree();
assert.equal(largeTree.querySelectorAll("ha-form").length, 0, "a closed root stays closed");
assert.equal(large.config.pages.length, 1086, "unmounting never removes configuration");

// The dialog round-trips rich entity settings without disturbing tree ordering.
large.setEntities('home', ['light.demo']);
openOptions(large, 'home', 'light.demo');
const dialog = large.children.at(-1);
const optionsForm = dialog.children[1].children.find((node)=>node.tag==='ha-form');
optionsForm.events['value-changed']({stopPropagation(){},detail:{value:{label:'Reading light',icon:'mdi:book-open',style:'CTL-LIGHT-EDITORIAL'}}});
const detailedAppearance = dialog.children[1].children[2].children[1];
detailedAppearance.events['value-changed']({stopPropagation(){},detail:{value:{...detailedAppearance.data,'outer-border':false,'border-width':2,'font-size':11,'icon-size':18,raster:'smooth'}}});
dialog.children[1].children[3].children[2].events['value-changed']({stopPropagation(){},detail:{value:{conditions:[{condition:'state',entity_id:'switch.demo',state:'on'}]}}});
dialog.children[2].children.find((node)=>node.textContent==='Apply').events.click();
const editedEntity = large.entities('home')[0];
assert.equal(editedEntity.entity_id,'light.demo');
assert.equal(editedEntity.label,'Reading light');
assert.equal(editedEntity.appearance['outer-border'],false);
assert.equal(editedEntity.conditions[0].entity_id,'switch.demo');
assert.equal(editedEntity.style,'CTL-LIGHT-EDITORIAL');
openOptions(large, 'home');
const clockDialog = large.children.at(-1);
const clockForm = clockDialog.children[1].children.find(node=>node.tag==='ha-form');
clockForm.events['value-changed']({stopPropagation(){},detail:{value:{title:'Time',style:'CHR-WORLDTIMER',clock_timezone:'UTC',clock_world_zones:'UTC, Asia/Tokyo',clock_moon_entity:'sensor.moon',clock_reserve_entity:'sensor.reserve'}}});
clockDialog.children[2].children.find(node=>node.textContent==='Apply').events.click();
assert.equal(large.config.pages[0].style,'CHR-WORLDTIMER');
assert.deepEqual(large.config.pages[0].clock,{timezone:'UTC',world_zones:['UTC','Asia/Tokyo'],moon_entity:'sensor.moon',reserve_entity:'sensor.reserve'});
// The panel's Options dialog: every setting a style reads must be reachable, and its own come first.
const settingGroups = (entity, appearance = {}) => {
  const panel = new Element();
  panel.panelMode = true;
  panel._hass = { callWS: async () => ({ styles: {}, themes: {}, frames: {} }) };
  panel.config = { pages: [{ id: "home", title: "Home", appearance, entities: [entity] }] };
  panel.entities = () => [entity];
  panel.querySelector = () => null;
  openOptions(panel, "home", entity.entity_id);
  const dialog = panel.children.at(-1);
  const find = (node, name) => node.className?.includes?.(name) ? node : node.children.map((child) => find(child, name)).find(Boolean);
  const chips = find(dialog, "setting-groups").children;
  return { names: chips.map((chip) => chip.textContent), chips, body: find(dialog, "setting-group ") ?? find(dialog, "setting-group") };
};
assert.deepEqual(settingGroups({ entity_id: "camera.demo" }).names.slice(0, 2), ["Rendering", "Picture"]);
assert.equal(settingGroups({ entity_id: "camera.demo", style: "CAM-RADAR" }).names[1], "Picture");
assert.equal(settingGroups({ entity_id: "camera.demo", style: "CAM-CINEMA" }).names[1], "Picture");
assert.equal(settingGroups({ entity_id: "camera.demo" }, { raster: "crisp" }).names[1], "Picture", "Crisp is about lines and curves, not pictures");
const pictureGroup = settingGroups({ entity_id: "camera.demo" });
pictureGroup.chips.find((chip) => chip.textContent === "Picture").click();
// Snake: its own settings lead, a slider shows only while it has an effect, and its colours stay out of other styles.
const panelDialog = (page) => {
  const panel = new Element();
  panel.panelMode = true;
  panel._hass = { callWS: async () => ({ styles: {}, themes: {}, frames: {} }) };
  panel.config = { pages: [page] };
  panel.entities = () => [];
  panel.querySelector = () => null;
  openOptions(panel, page.id);
  return panel.children.at(-1);
};
const everyNode = (node) => [node, ...(node.children || []).flatMap(everyNode)];
const labelled = (dialog, label) => everyNode(dialog).find((node) => node["aria-label"] === label);
const snakeDialog = panelDialog({ id: "home", title: "Home", style: "NAV-SNAKE", entities: [] });
const groupChips = everyNode(snakeDialog).find((node) => node.className === "dialog-tabs setting-groups");
assert.deepEqual(groupChips.children.map((chip) => chip.textContent).slice(0, 3), ["Rendering", "Snake path", "Snake line"]);
groupChips.children.find((chip) => chip.textContent === "Snake path").click();
assert(labelled(snakeDialog, "Icons per row"), "per row is the default placement");
assert(!labelled(snakeDialog, "Icon spacing"), "spacing does nothing per row");
labelled(snakeDialog, "Placement").children.find((button) => button.textContent === "along path").click();
assert(labelled(snakeDialog, "Icon spacing"), "choosing along path offers spacing");
assert(!labelled(snakeDialog, "Icons per row"));
assert(labelled(snakeDialog, "Turn extension") && labelled(snakeDialog, "Twist"));
const colourRow = (dialog, label) => labelled(dialog, label).parentNode.parentNode;
assert.equal(colourRow(snakeDialog, "Snake line colour").style.display, "");
const orbitDialog = panelDialog({ id: "home", title: "Home", style: "NAV-ORBIT", entities: [] });
assert.equal(colourRow(orbitDialog, "Snake line colour").style.display, "none");
assert.equal(colourRow(orbitDialog, "Snake travelled colour").style.display, "none");
assert(fs.readFileSync("custom_components/ha_dial/www/panel.js", "utf8").includes(".setting-groups{flex-wrap:wrap"), "a phone must be able to reach every group");
// Explorer: it takes one slot beside the owner's own pages, and the panel explains what it left out.
const explorerCalls = [];
const explorerWs = async (message) => {
  if (message.type !== "ha_dial/explorer") return { styles: {}, themes: {}, frames: {} };
  explorerCalls.push(message);
  return { shown: 12, omitted: { diagnostic: 30, hidden: 2 }, style: "NAV-LIST", items: [{ id: "x_area_kitchen", label: "Kitchen", style: "NAV-ORBIT", children: [{ id: "light.a", label: "Lamp", entity_id: "light.a" }] }] };
};
const explorerSpace = new Workspace(); explorerSpace.setConfig({}); explorerSpace.hass = { states: {}, callWS: explorerWs };
explorerSpace.addPage("home");
const ownPage = explorerSpace.selectedPage;
explorerSpace.addExplorer("home");
assert.deepEqual(explorerSpace.config.pages.map((page) => page.title), ["Home", "New page", "Explorer"], "it joins the owner's pages rather than replacing them");
const explorerPage = explorerSpace.config.pages[2];
assert.equal(explorerPage.parent, "home");
assert.deepEqual(explorerPage.explorer, {});
assert.equal(explorerPage.style, "NAV-LIST");
assert.notEqual(ownPage, explorerPage.id);
await new Promise((resolve) => setTimeout(resolve, 0));
const inspector = explorerSpace.querySelector(".inspector-content");
const inspectorNodes = () => everyNode(inspector);
const explorerText = () => inspectorNodes().map((node) => node.textContent).filter(Boolean);
assert(explorerText().some((text) => text === "12 shown. Left out: 30 diagnostic or configuration, 2 hidden in HA."), "omissions are explained");
assert(explorerText().some((text) => text.startsWith("Kitchen (1)")), "generated pages are listed");
assert(!explorerText().includes("+ Subpage"), "its contents come from the home");
const explorerForm = inspectorNodes().find((node) => node.tag === "ha-form");
const changeExplorer = (value) => explorerForm.events["value-changed"]({ stopPropagation() {}, detail: { value } });
const shuffleChip = inspectorNodes().find((node) => node.textContent === "Shuffle styles");
assert.equal(shuffleChip.hidden, true, "Shuffle only appears for Random");
changeExplorer({ ...explorerForm.data, random: true });
assert.equal(shuffleChip.hidden, false);
shuffleChip.click();
assert.equal(explorerSpace.config.pages[2].explorer.shuffle, 1);
changeExplorer({ ...explorerForm.data, scope: "area" });
assert(explorerForm.schema.some((field) => field.name === "area_id"), "choosing one area asks which");
assert.equal(explorerSpace.config.pages[2].explorer.scope, undefined, "the chooser's own value isn't stored");
changeExplorer({ ...explorerForm.data, scope: "home" });
assert.equal("area_id" in explorerSpace.config.pages[2].explorer, false);
assert(explorerSpace.config.pages[2].explorer.random, "other settings survive");
await new Promise((resolve) => setTimeout(resolve, 0));
assert.equal(explorerCalls.at(-1).options.shuffle, 1);
// A generated page's own appearance is an override on the Explorer, and only pins what was chosen.
const kitchenRow = inspectorNodes().find((node) => node.textContent?.startsWith("Kitchen (1)"));
kitchenRow.click();
const kitchenDialog = explorerSpace.children.at(-1);
const footButtons = () => kitchenDialog.children.at(-1).children;
footButtons().find((node) => node.textContent === "Apply").click();
assert.equal(explorerSpace.config.pages[2].explorer.pages.x_area_kitchen.style, undefined, "opening a Random page must not stop it following Shuffle");
explorerSpace.selectedPage = explorerPage.id; explorerSpace.renderTree();
await new Promise((resolve) => setTimeout(resolve, 0));
const storage = new Map();
globalThis.localStorage = { getItem: (key) => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) };
const zoomCard = new Card();
zoomCard.setConfig({device:"preview",zoom:200});
const zoomRoot = zoomCard.shadowRoot, zoomStyle = zoomRoot.querySelector("ha-card").style;
assert.equal(zoomCard.zoom, 100, "a saved card's old zoom value is ignored");
assert.equal(zoomStyle["--dial-stage-width"], "100%", "at 100% the preview still fits a narrow phone");
assert(!("zoom" in zoomCard._definition()), "zoom is presentation only");
assert(!("zoom" in zoomCard.config));
zoomRoot.querySelector(".zoom input").events.input({target:{value:"400"}});
assert.equal(zoomStyle["--dial-zoom"], "4");
assert.equal(zoomStyle["--dial-stage-width"], "1440px", "the rectangle is fixed, so the viewport pans around it");
assert.equal(zoomCard.style["--dial-preview-width"], "1440px");
assert.equal(zoomRoot.querySelector(".zoom output").textContent, "400%");
assert.equal(storage.get("ha-dial-preview-zoom"), "400");
const sharp = new Card();
sharp.setConfig({device:"preview"});
assert.equal(sharp.zoom, 400, "the size is remembered per browser");
assert.equal(sharp.shadowRoot.querySelector(".zoom input").value, "400");
const canvasEl = sharp.shadowRoot.querySelector("canvas");
canvasEl.getBoundingClientRect = () => ({width:240});
sharp.applyZoom(150);
assert.equal(canvasEl.style.imageRendering, "pixelated", "enlarged Dial pixels stay hard-edged");
canvasEl.getBoundingClientRect = () => ({width:190});
sharp.applyZoom(100);
assert.equal(canvasEl.style.imageRendering, "auto", "scaling down must not drop pixels raggedly");
for (const bad of ["999","abc","99"]) { storage.set("ha-dial-preview-zoom", bad); const card = new Card(); card.setConfig({device:"preview"}); assert.equal(card.zoom, 100, bad); }
globalThis.localStorage = { get getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } };
const blocked = new Card();
blocked.setConfig({device:"preview"});
assert.equal(blocked.zoom, 100, "blocked storage still gives a working preview");
blocked.shadowRoot.querySelector(".zoom input").events.input({target:{value:"150"}});
assert.equal(blocked.zoom, 150);
delete globalThis.localStorage;
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

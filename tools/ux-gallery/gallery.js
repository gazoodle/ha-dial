import { concepts, themes } from "./concepts.js";
import { renderScene } from "./renderers.js";

const frameUrl = "../../custom_components/ha_dial/brand/icon@2x.png";
const catalogue = document.querySelector("#catalogue");
const empty = document.querySelector("#empty");
const count = document.querySelector("#visible-count");
const search = document.querySelector("#search");
const family = document.querySelector("#family");
const theme = document.querySelector("#theme");
const dialHost = document.querySelector("#dial-host");
const pushStatus = document.querySelector("#push-status");
const familyOrder = ["Navigation", "Domain controls", "Chronograph", "Smartwatch", "Data", "Camera", "Ambient"];

dialHost.value = localStorage.getItem("ha-dial-host") || dialHost.value;
dialHost.addEventListener("change", () => localStorage.setItem("ha-dial-host", dialHost.value.trim()));

for (const name of familyOrder) family.add(new Option(name, name));
for (const item of themes) theme.add(new Option(item.name, item.id));

const ordered = [...concepts].sort((a, b) =>
  familyOrder.indexOf(a.family) - familyOrder.indexOf(b.family)
  || a.title.localeCompare(b.title)
  || a.theme.name.localeCompare(b.theme.name)
);

const cards = ordered.map((concept, index) => {
  const article = document.createElement("article");
  article.className = "concept";
  article.id = concept.id;
  article.dataset.family = concept.family;
  article.dataset.theme = concept.theme.id;
  article.dataset.search = `${concept.id} ${concept.family} ${concept.title} ${concept.description} ${concept.theme.name}`.toLowerCase();
  article.style.setProperty("--glow", `${concept.theme.primary}20`);
  article.style.setProperty("--swatch", concept.theme.primary);
  article.innerHTML = `
    <div class="device">
      <img class="device-frame" src="${frameUrl}" alt="" draggable="false">
      <button class="device-screen" data-preview="${index}" type="button" aria-label="Push ${concept.title} to Dial"></button>
    </div>
    <div class="meta">
      <div class="meta-head"><a class="variant-id" href="#${concept.id}">${concept.id}</a><span class="swatch"></span></div>
      <h3>${concept.title}</h3>
      <p>${concept.description}</p>
      <div class="tags"><span>${concept.family}</span><span>${concept.theme.name}</span><span>${concept.layout || concept.domain}</span></div>
    </div>`;
  catalogue.append(article);
  return [article, concept];
});

const observer = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    if (!entry.isIntersecting) continue;
    const screen = entry.target.querySelector("[data-preview]");
    const concept = ordered[Number(screen.dataset.preview)];
    screen.innerHTML = renderScene(concept);
    observer.unobserve(entry.target);
  }
}, { rootMargin: "800px" });

for (const [card] of cards) observer.observe(card);

const asDataUrl = (blob) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(reader.result);
  reader.onerror = () => reject(reader.error);
  reader.readAsDataURL(blob);
});

async function rgb565(screen) {
  const svg = screen.querySelector("svg").cloneNode(true);
  for (const image of svg.querySelectorAll("image")) {
    const response = await fetch(new URL(image.getAttribute("href"), location.href));
    if (!response.ok) throw new Error(`Could not load image asset (${response.status})`);
    image.setAttribute("href", await asDataUrl(await response.blob()));
  }
  const source = new XMLSerializer().serializeToString(svg);
  const url = URL.createObjectURL(new Blob([source], { type: "image/svg+xml" }));
  try {
    const bitmap = new Image();
    bitmap.src = url;
    await bitmap.decode();
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 240;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(bitmap, 0, 0, 240, 240);
    const rgba = context.getImageData(0, 0, 240, 240).data;
    const frame = new Uint8Array(240 * 240 * 2);
    for (let sourceIndex = 0, targetIndex = 0; sourceIndex < rgba.length; sourceIndex += 4, targetIndex += 2) {
      const value = (rgba[sourceIndex] >> 3) << 11
        | (rgba[sourceIndex + 1] >> 2) << 5
        | rgba[sourceIndex + 2] >> 3;
      frame[targetIndex] = value >> 8;
      frame[targetIndex + 1] = value & 0xff;
    }
    return frame;
  } finally {
    URL.revokeObjectURL(url);
  }
}

async function push(card, concept, screen) {
  screen.disabled = true;
  card.classList.add("is-pushing");
  pushStatus.textContent = `Rendering ${concept.id}…`;
  try {
    if (!screen.firstElementChild) screen.innerHTML = renderScene(concept);
    const frame = await rgb565(screen);
    pushStatus.textContent = `Sending ${concept.id} to ${dialHost.value.trim()}…`;
    const response = await fetch(`/api/push?host=${encodeURIComponent(dialHost.value.trim())}&id=${encodeURIComponent(concept.id)}`, {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body: frame,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Push failed (${response.status})`);
    document.querySelector(".concept.is-pushed")?.classList.remove("is-pushed");
    card.classList.add("is-pushed");
    pushStatus.textContent = `${concept.id} is now on ${dialHost.value.trim()}.`;
  } catch (error) {
    pushStatus.textContent = `${concept.id}: ${error.message}`;
  } finally {
    card.classList.remove("is-pushing");
    screen.disabled = false;
  }
}

for (const [card, concept] of cards) {
  const screen = card.querySelector(".device-screen");
  screen.addEventListener("click", () => push(card, concept, screen));
}

function filter() {
  const query = search.value.trim().toLowerCase();
  let visible = 0;
  for (const [card] of cards) {
    const show = (!query || card.dataset.search.includes(query))
      && (family.value === "all" || card.dataset.family === family.value)
      && (theme.value === "all" || card.dataset.theme === theme.value);
    card.hidden = !show;
    if (show) visible += 1;
  }
  count.textContent = visible.toLocaleString();
  empty.hidden = visible !== 0;
}

search.addEventListener("input", filter);
family.addEventListener("change", filter);
theme.addEventListener("change", filter);
filter();

if (location.hash) document.querySelector(location.hash)?.scrollIntoView({ block: "center" });

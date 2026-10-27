import { domainIcons, icon } from "./icons.js";

const navItems = [
  ["Building", "building"], ["Floors", "floor"], ["Rooms", "room"],
  ["Lights", "light"], ["Climate", "climate"], ["Media", "media"],
];

const controlData = {
  light: ["72", "%", "WARM · 2700 K", "light"],
  thermostat: ["21.5", "°", "TARGET · HEAT", "climate"],
  media: ["03:42", "", "NIGHT DRIVE · PLAYING", "media"],
  volume: ["38", "%", "KITCHEN · GROUPED", "speaker"],
  cover: ["64", "%", "SOUTH SHADE · OPEN", "cover"],
  fan: ["3", "", "BREEZE · AUTO", "fan"],
  security: ["ARMED", "", "PERIMETER · CLEAR", "shield"],
  lock: ["LOCKED", "", "FRONT ENTRY · 22:41", "lock"],
  vacuum: ["68", "%", "42 M² · 18 MIN LEFT", "vacuum"],
  energy: ["4.8", "kW", "SOLAR 6.2 · GRID 1.4", "energy"],
  weather: ["17", "°C", "CLEAR · FEELS 16°C", "weather"],
  air: ["24", "AQI", "PM2.5  6 · CO₂  612", "air"],
  timer: ["18:42", "", "DINNER · RUNNING", "timer"],
  calendar: ["09:30", "", "DESIGN REVIEW · 45 MIN", "calendar"],
  vehicle: ["186", "mi", "CHARGING · 7.2 kW", "car"],
  water: ["12.4", "L/m", "TODAY · 286 L", "water"],
  scene: ["EVENING", "", "8 DEVICES · READY", "scene"],
  selector: ["FOCUS", "", "MODE · 3 OF 7", "more"],
};

const point = (cx, cy, radius, degrees) => {
  const angle = (degrees - 90) * Math.PI / 180;
  return [cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius];
};

const arc = (cx, cy, radius, start, end) => {
  const a = point(cx, cy, radius, end);
  const b = point(cx, cy, radius, start);
  return `M ${a[0]} ${a[1]} A ${radius} ${radius} 0 ${end - start > 180 ? 1 : 0} 0 ${b[0]} ${b[1]}`;
};

const label = (value, x, y, size, colour, anchor = "middle", weight = 600, spacing = 0) =>
  `<text x="${x}" y="${y}" fill="${colour}" text-anchor="${anchor}" font-family="Inter,Arial,sans-serif" font-size="${size}" font-weight="${weight}" letter-spacing="${spacing}">${value}</text>`;

const pill = (value, x, y, width, theme) =>
  `<rect x="${x - width / 2}" y="${y - 9}" width="${width}" height="18" rx="9" fill="${theme.primary}20" stroke="${theme.primary}" stroke-width="1"/>${label(value, x, y + 3.5, 7.5, theme.secondary, "middle", 700, 1)}`;

const tickRing = (theme, radius = 105, count = 60, strongEvery = 5) => Array.from({ length: count }, (_, index) => {
  const [x1, y1] = point(120, 120, radius - (index % strongEvery ? 3 : 7), index * 360 / count);
  const [x2, y2] = point(120, 120, radius, index * 360 / count);
  return `<path d="M${x1} ${y1}L${x2} ${y2}" stroke="${index % strongEvery ? theme.quiet : theme.secondary}" stroke-width="${index % strongEvery ? .55 : 1.2}"/>`;
}).join("");

const chrome = (theme, title = "") => `
  ${title ? pill(title.toUpperCase(), 120, 24, Math.min(116, Math.max(52, title.length * 6.2)), theme) : ""}
  <g opacity=".95">
    <rect x="54" y="199" width="58" height="20" rx="10" fill="${theme.surface}" stroke="${theme.quiet}" stroke-width="1.2"/>
    ${icon("back", 62, 203, 12, theme.primary, 2)}${label("BACK", 84, 212.5, 6.5, theme.text, "middle", 700, .8)}
    <rect x="128" y="199" width="58" height="20" rx="10" fill="${theme.surface}" stroke="${theme.quiet}" stroke-width="1.2"/>
    ${icon("home", 136, 203, 12, theme.primary, 2)}${label("HOME", 160, 212.5, 6.5, theme.text, "middle", 700, .8)}
  </g>`;

const innerNavigation = (theme) => `
  <g opacity=".96">
    <rect x="66" y="146" width="48" height="24" rx="12" fill="${theme.surface}" stroke="${theme.quiet}" stroke-width="1.2"/>
    ${icon("back", 72, 152, 12, theme.primary, 2)}${label("BACK", 97, 161.5, 6, theme.text, "middle", 700, .7)}
    <rect x="126" y="146" width="48" height="24" rx="12" fill="${theme.surface}" stroke="${theme.quiet}" stroke-width="1.2"/>
    ${icon("home", 132, 152, 12, theme.primary, 2)}${label("HOME", 158, 161.5, 6, theme.text, "middle", 700, .7)}
  </g>`;

const shell = (theme, body, title = "") => `
  <svg viewBox="0 0 240 240" role="img" aria-label="${title || "Dial concept"}">
    <circle cx="120" cy="120" r="120" fill="${theme.bg}"/>
    <circle cx="120" cy="120" r="116" fill="none" stroke="${theme.primary}" stroke-width="1.5" opacity=".8"/>
    <circle cx="120" cy="120" r="113" fill="none" stroke="${theme.primary}" stroke-width="1" opacity=".38"/>
    <circle cx="120" cy="120" r="102" fill="none" stroke="${theme.grid}" stroke-width=".6" stroke-dasharray="1 5"/>
    ${body}
  </svg>`;

function renderNavigation(concept) {
  const { theme, layout } = concept;
  let body = "";
  if (layout === "orbit" || layout === "pointer") {
    body += `<circle cx="120" cy="120" r="62" fill="${theme.surface}" opacity=".42" stroke="${theme.grid}" stroke-width=".7"${layout === "pointer" ? ' stroke-dasharray="2 4"' : ""}/>`;
    body += navItems.map(([name, symbol], index) => {
      const [x, y] = point(120, 120, 90, index * 60);
      const selected = index === 0;
      return `<g opacity="${selected ? 1 : .72}"><circle cx="${x}" cy="${y}" r="${selected ? 20 : 15}" fill="${selected ? theme.primary + "28" : theme.surface}" stroke="${selected ? theme.primary : theme.quiet}" stroke-width="${selected ? 1.5 : 1.2}"/>${icon(symbol, x - (selected ? 10 : 9), y - (selected ? 10 : 9), selected ? 20 : 18, selected ? theme.secondary : theme.text)}</g>`;
    }).join("");
    if (layout === "pointer") body += `<path d="M120 49 113 62h14Z" fill="${theme.primary}"/><circle cx="120" cy="64" r="1.5" fill="${theme.secondary}"/>`;
    body += label("BUILDING", 120, 104, 13, theme.text, "middle", 700, 1.4)
      + label(layout === "pointer" ? "SELECTED" : "TURN TO EXPLORE", 120, 120, 6, theme.quiet, "middle", 700, 1.1)
      + innerNavigation(theme);
    return shell(theme, body, concept.title);
  } else if (layout === "rolodex") {
    const rows = [["FLOORS", "floor", 70, .55, 74], ["ROOMS", "room", 103, 1, 112], ["LIGHTS", "light", 143, .68, 158]];
    body += rows.map(([name, symbol, y, scale, width]) => `<g opacity="${scale}"><path d="M${120 - width / 2} ${y - 13} Q120 ${y - 22} ${120 + width / 2} ${y - 13}L${120 + width / 2 - 8} ${y + 13}Q120 ${y + 20} ${120 - width / 2 + 8} ${y + 13}Z" fill="${name === "ROOMS" ? theme.primary + "2c" : theme.surface}" stroke="${name === "ROOMS" ? theme.primary : theme.quiet}"/>${icon(symbol, 84, y - 8, 16, name === "ROOMS" ? theme.secondary : theme.text)}${label(name, 130, y + 4, name === "ROOMS" ? 12 : 9, theme.text, "middle", 700, 1.2)}</g>`).join("");
    body += `<path d="m188 100 8 8-8 8" fill="none" stroke="${theme.primary}" stroke-width="1.5"/>`;
  } else if (layout === "petals") {
    body += navItems.map(([name, symbol], index) => {
      const [x, y] = point(120, 109, 59, index * 60);
      return `<g><path d="M120 109Q${x} ${y} ${point(120, 109, 82, index * 60 - 18).join(" ")}A82 82 0 0 1 ${point(120, 109, 82, index * 60 + 18).join(" ")}Q${x} ${y} 120 109" fill="${index === 0 ? theme.primary + "2d" : "none"}" stroke="${index === 0 ? theme.primary : theme.grid}" stroke-width=".8"/>${icon(symbol, x - 7, y - 7, 14, index === 0 ? theme.secondary : theme.text)}</g>`;
    }).join("");
    body += `<circle cx="120" cy="109" r="32" fill="${theme.bg}" stroke="${theme.quiet}"/>${label("BUILDING", 120, 107, 10, theme.text, "middle", 700, 1)}${label("01 / 06", 120, 121, 5.5, theme.primary, "middle", 700, 1.4)}`;
  } else if (layout === "constellation") {
    const nodes = [[120,57],[177,88],[168,149],[112,172],[63,137],[69,83]];
    body += `<path d="${nodes.map((p, i) => `${i ? "L" : "M"}${p[0]} ${p[1]}`).join("")}Z" fill="none" stroke="${theme.quiet}" stroke-width=".7"/>`;
    body += nodes.map((p, index) => `<g><circle cx="${p[0]}" cy="${p[1]}" r="${index === 2 ? 16 : 8}" fill="${index === 2 ? theme.primary + "33" : theme.surface}" stroke="${index === 2 ? theme.primary : theme.secondary}"/>${icon(navItems[index][1], p[0]-6, p[1]-6, 12, theme.text)}</g>`).join("");
    body += label("LIGHTS", 120, 111, 15, theme.text, "middle", 750, 1.5) + label("CONNECTED PATH", 120, 126, 6, theme.quiet, "middle", 700, 1);
  } else if (layout === "compass") {
    const nodes = [[120,67,"building"],[173,120,"floor"],[120,173,"room"],[67,120,"light"]];
    body += `<circle cx="120" cy="120" r="70" fill="none" stroke="${theme.grid}"/><path d="M120 44v152M44 120h152" stroke="${theme.grid}" stroke-width=".6"/>`;
    body += nodes.map(([x,y,symbol], index) => `<circle cx="${x}" cy="${y}" r="19" fill="${index === 0 ? theme.primary + "32" : theme.surface}" stroke="${index === 0 ? theme.primary : theme.quiet}"/>${icon(symbol,x-10,y-10,20,index===0?theme.secondary:theme.text)}`).join("");
    body += `<circle cx="120" cy="120" r="27" fill="${theme.surface}"/>${label("HOME",120,124,11,theme.text,"middle",700,1.3)}`;
  } else if (layout === "ribbon") {
    body += `<path d="M44 157C78 137 95 102 196 55" fill="none" stroke="${theme.grid}" stroke-width="19" opacity=".55"/><path d="M44 157C78 137 95 102 196 55" fill="none" stroke="${theme.primary}" stroke-width="1"/>`;
    body += navItems.slice(0,5).map(([name,symbol],index)=>{const x=57+index*31,y=153-index*22,selected=index===2;return `<g opacity="${selected?1:.52}"><circle cx="${x}" cy="${y}" r="${selected?16:10}" fill="${selected?theme.primary+"33":theme.surface}" stroke="${selected?theme.primary:theme.quiet}"/>${icon(symbol,x-(selected?8:6),y-(selected?8:6),selected?16:12,theme.text)}</g>`}).join("");
    body += label("ROOMS", 120, 181, 11, theme.text, "middle", 750, 1.5);
  } else {
    body += `<path d="M53 68h134M65 103h110M78 138h84" stroke="${theme.grid}" stroke-width="22" stroke-linecap="round"/>`;
    body += label("CAMPUS",120,72,8,theme.quiet,"middle",700,1.4)+label("FIRST FLOOR",120,107,11,theme.secondary,"middle",700,1.2)+label("STUDY",120,144,18,theme.text,"middle",750,1.6);
    body += `<path d="m120 157-6 7h12Z" fill="${theme.primary}"/>${label("6 DEVICES",120,181,6.5,theme.primary,"middle",700,1.3)}`;
  }
  const title = ["petals", "ribbon"].includes(layout) ? "" : "Navigate";
  return shell(theme, chrome(theme, title) + body, concept.title);
}

function domainGraphic(domain, theme, variant) {
  const [value, unit, detail, symbol] = controlData[domain];
  const editorial = variant === "editorial";
  let body = pill(domain.toUpperCase(), 120, 24, Math.min(108, 42 + domain.length * 6), theme);
  if (["light", "thermostat", "volume", "timer", "air"].includes(domain)) {
    body += `<path d="${arc(120,118,70,-132,132)}" fill="none" stroke="${theme.grid}" stroke-width="${editorial?5:10}" stroke-linecap="round"/><path d="${arc(120,118,70,-132,editorial?52:72)}" fill="none" stroke="${theme.primary}" stroke-width="${editorial?2.2:6}" stroke-linecap="round"/>`;
    body += Array.from({length:19},(_,i)=>{const [x1,y1]=point(120,118,60,-126+i*14);const [x2,y2]=point(120,118,64,-126+i*14);return `<path d="M${x1} ${y1}L${x2} ${y2}" stroke="${theme.secondary}" opacity="${i<13?.8:.2}"/>`}).join("");
  } else if (domain === "media") {
    body += `<rect x="55" y="50" width="130" height="89" rx="13" fill="${theme.surface}" stroke="${theme.quiet}"/><circle cx="92" cy="94" r="30" fill="${theme.primary}22" stroke="${theme.primary}"/><circle cx="92" cy="94" r="10" fill="${theme.bg}"/>${icon("play",82,84,20,theme.secondary)}${label("NIGHT",143,82,11,theme.text,"middle",800,1.3)}${label("DRIVE",143,98,11,theme.text,"middle",800,1.3)}${label("03 · AURORA",143,116,6,theme.quiet,"middle",700,1)}`;
    body += `<path d="M58 155h124" stroke="${theme.grid}" stroke-width="3" stroke-linecap="round"/><path d="M58 155h73" stroke="${theme.primary}" stroke-width="3" stroke-linecap="round"/>`;
  } else if (domain === "cover") {
    body += `<rect x="68" y="49" width="104" height="121" rx="8" fill="${theme.surface}" stroke="${theme.quiet}"/>${Array.from({length:7},(_,i)=>`<path d="M73 ${62+i*14}h94" stroke="${i<4?theme.primary:theme.grid}" stroke-width="6" opacity="${.9-i*.07}"/>`).join("")}<path d="M120 54v112" stroke="${theme.secondary}" opacity=".35"/>`;
  } else if (domain === "fan") {
    body += `<circle cx="120" cy="112" r="60" fill="${theme.surface}" stroke="${theme.quiet}"/>${Array.from({length:5},(_,i)=>`<ellipse cx="120" cy="79" rx="13" ry="32" fill="${theme.primary}${editorial?"24":"45"}" transform="rotate(${i*72} 120 112)"/>`).join("")}<circle cx="120" cy="112" r="14" fill="${theme.bg}" stroke="${theme.secondary}"/>`;
  } else if (["security", "lock"].includes(domain)) {
    body += `<circle cx="120" cy="109" r="60" fill="${theme.primary}0d" stroke="${theme.grid}"/>${tickRing(theme,58,24,3)}${icon(symbol,92,81,56,theme.primary,1.25)}`;
    body += `<circle cx="67" cy="158" r="3" fill="${theme.primary}"/><circle cx="82" cy="169" r="3" fill="${theme.primary}"/><circle cx="173" cy="158" r="3" fill="${theme.primary}"/>`;
  } else if (domain === "vacuum") {
    body += `<path d="M55 63h55v37h42v22h31v50H91v-31H55Z" fill="${theme.surface}" stroke="${theme.quiet}"/><path d="M68 78c54 0 18 47 72 48s3 27 28 30" fill="none" stroke="${theme.primary}" stroke-width="2" stroke-dasharray="2 3"/><circle cx="68" cy="78" r="7" fill="${theme.primary}"/>`;
  } else if (["energy", "water"].includes(domain)) {
    body += `<path d="M44 148C65 121 78 151 97 112s31 18 48-21 30 1 51-28V174H44Z" fill="${theme.primary}18"/><path d="M44 148C65 121 78 151 97 112s31 18 48-21 30 1 51-28" fill="none" stroke="${theme.primary}" stroke-width="2"/>${Array.from({length:5},(_,i)=>`<path d="M48 ${70+i*23}h144" stroke="${theme.grid}" stroke-width=".6"/>`).join("")}`;
  } else if (domain === "weather") {
    body += `${icon("sun",50,59,64,theme.primary,1.2)}<path d="M93 123c7-24 41-24 49-2 26-4 37 31 10 39H82c-31-5-20-45 11-37Z" fill="${theme.surface}" stroke="${theme.secondary}"/>${label("17°C",151,126,13,theme.text,"middle",750,-.4)}`;
  } else if (domain === "calendar") {
    body += `<circle cx="120" cy="113" r="67" fill="${theme.surface}" stroke="${theme.quiet}"/>${Array.from({length:7},(_,i)=>{const [x,y]=point(120,113,54,-90+i*30);return `<circle cx="${x}" cy="${y}" r="${i===2?7:3}" fill="${i===2?theme.primary:theme.quiet}"/>`}).join("")}${label("09",93,118,25,theme.text,"middle",500)}${label("30",140,118,25,theme.text,"middle",800)}${label("DESIGN REVIEW",120,143,6,theme.primary,"middle",700,1)}`;
  } else if (domain === "vehicle") {
    body += `${icon("car",82,51,76,theme.secondary,1.15)}${label("186",106,139,25,theme.text,"middle",750,-.8)}${label("mi",143,139,8,theme.primary,"start",700,.8)}<rect x="53" y="151" width="134" height="16" rx="8" fill="${theme.surface}" stroke="${theme.quiet}"/><rect x="57" y="155" width="88" height="8" rx="4" fill="${theme.primary}"/>${icon("energy",151,151,14,theme.primary)}`;
  } else if (domain === "scene") {
    body += `<circle cx="120" cy="111" r="65" fill="${theme.surface}" stroke="${theme.quiet}"/><path d="M72 128c20-18 33-17 48 0 16-23 35-24 52 0v31H72Z" fill="${theme.primary}27"/><circle cx="92" cy="87" r="15" fill="${theme.secondary}55"/>${Array.from({length:9},(_,i)=>`<circle cx="${78+(i*29)%88}" cy="${66+(i*17)%56}" r="1" fill="${theme.secondary}"/>`).join("")}`;
  } else {
    body += `<circle cx="120" cy="112" r="64" fill="${theme.surface}" stroke="${theme.quiet}"/>${["CALM","FOCUS","SOCIAL","AWAY"].map((name,i)=>{const [x,y]=point(120,112,43,i*90);return `${label(name,x,y+3,7,i===0?theme.secondary:theme.quiet,"middle",700,.8)}`}).join("")}<circle cx="120" cy="112" r="22" fill="${theme.primary}24" stroke="${theme.primary}"/>${icon(symbol,109,101,22,theme.secondary)}`;
  }
  if (!["media","calendar","vehicle","weather"].includes(domain)) body += label(value,120,editorial?113:121,editorial?24:31,theme.text,"middle",750,-.8)+label(unit,120,editorial?131:140,8,theme.primary,"middle",700,.8);
  body += label(detail,120,181,6.5,theme.quiet,"middle",700,.75);
  return body + chrome(theme);
}

function renderChronograph(concept) {
  const { theme, layout } = concept;
  let body = tickRing(theme,106,60,5);
  body += `<circle cx="120" cy="120" r="92" fill="${theme.surface}" opacity=".55" stroke="${theme.quiet}"/><circle cx="120" cy="120" r="83" fill="none" stroke="${theme.grid}" stroke-width=".7"/>`;
  if (layout === "tricompax" || layout === "moonphase") {
    [[76,121,"24"],[164,121,"60"],[120,157,"12"]].forEach(([x,y,value],index)=>{body+=`<circle cx="${x}" cy="${y}" r="24" fill="${theme.bg}" stroke="${theme.quiet}"/>${Array.from({length:12},(_,i)=>{const p1=point(x,y,18,i*30),p2=point(x,y,21,i*30);return `<path d="M${p1[0]} ${p1[1]}L${p2[0]} ${p2[1]}" stroke="${theme.secondary}" stroke-width=".6"/>`}).join("")}${label(value,x,y+3,6,theme.quiet,"middle",700,1)}`});
    if(layout==="moonphase") body+=`<path d="M101 151a19 19 0 0 0 38 0 18 18 0 0 1-38 0Z" fill="${theme.secondary}" opacity=".75"/><circle cx="113" cy="148" r="2" fill="${theme.quiet}"/><circle cx="126" cy="154" r="1.5" fill="${theme.quiet}"/>`;
  } else if (layout === "worldtimer") {
    ["LON","NYC","TYO","SYD","DXB","PAR","LAX","SIN"].forEach((city,index)=>{const [x,y]=point(120,120,75,index*45);body+=label(city,x,y+2,5.5,index===0?theme.primary:theme.quiet,"middle",700,.6)});
    body += `<circle cx="120" cy="120" r="51" fill="${theme.bg}" stroke="${theme.quiet}"/><path d="${arc(120,120,43,-110,55)}" stroke="${theme.primary}" stroke-width="4" fill="none"/>`;
  } else {
    body += `<path d="M58 137 88 70l25 31 24-50 45 86-38 38-61-7Z" fill="none" stroke="${theme.quiet}" stroke-width="6" opacity=".42"/><circle cx="84" cy="133" r="27" fill="${theme.bg}" stroke="${theme.primary}"/><circle cx="159" cy="105" r="32" fill="${theme.bg}" stroke="${theme.quiet}"/>`;
  }
  body += label("HA DIAL",120,58,7,theme.secondary,"middle",700,2)+label("AUTOMATIC",120,69,4.5,theme.quiet,"middle",700,1.4);
  body += `<path d="M120 120 106 77" stroke="${theme.text}" stroke-width="3" stroke-linecap="round"/><path d="M120 120 164 109" stroke="${theme.secondary}" stroke-width="2" stroke-linecap="round"/><path d="M120 120 83 151" stroke="${theme.primary}" stroke-width=".8"/><circle cx="120" cy="120" r="5" fill="${theme.primary}"/>`;
  body += chrome(theme);
  return shell(theme, body, concept.title);
}

function renderSmartwatch(concept) {
  const { theme, layout } = concept;
  let body = "";
  if (layout === "contour") {
    const numerals = [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
    body += numerals.map((value, index) => {
      const [x, y] = point(120, 110, 80, index * 30);
      const size = index % 3 === 0 ? 22 : 14;
      return label(value, x, y + size * .32, size, index < 5 ? theme.primary : theme.quiet, "middle", 750, -1.5);
    }).join("");
    body += label("10:09", 120, 116, 31, theme.text, "middle", 500, -1.8) + label("MON 27", 120, 137, 7, theme.secondary, "middle", 700, 1.2);
  } else if (layout === "modular") {
    body += label("10:09", 167, 57, 25, theme.text, "end", 650, -1.4) + label("MON 27", 63, 56, 7, theme.primary, "start", 750, 1);
    body += `<rect x="45" y="72" width="150" height="48" rx="13" fill="${theme.surface}" stroke="${theme.quiet}"/>${label("NEXT",58,88,5.5,theme.quiet,"start",700,1)}${label("Design review",58,105,10,theme.text,"start",650)}${label("11:30",181,105,9,theme.secondary,"end",700)}`;
    body += `<rect x="45" y="129" width="72" height="54" rx="13" fill="${theme.surface}" stroke="${theme.quiet}"/>${label("17°C",81,154,17,theme.text,"middle",700,-.5)}${label("CLEAR",81,169,5.5,theme.primary,"middle",700,1)}`;
    body += `<rect x="123" y="129" width="72" height="54" rx="13" fill="${theme.surface}" stroke="${theme.quiet}"/>${label("68%",159,154,17,theme.text,"middle",700,-.5)}${label("ENERGY",159,169,5.5,theme.primary,"middle",700,1)}`;
  } else if (layout === "palette") {
    [86,72,58,44].forEach((radius, index) => body += `<path d="${arc(120,110,radius,-115,115-index*15)}" fill="none" stroke="${index % 2 ? theme.secondary : theme.primary}" stroke-width="10" stroke-linecap="round" opacity="${.28+index*.18}"/>`);
    body += label("10", 93, 116, 35, theme.text, "middle", 350, -2) + label("09", 148, 116, 35, theme.primary, "middle", 750, -2) + label("MONDAY", 120, 151, 6.5, theme.secondary, "middle", 750, 1.8);
  } else if (layout === "rings") {
    [[64,290,theme.primary],[49,235,theme.secondary],[35,180,theme.text]].forEach(([radius,end,colour]) => body += `<circle cx="105" cy="108" r="${radius}" fill="none" stroke="${theme.grid}" stroke-width="9"/><path d="${arc(105,108,radius,-90,end-90)}" fill="none" stroke="${colour}" stroke-width="9" stroke-linecap="round"/>`);
    body += label("MOVE", 171, 81, 5.5, theme.quiet, "middle", 700, 1) + label("640", 171, 97, 15, theme.text, "middle", 750) + label("EXERCISE", 171, 121, 5.5, theme.quiet, "middle", 700, 1) + label("28", 171, 137, 15, theme.text, "middle", 750) + label("STAND", 171, 161, 5.5, theme.quiet, "middle", 700, 1) + label("10", 171, 177, 15, theme.text, "middle", 750);
  } else if (layout === "solar") {
    body += `<defs><radialGradient id="solar-${theme.id}" cx="50%" cy="70%"><stop offset="0" stop-color="${theme.secondary}" stop-opacity=".82"/><stop offset=".38" stop-color="${theme.primary}" stop-opacity=".3"/><stop offset="1" stop-color="${theme.bg}" stop-opacity="0"/></radialGradient></defs><circle cx="120" cy="107" r="92" fill="url(#solar-${theme.id})"/><path d="M33 132Q120 75 207 132" fill="none" stroke="${theme.secondary}" stroke-width="1"/><circle cx="166" cy="101" r="6" fill="${theme.secondary}"/>${label("10:09",120,123,32,theme.text,"middle",450,-1.7)}${label("SUNSET 17:42",120,151,6.5,theme.primary,"middle",700,1.2)}`;
  } else if (layout === "reflections") {
    body += `<defs><radialGradient id="metal-${theme.id}"><stop offset="0" stop-color="${theme.text}" stop-opacity=".55"/><stop offset=".45" stop-color="${theme.primary}" stop-opacity=".16"/><stop offset="1" stop-color="${theme.bg}" stop-opacity="0"/></radialGradient></defs>`;
    body += Array.from({length:18},(_,index)=>`<path d="M120 108L${point(120,108,88,index*20-7).join(" ")}A88 88 0 0 1 ${point(120,108,88,index*20+7).join(" ")}Z" fill="${index%3===0?theme.secondary:theme.primary}" opacity="${.08+(index%4)*.05}"/>`).join("");
    body += `<circle cx="120" cy="108" r="74" fill="url(#metal-${theme.id})"/>${label("10:09",120,116,31,theme.text,"middle",500,-1.5)}${label("MON · 27 OCT",120,139,6,theme.secondary,"middle",700,1.4)}`;
  } else if (layout === "photos") {
    body += `<defs><clipPath id="photo-${theme.id}"><circle cx="120" cy="108" r="94"/></clipPath><linearGradient id="photo-shade-${theme.id}" x1="0" y1="0" x2="0" y2="1"><stop offset=".35" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".86"/></linearGradient></defs><image href="assets/camera-gate-blue-hour.png" x="25" y="14" width="190" height="188" preserveAspectRatio="xMidYMid slice" clip-path="url(#photo-${theme.id})"/><circle cx="120" cy="108" r="94" fill="url(#photo-shade-${theme.id})"/>${label("10:09",57,155,31,"#fff","start",650,-1.6)}${label("MON 27 · 17°C",59,174,6.5,"#fff","start",750,1)}`;
  } else {
    body += `<circle cx="120" cy="107" r="91" fill="${theme.primary}18"/><path d="M48 152Q79 119 111 152T192 145V183H48Z" fill="${theme.primary}35"/><path d="M57 147h30l-4 11H61Z" fill="${theme.secondary}"/><path d="M64 142q8-15 16 0" fill="none" stroke="${theme.secondary}" stroke-width="5"/><path d="M149 137 166 83l18 54-18-9Z" fill="${theme.text}" opacity=".9"/><circle cx="166" cy="105" r="7" fill="${theme.primary}"/><rect x="153" y="139" width="27" height="13" rx="4" fill="${theme.secondary}"/><circle cx="159" cy="154" r="5" fill="${theme.quiet}"/><circle cx="175" cy="154" r="5" fill="${theme.quiet}"/>${label("10:09",120,75,31,theme.text,"middle",750,-1.8)}${label("TOYBOX ADVENTURE",120,94,6,theme.secondary,"middle",750,1.1)}`;
  }
  body += chrome(theme);
  return shell(theme, body, concept.title);
}

function renderData(concept) {
  const { theme, layout } = concept;
  let body = pill("LIVE TELEMETRY",120,24,101,theme);
  const grid = Array.from({length:5},(_,i)=>`<path d="M45 ${62+i*27}h150" stroke="${theme.grid}" stroke-width=".6"/>`).join("");
  if (layout === "area") body += grid+`<path d="M43 164C60 151 66 112 83 124s28 36 43 5 22-51 36-35 16 29 35 3v76H43Z" fill="${theme.primary}25"/><path d="M43 164C60 151 66 112 83 124s28 36 43 5 22-51 36-35 16 29 35 3" fill="none" stroke="${theme.primary}" stroke-width="2.2"/>`;
  if (layout === "radar") body += [24,42,61].map(r=>`<circle cx="120" cy="116" r="${r}" fill="none" stroke="${theme.grid}"/>`).join("")+`<path d="M120 56 162 91 151 148 103 166 69 120 90 76Z" fill="${theme.primary}28" stroke="${theme.primary}"/>`;
  if (layout === "bands") body += [72,61,50].map((r,i)=>`<path d="${arc(120,119,r,-130,130)}" fill="none" stroke="${i===0?theme.primary:i===1?theme.secondary:theme.quiet}" stroke-width="${8-i}" stroke-linecap="round" opacity="${1-i*.25}"/>`).join("");
  if (layout === "spark") body += grid+`<path d="M46 138 66 117 84 127 105 84 127 105 147 74 170 91 194 61" fill="none" stroke="${theme.primary}" stroke-width="2"/>${[[65,173,"4.8","kW"],[112,173,"62","%"],[160,173,"17","°C"]].map(([x,y,v,u])=>`${label(v,x,y,10,theme.text,"middle",750)}${label(u,x,y+10,5,theme.quiet,"middle",700)}`).join("")}`;
  body += label(layout==="radar"?"BALANCED":"4.82",120,layout==="radar"?120:112,layout==="radar"?10:28,theme.text,"middle",750,-.5)+label(layout==="radar"?"6 SIGNALS":"kW · NOW",120,layout==="radar"?133:126,6,theme.primary,"middle",700,1)+chrome(theme);
  return shell(theme,body,concept.title);
}

function cameraScene(theme, layout) {
  const clip = `camera-${layout}-${theme.id}`;
  const treatment = layout === "cinema" ? "saturate(1.08) contrast(1.04)" : layout === "portal" ? "grayscale(1) contrast(1.12)" : "grayscale(1) contrast(1.18)";
  const landscape = `<defs><clipPath id="${clip}"><rect x="38" y="51" width="164" height="112" rx="${layout==="cinema"?5:16}"/></clipPath></defs><image href="assets/camera-gate-blue-hour.png" x="38" y="51" width="164" height="112" preserveAspectRatio="xMidYMid slice" clip-path="url(#${clip})" style="filter:${treatment}"/><rect x="38" y="51" width="164" height="112" rx="${layout==="cinema"?5:16}" fill="none" stroke="${theme.quiet}"/>${layout === "radar" ? `<rect x="38" y="51" width="164" height="112" rx="16" fill="${theme.primary}" opacity=".22" style="mix-blend-mode:color"/>` : ""}`;
  let body = pill("CAMERA · 2 SEC",120,24,105,theme)+landscape;
  if(layout==="portal") body += `<rect x="50" y="64" width="140" height="87" rx="11" fill="none" stroke="${theme.primary}" stroke-width="1.2"/><circle cx="171" cy="68" r="4" fill="${theme.primary}"/>`;
  if(layout==="radar") body += `<path d="M51 135 120 52l69 83" fill="none" stroke="${theme.primary}" stroke-dasharray="3 3"/><rect x="83" y="103" width="39" height="55" fill="none" stroke="${theme.secondary}"/><text x="85" y="100" fill="${theme.secondary}" font-size="5">PERSON · 94%</text>`;
  body += chrome(theme);
  return shell(theme,body,"Camera snapshot");
}

function renderAmbient(concept) {
  const {theme,layout}=concept;
  let body=tickRing(theme,104,60,5);
  if(layout==="typographic") body+=label("22",83,130,67,theme.text,"middle",300,-5)+label("47",159,130,67,theme.primary,"middle",700,-5)+label("MON · 26 OCT",120,158,7,theme.quiet,"middle",700,1.5);
  if(layout==="solar") body+=`<path d="${arc(120,125,75,-120,120)}" fill="none" stroke="${theme.grid}" stroke-width="8"/><path d="${arc(120,125,75,-120,42)}" fill="none" stroke="${theme.primary}" stroke-width="4"/><circle cx="${point(120,125,75,42)[0]}" cy="${point(120,125,75,42)[1]}" r="6" fill="${theme.secondary}"/>${label("22:47",120,125,34,theme.text,"middle",450,-1.5)}${label("SUNSET 17:42 · DAWN 07:18",120,149,6,theme.quiet,"middle",700,.8)}`;
  if(layout==="orbital") body+=`<circle cx="120" cy="119" r="70" fill="none" stroke="${theme.quiet}"/><circle cx="120" cy="119" r="50" fill="none" stroke="${theme.grid}"/><circle cx="${point(120,119,70,55)[0]}" cy="${point(120,119,70,55)[1]}" r="7" fill="${theme.primary}"/><circle cx="${point(120,119,50,210)[0]}" cy="${point(120,119,50,210)[1]}" r="4" fill="${theme.secondary}"/>${label("22:47",120,124,31,theme.text,"middle",500,-1)}${label("26 · 10 · 26",120,141,6,theme.quiet,"middle",700,1.1)}`;
  if(layout==="status") body+=`${label("22:47",120,109,35,theme.text,"middle",500,-1)}${label("MONDAY · 26 OCTOBER",120,126,6,theme.quiet,"middle",700,1)}${[[72,158,"17°","weather"],[120,164,"4.8","energy"],[168,158,"SAFE","shield"]].map(([x,y,v,s])=>`<circle cx="${x}" cy="${y}" r="22" fill="${theme.surface}" stroke="${theme.quiet}"/>${icon(s,x-7,y-13,14,theme.primary)}${label(v,x,y+9,7,theme.text,"middle",700)}`).join("")}`;
  body+=chrome(theme);
  return shell(theme,body,concept.title);
}

export function renderScene(concept) {
  if (concept.kind === "navigation") return renderNavigation(concept);
  if (concept.kind === "control") return shell(concept.theme, domainGraphic(concept.domain, concept.theme, concept.variant), concept.title);
  if (concept.kind === "chronograph") return renderChronograph(concept);
  if (concept.kind === "smartwatch") return renderSmartwatch(concept);
  if (concept.kind === "data") return renderData(concept);
  if (concept.kind === "camera") return cameraScene(concept.theme, concept.layout);
  return renderAmbient(concept);
}

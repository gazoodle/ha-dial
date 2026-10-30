// Pixel raster contract mirrored by the firmware and checked with shared scenes.
export function rasterize(scene, localValue = NaN) {
  const local = Number.isFinite(localValue);
  const data = new Uint8ClampedArray(240 * 240 * 4);
  const colours = new Map();
  const colour = (value) => {
    if (!colours.has(value)) {
      const [r, g, b] = value.match(/[\da-f]{2}/gi).map((part) => parseInt(part, 16));
      colours.set(value, [Math.floor((r >> 3) * 255 / 31), Math.floor((g >> 2) * 255 / 63), Math.floor((b >> 3) * 255 / 31)]);
    }
    return colours.get(value);
  };
  const pixel = (x, y, value) => {
    if (x < 0 || x >= 240 || y < 0 || y >= 240) return;
    const index = (y * 240 + x) * 4;
    data.set(colour(value), index);
    data[index + 3] = 255;
  };
  for (let y = 0; y < 240; y++) for (let x = 0; x < 240; x++) pixel(x, y, scene.background);
  const line = (x1, y1, x2, y2, colour) => {
    let dx = Math.abs(x2 - x1), sx = x1 < x2 ? 1 : -1;
    let dy = -Math.abs(y2 - y1), sy = y1 < y2 ? 1 : -1;
    let error = dx + dy;
    while (true) {
    pixel(x1, y1, colour);
    if (x1 === x2 && y1 === y2) break;
    const twice = error * 2;
    if (twice >= dy) { error += dy; x1 += sx; }
    if (twice <= dx) { error += dx; y1 += sy; }
    }
  };
  const circle = (cx, cy, radius, colour, fill = false) => {
    let x = radius, y = 0, error = 1 - radius;
    while (x >= y) {
    if (fill) {
      line(cx - x, cy + y, cx + x, cy + y, colour);
      line(cx - x, cy - y, cx + x, cy - y, colour);
      line(cx - y, cy + x, cx + y, cy + x, colour);
      line(cx - y, cy - x, cx + y, cy - x, colour);
    } else {
      for (const [px, py] of [[x,y], [y,x], [-y,x], [-x,y], [-x,-y], [-y,-x], [y,-x], [x,-y]])
      pixel(cx + px, cy + py, colour);
    }
    y++;
    if (error < 0) error += 2 * y + 1;
    else { x--; error += 2 * (y - x) + 1; }
    }
  };
  for (const element of scene.elements) {
    if (element.op === "circle") {
      if (element.fill) circle(element.x, element.y, element.r, element.fill, true);
      if (element.stroke) for (let width = 0; width < (element.width || 1); width++)
        circle(element.x, element.y, Math.max(0, element.r - width), element.stroke);
    } else if (element.op === "arc" || element.op === "gauge") {
      const value = local ? Math.round((localValue - (element.minimum ?? 0)) * 100 / ((element.maximum ?? 100) - (element.minimum ?? 0))) : element.value;
      const end = element.op === "gauge" ? element.start + Math.round((element.end - element.start) * Math.max(0, Math.min(100, value)) / 100) : element.end;
      const stroke = element.op === "gauge" && local ? (element.fill || element.stroke) : element.stroke;
      for (let width = 0; width < element.width; width++) {
        const radius = Math.max(1, element.r + width - Math.floor(element.width / 2));
        let previous;
        for (let degree = element.start; degree <= end; degree += 3) {
          const angle = (degree - 90) * Math.PI / 180;
          const point = [element.x + Math.round(Math.cos(angle) * radius), element.y + Math.round(Math.sin(angle) * radius)];
          if (previous) line(...previous, ...point, stroke);
          previous = point;
        }
      }
    } else if (element.op === "polyline") {
      for (let index = 1; index < element.points.length; index++)
        line(...element.points[index - 1], ...element.points[index], element.stroke);
    } else if (element.op === "line") {
      line(element.x1, element.y1, element.x2, element.y2, element.stroke);
    } else if (element.op === "mask" || element.op === "number") {
      const scale = 10 ** (element.precision || 0);
      const digits = element.op !== 'number' ? '' : element.characters ? (local ? Math.max(-999999 / scale, Math.min(999999 / scale, localValue)) : element.value / scale).toFixed(element.precision || 0) : String(Math.max(0, Math.min(999, local ? Math.round(localValue) : element.value)));
      const drawWidth = element.width * (element.op === "number" ? digits.length : 1);
      const ink = element.op === "number" && local ? element.stroke : element.colour;
      const front = ink.match(/[\da-f]{2}/gi).map((part) => parseInt(part, 16));
      const back = (element.background || scene.background).match(/[\da-f]{2}/gi).map((part) => parseInt(part, 16));
      const palette = Array.from({ length: 4 }, (_, level) => "#" + front.map((value, index) =>
        Math.floor((value * level + back[index] * (3 - level)) / 3).toString(16).padStart(2, "0")).join(""));
      const left = element.x - Math.floor(drawWidth / 2), top = element.y - Math.floor(element.height / 2);
      for (let index = 0; index < drawWidth * element.height; index++) {
        const column = index % drawWidth, row = Math.floor(index / drawWidth);
        const source = element.op === "number" ? (element.characters ? element.characters.indexOf(digits[Math.floor(column / element.width)]) : Number(digits[Math.floor(column / element.width)])) * element.width * element.height + row * element.width + column % element.width : index;
        const packed = parseInt(element.pixels.slice(Math.floor(source / 4) * 2, Math.floor(source / 4) * 2 + 2), 16);
        const level = (packed >> (6 - (source % 4) * 2)) & 3;
        if (level) pixel(left + column, top + row, palette[level]);
      }
    }
  }
  return data;
}

export function renderScene(canvas, scene) {
  const ctx = canvas.getContext("2d");
  const image = ctx.createImageData(240, 240);
  image.data.set(rasterize(scene));
  ctx.putImageData(image, 0, 0);
}

// Pixel raster contract mirrored by the firmware and checked with shared scenes.
export function rasterize(scene, localValue = NaN, frames = {}) {
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
  const parts = (value) => value.match(/[\da-f]{2}/gi).map((part) => parseInt(part, 16));
  const shade = (front, back) => {
    const f = parts(front), b = parts(back);
    const table = Array.from({ length: 16 }, (_, level) => "#" + f.map((value, index) =>
      Math.floor((value * level + b[index] * (15 - level)) / 15).toString(16).padStart(2, "0")).join(""));
    return (x, y, level) => pixel(x, y, table[level]);
  };
  const isqrt = (value) => {
    let result = 0, bit = 1 << 28;
    while (bit > value) bit >>= 2;
    while (bit) {
      if (value >= result + bit) { value -= result + bit; result = (result >> 1) + bit; }
      else result >>= 1;
      bit >>= 2;
    }
    return result;
  };
  const level16 = (coverage, smooth) => smooth ? Math.trunc(coverage * 15 / 16) : coverage >= 8 ? 15 : 0;
  const clamp16 = (value) => Math.max(0, Math.min(16, value));
  const unit = (degrees) => [Math.round(Math.sin(degrees * Math.PI / 180) * 1024), Math.round(-Math.cos(degrees * Math.PI / 180) * 1024)];
  const band = (cx, cy, outer, inner, start, end, cap, smooth, plot) => {
    const whole = end - start >= 360;
    const [sx, sy] = unit(start), [ex, ey] = unit(end);
    const middle = Math.trunc((outer + inner) / 2), half = Math.trunc((outer - inner) / 2);
    const solid = inner < 0 ? Math.max(0, Math.trunc((outer - 8) / 16) - 1) : 0;
    const capped = (dx, dy, ux, uy) => {
      const px = dx * 16 - Math.trunc(ux * middle / 1024), py = dy * 16 - Math.trunc(uy * middle / 1024);
      if (Math.abs(px) >= half + 8 || Math.abs(py) >= half + 8) return 0;
      return clamp16(half + 8 - isqrt(px * px + py * py));
    };
    const visit = (dx, dy) => {
      const squared = dx * dx + dy * dy;
      let coverage = 16;
      if (squared > solid * solid) {
        const distance = isqrt(squared << 8);
        coverage = Math.min(clamp16(outer - distance + 8), clamp16(distance - inner + 8));
      }
      if (!whole) {
        const from = clamp16(Math.trunc((sx * dy - sy * dx) / 64) + 8), to = clamp16(8 - Math.trunc((ex * dy - ey * dx) / 64));
        coverage = Math.min(coverage, end - start < 180 ? Math.min(from, to) : Math.max(from, to));
        if (cap) coverage = Math.max(coverage, capped(dx, dy, sx, sy), capped(dx, dy, ex, ey));
      }
      const level = level16(coverage, smooth);
      if (level) plot(cx + dx, cy + dy, level);
    };
    const reach = Math.trunc((outer + 8) / 16) + 1, hole = Math.trunc((inner - 8) / 16) - 1;
    for (let dy = -reach; dy <= reach; dy++) {
      const last = isqrt(reach * reach - dy * dy);
      const first = hole > 0 && Math.abs(dy) < hole ? isqrt(hole * hole - dy * dy) + 1 : 0;
      for (let dx = first; dx <= last; dx++) {
        visit(dx, dy);
        if (dx) visit(-dx, dy);
      }
    }
  };
  const polygon = (points, smooth, plot) => {
    const ys = points.map((point) => point[1]);
    const low = Math.trunc(Math.min(...ys) / 4), high = Math.trunc((Math.max(...ys) + 3) / 4);
    for (let y = Math.max(0, low - 1); y <= Math.min(239, high + 1); y++) {
      const row = new Int32Array(240);
      for (let sub = 1; sub < 8; sub += 2) {
        const sample = y * 8 + sub, crossings = [];
        for (let index = 0; index < points.length; index++) {
          const a = points[index], b = points[(index + 1) % points.length];
          const ax = a[0] * 2 + 4, ay = a[1] * 2 + 4, bx = b[0] * 2 + 4, by = b[1] * 2 + 4;
          if ((ay <= sample) !== (by <= sample)) crossings.push(ax + Math.trunc((sample - ay) * (bx - ax) / (by - ay)));
        }
        crossings.sort((p, q) => p - q);
        for (let index = 0; index + 1 < crossings.length; index += 2) {
          const left = crossings[index], right = crossings[index + 1];
          for (let x = Math.max(0, left >> 3); x <= Math.min(239, (right - 1) >> 3); x++)
            row[x] += Math.max(0, Math.min(right, x * 8 + 8) - Math.max(left, x * 8));
        }
      }
      for (let x = 0; x < 240; x++) {
        const level = smooth ? Math.trunc(row[x] * 15 / 32) : row[x] >= 16 ? 15 : 0;
        if (level) plot(x, y, level);
      }
    }
  };
  const wu = (x1, y1, x2, y2, plot) => {
    const steep = Math.abs(y2 - y1) > Math.abs(x2 - x1);
    if (steep) [x1, y1, x2, y2] = [y1, x1, y2, x2];
    if (x1 > x2) [x1, y1, x2, y2] = [x2, y2, x1, y1];
    const span = x2 - x1, gradient = span ? Math.trunc((y2 - y1) * 65536 / span) : 0;
    let minor = y1 * 65536;
    for (let major = x1; major <= x2; major++, minor += gradient) {
      const whole = minor >> 16, part = (minor >> 12) & 15;
      if (15 - part > 0) { if (steep) plot(whole, major, 15 - part); else plot(major, whole, 15 - part); }
      if (part > 0) { if (steep) plot(whole + 1, major, part); else plot(major, whole + 1, part); }
    }
  };
  const stroked = (element, x1, y1, x2, y2) => {
    if (element.background) wu(x1, y1, x2, y2, shade(element.stroke, element.background));
    else line(x1, y1, x2, y2, element.stroke);
  };
  const frameBytes = (encoded) => Uint8Array.from(atob(encoded), (character) => character.charCodeAt(0));
  for (const element of scene.elements) {
    if (element.op === "image") {
      // An unknown frame draws the placeholder, exactly as the Dial does before its fetch completes.
      const bytes = frames[element.crc] ? frameBytes(frames[element.crc]) : null;
      const scale = element.scale || 1;
      const left = element.x - Math.trunc(element.width * scale / 2), top = element.y - Math.trunc(element.height * scale / 2);
      const put = (x, y, r, g, b) => {
        if (x < 0 || x >= 240 || y < 0 || y >= 240) return;
        data.set([r, g, b, 255], (y * 240 + x) * 4);
      };
      const [fr, fg, fb] = element.fill ? colour(element.fill) : [0, 0, 0];
      for (let row = 0; row < element.height; row++) {
        for (let column = 0; column < element.width; column++) {
          if (!bytes && !element.fill) continue;
          let r = fr, g = fg, b = fb;
          if (bytes) {
            const at = (row * element.width + column) * 2, value = bytes[at] << 8 | bytes[at + 1];
            r = Math.floor(((value >> 11) & 31) * 255 / 31); g = Math.floor(((value >> 5) & 63) * 255 / 63); b = Math.floor((value & 31) * 255 / 31);
          }
          for (let dy = 0; dy < scale; dy++) for (let dx = 0; dx < scale; dx++) put(left + column * scale + dx, top + row * scale + dy, r, g, b);
        }
      }
    } else if (element.op === "polygon") {
      polygon(element.points, Boolean(element.background), shade(element.fill, element.background || element.fill));
    } else if (element.op === "segments") {
      for (let index = 0; index + 3 < element.lines.length; index += 4)
        stroked(element, element.lines[index], element.lines[index + 1], element.lines[index + 2], element.lines[index + 3]);
    } else if (element.op === "circle" && element.solid) {
      const smooth = Boolean(element.background), width = element.width || 1;
      const outer = element.r * 16 + 8, inner = (element.r - width) * 16 + 8;
      if (element.stroke && element.fill) {
        band(element.x, element.y, outer, -1000, 0, 360, false, smooth, shade(element.stroke, element.background || element.stroke));
        band(element.x, element.y, inner, -1000, 0, 360, false, smooth, shade(element.fill, element.stroke));
      } else if (element.fill) {
        band(element.x, element.y, outer, -1000, 0, 360, false, smooth, shade(element.fill, element.background || element.fill));
      } else if (element.stroke) {
        band(element.x, element.y, outer, inner, 0, 360, false, smooth, shade(element.stroke, element.background || element.stroke));
      }
    } else if (element.op === "circle") {
      if (element.fill) circle(element.x, element.y, element.r, element.fill, true);
      if (element.stroke) for (let width = 0; width < (element.width || 1); width++)
        circle(element.x, element.y, Math.max(0, element.r - width), element.stroke);
    } else if (element.op === "arc" || element.op === "gauge") {
      const value = local ? Math.round((localValue - (element.minimum ?? 0)) * 100 / ((element.maximum ?? 100) - (element.minimum ?? 0))) : element.value;
      const end = element.op === "gauge" ? element.start + Math.round((element.end - element.start) * Math.max(0, Math.min(100, value)) / 100) : element.end;
      const stroke = element.op === "gauge" && local ? (element.fill || element.stroke) : element.stroke;
      if (element.solid) {
        const inner = element.r - Math.floor(element.width / 2);
        if (end > element.start)
          band(element.x, element.y, (inner + element.width - 1) * 16 + 8, inner * 16 - 8, element.start, end, Boolean(element.cap),
            Boolean(element.background), shade(stroke, element.background || stroke));
        continue;
      }
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
        stroked(element, ...element.points[index - 1], ...element.points[index]);
    } else if (element.op === "line") {
      stroked(element, element.x1, element.y1, element.x2, element.y2);
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

export function renderScene(canvas, scene, frames = {}) {
  const ctx = canvas.getContext("2d");
  const image = ctx.createImageData(240, 240);
  image.data.set(rasterize(scene, NaN, frames));
  ctx.putImageData(image, 0, 0);
}

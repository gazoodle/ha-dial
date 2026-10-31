#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <utility>
#include <vector>

namespace esphome::ha_dial {

// Integer raster contract shared with the card and checked with the same fixture.
template<typename Plot> class Raster {
 public:
  explicit Raster(Plot plot) : plot_(plot) {}

  template<typename Colour>
  void line(int x1, int y1, int x2, int y2, Colour colour) {
    int dx = std::abs(x2 - x1), sx = x1 < x2 ? 1 : -1;
    int dy = -std::abs(y2 - y1), sy = y1 < y2 ? 1 : -1;
    int error = dx + dy;
    while (true) {
      pixel(x1, y1, colour);
      if (x1 == x2 && y1 == y2) break;
      int twice = error * 2;
      if (twice >= dy) { error += dy; x1 += sx; }
      if (twice <= dx) { error += dx; y1 += sy; }
    }
  }

  template<typename Colour>
  void circle(int cx, int cy, int radius, Colour colour, bool fill = false) {
    int x = radius, y = 0, error = 1 - radius;
    while (x >= y) {
      if (fill) {
        line(cx-x, cy+y, cx+x, cy+y, colour); line(cx-x, cy-y, cx+x, cy-y, colour);
        line(cx-y, cy+x, cx+y, cy+x, colour); line(cx-y, cy-x, cx+y, cy-x, colour);
      } else {
        pixel(cx+x, cy+y, colour); pixel(cx+y, cy+x, colour);
        pixel(cx-y, cy+x, colour); pixel(cx-x, cy+y, colour);
        pixel(cx-x, cy-y, colour); pixel(cx-y, cy-x, colour);
        pixel(cx+y, cy-x, colour); pixel(cx+x, cy-y, colour);
      }
      y++;
      if (error < 0) error += 2*y + 1;
      else { x--; error += 2*(y-x) + 1; }
    }
  }

  template<typename Colour>
  void pixel(int x, int y, Colour colour) {
    if (x >= 0 && x < 240 && y >= 0 && y < 240) plot_(x, y, colour);
  }

 private:
  Plot plot_;
};

// Coverage rasters. Integer arithmetic only, so card and device agree pixel for pixel.
// plot(x, y, level) receives a blend level from 1 to 15; hard edges always plot 15.
inline int integer_sqrt(int value) {
  int result = 0, bit = 1 << 28;
  while (bit > value) bit >>= 2;
  while (bit) {
    if (value >= result + bit) { value -= result + bit; result = (result >> 1) + bit; }
    else result >>= 1;
    bit >>= 2;
  }
  return result;
}

inline int coverage_level(int coverage, bool smooth) {
  return smooth ? coverage * 15 / 16 : coverage >= 8 ? 15 : 0;
}

// Annular sector between edge radii in sixteenths of a pixel. Degrees run clockwise from 12.
template<typename Plot>
void coverage_band(int cx, int cy, int outer, int inner, int start, int end, bool cap, bool smooth, Plot plot) {
  const bool whole = end - start >= 360;
  const double to_radians = M_PI / 180.0;
  const int sx = static_cast<int>(std::floor(std::sin(start * to_radians) * 1024 + 0.5));
  const int sy = static_cast<int>(std::floor(-std::cos(start * to_radians) * 1024 + 0.5));
  const int ex = static_cast<int>(std::floor(std::sin(end * to_radians) * 1024 + 0.5));
  const int ey = static_cast<int>(std::floor(-std::cos(end * to_radians) * 1024 + 0.5));
  const int middle = (outer + inner) / 2, half = (outer - inner) / 2;
  const int solid = inner < 0 ? std::max(0, (outer - 8) / 16 - 1) : 0;
  const auto clamp16 = [](int value) { return std::clamp(value, 0, 16); };
  const auto cap_coverage = [&](int dx, int dy, int ux, int uy) {
    const int px = dx * 16 - ux * middle / 1024, py = dy * 16 - uy * middle / 1024;
    if (std::abs(px) >= half + 8 || std::abs(py) >= half + 8) return 0;
    return clamp16(half + 8 - integer_sqrt(px * px + py * py));
  };
  const auto visit = [&](int dx, int dy) {
    const int squared = dx * dx + dy * dy;
    int coverage = 16;
    if (squared > solid * solid) {
      const int distance = integer_sqrt(squared << 8);
      coverage = std::min(clamp16(outer - distance + 8), clamp16(distance - inner + 8));
    }
    if (!whole) {
      const int from = clamp16((sx * dy - sy * dx) / 64 + 8), to = clamp16(8 - (ex * dy - ey * dx) / 64);
      coverage = std::min(coverage, end - start < 180 ? std::min(from, to) : std::max(from, to));
      if (cap) coverage = std::max({coverage, cap_coverage(dx, dy, sx, sy), cap_coverage(dx, dy, ex, ey)});
    }
    const int level = coverage_level(coverage, smooth);
    if (level) plot(cx + dx, cy + dy, level);
  };
  const int reach = (outer + 8) / 16 + 1, hole = (inner - 8) / 16 - 1;
  for (int dy = -reach; dy <= reach; dy++) {
    const int last = integer_sqrt(reach * reach - dy * dy);
    const int first = hole > 0 && std::abs(dy) < hole ? integer_sqrt(hole * hole - dy * dy) + 1 : 0;
    for (int dx = first; dx <= last; dx++) {
      visit(dx, dy);
      if (dx) visit(-dx, dy);
    }
  }
}

// Even-odd polygon in quarter pixels, where a whole coordinate is a pixel centre.
template<typename Point, typename Plot>
void coverage_polygon(const std::vector<Point> &points, bool smooth, Plot plot) {
  int low = 239, high = 0;
  for (const auto &point : points) {
    low = std::min(low, static_cast<int>(point.second) / 4);
    high = std::max(high, (static_cast<int>(point.second) + 3) / 4);
  }
  std::vector<int> crossings;
  crossings.reserve(points.size());
  std::array<int, 240> row{};
  for (int y = std::max(0, low - 1); y <= std::min(239, high + 1); y++) {
    row.fill(0);
    for (int sub = 1; sub < 8; sub += 2) {
      const int sample = y * 8 + sub;
      crossings.clear();
      for (size_t index = 0; index < points.size(); index++) {
        const auto &a = points[index], &b = points[(index + 1) % points.size()];
        const int ax = a.first * 2 + 4, ay = a.second * 2 + 4, bx = b.first * 2 + 4, by = b.second * 2 + 4;
        if ((ay <= sample) != (by <= sample)) crossings.push_back(ax + (sample - ay) * (bx - ax) / (by - ay));
      }
      std::sort(crossings.begin(), crossings.end());
      for (size_t index = 0; index + 1 < crossings.size(); index += 2) {
        const int left = crossings[index], right = crossings[index + 1];
        for (int x = std::max(0, left >> 3); x <= std::min(239, (right - 1) >> 3); x++)
          row[x] += std::max(0, std::min(right, x * 8 + 8) - std::max(left, x * 8));
      }
    }
    for (int x = 0; x < 240; x++) {
      const int level = smooth ? row[x] * 15 / 32 : row[x] >= 16 ? 15 : 0;
      if (level) plot(x, y, level);
    }
  }
}

// Wu line in 16.16 fixed point.
template<typename Plot>
void coverage_line(int x1, int y1, int x2, int y2, Plot plot) {
  const bool steep = std::abs(y2 - y1) > std::abs(x2 - x1);
  if (steep) { std::swap(x1, y1); std::swap(x2, y2); }
  if (x1 > x2) { std::swap(x1, x2); std::swap(y1, y2); }
  const int span = x2 - x1;
  const int gradient = span ? (y2 - y1) * 65536 / span : 0;
  int minor = y1 * 65536;
  for (int major = x1; major <= x2; major++, minor += gradient) {
    const int whole = minor >> 16, part = (minor >> 12) & 15;
    if (15 - part > 0) { if (steep) plot(whole, major, 15 - part); else plot(major, whole, 15 - part); }
    if (part > 0) { if (steep) plot(whole + 1, major, part); else plot(major, whole + 1, part); }
  }
}
}  // namespace esphome::ha_dial

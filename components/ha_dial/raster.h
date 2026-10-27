#pragma once

#include <algorithm>
#include <cmath>

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
}  // namespace esphome::ha_dial

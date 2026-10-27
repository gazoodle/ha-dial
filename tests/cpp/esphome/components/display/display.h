#pragma once
#include <array>
#include <cstdint>
namespace esphome {
struct Color {
  uint8_t r, g, b;
  Color(int r, int g, int b) : r(r), g(g), b(b) {}
  static const Color BLACK;
};
inline const Color Color::BLACK{0, 0, 0};
namespace display {
class Display {
 public:
  std::array<uint8_t, 240*240*4> pixels{};
  void draw_pixel_at(int x, int y, Color c) {
    if (x < 0 || x >= 240 || y < 0 || y >= 240) return;
    auto index = (y*240+x)*4;
    pixels[index] = (c.r >> 3)*255/31;
    pixels[index+1] = (c.g >> 2)*255/63;
    pixels[index+2] = (c.b >> 3)*255/31;
    pixels[index+3] = 255;
  }
  void fill(Color c) {
    for (int y=0; y<240; y++) for (int x=0; x<240; x++) draw_pixel_at(x,y,c);
  }
};
}
}

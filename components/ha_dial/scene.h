#pragma once

#include <array>
#include <string>
#include <memory>
#include <utility>
#include <limits>
#include <vector>
#include "esphome/components/json/json_util.h"
#include "esphome/components/display/display.h"

namespace esphome::ha_dial {
inline constexpr size_t MAX_VIEW_BYTES = 24576;
int hex_value(char value);
Color scene_colour(const std::string &value, const Color &fallback);
struct SceneElement {
  char op{' '};
  int value{0}, precision{0}, glyphs{10};
  float minimum{0}, maximum{100};
  int x{0}, y{0}, x2{0}, y2{0}, radius{0}, start{0}, end{0}, width{1}, mask_width{0}, mask_height{0};
  Color stroke{Color::BLACK}, fill{Color::BLACK}, colour{Color::BLACK}, background{Color::BLACK};
  bool has_stroke{false}, has_fill{false};
  std::string pixels;
  std::vector<std::pair<uint8_t, uint8_t>> points;
};

struct SceneRegion {
  std::string id;
  int value{0};
  int x{0}, y{0}, radius{0};
};

struct SceneBuffer {
  std::array<SceneElement, 64> elements{};
  std::array<SceneRegion, 16> regions{};
  size_t element_count{0}, region_count{0};
  std::string background, screen;
  bool valid{false};
};

struct SceneHistory {
  std::unique_ptr<SceneBuffer> current, previous;
  uint64_t revision{0};

  bool apply(uint64_t next, std::unique_ptr<SceneBuffer> scene,
             std::unique_ptr<SceneBuffer> parent) {
    if (next <= revision) return false;
    current = std::move(scene);
    previous = std::move(parent);
    revision = next;
    return true;
  }

  bool back() {
    if (!previous) return false;
    current = std::move(previous);
    return true;
  }
};

bool parse_scene(JsonObject source, SceneBuffer &target);
bool parse_clear_request(JsonObject source, uint64_t applied_revision, uint64_t &revision);
void draw_scene(display::Display &it, const SceneBuffer &scene, float local_value = std::numeric_limits<float>::quiet_NaN());
}  // namespace esphome::ha_dial

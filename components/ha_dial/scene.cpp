#include "scene.h"
#include "raster.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <utility>

namespace esphome::ha_dial {
int hex_value(char value) {
  if (value >= '0' && value <= '9')
    return value - '0';
  if (value >= 'a' && value <= 'f')
    return value - 'a' + 10;
  if (value >= 'A' && value <= 'F')
    return value - 'A' + 10;
  return -1;
}

static bool valid_colour(const char *value) {
  return value != nullptr && strlen(value) == 7 && value[0] == '#' &&
         std::all_of(value + 1, value + 7, [](char digit) { return hex_value(digit) >= 0; });
}

Color scene_colour(const std::string &value, const Color &fallback) {
  if (value.size() != 7 || value[0] != '#')
    return fallback;
  const auto component = [&value](size_t offset) {
    return hex_value(value[offset]) * 16 + hex_value(value[offset + 1]);
  };
  return Color(component(1), component(3), component(5));
}

static Color blend_scene_colour(const Color &front, const Color &back, int level) {
  const auto blend = [level](int f, int b) { return (f*level + b*(15-level))/15; };
  return Color(blend(front.r, back.r), blend(front.g, back.g), blend(front.b, back.b));
}

bool parse_clear_request(JsonObject source, uint64_t applied_revision, uint64_t &revision) {
  if (!source["clear"].is<bool>() || !source["clear"].as<bool>() ||
      !source["scene"].isNull() || !source["previous"].isNull() ||
      !source["revision"].is<uint64_t>()) return false;
  const uint64_t incoming = source["revision"].as<uint64_t>();
  if (incoming <= applied_revision) return false;
  revision = incoming;
  return true;
}

bool parse_scene(JsonObject source, SceneBuffer &target) {
    target.element_count = target.region_count = 0;
    target.valid = false;
    if (((source["version"] | 0) < 1 || (source["version"] | 0) > 4) || (source["width"] | 0) != 240 ||
        (source["height"] | 0) != 240 || !valid_colour(source["background"]))
      return false;
    const char *screen = source["screen"];
    if (screen == nullptr || strlen(screen) > 320)
      return false;
    target.screen = screen;
    target.background = source["background"].as<std::string>();
    JsonArray elements = source["elements"].as<JsonArray>();
    if (elements.isNull() || elements.size() > target.elements.size())
      return false;
    for (JsonObject input : elements) {
      const char *operation = input["op"];
      if (operation == nullptr)
        return false;
      SceneElement element;
      const char *stroke = input["stroke"] | "";
      const char *fill = input["fill"] | "";
      if ((*stroke && !valid_colour(stroke)) || (*fill && !valid_colour(fill))) return false;
      element.has_stroke = *stroke;
      element.has_fill = *fill;
      element.stroke = scene_colour(stroke, Color::BLACK);
      element.fill = scene_colour(fill, Color::BLACK);
      element.width = input["width"] | 1;
      if (strcmp(operation, "polyline") == 0) {
        if ((source["version"] | 0) < 4 || !element.has_stroke) return false;
        element.op = 'p';
        JsonArray points = input["points"].as<JsonArray>();
        if (points.isNull() || points.size() < 2 || points.size() > 128) return false;
        element.points.reserve(points.size());
        for (JsonVariant value : points) {
          JsonArray point = value.as<JsonArray>();
          if (point.isNull() || point.size() != 2 || !point[0].is<int>() || !point[1].is<int>()) return false;
          const int x = point[0].as<int>(), y = point[1].as<int>();
          if (x < 0 || x >= 240 || y < 0 || y >= 240) return false;
          element.points.emplace_back(x, y);
        }
      } else if (strcmp(operation, "line") == 0) {
        element.op = 'l';
        element.x = input["x1"] | -1;
        element.y = input["y1"] | -1;
        element.x2 = input["x2"] | -1;
        element.y2 = input["y2"] | -1;
        if (element.x < 0 || element.x >= 240 || element.y < 0 || element.y >= 240 ||
            element.x2 < 0 || element.x2 >= 240 || element.y2 < 0 || element.y2 >= 240)
          return false;
      } else {
        element.x = input["x"] | -1;
        element.y = input["y"] | -1;
        element.radius = input["r"] | 0;
        if (element.x < 0 || element.x >= 240 || element.y < 0 || element.y >= 240 ||
            element.radius < 0 || element.radius > 120 || element.width < 1 ||
            (strcmp(operation, "mask") != 0 && strcmp(operation, "number") != 0 && element.width > 16))
          return false;
      }
      if (strcmp(operation, "circle") == 0) {
        element.op = 'c';
      } else if ((strcmp(operation, "arc") == 0 || strcmp(operation, "gauge") == 0)) {
        element.op = strcmp(operation, "gauge") == 0 ? 'g' : 'a';
        element.value = input["value"] | 0;
        element.minimum = input["minimum"] | 0.0f;
        element.maximum = input["maximum"] | 100.0f;
        if (!std::isfinite(element.minimum) || !std::isfinite(element.maximum) || element.minimum >= element.maximum) return false;
        if (element.op == 'g' && (element.value < 0 || element.value > 100)) return false;
        element.start = input["start"] | 0;
        element.end = input["end"] | 0;
        if (element.start < -360 || element.start > 360 || element.end < -360 ||
            element.end > 360 || element.end < element.start || element.end - element.start > 360)
          return false;
      } else if ((strcmp(operation, "mask") == 0 || strcmp(operation, "number") == 0)) {
        element.op = strcmp(operation, "number") == 0 ? 'n' : 'm';
        element.value = input["value"] | -1;
        const char *characters = input["characters"] | "0123456789";
        if (strcmp(characters, "0123456789.-") == 0) element.glyphs = 12;
        else if (strcmp(characters, "0123456789") != 0) return false;
        element.precision = input["precision"] | 0;
        if (element.precision < 0 || element.precision > 2 || (element.precision && element.glyphs != 12)) return false;
        if (element.op == 'n' && (!element.has_stroke || (element.glyphs == 10 && (element.value < 0 || element.value > 999)) || (element.glyphs == 12 && (element.value < -999999 || element.value > 999999)))) return false;
        element.mask_width = input["width"] | 0;
        element.mask_height = input["height"] | 0;
        const char *colour = input["colour"] | "";
        const char *background = input["background"] | target.background.c_str();
        const char *pixels = input["pixels"];
        const size_t expected = static_cast<size_t>(element.mask_width) * element.mask_height * (element.op == 'n' ? element.glyphs : 1);
        const size_t packed_length = ((expected + 3) / 4) * 2;
        if (element.mask_width <= 0 || element.mask_width > (element.op == 'n' ? 32 : 120) || element.mask_height <= 0 ||
            element.mask_height > 32 || pixels == nullptr || strlen(pixels) != packed_length ||
            !valid_colour(colour) ||
            !valid_colour(background) ||
            !std::all_of(pixels, pixels + packed_length,
                         [](char digit) { return hex_value(digit) >= 0; }))
          return false;
        element.pixels = pixels;
        element.colour = scene_colour(colour, Color::BLACK);
        element.background = scene_colour(background, Color::BLACK);
      } else if (strcmp(operation, "line") != 0 && strcmp(operation, "polyline") != 0) {
        return false;
      }
      if ((element.op == 'l' || element.op == 'a' || element.op == 'g') && !element.has_stroke) return false;
      target.elements[target.element_count++] = std::move(element);
    }
    JsonArray regions = source["regions"].as<JsonArray>();
    if (regions.isNull() || regions.size() > target.regions.size())
      return false;
    for (JsonObject input : regions) {
      const char *id = input["id"];
      SceneRegion region;
      region.x = input["x"] | -1;
      region.y = input["y"] | -1;
      region.radius = input["r"] | 0;
      if (id == nullptr || strlen(id) > 64 || region.x < 0 || region.x >= 240 || region.y < 0 ||
          region.y >= 240 || region.radius < 1 || region.radius > 120)
        return false;
      region.id = id;
      target.regions[target.region_count++] = std::move(region);
    }
    target.valid = true;
    return true;
}

void draw_scene(display::Display &it, const SceneBuffer &scene, float local_value) {
  Raster raster([&it](int x, int y, Color colour) { it.draw_pixel_at(x, y, colour); });
  const bool local = std::isfinite(local_value);
  const Color background = scene_colour(scene.background, Color::BLACK);
  it.fill(background);
    for (size_t index = 0; index < scene.element_count; index++) {
      const auto &element = scene.elements[index];
      if (element.op == 'c') {
        if (element.has_fill)
          raster.circle(element.x, element.y, element.radius,
                           element.fill, true);
        if (element.has_stroke) {
          const Color stroke = element.stroke;
          for (int width = 0; width < element.width; width++)
            raster.circle(element.x, element.y, std::max(0, element.radius - width), stroke);
        }
      } else if (element.op == 'a' || element.op == 'g') {
        const int value = local ? static_cast<int>(std::floor((local_value - element.minimum) * 100 / (element.maximum - element.minimum) + 0.5f)) : element.value;
        const int end = element.op == 'g' ? element.start + static_cast<int>(std::floor((element.end - element.start) * std::clamp(value, 0, 100) / 100.0 + 0.5)) : element.end;
        const Color stroke = element.op == 'g' && local && element.has_fill ? element.fill : element.stroke;
        for (int thickness = 0; thickness < element.width; thickness++) {
          const int radius = std::max(1, element.radius + thickness - element.width / 2);
          int previous_x = 0, previous_y = 0;
          bool first = true;
          for (int degree = element.start; degree <= end; degree += 3) {
            const double angle = (degree - 90) * M_PI / 180.0;
            const int x = element.x + static_cast<int>(std::floor(std::cos(angle) * radius + 0.5));
            const int y = element.y + static_cast<int>(std::floor(std::sin(angle) * radius + 0.5));
            if (!first)
              raster.line(previous_x, previous_y, x, y, stroke);
            previous_x = x;
            previous_y = y;
            first = false;
          }
        }
      } else if (element.op == 'p') {
        for (size_t point = 1; point < element.points.size(); point++) {
          const auto &a = element.points[point - 1], &b = element.points[point];
          raster.line(a.first, a.second, b.first, b.second, element.stroke);
        }
      } else if (element.op == 'l') {
        raster.line(element.x, element.y, element.x2, element.y2,
                element.stroke);
      } else if (element.op == 'm' || element.op == 'n') {
        std::string digits;
        if (element.op == 'n') {
          if (element.glyphs == 12) {
            const int scale = element.precision == 2 ? 100 : element.precision == 1 ? 10 : 1;
            const double value = local ? std::clamp(static_cast<double>(local_value), -999999.0 / scale, 999999.0 / scale) : static_cast<double>(element.value) / scale;
            char buffer[20];
            snprintf(buffer, sizeof(buffer), "%.*f", element.precision, value == 0 ? 0.0 : value);
            digits = buffer;
          } else digits = std::to_string(std::clamp(local ? static_cast<int>(std::floor(local_value + 0.5f)) : element.value, 0, 999));
        }
        const int draw_width = element.mask_width * (element.op == 'n' ? digits.size() : 1);
        const Color colour = element.op == 'n' && local ? element.stroke : element.colour;
        const int left = element.x - draw_width / 2;
        const int top = element.y - element.mask_height / 2;
        for (int pixel = 0; pixel < draw_width * element.mask_height; pixel++) {
          const int column = pixel % draw_width, row = pixel / draw_width;
          const int source_pixel = element.op == 'n' ? (digits[column / element.mask_width] == '.' ? 10 : digits[column / element.mask_width] == '-' ? 11 : digits[column / element.mask_width] - '0') * element.mask_width * element.mask_height + row * element.mask_width + column % element.mask_width : pixel;
          const size_t packed_index = static_cast<size_t>(source_pixel / 4) * 2;
          const int packed = hex_value(element.pixels[packed_index]) * 16 +
                             hex_value(element.pixels[packed_index + 1]);
          const int level = ((packed >> (6 - (source_pixel % 4) * 2)) & 3) * 5;
          if (level == 0)
            continue;
          const int x = left + column;
          const int y = top + row;
          if (x >= 0 && x < 240 && y >= 0 && y < 240)
            it.draw_pixel_at(x, y, blend_scene_colour(colour, element.background, level));
        }
      }
    }
}
}  // namespace esphome::ha_dial

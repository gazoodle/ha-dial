#include "raster.h"
#include "scene.h"
#include <cassert>
#include <iostream>
#include <iterator>
#include <memory>
#include <vector>

using namespace esphome::ha_dial;
int main() {
  std::string input((std::istreambuf_iterator<char>(std::cin)), {});
  ArduinoJson::JsonDocument document;
  assert(!ArduinoJson::deserializeJson(document, input));
  for (JsonObject source : document.as<JsonArray>()) {
    auto scene = std::make_unique<SceneBuffer>();
    assert(parse_scene(source, *scene));
    auto display = std::make_unique<esphome::display::Display>();
    // Frames travel outside the scene: base64 here, as the browser has them, into the Dial's buffer shape.
    std::vector<uint8_t> frame_bytes;
    FrameView frame;
    if (const SceneElement *image = scene_image(*scene)) {
      const std::string key = std::to_string(image->crc);
      const char *encoded = source["test_frames"][key] | "";
      static const std::string alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
      int bits = 0, buffer = 0;
      for (const char *cursor = encoded; *cursor && *cursor != '='; cursor++) {
        buffer = (buffer << 6) | static_cast<int>(alphabet.find(*cursor));
        bits += 6;
        if (bits >= 8) { bits -= 8; frame_bytes.push_back((buffer >> bits) & 0xFF); }
      }
      if (!frame_bytes.empty()) {
        assert(frame_crc32(frame_bytes.data(), frame_bytes.size()) == image->crc);
        frame = {frame_bytes.data(), image->mask_width, image->mask_height, image->crc};
      }
    }
    draw_scene(*display, *scene, source["test_local_value"] | std::numeric_limits<float>::quiet_NaN(), &frame);
    std::cout.write(reinterpret_cast<const char *>(display->pixels.data()), display->pixels.size());
    const int version = source["version"];
    source["version"] = 7;
    auto unknown = std::make_unique<SceneBuffer>();
    assert(!parse_scene(source, *unknown));
    source["version"] = version;
    for (JsonObject element : source["elements"].as<JsonArray>()) {
      if (element["op"].as<std::string>() != "polyline") continue;
      source["version"] = 3;
      assert(!parse_scene(source, *unknown));
      source["version"] = version;
      const int x = element["points"][0][0];
      element["points"][0][0] = 240;
      assert(!parse_scene(source, *unknown));
      element["points"][0][0] = x;
      element["points"][0][0] = 1.5;
      assert(!parse_scene(source, *unknown));
      element["points"][0][0] = x;
    }
    for (JsonObject element : source["elements"].as<JsonArray>()) {
      const std::string op = element["op"].as<std::string>();
      if (op == "image") {
        source["version"] = 5;
        assert(!parse_scene(source, *unknown));
        source["version"] = version;
        const int width = element["width"];
        element["width"] = 2000;
        assert(!parse_scene(source, *unknown));
        element["width"] = width;
        const std::string url = element["url"].as<std::string>();
        element["url"] = "https://example.invalid/frame";
        assert(!parse_scene(source, *unknown));
        element["url"] = url;
        assert(parse_scene(source, *unknown));
      } else if (op == "polygon") {
        const int x = element["points"][0][0];
        element["points"][0][0] = 960;
        assert(!parse_scene(source, *unknown));
        element["points"][0][0] = x;
      } else if (op == "segments") {
        const int x = element["lines"][0];
        element["lines"][0] = 240;
        assert(!parse_scene(source, *unknown));
        element["lines"][0] = x;
      } else if (element["solid"].is<bool>()) {
        source["version"] = 4;
        assert(!parse_scene(source, *unknown));
        source["version"] = version;
      }
    }
    source["width"] = 241;
    auto invalid = std::make_unique<SceneBuffer>();
    assert(!parse_scene(source, *invalid));
    source["width"] = 240;
    source["regions"][0]["r"] = -1;
    assert(!parse_scene(source, *invalid));
    source["regions"][0]["r"] = 16;
    for (JsonObject element : source["elements"].as<JsonArray>()) {
      if (element["op"].as<std::string>() != "number") continue;
      const std::string pixels = element["pixels"].as<std::string>();
      element["pixels"] = "00";
      assert(!parse_scene(source, *invalid));
      element["pixels"] = pixels;
      element["value"] = element["characters"].isNull() ? 1000 : 1000000;
      assert(!parse_scene(source, *invalid));
      element["value"] = 72;
    }
    for (JsonObject element : source["elements"].as<JsonArray>()) {
      if (element["op"].as<std::string>() != "mask") continue;
      element["pixels"] = "invalid";
      assert(!parse_scene(source, *invalid));
      break;
    }
  }
  SceneHistory history;
  auto current = std::make_unique<SceneBuffer>(); current->screen="child";
  auto parent = std::make_unique<SceneBuffer>(); parent->screen="parent";
  assert(history.apply(2, std::move(current), std::move(parent)));
  assert(!history.apply(1, std::make_unique<SceneBuffer>(), nullptr));
  assert(history.current->screen == "child");
  assert(history.back());
  assert(!history.back());
  assert(history.current->screen == "parent");
  assert(history.apply(3, std::make_unique<SceneBuffer>(), nullptr));
  assert(!history.previous);
  assert(history.apply(4, nullptr, nullptr));
  assert(!history.current && !history.previous);
  assert(!history.apply(3, std::make_unique<SceneBuffer>(), nullptr));
  assert(history.apply(5, std::make_unique<SceneBuffer>(), nullptr));
  uint64_t clear_revision = 0;
  assert(!ArduinoJson::deserializeJson(document, "{\"revision\":6,\"clear\":true}"));
  assert(parse_clear_request(document.as<JsonObject>(), history.revision, clear_revision));
  assert(history.apply(clear_revision, nullptr, nullptr));
  assert(!parse_clear_request(document.as<JsonObject>(), history.revision, clear_revision));
  for (const char *invalid : {"{}", "{\"clear\":true}", "{\"clear\":1,\"revision\":7}",
                             "{\"clear\":true,\"revision\":\"7\"}",
                             "{\"clear\":true,\"revision\":-1}",
                             "{\"clear\":true,\"revision\":7,\"scene\":{}}",
                             "{\"clear\":true,\"revision\":7,\"previous\":{}}"}) {
    assert(!ArduinoJson::deserializeJson(document, invalid));
    assert(!parse_clear_request(document.as<JsonObject>(), history.revision, clear_revision));
    assert(clear_revision == 6);
  }
}

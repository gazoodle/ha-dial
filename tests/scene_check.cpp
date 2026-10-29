#include "scene.h"
#include <cassert>
#include <iostream>
#include <iterator>
#include <memory>

using namespace esphome::ha_dial;
int main() {
  std::string input((std::istreambuf_iterator<char>(std::cin)), {});
  ArduinoJson::JsonDocument document;
  assert(!ArduinoJson::deserializeJson(document, input));
  for (JsonObject source : document.as<JsonArray>()) {
    auto scene = std::make_unique<SceneBuffer>();
    assert(parse_scene(source, *scene));
    auto display = std::make_unique<esphome::display::Display>();
    draw_scene(*display, *scene, source["test_local_value"] | -1.0f);
    std::cout.write(reinterpret_cast<const char *>(display->pixels.data()), display->pixels.size());
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
      element["value"] = 1000;
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

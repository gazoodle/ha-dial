#pragma once

#include <array>
#include <string>

#include "esphome/components/api/custom_api_device.h"
#include "esphome/components/display/display.h"
#include "esphome/components/font/font.h"
#include "esphome/core/component.h"

namespace esphome::ha_dial {

struct ViewItem {
  std::string id;
  std::string label;
};

class HaDial : public Component, public api::CustomAPIDevice {
 public:
  void setup() override;
  void loop() override;
  void set_device(const std::string &device) { this->device_ = device; }
  void set_display(display::Display *display) { this->display_ = display; }
  void set_font(font::Font *font) { this->font_ = font; }

  void show_view(std::string view);
  void draw(display::Display &display);
  void rotate(int direction);
  void press();
  void touch(int x, int y);
  void back();

 protected:
  void flush_value_();
  void draw_pill_(display::Display &display);
  void send_input_(const std::string &action, const std::string &item = "",
                   const std::string &value = "");

  std::string device_;
  std::string title_{"Waiting for HA"};
  std::string profile_;
  std::string unit_;
  std::string pill_pixels_;
  int pill_width_{0};
  int pill_height_{0};
  std::array<ViewItem, 8> items_{};
  size_t item_count_{0};
  size_t selected_{0};
  float value_{0};
  float confirmed_value_{0};
  float minimum_{0};
  float maximum_{0};
  float step_{1};
  bool has_value_{false};
  bool has_confirmed_value_{false};
  bool value_dirty_{false};
  bool value_pending_{false};
  bool has_back_{false};
  bool was_connected_{false};
  uint32_t last_rotate_ms_{0};
  display::Display *display_{nullptr};
  font::Font *font_{nullptr};
};

}  // namespace esphome::ha_dial

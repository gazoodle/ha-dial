#include "ha_dial.h"

#include <algorithm>
#include <cmath>
#include <map>

#include "esphome/components/json/json_util.h"
#include "esphome/core/log.h"

namespace esphome::ha_dial {

static const char *const TAG = "ha_dial";
static const Color ORANGE(244, 111, 34);
static const Color ITEM(42, 45, 50);
static constexpr uint32_t VALUE_DEBOUNCE_MS = 150;

void HaDial::setup() {
  this->register_service(&HaDial::show_view, "ha_dial_show_view", {"view"});
}

void HaDial::loop() {
  const bool connected = this->is_connected();
  if (connected && !this->was_connected_)
    this->send_input_("ready");
  this->was_connected_ = connected;
  if (this->value_dirty_ && millis() - this->last_rotate_ms_ >= VALUE_DEBOUNCE_MS)
    this->flush_value_();
}

void HaDial::show_view(std::string view) {
  if (view.size() > 4096) {
    ESP_LOGW(TAG, "Ignoring view larger than 4096 bytes");
    return;
  }
  const bool valid = json::parse_json(view, [this](JsonObject root) {
    const char *title = root["title"];
    const char *profile = root["profile"];
    const char *unit = root["unit"];
    this->title_ = title == nullptr ? "" : std::string(title).substr(0, 24);
    this->profile_ = profile == nullptr ? "" : std::string(profile).substr(0, 16);
    this->unit_ = unit == nullptr ? "" : std::string(unit).substr(0, 4);
    const bool incoming_has_value = !root["value"].isNull();
    const float incoming_value = root["value"] | 0.0f;
    this->minimum_ = root["minimum"] | 0.0f;
    this->maximum_ = root["maximum"] | 0.0f;
    this->step_ = root["step"] | 1.0f;
    if (this->maximum_ < this->minimum_)
      std::swap(this->minimum_, this->maximum_);
    if (this->step_ <= 0)
      this->step_ = 1;
    this->has_value_ = incoming_has_value;
    if (incoming_has_value) {
      this->confirmed_value_ = std::clamp(incoming_value, this->minimum_, this->maximum_);
      this->has_confirmed_value_ = true;
      if (!this->value_dirty_ && !this->value_pending_) {
        this->value_ = this->confirmed_value_;
      } else if (std::fabs(this->confirmed_value_ - this->value_) < 0.5f) {
        this->value_ = this->confirmed_value_;
        this->value_dirty_ = false;
        this->value_pending_ = false;
      }
    } else {
      this->has_confirmed_value_ = false;
      this->value_dirty_ = false;
      this->value_pending_ = false;
    }
    this->has_back_ = root["back"] | false;
    const int selected = root["selected"] | 0;
    this->selected_ = selected < 0 ? 0 : static_cast<size_t>(selected);
    this->item_count_ = 0;
    JsonArray items = root["items"].as<JsonArray>();
    for (JsonObject item : items) {
      if (this->item_count_ == this->items_.size())
        break;
      const char *id = item["id"];
      const char *label = item["label"];
      if (id == nullptr || label == nullptr)
        continue;
      auto &target = this->items_[this->item_count_++];
      target.id = std::string(id).substr(0, 32);
      target.label = std::string(label).substr(0, 24);
    }
    if (this->item_count_ == 0)
      this->selected_ = 0;
    else
      this->selected_ %= this->item_count_;
    return true;
  });
  if (!valid) {
    ESP_LOGW(TAG, "Ignoring invalid view JSON");
    return;
  }
  if (this->display_ != nullptr)
    this->display_->update();
}

void HaDial::draw(display::Display &it) {
  it.fill(Color::BLACK);
  it.circle(120, 120, 116, ORANGE);
  it.circle(120, 120, 113, ORANGE);

  for (size_t index = 0; index < this->item_count_; index++) {
    const double angle = -M_PI_2 + index * 2.0 * M_PI / this->item_count_;
    const int x = 120 + static_cast<int>(std::lround(std::cos(angle) * 88));
    const int y = 120 + static_cast<int>(std::lround(std::sin(angle) * 88));
    it.filled_circle(x, y, index == this->selected_ ? 23 : 19,
                     index == this->selected_ ? ORANGE : ITEM);
    if (this->font_ != nullptr && !this->items_[index].label.empty())
      it.printf(x, y, this->font_, Color::WHITE, display::TextAlign::CENTER, "%c",
                this->items_[index].label.front());
  }

  if (this->font_ == nullptr)
    return;
  it.print(120, 78, this->font_, ORANGE, display::TextAlign::CENTER, this->title_.c_str());
  if (this->item_count_ != 0)
    it.print(120, 120, this->font_, Color::WHITE, display::TextAlign::CENTER,
             this->items_[this->selected_].label.c_str());
  else if (this->has_value_) {
    if (this->has_confirmed_value_ && std::fabs(this->confirmed_value_ - this->value_) >= 0.5f) {
      it.printf(120, 110, this->font_, Color::WHITE, display::TextAlign::CENTER, "%.0f%s",
                this->value_, this->unit_.c_str());
      it.printf(120, 140, this->font_, Color(150, 150, 150), display::TextAlign::CENTER,
                "HA %.0f%s", this->confirmed_value_, this->unit_.c_str());
    } else {
      it.printf(120, 120, this->font_, Color::WHITE, display::TextAlign::CENTER, "%.0f%s",
                this->value_, this->unit_.c_str());
    }
  } else
    it.print(120, 120, this->font_, Color::WHITE, display::TextAlign::CENTER,
             this->profile_.empty() ? "Ready" : this->profile_.c_str());
  if (this->has_back_)
    it.print(120, 178, this->font_, Color(150, 150, 150), display::TextAlign::CENTER, "<");
}

void HaDial::rotate(int direction) {
  if (this->item_count_ == 0) {
    if (this->has_value_) {
      this->value_ = std::clamp(this->value_ + (direction < 0 ? -this->step_ : this->step_),
                                this->minimum_, this->maximum_);
      this->value_dirty_ = true;
      this->value_pending_ = false;
      this->last_rotate_ms_ = millis();
      if (this->display_ != nullptr)
        this->display_->update();
    }
    return;
  }
  this->selected_ = (this->selected_ + this->item_count_ + (direction < 0 ? -1 : 1)) %
                    this->item_count_;
  if (this->display_ != nullptr)
    this->display_->update();
  this->send_input_(direction < 0 ? "rotate_left" : "rotate_right");
}

void HaDial::press() {
  this->flush_value_();
  this->send_input_("press", this->item_count_ == 0 ? "" : this->items_[this->selected_].id);
}

void HaDial::back() {
  this->flush_value_();
  this->send_input_("back");
}

void HaDial::touch(int x, int y) {
  const int center_distance = (x - 120) * (x - 120) + (y - 120) * (y - 120);
  if (this->has_back_ && center_distance < 45 * 45) {
    this->back();
    return;
  }
  for (size_t index = 0; index < this->item_count_; index++) {
    const double angle = -M_PI_2 + index * 2.0 * M_PI / this->item_count_;
    const int item_x = 120 + static_cast<int>(std::lround(std::cos(angle) * 88));
    const int item_y = 120 + static_cast<int>(std::lround(std::sin(angle) * 88));
    if ((x - item_x) * (x - item_x) + (y - item_y) * (y - item_y) <= 30 * 30) {
      this->selected_ = index;
      if (this->display_ != nullptr)
        this->display_->update();
      this->send_input_("touch", this->items_[index].id);
      return;
    }
  }
}

void HaDial::flush_value_() {
  if (!this->value_dirty_ || !this->is_connected())
    return;
  this->value_dirty_ = false;
  this->value_pending_ = true;
  this->send_input_("set_value", "", std::to_string(this->value_));
}

void HaDial::send_input_(const std::string &action, const std::string &item,
                         const std::string &value) {
  if (!this->is_connected())
    return;
  this->fire_homeassistant_event("esphome.ha_dial_input",
                                 {{"device", this->device_},
                                  {"action", action},
                                  {"item", item},
                                  {"value", value}});
}

}  // namespace esphome::ha_dial

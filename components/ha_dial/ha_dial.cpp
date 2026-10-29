#include "ha_dial.h"
#include <esp_wifi.h>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <map>
#include <cstdlib>
#include <utility>
#include <memory>

#include "esphome/components/json/json_util.h"
#include "esphome/core/log.h"

namespace esphome::ha_dial {

static const char *const TAG = "ha_dial";
static const Color ORANGE(244, 111, 34);
static const Color ITEM(42, 45, 50);
static constexpr uint32_t VALUE_DEBOUNCE_MS = 150;
static constexpr int MAX_PILL_WIDTH = 150;
static constexpr int MAX_PILL_HEIGHT = 22;
static constexpr size_t ATLAS_FRAME_BYTES = 240 * 240 * 2;
static constexpr const char *ATLAS_FRAME_PATH = "/ha-dial/atlas-frame";

void HaDial::setup() {
  if (esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &HaDial::network_event_, this,
                                          &this->wifi_handler_) != ESP_OK ||
      esp_event_handler_instance_register(IP_EVENT, ESP_EVENT_ANY_ID, &HaDial::network_event_, this,
                                          &this->ip_handler_) != ESP_OK) {
    ESP_LOGE(TAG, "Could not subscribe to network status events");
    this->status_set_error();
  }
  this->set_timeout("startup", 0, [this]() {
    if (this->display_ != nullptr) this->display_->update();
    this->started_ = true;
    this->network_changed_ = true;
  });
  this->register_service(&HaDial::show_view, "ha_dial_show_view", {"view"});
  auto *server = web_server_base::global_web_server_base;
  if (server != nullptr) {
    server->add_handler(this);
    server->init();
    this->web_server_started_ = true;
  }
}

void HaDial::on_shutdown() {
  if (this->wifi_handler_ != nullptr)
    esp_event_handler_instance_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID, this->wifi_handler_);
  if (this->ip_handler_ != nullptr)
    esp_event_handler_instance_unregister(IP_EVENT, ESP_EVENT_ANY_ID, this->ip_handler_);
  if (this->web_server_started_ && web_server_base::global_web_server_base != nullptr)
    web_server_base::global_web_server_base->deinit();
}

float HaDial::get_setup_priority() const { return setup_priority::WIFI - 1.0f; }

bool HaDial::canHandle(AsyncWebServerRequest *request) const {
  if (request->method() != HTTP_POST)
    return false;
#ifdef USE_ESP32
  char url_buffer[AsyncWebServerRequest::URL_BUF_SIZE];
  return request->url_to(url_buffer) == ATLAS_FRAME_PATH;
#else
  return request->url() == ATLAS_FRAME_PATH;
#endif
}

void HaDial::handleBody(AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index,
                        size_t total) {
  if (index == 0) {
    this->atlas_upload_error_ = total != ATLAS_FRAME_BYTES;
    this->atlas_received_ = 0;
    if (!this->atlas_upload_error_ && this->atlas_frame_ == nullptr)
      this->atlas_frame_ = RAMAllocator<uint8_t>().make_unique_array_for_overwrite(ATLAS_FRAME_BYTES);
    if (this->atlas_frame_ == nullptr)
      this->atlas_upload_error_ = true;
  }
  if (this->atlas_upload_error_ || index != this->atlas_received_ || len > total - index) {
    this->atlas_upload_error_ = true;
    return;
  }
  std::memcpy(this->atlas_frame_.get() + index, data, len);
  this->atlas_received_ += len;
}

void HaDial::handleRequest(AsyncWebServerRequest *request) {
  if (this->atlas_upload_error_ || this->atlas_received_ != ATLAS_FRAME_BYTES) {
    request->send(this->atlas_frame_ == nullptr ? 503 : 400, "application/json",
                  this->atlas_frame_ == nullptr ? "{\"ok\":false,\"error\":\"not enough memory\"}"
                                                : "{\"ok\":false,\"error\":\"expected 115200 bytes\"}");
    return;
  }
  this->defer("atlas-frame", [this]() {
    if (this->display_ != nullptr)
      this->display_->update();
  });
  request->send(200, "application/json", "{\"ok\":true,\"bytes\":115200}");
}

void HaDial::loop() {
  if (this->network_changed_.exchange(false)) {
    // ESPHome applies driver events on its main loop before this deferred redraw.
    this->set_timeout("network-draw", 100, [this]() {
      if (this->display_ != nullptr) this->display_->update();
    });
  }
  const bool connected = this->is_connected();
  if (connected != this->was_connected_) {
    if (!connected) {
      this->scene_received_ = false;
      this->value_dirty_ = this->value_pending_ = false;
    }
    if (this->display_ != nullptr) this->display_->update();
  }
  if (connected && !this->was_connected_)
    this->send_input_("ready");
  this->was_connected_ = connected;
  if (this->value_dirty_ && millis() - this->last_rotate_ms_ >= VALUE_DEBOUNCE_MS)
    this->flush_value_();
}

void HaDial::show_view(std::string view) {
  if (view.size() > MAX_VIEW_BYTES) {
    ESP_LOGW(TAG, "Ignoring view larger than %u bytes", static_cast<unsigned>(MAX_VIEW_BYTES));
    return;
  }
  std::unique_ptr<SceneBuffer> incoming_scene;
  std::unique_ptr<SceneBuffer> incoming_previous;
  uint64_t incoming_revision = 0;
  bool stale = false;
  bool clear_requested = false;
  const bool valid = json::parse_json(view, [this, &incoming_scene,
                                             &incoming_previous, &incoming_revision,
                                             &stale, &clear_requested](JsonObject root) {
    JsonObject scene = root["scene"].as<JsonObject>();
    if (!root["clear"].isNull()) {
      clear_requested = parse_clear_request(root, this->scenes_.revision, incoming_revision);
      return clear_requested;
    }
    if (!scene.isNull()) {
      incoming_revision = root["revision"] | uint64_t(0);
      if (incoming_revision == 0 || incoming_revision <= this->scenes_.revision) {
        stale = true;
        return false;
      }
      incoming_scene = std::make_unique<SceneBuffer>();
      if (!parse_scene(scene, *incoming_scene))
        return false;
      JsonObject previous = root["previous"].as<JsonObject>();
      if (!previous.isNull()) {
        incoming_previous = std::make_unique<SceneBuffer>();
        if (!parse_scene(previous, *incoming_previous))
          return false;
      }
      if (this->scenes_.current == nullptr || this->scenes_.current->screen != incoming_scene->screen) {
        this->value_dirty_ = false;
        this->value_pending_ = false;
      }
    }
    const char *title = root["title"];
    const char *profile = root["profile"];
    const char *unit = root["unit"];
    this->title_ = title == nullptr ? "" : std::string(title).substr(0, 24);
    this->profile_ = profile == nullptr ? "" : std::string(profile).substr(0, 16);
    this->unit_ = unit == nullptr ? "" : std::string(unit).substr(0, 4);
    this->pill_pixels_.clear();
    JsonObject pill = root["pill"].as<JsonObject>();
    const char *pixels = pill["pixels"];
    const int pill_width = pill["width"] | 0;
    const int pill_height = pill["height"] | 0;
    const size_t expected = static_cast<size_t>(pill_width) * pill_height;
    if (pixels != nullptr && pill_width > 0 && pill_width <= MAX_PILL_WIDTH && pill_height > 0 &&
        pill_height <= MAX_PILL_HEIGHT && strlen(pixels) == expected &&
        std::all_of(pixels, pixels + expected, [](char value) { return hex_value(value) >= 0; })) {
      this->pill_width_ = pill_width;
      this->pill_height_ = pill_height;
      this->pill_pixels_ = pixels;
    }
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
    this->control_available_ = root["available"] | true;
    if (!this->control_available_) this->value_dirty_ = this->value_pending_ = false;
    if (incoming_has_value) {
      const bool pending = root["pending"] | false;
      if (!pending) {
        this->confirmed_value_ = std::clamp(incoming_value, this->minimum_, this->maximum_);
        this->has_confirmed_value_ = true;
      }
      const uint64_t acknowledged = root["input_sequence"] | uint64_t(0);
      if (acknowledged >= this->input_sequence_ && !this->value_dirty_) {
        this->value_ = incoming_value;
        this->value_pending_ = pending;
      }
      this->input_sequence_ = std::max(this->input_sequence_, acknowledged);
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
    if (stale) ESP_LOGD(TAG, "Ignoring stale scene revision");
    else ESP_LOGW(TAG, "Ignoring invalid view JSON");
    return;
  }
  if (incoming_scene) {
    this->scenes_.apply(incoming_revision, std::move(incoming_scene), std::move(incoming_previous));
    this->scene_received_ = this->is_connected();
  }
  if (clear_requested) {
    this->scenes_.apply(incoming_revision, nullptr, nullptr);
    this->scene_received_ = false;
    this->value_dirty_ = this->value_pending_ = false;
  }
  this->atlas_received_ = 0;
  if (this->display_ != nullptr)
    this->display_->update();
  if (incoming_revision != 0)
    this->fire_homeassistant_event("esphome.ha_dial_scene_status",
                                  {{"device", this->device_}, {"revision", std::to_string(incoming_revision)}});
}

void HaDial::draw(display::Display &it) {
  if (this->reset_confirmation_) {
    this->draw_setup_(it);
    return;
  }
  if (this->atlas_received_ == ATLAS_FRAME_BYTES && !this->atlas_upload_error_) {
    for (size_t pixel = 0; pixel < 240 * 240; pixel++) {
      const uint16_t rgb565 = static_cast<uint16_t>(this->atlas_frame_[pixel * 2]) << 8 |
                              this->atlas_frame_[pixel * 2 + 1];
      it.draw_pixel_at(pixel % 240, pixel / 240,
                       Color(((rgb565 >> 11) & 0x1F) * 255 / 31,
                             ((rgb565 >> 5) & 0x3F) * 255 / 63, (rgb565 & 0x1F) * 255 / 31));
    }
    return;
  }
  if (!this->ready_()) {
    this->draw_setup_(it);
    return;
  }
  if (this->scenes_.current != nullptr && this->scenes_.current->valid) {
    draw_scene(it, *this->scenes_.current,
               this->has_value_ && (this->value_dirty_ || this->value_pending_) ? this->value_ : -1);
    return;
  }
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
  if (this->pill_pixels_.empty())
    it.print(120, 78, this->font_, ORANGE, display::TextAlign::CENTER, this->title_.c_str());
  else
    this->draw_pill_(it);
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

void HaDial::draw_pill_(display::Display &it) {
  const int left = 120 - this->pill_width_ / 2;
  const int top = 78 - this->pill_height_ / 2;
  for (int index = 0; index < this->pill_width_ * this->pill_height_; index++) {
    const int level = hex_value(this->pill_pixels_[index]);
    if (level == 0)
      continue;
    it.draw_pixel_at(left + index % this->pill_width_, top + index / this->pill_width_,
                     Color(100 * level / 15, 255 * level / 15, 184 * level / 15));
  }
}

void HaDial::rotate(int direction) {
  if (this->reset_confirmation_) {
    this->reset_confirmation_ = false;
    if (this->display_ != nullptr) this->display_->update();
    return;
  }
  if (!this->ready_()) return;
  if (this->scenes_.current && !this->has_value_) {
    this->send_input_(direction < 0 ? "rotate_left" : "rotate_right");
    return;
  }
  if (!this->control_available_) return;
  if (this->item_count_ == 0) {
    if (this->has_value_) {
      this->value_ = std::clamp(this->value_ + (direction < 0 ? -this->step_ : this->step_),
                                this->minimum_, this->maximum_);
      ++this->input_sequence_;
      this->value_dirty_ = true;
      this->value_pending_ = false;
      this->last_rotate_ms_ = millis();
      this->defer("rotary-draw", [this]() {
        if (this->display_ != nullptr) this->display_->update();
      });
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
  if (this->reset_confirmation_) {
    this->reset_confirmation_ = false;
    ESP_LOGW(TAG, "Clearing saved Wi-Fi at the device owner's request");
    auto *wifi = wifi::global_wifi_component;
    wifi->save_wifi_sta("", "");
    wifi->disable();
    wifi->clear_sta();
    wifi->enable();
    this->scene_received_ = false;
    this->wifi_failure_ = 0;
    this->network_changed_ = true;
    return;
  }
  if (!this->ready_()) return;
  this->flush_value_();
  this->send_input_("press", this->item_count_ == 0 ? "" : this->items_[this->selected_].id);
}

void HaDial::back() {
  if (!this->ready_() || this->reset_confirmation_) return;
  this->flush_value_();
  if (this->scenes_.back()) {
    this->has_value_ = false;
    this->value_pending_ = this->value_dirty_ = false;
    this->item_count_ = 0;
    if (this->display_ != nullptr)
      this->display_->update();
  }
  this->send_input_("back");
}

void HaDial::touch(int x, int y) {
  if (!this->ready_() || this->reset_confirmation_) return;
  if (this->scenes_.current != nullptr && this->scenes_.current->valid) {
    for (size_t index = 0; index < this->scenes_.current->region_count; index++) {
      const auto &region = this->scenes_.current->regions[index];
      if ((x - region.x) * (x - region.x) + (y - region.y) * (y - region.y) >
          region.radius * region.radius)
        continue;
      if (region.id == "back") {
        this->back();
      } else if (region.id == "home") {
        this->send_input_("home");
      } else if (region.id == "control") {
        this->press();
      } else {
        this->send_input_("touch", region.id);
      }
      return;
    }
    return;
  }
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
  ++this->input_sequence_;
  this->fire_homeassistant_event("esphome.ha_dial_input",
                                 {{"device", this->device_},
                                  {"action", action},
                                  {"item", item},
                                  {"value", value}, {"sequence", std::to_string(this->input_sequence_)}});
}

}  // namespace esphome::ha_dial

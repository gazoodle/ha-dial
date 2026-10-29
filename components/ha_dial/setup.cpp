#include "ha_dial.h"

#include <esp_wifi.h>
#include "esphome/core/defines.h"
#include "esphome/core/log.h"

namespace esphome::ha_dial {

static const Color ORANGE(244, 111, 34);
#ifdef ESPHOME_PROJECT_VERSION
static constexpr const char *FIRMWARE_VERSION = ESPHOME_PROJECT_VERSION;
#else
static constexpr const char *FIRMWARE_VERSION = "Version not configured";
#endif

void HaDial::network_event_(void *arg, esp_event_base_t base, int32_t event, void *data) {
  auto *dial = static_cast<HaDial *>(arg);
  if (base == WIFI_EVENT) {
    if (event == WIFI_EVENT_STA_DISCONNECTED) {
      dial->wifi_failure_ = static_cast<wifi_event_sta_disconnected_t *>(data)->reason;
    } else if (event == WIFI_EVENT_STA_CONNECTED) {
      dial->wifi_failure_ = 0;
    } else if (event != WIFI_EVENT_STA_START && event != WIFI_EVENT_SCAN_DONE &&
               event != WIFI_EVENT_AP_START && event != WIFI_EVENT_AP_STOP) {
      return;
    }
  }
  dial->network_changed_ = true;
}

bool HaDial::ready_() const {
  return wifi::global_wifi_component->is_connected() && this->is_connected() && this->scene_received_;
}

void HaDial::request_wifi_reset() {
  this->reset_confirmation_ = true;
  this->value_dirty_ = this->value_pending_ = false;
  if (this->display_ != nullptr) this->display_->update();
  this->set_timeout("reset-confirmation", 15000, [this]() {
    this->reset_confirmation_ = false;
    if (this->display_ != nullptr) this->display_->update();
  });
}

void HaDial::draw_setup_(display::Display &it) {
  auto *wifi = wifi::global_wifi_component;
  const auto sta = wifi->get_sta();
  const auto ap = wifi->get_ap();
  char ip_buffer[network::IP_ADDRESS_BUFFER_SIZE];
  const std::string address = wifi->is_connected()
      ? wifi->get_ip_addresses()[0].str_to(ip_buffer)
      : wifi->wifi_soft_ap_ip().str_to(ip_buffer);
  const auto screen = setup_screen(this->started_, wifi->is_connected(), wifi->is_ap_active(),
                                   !sta.get_ssid().empty(), this->is_connected(), this->scene_received_);
  const char *title = "Starting";
  std::array<std::string, 6> lines{};
  if (this->reset_confirmation_) {
    title = "Reset Wi-Fi?";
    lines = {"Forget saved network", "Press to confirm", "Turn to cancel", "Definitions stay in HA", "", "Cancels after 15s"};
  } else {
    switch (screen) {
      case SetupScreen::STARTING:
        lines = {"M5Dial v1.1", FIRMWARE_VERSION, "Starting network", "", "", "Hold 5s: Wi-Fi reset"};
        break;
      case SetupScreen::NEEDS_WIFI:
      case SetupScreen::WIFI_FAILED:
        title = screen == SetupScreen::NEEDS_WIFI ? "Needs Wi-Fi" : "Wi-Fi failed";
        lines = {ap.get_ssid().str(), "Password", ap.get_password().str(), "Open in browser", address, "Hold 5s: Wi-Fi reset"};
        break;
      case SetupScreen::CONNECTING: {
        title = this->wifi_failure_ ? "Wi-Fi failed" : "Connecting";
        const auto ssid = sta.get_ssid().str();
        lines = {ssid.substr(0, 20), ssid.substr(std::min<size_t>(20, ssid.size())),
                 "Retrying Wi-Fi", "Setup AP within 30s", "", "Hold 5s: Wi-Fi reset"};
        break;
      }
      case SetupScreen::WAITING_API:
        title = "Wi-Fi connected";
        lines = {address, "In Home Assistant:", "Settings / Integrations", "Add ESPHome using IP", "API not connected", "Hold 5s: Wi-Fi reset"};
        break;
      case SetupScreen::WAITING_HA:
        title = "Waiting for HA";
        lines = {address, "ESPHome API connected", "Add HA Dial Server", "then add HA Dial card", "to a dashboard", "Hold 5s: Wi-Fi reset"};
        break;
      case SetupScreen::READY:
        return;
    }
    const int failure = this->wifi_failure_;
    if (!wifi->is_connected() && failure != 0 && screen != SetupScreen::NEEDS_WIFI) {
      lines[4] = failure == WIFI_REASON_NO_AP_FOUND ? "Network not found" :
                 failure == WIFI_REASON_AUTH_FAIL || failure == WIFI_REASON_HANDSHAKE_TIMEOUT ||
                 failure == WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT ? "Check Wi-Fi password" : "Wi-Fi reason " + std::to_string(failure);
      // Keep the portal address visible even when a driver reason is available.
      if (wifi->is_ap_active()) lines[3] = address;
    }
  }
  it.fill(Color::BLACK);
  it.circle(120, 120, 116, ORANGE);
  if (this->font_ == nullptr) return;
  it.print(120, 35, this->font_, ORANGE, display::TextAlign::CENTER, title);
  for (size_t index = 0; index < lines.size(); ++index) {
    // The compiled fallback font has ASCII glyphs only; never send unsupported bytes to it.
    for (char &value : lines[index]) if (value < 32 || value > 126) value = '?';
    it.print(120, 65 + index * 24, this->font_, Color::WHITE, display::TextAlign::CENTER, lines[index].c_str());
  }
  if (this->touchscreen_ != nullptr &&
      (this->touchscreen_->is_failed() || this->touchscreen_->status_has_warning() ||
       this->touchscreen_->status_has_error()))
    it.print(120, 211, this->font_, ORANGE, display::TextAlign::CENTER, "Touch fault");
}

}  // namespace esphome::ha_dial

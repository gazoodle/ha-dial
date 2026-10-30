#pragma once

namespace esphome::ha_dial {

enum class SetupScreen { STARTING, NEEDS_WIFI, CONNECTING, WIFI_FAILED, WAITING_API, WAITING_HA, READY };

enum class LocalScreen { NORMAL, SETTINGS, RESET_CONFIRMATION };

inline LocalScreen local_screen(bool reset, bool settings, bool enabled) {
  if (reset) return LocalScreen::RESET_CONFIRMATION;
  return settings && enabled ? LocalScreen::SETTINGS : LocalScreen::NORMAL;
}

inline SetupScreen setup_screen(bool started, bool wifi, bool ap, bool credentials, bool api, bool scene) {
  if (!started) return SetupScreen::STARTING;
  if (!wifi) {
    if (ap) return credentials ? SetupScreen::WIFI_FAILED : SetupScreen::NEEDS_WIFI;
    return SetupScreen::CONNECTING;
  }
  if (!api) return SetupScreen::WAITING_API;
  return scene ? SetupScreen::READY : SetupScreen::WAITING_HA;
}

}  // namespace esphome::ha_dial

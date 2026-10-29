#include "../components/ha_dial/setup_state.h"
#include <cassert>

int main() {
  using namespace esphome::ha_dial;
  assert(setup_screen(false, false, false, false, false, false) == SetupScreen::STARTING);
  assert(setup_screen(true, false, true, false, false, false) == SetupScreen::NEEDS_WIFI);
  assert(setup_screen(true, false, false, true, false, false) == SetupScreen::CONNECTING);
  assert(setup_screen(true, false, true, true, false, false) == SetupScreen::WIFI_FAILED);
  assert(setup_screen(true, true, false, true, false, false) == SetupScreen::WAITING_API);
  assert(setup_screen(true, true, false, true, true, false) == SetupScreen::WAITING_HA);
  assert(setup_screen(true, true, false, true, true, true) == SetupScreen::READY);
  // A cached scene must never conceal lost Wi-Fi or a disconnected API.
  assert(setup_screen(true, false, true, true, false, true) == SetupScreen::WIFI_FAILED);
  assert(setup_screen(true, true, false, true, false, true) == SetupScreen::WAITING_API);
}

#pragma once

#include <cmath>
#include <cstdint>

namespace ha_dial_geometry {

struct Point {
  int x;
  int y;
};

inline Point pointer_position(std::int32_t steps, int radius = 105) {
  constexpr int STEPS_PER_TURN = 24;
  constexpr double PI = 3.14159265358979323846;
  const int wrapped = (steps % STEPS_PER_TURN + STEPS_PER_TURN) % STEPS_PER_TURN;
  const double angle = wrapped * 2.0 * PI / STEPS_PER_TURN - PI / 2.0;
  return {120 + static_cast<int>(std::lround(radius * std::cos(angle))),
          120 + static_cast<int>(std::lround(radius * std::sin(angle)))};
}

}  // namespace ha_dial_geometry

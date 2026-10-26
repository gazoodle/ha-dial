#include <cassert>

#include "../firmware/pointer.h"

using ha_dial_geometry::pointer_position;

int main() {
  const auto top = pointer_position(0);
  const auto right = pointer_position(6);
  const auto bottom = pointer_position(12);
  const auto left = pointer_position(18);

  assert(top.x == 120 && top.y == 15);
  assert(right.x == 225 && right.y == 120);
  assert(bottom.x == 120 && bottom.y == 225);
  assert(left.x == 15 && left.y == 120);
  assert(pointer_position(24).y == top.y);
  assert(pointer_position(-6).x == left.x);
}

// The Dial's ownership of a value while it's being turned, with a controlled clock.
#include <cassert>
#include <cstdio>

#include "value_owner.h"

using esphome::ha_dial::ValueOwner;
using Step = ValueOwner::Step;
using Reply = ValueOwner::Reply;

static ValueOwner waiting(uint32_t now, uint64_t sequence) {
  ValueOwner owner;
  owner.edit(now);
  owner.sent(now, sequence);
  return owner;
}

int main() {
  // A turn takes ownership, and each detent restarts the settle time.
  ValueOwner owner;
  assert(!owner.owned());
  assert(owner.tick(1000) == Step::NONE);
  owner.edit(1000);
  assert(owner.owned() && owner.editing());
  assert(owner.tick(1149) == Step::NONE);
  owner.edit(1100);
  assert(owner.tick(1249) == Step::NONE);
  assert(owner.tick(1250) == Step::SEND);

  // Replies during a turn are held, whatever they say: the Dial has moved on.
  assert(owner.reply(1200, 99, false, true) == Reply::HOLD);
  assert(owner.reply(1200, 99, false, false) == Reply::HOLD);
  assert(owner.editing());

  // Once sent, a reply to an older command is held.
  owner.sent(2000, 5);
  assert(!owner.editing() && owner.owned());
  assert(owner.reply(2010, 4, false, false) == Reply::HOLD);

  // A pending acknowledgement is held, and agreement hands the screen back.
  assert(owner.reply(2020, 5, true, true) == Reply::HOLD);
  assert(owner.owned());
  assert(owner.reply(2030, 5, false, true) == Reply::AGREED);
  assert(!owner.owned());
  assert(owner.reply(2040, 5, false, false) == Reply::FOLLOW);

  // HA finishing with a different value hands the screen back as a refusal.
  owner = waiting(0, 7);
  assert(owner.reply(10, 7, false, false) == Reply::REFUSED);
  assert(!owner.owned());

  // Nothing acknowledged: resend after the resend time, with the clock restarted by sending.
  owner = waiting(0, 7);
  assert(owner.tick(1499) == Step::NONE);
  assert(owner.tick(1500) == Step::RESEND);
  owner.sent(1500, 8);
  assert(owner.tick(2999) == Step::NONE);
  assert(owner.tick(3000) == Step::RESEND);
  owner.sent(3000, 9);
  assert(owner.reply(3010, 8, false, true) == Reply::HOLD);  // A reply to the one before doesn't count.

  // Acknowledged but not there yet: waits the longer time, so a moving blind isn't sent it again.
  owner = waiting(0, 7);
  assert(owner.reply(100, 7, true, false) == Reply::HOLD);
  assert(owner.tick(1600) == Step::NONE);
  assert(owner.tick(10099) == Step::NONE);
  assert(owner.tick(10100) == Step::RESEND);
  // A resend has to be acknowledged again before it gets the longer wait.
  owner.sent(10100, 8);
  assert(owner.tick(11600) == Step::RESEND);

  // It gives up after the limit, rather than waiting forever on a value the device can't reach.
  owner = waiting(0, 1);
  uint32_t now = 0;
  for (uint64_t sequence = 2; sequence <= 4; sequence++) {
    now += 1500;
    assert(owner.tick(now) == Step::RESEND);
    owner.sent(now, sequence);
  }
  now += 1500;
  assert(owner.tick(now) == Step::GAVE_UP);
  assert(!owner.owned());
  assert(owner.tick(now + 99999) == Step::NONE);

  // Turning again while waiting starts over, including the count of resends.
  owner = waiting(0, 1);
  assert(owner.tick(1500) == Step::RESEND);
  owner.sent(1500, 2);
  owner.edit(1600);
  assert(owner.editing());
  assert(owner.reply(1610, 2, false, true) == Reply::HOLD);
  assert(owner.tick(1750) == Step::SEND);
  owner.sent(1750, 3);
  now = 1750;
  for (uint64_t sequence = 4; sequence <= 6; sequence++) {
    now += 1500;
    assert(owner.tick(now) == Step::RESEND);
    owner.sent(now, sequence);
  }
  assert(owner.tick(now + 1500) == Step::GAVE_UP);

  // Timings can be tuned, and millis() wrapping round doesn't disturb them.
  ValueOwner tuned;
  ValueOwner::Timings timings;
  timings.settle_ms = 50;
  timings.resend_ms = 200;
  timings.resends = 0;
  tuned.configure(timings);
  const uint32_t nearly = 0xFFFFFFF0u;
  tuned.edit(nearly);
  assert(tuned.tick(nearly + 49) == Step::NONE);
  assert(tuned.tick(nearly + 50) == Step::SEND);
  tuned.sent(nearly + 50, 1);
  assert(tuned.tick(nearly + 249) == Step::NONE);
  assert(tuned.tick(nearly + 250) == Step::GAVE_UP);

  // Releasing is unconditional, for leaving the screen or losing the connection.
  owner = waiting(0, 1);
  owner.release();
  assert(!owner.owned());
  std::puts("value owner passed");
}

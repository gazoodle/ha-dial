#pragma once

#include <cstdint>

namespace esphome::ha_dial {

// From the first detent the Dial owns a control's value, and HA can't change what's on screen until
// they agree. Without this, a reply drawn from an older value made bars and markers jump back while
// the turn was still going on. This holds no display or network code, so it can be tested on a host.
class ValueOwner {
 public:
  enum class Step : uint8_t { NONE, SEND, RESEND, GAVE_UP };
  enum class Reply : uint8_t { FOLLOW, HOLD, AGREED, REFUSED };

  struct Timings {
    uint32_t settle_ms{150};   // No change for this long sends the value.
    uint32_t resend_ms{1500};  // HA hasn't acknowledged it: the command may be lost, so send it again.
    uint32_t wait_ms{10000};   // HA has it, but the device isn't there yet, and may be moving or fading.
    uint8_t resends{3};        // Then HA wins, or a value the device can't reach would wait forever.
  };

  void configure(const Timings &timings) { this->timings_ = timings; }
  bool owned() const { return this->state_ != State::FOLLOWING; }
  bool editing() const { return this->state_ == State::EDITING; }

  void edit(uint32_t now) {
    this->state_ = State::EDITING;
    this->since_ = now;
    this->resent_ = 0;
  }

  void sent(uint32_t now, uint64_t sequence) {
    this->state_ = State::WAITING;
    this->since_ = now;
    this->sequence_ = sequence;
    this->acknowledged_ = false;
  }

  void release() { this->state_ = State::FOLLOWING; }

  Step tick(uint32_t now) {
    if (this->state_ == State::EDITING)
      return now - this->since_ >= this->timings_.settle_ms ? Step::SEND : Step::NONE;
    if (this->state_ != State::WAITING) return Step::NONE;
    if (now - this->since_ < (this->acknowledged_ ? this->timings_.wait_ms : this->timings_.resend_ms)) return Step::NONE;
    if (this->resent_ >= this->timings_.resends) {
      this->release();
      return Step::GAVE_UP;
    }
    ++this->resent_;
    return Step::RESEND;
  }

  // `close` says the value in this reply is within tolerance of the one on screen.
  Reply reply(uint32_t now, uint64_t acknowledged, bool pending, bool close) {
    if (this->state_ == State::FOLLOWING) return Reply::FOLLOW;
    if (this->state_ == State::EDITING || acknowledged < this->sequence_) return Reply::HOLD;
    if (!this->acknowledged_) {
      this->acknowledged_ = true;
      this->since_ = now;
    }
    if (pending) return Reply::HOLD;
    this->release();
    // HA has finished with this command, so a different value means it failed or the device refused it.
    return close ? Reply::AGREED : Reply::REFUSED;
  }

 private:
  enum class State : uint8_t { FOLLOWING, EDITING, WAITING };

  Timings timings_{};
  State state_{State::FOLLOWING};
  uint32_t since_{0};  // Compared by subtraction, so millis() wrapping round is harmless.
  uint64_t sequence_{0};
  bool acknowledged_{false};
  uint8_t resent_{0};
};

}  // namespace esphome::ha_dial

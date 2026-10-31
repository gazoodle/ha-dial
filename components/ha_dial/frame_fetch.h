#pragma once

#include <atomic>
#include <cstdint>
#include <string>
#include "scene.h"
#include "esphome/core/helpers.h"

namespace esphome::ha_dial {

struct FrameOutcome {
  uint32_t crc{0};
  bool ok{false};
  const char *error{""};
  uint32_t elapsed_ms{0};
  size_t free_heap{0}, largest_block{0};
};

// Streams one image frame at a time from HA on its own task, so a slow network can't stall rotary
// input. Only a frame that passes its length and CRC replaces the one on screen.
class FrameFetcher {
 public:
  void request(const SceneElement &image);
  // Main loop only. Returns true when a fetch has just finished, swapping in a good frame.
  bool collect(FrameOutcome &outcome);
  // Gives the buffers back once no scene needs them; does nothing mid-transfer.
  void release();
  void cancel() { this->cancel_ = true; }
  FrameView view() const { return {this->current_.get(), this->width_, this->height_, this->crc_}; }

 protected:
  struct Job {
    std::string url;
    uint32_t crc{0};
    size_t bytes{0};
    int width{0}, height{0};
  };
  static void task_(void *argument);
  void run_();
  void start_(const Job &job);

  RAMUniquePtr<uint8_t[]> current_, incoming_;
  int width_{0}, height_{0};
  uint32_t crc_{0};
  Job job_, next_;
  std::string attempted_;
  bool has_next_{false};
  std::atomic<bool> busy_{false}, done_{false}, cancel_{false};
  const char *error_{""};
  uint32_t started_ms_{0};
  uint32_t elapsed_ms_{0};
};

}  // namespace esphome::ha_dial

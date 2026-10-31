#include "frame_fetch.h"

#include <cstring>
#include <esp_heap_caps.h>
#include <esp_http_client.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include "raster.h"
#include "esphome/core/hal.h"

namespace esphome::ha_dial {

static constexpr int TIMEOUT_MS = 5000;
static constexpr uint32_t TASK_STACK = 6144;

namespace {
// Closing the client on every path is what stops a failed transfer leaking its socket.
class ClientGuard {
 public:
  explicit ClientGuard(esp_http_client_handle_t client) : client_(client) {}
  ~ClientGuard() {
    if (this->client_ != nullptr) {
      esp_http_client_close(this->client_);
      esp_http_client_cleanup(this->client_);
    }
  }
  ClientGuard(const ClientGuard &) = delete;
  ClientGuard &operator=(const ClientGuard &) = delete;

 private:
  esp_http_client_handle_t client_;
};
}  // namespace

void FrameFetcher::request(const SceneElement &image) {
  Job job;
  job.url = image.pixels;
  job.crc = image.crc;
  job.width = image.mask_width;
  job.height = image.mask_height;
  job.bytes = static_cast<size_t>(job.width) * job.height * 2;
  if (job.url.empty() || (job.crc == this->crc_ && this->current_ != nullptr)) return;
  if (this->busy_) {
    this->next_ = job;
    this->has_next_ = job.crc != this->job_.crc;
    return;
  }
  // A failed URL isn't retried until HA issues another, so an unreachable HA can't cause a storm.
  if (job.url == this->attempted_) return;
  this->start_(job);
}

void FrameFetcher::start_(const Job &job) {
  this->attempted_ = job.url;
  this->job_ = job;
  this->error_ = "";
  this->started_ms_ = millis();
  if (this->current_ == nullptr) this->current_ = RAMAllocator<uint8_t>().make_unique_array_for_overwrite(MAX_FRAME_BYTES);
  if (this->incoming_ == nullptr) this->incoming_ = RAMAllocator<uint8_t>().make_unique_array_for_overwrite(MAX_FRAME_BYTES);
  this->busy_ = true;
  this->done_ = false;
  if (this->current_ == nullptr || this->incoming_ == nullptr) {
    this->error_ = "not enough memory";
    this->done_ = true;
    return;
  }
  if (xTaskCreate(&FrameFetcher::task_, "ha_dial_frame", TASK_STACK, this, 1, nullptr) != pdPASS) {
    this->error_ = "could not start the fetch task";
    this->done_ = true;
  }
}

void FrameFetcher::task_(void *argument) {
  static_cast<FrameFetcher *>(argument)->run_();
  vTaskDelete(nullptr);
}

void FrameFetcher::run_() {
  esp_http_client_config_t config{};
  config.url = this->job_.url.c_str();
  config.timeout_ms = TIMEOUT_MS;
  config.buffer_size = 1024;
  esp_http_client_handle_t client = esp_http_client_init(&config);
  ClientGuard guard(client);
  const size_t expected = this->job_.bytes;
  size_t received = 0;
  if (client == nullptr) {
    this->error_ = "could not create the HTTP client";
  } else if (esp_http_client_open(client, 0) != ESP_OK) {
    this->error_ = "could not connect to HA";
  } else if (esp_http_client_fetch_headers(client) < 0) {
    this->error_ = "no response from HA";
  } else if (esp_http_client_get_status_code(client) != 200) {
    this->error_ = "HA refused the frame";
  } else {
    while (received < expected && !this->cancel_) {
      const int chunk = esp_http_client_read(client, reinterpret_cast<char *>(this->incoming_.get()) + received, expected - received);
      if (chunk <= 0) break;
      received += chunk;
    }
    char spare;
    if (received != expected || esp_http_client_read(client, &spare, 1) > 0) this->error_ = "wrong frame length";
    else if (frame_crc32(this->incoming_.get(), expected) != this->job_.crc) this->error_ = "frame failed its CRC";
  }
  this->elapsed_ms_ = millis() - this->started_ms_;
  this->done_ = true;
}

bool FrameFetcher::collect(FrameOutcome &outcome) {
  if (!this->done_.exchange(false)) return false;
  outcome.crc = this->job_.crc;
  outcome.error = this->error_;
  outcome.ok = *this->error_ == '\0';
  outcome.elapsed_ms = this->elapsed_ms_;
  outcome.free_heap = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
  outcome.largest_block = heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL);
  if (outcome.ok) {
    this->current_.swap(this->incoming_);
    this->width_ = this->job_.width;
    this->height_ = this->job_.height;
    this->crc_ = this->job_.crc;
  }
  this->busy_ = false;
  if (this->has_next_) {
    this->has_next_ = false;
    if (this->next_.crc != this->crc_) this->start_(this->next_);
  }
  return true;
}

void FrameFetcher::release() {
  if (this->busy_) return;
  this->current_.reset();
  this->incoming_.reset();
  this->width_ = this->height_ = 0;
  this->crc_ = 0;
  this->attempted_.clear();
}

}  // namespace esphome::ha_dial

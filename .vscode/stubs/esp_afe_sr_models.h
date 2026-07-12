// IntelliSense stub — ESP-SR AFE (Audio Front-End) wake word models
// Real header from espressif/esp-sr component
#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// AFE configuration types (minimal stubs)
typedef enum {
    AFE_TYPE_SR = 0,
    AFE_TYPE_WAKE = 1,
} afe_type_t;

typedef enum {
    AFE_MODE_LOW_POWER = 0,
    AFE_MODE_HIGH_PERF = 1,
} afe_mode_t;

typedef struct {
    afe_type_t type;
    afe_mode_t mode;
    const char *model_partition;
    int sampling_rate;
    int audio_channel;
    void *afe_config;  // opaque
} afe_config_t;

typedef void *esp_afe_sr_data_t;
typedef void *afe_handle_t;
typedef void *esp_afe_sr_iface_t;

// Minimal function declarations
afe_handle_t *esp_afe_sr_create(const afe_config_t *config);
void esp_afe_sr_destroy(afe_handle_t *handle);
int esp_afe_sr_feed(afe_handle_t *handle, const int16_t *audio, int len);
int esp_afe_sr_fetch(afe_handle_t *handle);
int esp_afe_sr_get_channel_num(afe_handle_t *handle);

#ifdef __cplusplus
}
#endif

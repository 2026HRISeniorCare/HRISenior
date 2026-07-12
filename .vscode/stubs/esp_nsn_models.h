// IntelliSense stub — ESP-SR Noise Suppression (NSN) models
// Real header from espressif/esp-sr component
#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void *esp_nsn_handle_t;

typedef struct {
    int sampling_rate;
    int audio_channel;
    const char *model_partition;
} nsn_config_t;

esp_nsn_handle_t *esp_nsn_create(const nsn_config_t *config);
void esp_nsn_destroy(esp_nsn_handle_t *handle);
int esp_nsn_process(esp_nsn_handle_t *handle, const int16_t *in, int16_t *out, int len);

#ifdef __cplusplus
}
#endif

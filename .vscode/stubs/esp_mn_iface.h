// IntelliSense stub — ESP-SR Multinet (MN) interface
// Real header from espressif/esp-sr component
#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void *esp_mn_iface_t;
typedef void *esp_mn_handle_t;

esp_mn_iface_t *esp_mn_handle_get_iface(esp_mn_handle_t handle);
esp_mn_handle_t *esp_mn_create(const void *config);
void esp_mn_destroy(esp_mn_handle_t *handle);
int esp_mn_detect(esp_mn_handle_t *handle, const int16_t *audio, int len);

#ifdef __cplusplus
}
#endif

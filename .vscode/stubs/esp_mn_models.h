// IntelliSense stub — ESP-SR Multinet (MN) model definitions
#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Multinet command IDs (minimal set)
typedef enum {
    ESP_MN_CHINESE = 0,
    ESP_MN_ENGLISH = 1,
} esp_mn_language_t;

typedef void model_iface_data_t;
typedef void esp_mn_commands_t;

#ifdef __cplusplus
}
#endif

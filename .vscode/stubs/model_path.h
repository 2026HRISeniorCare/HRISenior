// IntelliSense stub — real header from espressif/esp-sr component
#pragma once
#include <cstdint>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    const char* model_name;
    const void* model_data;
    uint32_t model_size;
} srmodel_list_t;

// Model prefix constants for esp_srmodel_filter
#define ESP_WN_PREFIX    "wn"
#define ESP_MN_PREFIX    "mn"
#define ESP_NSNET_PREFIX "nsnet"
#define ESP_VADN_PREFIX  "vadn"
#define ESP_AFE_PREFIX   "afe"

// Filter model list by prefix
char* esp_srmodel_filter(srmodel_list_t* models, const char* prefix, const char* name);

#ifdef __cplusplus
}
#endif

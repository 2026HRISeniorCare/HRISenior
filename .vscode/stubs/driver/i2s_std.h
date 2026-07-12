// IntelliSense stub — ESP-IDF v5.x I2S standard mode driver
#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// I2S channel handle (forward declaration)
typedef struct i2s_channel_obj_t *i2s_chan_handle_t;

typedef enum {
    I2S_STD_SLOT_DEFAULT = 0,
} i2s_std_slot_mask_t;

typedef struct {
    int clk_cfg;
    int slot_cfg;
    int gpio_cfg;
} i2s_std_config_t;

#ifdef __cplusplus
}
#endif

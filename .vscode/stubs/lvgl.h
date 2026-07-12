// IntelliSense stub — LVGL v9.x graphics library
// Provides minimal type declarations for xiaozhi-esp32 compilation
#pragma once

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// ── Basic types ──────────────────────────────────────────────────
typedef int32_t  lv_coord_t;
typedef uint32_t lv_color_t;
typedef int      lv_result_t;
typedef uint32_t lv_opa_t;

#define LV_OPA_TRANSP  0
#define LV_OPA_COVER   255
#define LV_OPA_50      128

typedef enum {
    LV_COLOR_FORMAT_RGB565 = 0,
    LV_COLOR_FORMAT_RGB888 = 1,
    LV_COLOR_FORMAT_XRGB8888 = 2,
} lv_color_format_t;

// ── Object types ─────────────────────────────────────────────────
typedef struct _lv_obj_t       lv_obj_t;
typedef struct _lv_event_t     lv_event_t;
typedef struct _lv_display_t   lv_display_t;
typedef struct _lv_indev_t     lv_indev_t;
typedef struct _lv_group_t     lv_group_t;
typedef struct _lv_theme_t     lv_theme_t;
typedef struct _lv_font_t      lv_font_t;
typedef struct _lv_style_t     lv_style_t;

// ── Image descriptor ─────────────────────────────────────────────
typedef struct {
    const void *data;
    uint32_t data_size;
    lv_coord_t w;
    lv_coord_t h;
    int32_t stride;
    lv_color_format_t color_format;
    uint32_t flags;
} lv_image_dsc_t;

// Compatibility alias
typedef lv_image_dsc_t lv_img_dsc_t;

// ── Area/Rect ────────────────────────────────────────────────────
typedef struct {
    lv_coord_t x1;
    lv_coord_t y1;
    lv_coord_t x2;
    lv_coord_t y2;
} lv_area_t;

// ── Display rotation ─────────────────────────────────────────────
typedef enum {
    LV_DISPLAY_ROTATION_0   = 0,
    LV_DISPLAY_ROTATION_90  = 1,
    LV_DISPLAY_ROTATION_180 = 2,
    LV_DISPLAY_ROTATION_270 = 3,
} lv_display_rotation_t;

// ── Input device data ────────────────────────────────────────────
typedef struct {
    lv_coord_t x;
    lv_coord_t y;
    uint8_t state;
} lv_indev_data_t;

// ── Event callback type ──────────────────────────────────────────
typedef void (*lv_event_cb_t)(lv_event_t *e);

// ── Minimal function declarations ────────────────────────────────
lv_display_t *lv_display_get_default(void);
lv_color_format_t lv_display_get_color_format(lv_display_t *disp);
lv_display_rotation_t lv_display_get_rotation(lv_display_t *disp);
void lv_display_add_event_cb(lv_display_t *disp, lv_event_cb_t cb, uint32_t filter, void *user_data);
void *lv_event_get_param(lv_event_t *e);

void lv_obj_set_style_text_font(lv_obj_t *obj, const lv_font_t *font, uint32_t selector);
void lv_obj_set_style_text_color(lv_obj_t *obj, lv_color_t color, uint32_t selector);
void lv_obj_set_style_bg_color(lv_obj_t *obj, lv_color_t color, uint32_t selector);
void lv_obj_set_style_bg_opa(lv_obj_t *obj, lv_opa_t opa, uint32_t selector);
void lv_obj_set_style_bg_image_src(lv_obj_t *obj, const void *src, uint32_t selector);

#ifdef __cplusplus
}
#endif

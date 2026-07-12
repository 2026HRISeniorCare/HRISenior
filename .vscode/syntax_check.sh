#!/bin/bash
# Comprehensive syntax check for HRI-SeniorCare files
# Usage: bash .vscode/syntax_check.sh

GXX="/c/Users/25453/.espressif/tools/xtensa-esp-elf/esp-14.2.0_20241119/xtensa-esp-elf/bin/xtensa-esp32s3-elf-g++.exe"
PROJECT_ROOT="/c/Users/25453/Desktop/HRISenior"
MAIN_DIR="$PROJECT_ROOT/HRI-SeniorCare/Main/main"
XIAOZHI_DIR="$PROJECT_ROOT/HRI-SeniorCare/xiaozhi-esp32/main"
IDF_DIR="/c/Users/25453/esp-idf"
STUBS="$PROJECT_ROOT/.vscode/stubs"

CXXFLAGS="-std=gnu++17 -fsyntax-only -Wno-missing-field-initializers"
DEFINES="-DESP_PLATFORM -DESP32 -DCONFIG_IDF_TARGET_ESP32S3=1 -DCONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI=1"

# ── Build include path ──────────────────────────────────────────
INCLUDES=""

# 1. Stubs (sdkconfig.h, opus stubs, etc.) — must be first
INCLUDES="$INCLUDES -I$STUBS -I$STUBS/driver"

# 2. Project source directories
INCLUDES="$INCLUDES -I$MAIN_DIR"
INCLUDES="$INCLUDES -I$MAIN_DIR/emotion"
INCLUDES="$INCLUDES -I$MAIN_DIR/uart_k210"
INCLUDES="$INCLUDES -I$MAIN_DIR/audio"
INCLUDES="$INCLUDES -I$MAIN_DIR/protocols"
INCLUDES="$INCLUDES -I$MAIN_DIR/display"
INCLUDES="$INCLUDES -I$MAIN_DIR/display/lvgl_display"
INCLUDES="$INCLUDES -I$MAIN_DIR/led"
INCLUDES="$INCLUDES -I$MAIN_DIR/boards/common"
INCLUDES="$INCLUDES -I$MAIN_DIR/boards/bread-compact-wifi"
INCLUDES="$INCLUDES -I$XIAOZHI_DIR"

# 3. ESP32-S3 specific paths (BEFORE generic to prevent wrong arch selection)
add_s3() { INCLUDES="$INCLUDES -I$IDF_DIR/components/$1"; }
add_s3 soc/esp32s3/include
add_s3 soc/esp32s3/include/soc
add_s3 soc/esp32s3/register          # reg_base.h etc
add_s3 hal/esp32s3/include
add_s3 esp_hw_support/include/soc/esp32s3
add_s3 esp_hw_support/port/esp32s3
add_s3 esp_rom/include/esp32s3
add_s3 esp_rom/esp32s3
add_s3 xtensa/esp32s3/include
add_s3 esp_phy/esp32s3/include
add_s3 driver/esp32s3/include
add_s3 efuse/esp32s3/include

# 4. FreeRTOS xtensa paths (BEFORE SMP and kernel general)
add_s3 freertos/config/include
add_s3 freertos/config/include/freertos
add_s3 freertos/config/xtensa/include
add_s3 freertos/config/xtensa/include/freertos
add_s3 freertos/FreeRTOS-Kernel/portable/xtensa/include
add_s3 freertos/FreeRTOS-Kernel/portable/xtensa/include/freertos
add_s3 freertos/esp_additions/include
add_s3 freertos/esp_additions/include/freertos
add_s3 freertos/FreeRTOS-Kernel/include
add_s3 freertos/FreeRTOS-Kernel/include/freertos
add_s3 freertos/FreeRTOS-Kernel/include/esp_additions

# 5. Non-standard header dirs not named "include"
add_s3 newlib/platform_include
add_s3 json/cJSON

# 6. Generic ESP-IDF component "include" dirs (depth ≤4, skip arch-specific)
while IFS= read -r incdir; do
    case "$incdir" in
        */freertos/*|*/linux/*|*/riscv/*|*/esp32s3/*|*/esp32s2/*|*/esp32c*|*/esp32h*|*/esp32p*) continue ;;
    esac
    INCLUDES="$INCLUDES -I$incdir"
done < <(find "$IDF_DIR/components" -maxdepth 4 -type d -name "include" 2>/dev/null)

# 6. Generic "esp32" paths last (fallback for missing s3 headers)
while IFS= read -r incdir; do
    INCLUDES="$INCLUDES -I$incdir"
done < <(find "$IDF_DIR/components" -maxdepth 4 -type d -name "include" -path "*/esp32/*" 2>/dev/null | grep -v esp32s)

# ── Check each file ─────────────────────────────────────────────
echo "=== HRI-SeniorCare Syntax Check ==="
echo "Compiler: xtensa-esp32s3-elf-g++ (GCC 14.2.0)"
echo ""

PASS=0; FAIL=0
declare -A RESULTS

check_file() {
    local file="$1" label="$2"
    echo -n "[CHECK] $label ... "
    local out rc
    out=$("$GXX" $CXXFLAGS $DEFINES $INCLUDES -c "$file" -o /dev/null 2>&1)
    rc=$?
    if [ $rc -eq 0 ]; then
        echo "PASS"
        PASS=$((PASS + 1))
        RESULTS["$label"]="PASS"
    else
        echo "FAIL"
        echo "$out" | head -8 | sed 's/^/  | /'
        FAIL=$((FAIL + 1))
        RESULTS["$label"]="FAIL"
    fi
}

check_file "$MAIN_DIR/emotion/speech_emotion.cc"   "speech_emotion.cc"
check_file "$MAIN_DIR/emotion/ds_fusion_engine.cc"  "ds_fusion_engine.cc"
check_file "$MAIN_DIR/uart_k210/uart_k210.cc"       "uart_k210.cc"
check_file "$MAIN_DIR/audio/audio_service.cc"        "audio_service.cc"
check_file "$MAIN_DIR/application.cc"                "application.cc"
check_file "$MAIN_DIR/main.cc"                       "main.cc"

echo ""
echo "=== Results: $((PASS + FAIL)) files — $PASS PASS, $FAIL FAIL ==="
for f in "${!RESULTS[@]}"; do echo "  $f: ${RESULTS[$f]}"; done | sort

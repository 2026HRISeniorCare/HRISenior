#!/bin/bash
# ESP-IDF v5.4 environment for Git Bash (MSYS2) — validated 2026-07
# 用法:  source .vscode/idf_env.sh   然后  idf build
#
# 说明:Windows 上 esp-idf 官方的 export.sh 在 Git Bash 里会把临时路径的反斜杠
# 吃掉导致 idf.py 不上 PATH;export.bat 又会弹交互式 cmd。这里直接用 activate
# 脚本里的真实工具路径手工拼环境,可在 Git Bash 中稳定驱动 idf.py。
# 注意:项目路径必须是纯英文(ESP-IDF 不支持非 ASCII 路径,如"大创")。

export IDF_PATH="C:/Users/25453/esp-idf-v54"   # 干净 v5.4(gh-proxy 镜像克隆);旧 C:/Users/25453/esp-idf 已损坏,保留作备份
export IDF_TOOLS_PATH="C:/Users/25453/.espressif"
export IDF_PYTHON_ENV_PATH="C:/Users/25453/.espressif/python_env/idf5.4_py3.13_env"
export IDF_PYTHON="C:/Users/25453/.espressif/python_env/idf5.4_py3.13_env/Scripts/python.exe"
export ESP_ROM_ELF_DIR="C:/Users/25453/.espressif/tools/esp-rom-elfs/20241011/"
export OPENOCD_SCRIPTS="C:/Users/25453/.espressif/tools/openocd-esp32/v0.12.0-esp32-20241016/openocd-esp32/share/openocd/scripts"
export IDF_CCACHE_ENABLE=1

# 不让 git 因子模块拉取而弹 Git Credential Manager(esp-idf 子模块已改为 github 公开源)
export GIT_TERMINAL_PROMPT=0

T=/c/Users/25453/.espressif/tools
V=/c/Users/25453/.espressif/python_env/idf5.4_py3.13_env/Scripts
export PATH="$T/xtensa-esp-elf/esp-14.2.0_20241119/xtensa-esp-elf/bin:$T/riscv32-esp-elf/esp-14.2.0_20241119/riscv32-esp-elf/bin:$T/esp32ulp-elf/2.38_20240113/esp32ulp-elf/bin:$T/cmake/3.30.2/bin:$T/ninja/1.12.1:$T/idf-exe/1.0.3:$T/ccache/4.10.2/ccache-4.10.2-windows-x86_64:$T/xtensa-esp-elf-gdb/14.2_20240403/xtensa-esp-elf-gdb/bin:$T/openocd-esp32/v0.12.0-esp32-20241016/openocd-esp32/bin:$T/dfu-util/0.11/dfu-util-0.11-win64:$V:/c/Users/25453/esp-idf-v54/tools:$PATH"

# idf 快捷命令(通过 venv python 调 idf.py,最稳)
idf() { "$IDF_PYTHON" "$IDF_PATH/tools/idf.py" "$@"; }
export -f idf

echo "ESP-IDF 5.4 环境就绪 (Git Bash)。芯片串口默认 COM5 (CH343)。"
echo "常用:  idf set-target esp32s3  |  idf build  |  idf -p COM5 flash monitor"

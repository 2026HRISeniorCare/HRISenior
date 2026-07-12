# ESP32-S3 固件编译烧录 · 交接单(会话可能因移动路径而中断,新会话读这份继续)

> 目标:把这份带 SIEVOX 情绪集成的 xiaozhi 固件,在本机 ESP-IDF v5.4 编译出来并烧录到 ESP32-S3。
> 新会话开场只需说:「读 .scratch/esp-build-handoff.md,接着编译烧录」。

## 更新 2026-07-12c(编译+烧录成功,固件启动但卡在板级初始化 · 读这段最新)

**结论:编译✅ 烧录✅ 启动✅,但设备启动到 286ms 后卡住(疑似音频 codec I²C),非固件 bug。**

- **编译**:`-Wno-error=format` 补丁(见下)后全过,`Project build complete`,`build/xiaozhi.bin` = 0x26b900(~2.5MB,app 分区余 39%)。
- **又一处必打补丁**:`HRI-SeniorCare/Main/main/CMakeLists.txt` 在 `idf_component_register(...)` 之后加了 `target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-error=format)`。原因:xtensa 上 `uint32_t/int32_t` = `(unsigned) long int`,`uart_k210.cc`/`application.cc`/`esp32_camera.cc` 里 `ESP_LOGx` 用 `%u/%d/%x` 打印它们触发 `-Werror=format`。降级为 warning,不必逐行改 PRIu32。
- **烧录**:⚠️ **必须用低波特率**。默认 460800 在写 app 到 10% 时 "chip stopped responding";改 `-b 115200` 一次成功(app 写了 ~132s),5 个分区全部 `Hash of data verified` + `Hard resetting`。
  - 命令:`"$IDF_PYTHON" "$IDF_PATH/tools/idf.py" -C "$MAIN" -p COM5 -b 115200 flash`
- **启动日志**(`.scratch/monitor.log`):`rst:POWERON` → `app_main()` → **`DS_FUSION: D-S Fusion Engine created`**(情绪引擎起来了✅)→ Board UUID → button → SSD1306 driver installed → **然后停住,无 panic/backtrace/重启**,1 分多钟无新行。
- **卡点推测**:停在 SSD1306 之后,下一步通常是**音频 codec(I²C)初始化**(用户当时在看 `main/audio/audio_codec.h`)。这类"起来了但不往下走、又不崩"极可能是**外设没接好 / I²C 地址或上拉问题 / codec 未上电**,不是编译或代码逻辑问题。
- **未看到**:完整那行 `SIEVOX Emotion pipeline initialised: SER + D-S Fusion + Upstream`(它在 codec 之后才打印,因卡住没走到)。

### 下一步排查(新会话从这里接)
1. 确认硬件:OLED(SSD1306,I²C)、音频 codec(如 ES8311/ES7210)是否接好、供电、SDA/SCL 上拉。面包板接触不良很常见。
2. 看 codec 初始化代码:`main/audio/audio_codec.h` 及 `bread-compact-wifi` 板级 `compact_wifi_board.cc` 里 codec/I²C 初始化顺序。
3. 重连 monitor 抓完整日志:`"$IDF_PYTHON" "$IDF_PATH/tools/idf.py" -C "$MAIN" -p COM5 monitor`(monitor 波特率仍 115200)。
4. 若怀疑 I²C 扫描,可在 codec init 前加一次 i2c bus scan 打印地址。

---

## 更新 2026-07-12b(重装干净 IDF)

**决定**:旧 `C:/Users/25453/esp-idf` 被上一位操作者改坏(删文件、手改版本号、gitee/github 源混乱),放弃修复,**重装一份干净的 v5.4** 到新目录,旧目录保留作备份(不删)。

- **新 IDF 路径**:`C:/Users/25453/esp-idf-v54`(浅克隆 `--depth 1 --branch v5.4`)。
- **网络**:本机 **github 直连不通、gitee 通**,但用户要求**走 github 国内镜像**。可用镜像前缀:`https://gh-proxy.com/https://github.com/...`(kkgithub / gitmirror 当时不通)。
- **子模块**:新库里设 `git config url."https://gh-proxy.com/https://github.com/".insteadOf "https://github.com/"`,再 `git submodule update --init --recursive --depth 1`。S3 相关(esp_phy/lib/esp32s3、xtensa/esp32s3、esp_wifi/lib/esp32s3、mbedtls、nimble)已核对存在。
- **两处必打补丁(干净 v5.4 在 Git Bash/MSYS 下会直接退出、根本不编译)**:
  1. `esp-idf-v54/tools/idf.py`(~837 行):`if 'MSYSTEM' in os.environ:` 分支原来只 `print_warning` 不调 `main()` → warning 后补 `main()`。
  2. `esp-idf-v54/tools/idf_tools.py`(~3254 行):同分支原来 `fatal(...) + raise SystemExit(1)` → 改 `warn(...)` 不退出。
  - 验证:`idf.py --version` 打印 `ESP-IDF v5.4-dirty`、exit 0 即 OK。
- **[idf_env.sh](../.vscode/idf_env.sh) 已改**:`IDF_PATH` 与末尾 PATH 的 `tools` 都指向 `esp-idf-v54`。
- **进行中**:全量 build(clean IDF)。成功后 `"$IDF_PYTHON" "$IDF_PATH/tools/idf.py" -C "$MAIN" -p COM5 flash monitor`。

---

## 更新 2026-07-12(暂停点):现在是 `C:/Users/25453/Desktop/HRISenior/HRISenior/HRI-SeniorCare/Main`(多套了一层 `HRISenior/HRISenior`)。下面第 2 节的旧路径已失效,以本段为准。
- **COM5 仍在**(注册表 `\Device\Serial2` = COM5)。COM3/4/8/9 是蓝牙。
- **sdkconfig 仍 OK**:`CONFIG_IDF_TARGET="esp32s3"`、`CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI=y`。
- **本次 configure 失败根因 + 已修复**:`C:/Users/25453/esp-idf` 里 `components/xtensa/esp32s3/`(芯片头文件 `include/xtensa/config/*.h` + `libxt_hal.a`)被整目录**删除**,导致 cmake 报 `Include directory '.../xtensa/esp32s3/include' is not a directory`。已用 `git -C C:/Users/25453/esp-idf checkout -- components/xtensa/esp32s3` 恢复,文件已回来(核对:`core-isa.h`、`libxt_hal.a` 存在)。
- **esp-idf 还有一批未记录的改动(暂未处理,先观察)**:`tools/cmake/version.cmake` 被手改 5.4→5.5(但 git tag 仍是 `v5.4`,`git describe` = v5.4);另有 `components/lwip|mbedtls|mqtt/CMakeLists.txt`、`tools/idf.py`、`tools/idf_tools.py` 被改。`.gitmodules`(gitee→github)是本项目有意改的、保留。其余这些若编译再出问题,优先怀疑并考虑 `git checkout --` 还原。
- **下一步**:进 Main 目录 → `rm -rf build`(旧 build 已删过一次,但 configure 失败后又生成了半截,建议再删)→ source 环境 → `idf build`。恢复 xtensa 后应能过 configure。

### 恢复命令(直接照抄)
```bash
MAIN="C:/Users/25453/Desktop/HRISenior/HRISenior/HRI-SeniorCare/Main"
rm -rf "$MAIN/build"
source "C:/Users/25453/Desktop/HRISenior/HRISenior/.vscode/idf_env.sh"
"$IDF_PYTHON" "$IDF_PATH/tools/idf.py" -C "$MAIN" build 2>&1 | tee "C:/Users/25453/Desktop/HRISenior/HRISenior/.scratch/build.log"
# 成功后:
"$IDF_PYTHON" "$IDF_PATH/tools/idf.py" -C "$MAIN" -p COM5 flash monitor
```

---

## 0. 当前状态(以下为旧记录,路径已过时,见上方更新段)

- 卡点已定位:**项目原路径含中文"大创"**,ESP-IDF 工具链(kconfgen 等)不支持非 ASCII 路径 → 已把项目移到纯英文路径(如 `C:\Users\25453\Desktop\HRISenior`)。
- 芯片已连:**串口 COM5**(USB-Enhanced-SERIAL CH343,VID:PID=1A86:55D3)。COM3/4/8/9 是蓝牙口,别选。
- 开发板:`bread-compact-wifi`(esp32s3),`sdkconfig` 已配好(`CONFIG_IDF_TARGET="esp32s3"`、`CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI=y`)。

## 1. 已做好的环境/修复(持久,无需重做)

- **ESP-IDF 环境**已固化进 [.vscode/idf_env.sh](../.vscode/idf_env.sh)(随项目移动;里面的 esp-idf 工具路径指向 `C:\Users\25453\esp-idf` 和 `.espressif`,不随项目变)。用法:`source .vscode/idf_env.sh`,之后 `idf ...`。
  - 背景:Windows 上 esp-idf 官方 `export.sh` 在 Git Bash 里会因反斜杠被吃导致 idf.py 不上 PATH;`export.bat` 会弹交互 cmd。所以手工拼了环境。
- **esp-idf 的 git 修复**(在 `C:\Users\25453\esp-idf`,不随项目移动):
  - `.gitmodules` 里 17 条子模块源已从 **gitee 改回 github**(gitee 镜像缺 esp32c5 等新芯片库,导致克隆失败/弹认证)。
  - `git -C C:\Users\25453\esp-idf config credential.helper ""` 已关掉 **Git Credential Manager**;env 里也设了 `GIT_TERMINAL_PROMPT=0`。→ 不会再弹认证框。

## 2. 接着要做(按顺序)

```bash
cd "C:/Users/25453/Desktop/HRISenior/HRI-SeniorCare/Main"   # 新英文路径
rm -rf build            # 旧 build 缓存了旧路径,必须删
source ../../.vscode/idf_env.sh   # 或从仓库根 source .vscode/idf_env.sh
idf build               # 首次全量编译约 10~20 分钟
# 成功后:
idf -p COM5 flash monitor
```

- 若 `idf` 函数没生效(非交互 shell),改用:`"$IDF_PYTHON" "$IDF_PATH/tools/idf.py" -C <Main目录> build`。
- 验收:编译末尾出现 `Project build complete`,生成 `build/xiaozhi.bin`;`monitor` 里看到 `SIEVOX Emotion pipeline initialised: SER + D-S Fusion + Upstream`。

## 3. 可忽略的告警(正常)

- `MSys/Mingw is no longer supported ... continue at your own risk` — 警告,能编。
- `Python interpreter ... is not from installed venv` — 路径格式误报,无害。
- `Git submodule components/cmock/CMock is out of date` — 警告,不影响。

## 4. 仓库里已完成的其他工作(未提交)

- 根 `README.md`:已整合为完整中文,加了大创全名「基于人机交互与模态识别的语音情感交流式助老机器人」,补了技术路线(SNR/Lux 纠偏、TDOA/GCC-PHAT/卡尔曼、DeepSeek、隐私、路线图),并修正了"树莓派"误述为"后端服务器"。
- `.scratch/doc-code-consistency/gap-list.md`:文档↔代码差距清单(SNR/Lux 引擎、TDOA 定位、蒙特卡洛脚本 = 仅仿真/缺代码)。
- `HRI-SeniorCare/.gitignore`:已加 `Main/esp-idf/`(误拷的空框架副本)。
- 情绪模块已在 `HRI-SeniorCare/Main/main/CMakeLists.txt` 注册进构建。

## 5. 后端(对话)说明

- 用户选择:后端接 **DeepSeek API**(对话体系已能用,可在小智官网改配置)。情绪 JSON 走 `SendMcpMessage` → 现有 WebSocket/MQTT 通道 → 后端。
- 注:模型(K210 FER + SER)尚未训练;后续若要"情绪注入 LLM 提示词"需在服务端处理 `type:"mcp"` 的 `emotion_state` 载荷。

# Resona：ESP32-S3-N16R8 PCB 迁移与扩展方案

更新时间：2026-08-17  
当前标准板：嘉立创EDA 项目 `Resona` 中的 `ESP32-S3-N16R8`  
PCB UUID：`3d79e1e63321a03a`

## 1. 当前设计基线

- 后续 PCB 工作以现有 `ESP32-S3-N16R8` 文件为唯一板级基线。
- 旧方案中的“左右两排中心距 24.0 mm、两个 1x22 母座”仅适用于独立扩展底板，不再作为当前 PCB 的封装依据。
- 当前 PCB 已带 ESP32-S3-N16R8 模组、电源、USB、下载电路和 GPIO 引出，禁止重复设计这些基础电路。
- 现阶段完成的是功能映射迁移：已在 PCB 中加入 24 条以 `RSN:` 开头的功能丝印，并保存到当前文件。
- 尚未完成的是外设接口、电源保护、双舵机供电和对应走线；这些应作为下一阶段的板级扩展进行。

## 2. 固件与 PCB 统一引脚表

| 功能 | GPIO | 接口/信号 | 设计说明 |
|---|---:|---|---|
| MaixCam UART RX | 38 | MaixCam A16/TX -> ESP32 RX | MaixCam TX 串联 4.7kΩ--10kΩ，实测 5kΩ稳定 |
| MaixCam UART TX | 39 | ESP32 TX -> MaixCam A17/RX | 可串 0Ω并预留断开焊盘 |
| 音量加 | 40 | VOL+ | 按键到 GPIO，按固件有效电平接法 |
| 水平舵机 | 41 | PAN PWM | 仅信号，舵机使用外部 5V |
| 俯仰舵机 | 18 | TILT PWM | 仅信号，舵机使用外部 5V |
| 音量减 | 17 | VOL- | 已避开视觉 UART GPIO39 |
| LCD MOSI | 11 | ST7789 MOSI | 显示总线 |
| LCD CLK | 12 | ST7789 SCLK | 显示总线 |
| LCD DC | 13 | ST7789 DC | 显示控制 |
| LCD RST | 14 | ST7789 RST | 显示复位 |
| LCD CS | 21 | ST7789 CS | 显示片选 |
| LCD BL | 2 | ST7789 BL | 背光控制 |
| 麦克风 WS | 4 | MIC WS | I2S 输入 |
| 麦克风 SCK | 5 | MIC SCK | I2S 输入 |
| 麦克风 DIN | 6 | MIC DATA | I2S 输入 |
| 扬声器 DOUT | 7 | AMP DIN | I2S 输出 |
| 扬声器 BCLK | 15 | AMP BCLK | I2S 输出 |
| 扬声器 LRCK | 16 | AMP LRCK | I2S 输出 |
| 灯控制 | 10 | LAMP | 外接负载时必须经驱动器件 |
| 触摸/功能键 | 47 | TOUCH | 数字输入 |
| Boot | 0 | BOOT | 保留下载功能 |
| 板载 LED | 48 | LED | 板载状态指示 |

固件依据：`HRI-SeniorCare/Main/main/boards/bread-compact-wifi/config.h`、`main/uart_k210/uart_k210.h` 和 `main/servo/servo_tracker.cc`。

## 3. 外设接口电路

### MaixCam Pro UART

```text
MaixCam A16/TX -- 4.7kΩ~10kΩ -- ESP32 GPIO38/RX
ESP32 GPIO39/TX -- 0Ω/可断开跳线 -- MaixCam A17/RX
MaixCam GND -------------------- ESP32 GND
Baud: 115200, 8N1
```

接口建议使用 1x3 防呆插座，丝印按设备视角明确标注 `GND / ESP_TX / ESP_RX`，并额外标注 A16、A17，避免 TX/RX 命名歧义。

### 双舵机

```text
PAN:  GND / 5V_SERVO / GPIO41
TILT: GND / 5V_SERVO / GPIO18
```

- 舵机由独立 5V 电源输入供电，不得从 ESP32 3V3 取电。
- 舵机电源地、ESP32 地、MaixCam 地必须共地。
- 5V_SERVO 入口建议加入 470µF--1000µF 电解电容和 0.1µF 陶瓷电容。
- 舵机 5V 与 GND 使用宽线或铺铜，PWM 信号远离音频输入线。

### 显示、音频和按键

- ST7789 使用 GPIO2/11/12/13/14/21，接口顺序必须按实际屏幕模块复核。
- I2S 麦克风使用 GPIO4/5/6；I2S 功放使用 GPIO7/15/16。
- 音量键使用 GPIO40 和 GPIO17，不再占用 GPIO39。
- GPIO10 只输出控制信号；若驱动较大灯负载，使用 MOSFET 和保护电路。

## 4. 当前嘉立创EDA迁移结果

已在 `ESP32-S3-N16R8` PCB 上保存 `RSN:` 功能丝印：包含板级标题、GPIO 功能标注、电源/UART 约束说明，以及 LCD、Audio、UI、Vision、Servo、Power 等模块分区标题。

当前板框已调整为以 ESP32-S3 主体为中心的横向布局。左侧用于显示、音频和人机交互模块，右侧用于 MaixCam 视觉、双舵机和独立舵机电源接口。MaixCam、PAN、TILT、5V_SERVO 输入、电容位和 MaixCam TX 串联电阻位已落到 PCB；LCD、MIC、AMP/SPK、UI/LAMP 模块也已补充为左侧功能接口。

左侧新增接口如下：

| 接口 | 功能 | 网络 |
|---|---|---|
| J5 | LCD / ST7789 | 3V3, IO14, IO13, IO12, IO11, GND, IO21, IO2 |
| J6 | I2S Microphone | GND, 3V3, IO4, IO5, IO6 |
| J7 | I2S AMP / Speaker | GND, 5V, IO16, IO15, IO7 |
| J8 | UI Buttons | GND, IO40, IO17, IO47 |
| J8 extension | Lamp | IO10, 5V |

注意：这些接口目前是 2.54 mm 通孔焊盘级布局，用于固化网络关系和模块分区。正式下单前应替换为具体器件封装，并重新布线、清除 DRC。

## 5. 下一阶段实施顺序

1. 在原理图中建立 MaixCam、PAN、TILT、LCD、MIC、AMP、VOL+/VOL- 和 5V_SERVO 接口。
2. 给全部接口连接本表中的 GPIO 网络名，并进行 ERC。
3. 同步到 `ESP32-S3-N16R8` PCB，在现有板框可扩展区域放置接口与保护器件。
4. 优先布置外部 5V、舵机接口和大电容，再布 UART、显示、音频和按键。
5. 完成 GND 铺铜、5V_SERVO 加宽、丝印方向检查和 DRC。
6. 输出 Gerber 前核对 GPIO、TX/RX 交叉、电源极性、连接器 Pin 1、板框和安装孔。

## 6. 制板前红线

- 不以旧的 24.0 mm 排针中心距替代当前 N16R8 PCB 的真实封装。
- 不把舵机接到 3V3，也不让舵机大电流经过 ESP32 的细电源线。
- 不移除 MaixCam TX 串联电阻位。
- 不在未核对模块接口顺序时直接下单。
- 原理图网络、PCB 丝印与固件 GPIO 三者必须一致后才能生成生产文件。

## 7. PCB 布线同步审计（2026-08-17）

已通过嘉立创EDA API 对当前 `ESP32-S3-N16R8` PCB 的焊盘、网络和导线进行核验：

- 项目使用的全部功能 GPIO 均存在真实 PCB 网络，并已从 ESP32-S3 模组连接到板边通孔。
- `IO38`、`IO39`、`IO41`、`IO18`、`IO40`、`IO17` 等关键网络均具有至少 2 个焊盘、非零导线数量和非零布线长度。
- 显示、音频、灯、触摸、5V、3V3 和 GND 网络同样已经存在。
- 因此当前“ESP32 模组 -> 板边排针”不需要重复布线；下一步应从板边排针扩展至专用外设连接器。

关键网络审计摘要：

| 网络 | 焊盘数 | 导线段数 | 网络长度（mil） |
|---|---:|---:|---:|
| IO38 / Maix RX | 2 | 7 | 564.59 |
| IO39 / Maix TX | 2 | 5 | 514.59 |
| IO41 / Pan | 3 | 12 | 802.58 |
| IO18 / Tilt | 2 | 10 | 623.25 |
| IO40 / VOL+ | 3 | 12 | 889.65 |
| IO17 / VOL- | 2 | 9 | 574.37 |
| 5V | 6 | 30 | 1815.64 |
| 3V3 | 13 | 34 | 3391.18 |

严格 DRC 当前报告 318 条既有细线规则错误：原板导线宽度为 0.10 mm，而当前规则下限为 0.127 mm。该问题属于导入板与当前 DRC 规则不一致。未自动批量加粗，原因是模组密集区可能产生新的间距或焊盘避让问题；应在保留原始版本后单独进行线宽修复并再次运行完整 DRC。

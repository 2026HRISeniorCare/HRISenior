# Resona PCB 打板前整理稿

更新时间：2026-08-16  
工程：Resona  
当前验证目标：把已在面包板/杜邦线环境中跑通的 ESP32-S3 + MaixCam Pro + 双 SG90 舵机 + 屏幕 + 音频系统整理为可画原理图和 PCB 的连接依据。

## 1. 当前硬件功能边界

本 PCB 只负责把现有已验证硬件连接固化，核心计算仍由现有模块完成：

- ESP32-S3：主控、语音交互、屏幕显示、云端通信、融合逻辑、舵机控制。
- MaixCam Pro：视觉识别、人脸检测、情绪结果输出。
- SG90 舵机 ×2：分别控制 XOY 水平转动和 XOZ 俯仰转动。
- ST7789 1.54 inch SPI 屏幕：本地状态显示。
- I2S 麦克风与 I2S 扬声器链路：语音输入输出。
- 外部 5V 电源：舵机供电，必须与 ESP32/MaixCam 共地。

## 2. ESP32-S3 引脚总表

| 功能 | ESP32-S3 GPIO | 方向 | 外设/连接对象 | 备注 |
|---|---:|---|---|---|
| MaixCam UART RX | GPIO38 | 输入 | MaixCam A16/TX | MaixCam TX → 串联 4.7kΩ/5.1kΩ → ESP32 GPIO38 |
| MaixCam UART TX | GPIO39 | 输出 | MaixCam A17/RX | 当前保留双向 UART；若只接收视觉，可预留但不焊 |
| UART 波特率 | - | - | - | 115200 |
| XOY 水平舵机 PWM | GPIO41 | 输出 | SG90 Pan Signal | 已实测可动 |
| XOZ 俯仰舵机 PWM | GPIO18 | 输出 | SG90 Tilt Signal | 已实测双轴代码可输出 |
| 音量加 | GPIO40 | 输入 | Button | 保留原配置 |
| 音量减 | GPIO17 | 输入 | Button | 已从 GPIO39 移走，避免 UART TX 冲突 |
| BOOT | GPIO0 | 输入 | Button | ESP32 下载/启动相关，不建议复用 |
| Touch | GPIO47 | 输入 | Touch/Button | 保留 |
| Builtin LED | GPIO48 | 输出 | LED | 保留 |
| Lamp | GPIO10 | 输出 | Lamp/LED | 保留 |

## 3. 显示屏 ST7789 连接

| ST7789 信号 | ESP32-S3 GPIO | 备注 |
|---|---:|---|
| SDA / DIN / MOSI | GPIO11 | SPI 数据 |
| SCL / SCK / CLK | GPIO12 | SPI 时钟 |
| DC | GPIO13 | 数据/命令 |
| RST | GPIO14 | 复位 |
| CS | GPIO21 | 片选 |
| BL | GPIO2 | 背光 |
| VCC | 3V3 或模块要求电压 | 按实际屏幕模块丝印确认 |
| GND | GND | 与 ESP32 共地 |

## 4. 音频连接

| 音频功能 | ESP32-S3 GPIO | 方向 | 备注 |
|---|---:|---|---|
| I2S MIC WS | GPIO4 | 输出/时钟 | 麦克风 LRCLK/WS |
| I2S MIC SCK | GPIO5 | 输出/时钟 | 麦克风 BCLK/SCK |
| I2S MIC DIN | GPIO6 | 输入 | 麦克风数据输入 |
| I2S SPK DOUT | GPIO7 | 输出 | 扬声器数据输出 |
| I2S SPK BCLK | GPIO15 | 输出/时钟 | 扬声器 BCLK |
| I2S SPK LRCK | GPIO16 | 输出/时钟 | 扬声器 LRCLK |

## 5. MaixCam Pro 视觉 UART 连接

| MaixCam Pro | PCB 网络 | ESP32-S3 | 处理方式 |
|---|---|---|---|
| A16 / TX | VISION_UART_RX | GPIO38 / RX | 串联 4.7kΩ 或 5.1kΩ，靠近 ESP32 侧放置也可 |
| A17 / RX | VISION_UART_TX | GPIO39 / TX | 直连或预留 0Ω 电阻位 |
| GND | GND | GND | 必须共地 |

注意：

- 原型中 MaixCam TX → ESP32 RX 使用约 5kΩ 后稳定，因此 PCB 上不要直接硬连，建议放 4.7kΩ 或 5.1kΩ串联电阻。
- ESP32 TX → MaixCam RX 当前不是系统必须链路，但建议在 PCB 上预留 0Ω 电阻/跳线位，方便以后调试。
- MaixCam 与 ESP32 的 UART 线尽量短，远离舵机电源线和扬声器功放线。

## 6. 双 SG90 舵机连接

| 舵机 | 信号线 | 电源 | 地线 | 备注 |
|---|---:|---|---|---|
| XOY 水平舵机 / Pan | ESP32 GPIO41 | 外部 5V | GND | 控制水平旋转 |
| XOZ 俯仰舵机 / Tilt | ESP32 GPIO18 | 外部 5V | GND | 控制上下俯仰 |

PCB 必须预留：

- 舵机 5V 电源输入端子。
- 舵机 5V 与系统 GND 之间的大电容焊盘，建议至少预留 470µF 或 1000µF 电解电容位置。
- 每个舵机接口采用 3Pin 排针：GND / 5V_SERVO / SIGNAL。
- 舵机电源线宽应明显大于信号线，建议 5V_SERVO 和 GND 用粗线或铺铜。

不要从 ESP32 3V3 给舵机供电。

## 7. 推荐连接器规划

| 连接器 | 建议命名 | 引脚顺序建议 | 说明 |
|---|---|---|---|
| MaixCam UART | J_MAIX_UART | GND, ESP_TX(GPIO39), ESP_RX(GPIO38) | ESP_RX 线上串 4.7kΩ/5.1kΩ |
| 舵机 Pan | J_SERVO_PAN | GND, 5V_SERVO, SIG(GPIO41) | 水平舵机 |
| 舵机 Tilt | J_SERVO_TILT | GND, 5V_SERVO, SIG(GPIO18) | 俯仰舵机 |
| 舵机电源输入 | J_SERVO_PWR | 5V_SERVO, GND | 外接 5V 电源 |
| 屏幕 | J_LCD | VCC, GND, MOSI, CLK, DC, RST, CS, BL | 按屏幕模块排针顺序调整 |
| 麦克风 | J_MIC | VCC, GND, WS, SCK, DIN | 按模块丝印调整 |
| 扬声器/I2S功放 | J_SPK | VCC, GND, DOUT, BCLK, LRCK | 按模块丝印调整 |

## 8. PCB 布局约束

1. ESP32 天线区域保持净空，不要铺铜、不要走高速线、不要放舵机电源线。
2. 舵机 5V 电源走线远离 ESP32 天线、MaixCam UART、I2S 麦克风线。
3. MaixCam UART 的 RX/TX 线短且靠近地线回流。
4. 屏幕 SPI 线尽量成组走线，避免横穿舵机供电区域。
5. 音频输入线尽量远离 PWM 舵机信号和舵机电源。
6. 所有外设 GND 必须汇到同一系统地，但舵机大电流回流路径不要穿过麦克风/ESP32 敏感区域。

## 9. 打板前必须确认的三项

- 确认 ESP32-S3 实际开发板/模组封装：如果直接把开发板插到 PCB 上，需要按开发板排针封装画；如果使用裸模组，需要重新考虑 USB、下载电路、3V3 电源和天线区。
- 确认 ST7789 屏幕、麦克风、功放、MaixCam 的实际排针顺序，不要只按功能名画。
- 确认 5V 舵机电源容量：双 SG90 同时动作时建议至少预留 1A 以上余量。

## 10. 当前软件对应关系

代码真值来源：

- ESP32 board config：`C:\Users\25453\Desktop\HRISenior\HRISenior\HRI-SeniorCare\Main\main\boards\bread-compact-wifi\config.h`
- MaixCam UART：`C:\Users\25453\Desktop\HRISenior\HRISenior\HRI-SeniorCare\Main\main\uart_k210\uart_k210.h`
- 双轴舵机：`C:\Users\25453\Desktop\HRISenior\HRISenior\HRI-SeniorCare\Main\main\servo\servo_tracker.cc`

关键软件配置：

- UART：TX GPIO39，RX GPIO38，115200 baud。
- Pan 舵机：GPIO41，50Hz PWM。
- Tilt 舵机：GPIO18，50Hz PWM。
- 舵机角度范围：20°–160°。
- 舵机控制更新间隔：80ms。

## 11. 下一步执行顺序

1. 在嘉立创 EDA 原理图中先建立连接器和网络名，不急着自动布线。
2. 按本表放置 ESP32、MaixCam UART、屏幕、音频、双舵机、电源输入、电容焊盘。
3. 先做 ERC/网络检查，确认没有 GPIO 冲突。
4. 再转 PCB，先摆放连接器位置，确保实际机械安装方向合理。
5. 最后布线：先电源地，再 UART/I2S/SPI/PWM。


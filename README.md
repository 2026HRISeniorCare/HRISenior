# 基于人机交互与模态识别的语音情感交流式助老机器人

> **Resona** · Multimodal Elderly Care Robot
> 北京化工大学 · 大学生创新创业训练计划项目(创新训练类)

> 在 [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 语音助手基座之上，扩展出「视觉驱动双轴人脸跟随」与「视觉 + 语音多模态情绪识别」两大能力，面向独居 / 空巢老人提供情感陪护与情绪风险记录。
>
> 核心链路：**MaixCAM Lite 视觉表情识别 → UART 上报 → ESP32-S3 Dempster-Shafer 证据融合 ← 板载语音情绪识别 → 云端大模型生成共情回复 → TTS 语音合成**。

---

## 目录

- [项目概述](#项目概述)
- [系统架构](#系统架构)
- [硬件与接线](#硬件与接线)
- [参数配置](#参数配置)
- [功能模块详解](#功能模块详解)
  - [1. 视觉情绪识别(MaixCAM Lite FER)](#1-视觉情绪识别maixcam-lite-fer)
  - [2. 语音情绪识别(SER)](#2-语音情绪识别ser)
  - [3. D-S 证据融合引擎](#3-d-s-证据融合引擎)
  - [4. 上行数据格式](#4-上行数据格式)
  - [5. 麦克风阵列声源定位](#5-麦克风阵列声源定位tdoa--gcc-phat--卡尔曼)
  - [6. 端云协同与隐私](#6-端云协同与隐私)
- [串口通信与 MCP](#串口通信与-mcp)
- [源码文件清单](#源码文件清单)
- [集成步骤](#集成步骤)
- [功能清单与阶段性成果](#功能清单与阶段性成果)
- [开发环境与固件](#开发环境与固件)
- [后期路线图](#后期路线图)
- [致谢与开源协议](#致谢与开源协议)

---

## 项目概述

> **背景:** 截至 2025 年,我国 60 岁以上人口占比已达 **23%**、65 岁以上占 **15.9%**(约 3.23 亿),独居与空巢老人占比激增。相比跌倒、火灾等物理隐患,老人"报喜不报忧""强颜欢笑"式的**隐性抑郁**更易被忽视。本项目聚焦开源社区关注较少的**多模态情绪识别**,用一台低成本边缘设备甄别老人的隐性负面情绪并触发共情陪护。
>

本项目基于 [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32)(v2.0.4)扩展而来。在保留其「离线唤醒 + 流式 ASR/LLM/TTS + MCP 设备控制」能力的基础上,新增了两大自研模块:

**① 视觉驱动的双轴云台追踪**

- **视觉定位**：MaixCAM Lite 使用 GC4653 摄像头检测人脸并输出边界框。
- **双轴云台**：两个 SG90 舵机分别控制水平（Pan）与俯仰（Tilt），由 ESP32-S3 根据人脸中心偏差闭环跟随。
- **串口通信**：MaixCAM Lite 与 ESP32-S3 通过 UART1 双向通信，实际波特率为 115200。
- **状态显示**：ESP32-S3 驱动 ST7789 屏幕显示设备、语音、视觉和融合状态。
- **MCP 语音控制**：通过语音指令控制舵机旋转与追踪开关。

**② 多模态情绪识别(SIEVOX 核心)**

将原有语音助手升级为**多模态情绪感知平台**：MaixCAM Lite 负责人脸检测与表情识别（FER），ESP32-S3 板载麦克风负责语音情绪识别（SER），两路证据通过 **Dempster-Shafer（D-S）证据理论**完成决策级融合。融合结果和模态冲突只上传到远端服务器记录，不在设备端播放警报，以免打断正常语音交互。

> 当前实机：ESP32-S3 N16R8（`board->bread-compact-wifi`）+ Sipeed MaixCAM Lite + 双 SG90 云台 + ST7789 屏幕。K210 仅保留为早期研究原型，不属于当前实机链路。

---

## 系统架构

```
┌─────────────────────┐            ┌──────────────────────────────────────┐
│   MaixCAM Lite      │   UART     │         ESP32-S3 主控                 │
│                     │  115200    │                                      │
│  摄像头 → FER       │ ─────────→ │  uart_k210.cc (JSON 解析 + CRC)      │
│  YOLOv8 人脸检测    │  JSON      │           │                          │
│  表情分类模型       │  数据包    │           ▼                          │
│  main.py            │           │  ┌─────────────────────┐             │
│                     │           │  │ DSFusionEngine       │             │
│  情绪概率:          │ ←──────── │  │ (Dempster-Shafer)    │             │
│  [H, S, N, A]       │  命令行    │  │                      │             │
└─────────────────────┘           │  └──────┬──────────────┘             │
                                  │         │                             │
┌─────────────────────┐           │  ┌──────┴──────────────┐             │
│   I2S 麦克风         │  PCM      │  │ SpeechEmotionAnalyser│             │
│   (板载)            │ ────────→ │  │ (Pitch/RMS/MFCC)     │             │
│                     │  16kHz    │  │                      │             │
└─────────────────────┘           │  └─────────────────────┘             │
                                  │         │                             │
                                  │         ▼                             │
                                  │  BuildEmotionPayload()                │
                                  │         │                             │
                                  │    MQTT / WebSocket                   │
                                  └─────────┼─────────────────────────────┘
                                            │
                                            ▼
                                  ┌─────────────────────┐
                                  │   后端服务器         │
                                  │   DeepSeek / Qwen    │
                                  │   → 共情回复          │
                                  └─────────────────────┘
```

> 情绪标签 `[H, S, N, A]` 分别为 快乐(Happy)/ 悲伤(Sad)/ 中性(Neutral)/ 愤怒(Angry)。两路传感器以不同速率异步工作:视觉 FER 约 6–8 FPS,语音 SER 在一段话结束时给出结果,融合引擎则由 1 Hz 定时器独立驱动,从而解耦两条数据流。

---

## 硬件与接线

### 当前实机配置 / Current Hardware

| 模块 / Module | 当前配置 / Current configuration |
|---|---|
| 主控 / Main controller | ESP32-S3 N16R8，ESP-IDF 工程，板型 `bread-compact-wifi` |
| 视觉 / Vision | Sipeed MaixCAM Lite，GC4653，MaixPy |
| 视觉模型 / Vision models | `yolov8n_face` 人脸检测 + `face_emotion_bf16` 表情分类 |
| 语音 / Audio | ESP32-S3 板载麦克风，16 kHz PCM，VAD + SER |
| 显示 / Display | ST7789 LCD，由 ESP32-S3 驱动 |
| 执行器 / Actuators | 2 × SG90：水平 Pan + 俯仰 Tilt |
| 云端 / Cloud | Xiaozhi 语音链路 + `https://sievox.cn/resona` 情绪数据与预警记录 |

The deployed prototype uses an **ESP32-S3 N16R8** as the main controller and a **Sipeed MaixCAM Lite** as the vision node. The Lite runs face detection and facial-expression inference locally; the ESP32-S3 performs speech-emotion analysis, multimodal fusion, display rendering, cloud reporting, and two-axis servo control. Raw audio and camera frames remain on-device.

### UART 接线 / UART Wiring

| MaixCAM Lite | 中间连接 / Connection | ESP32-S3 |
|---|---|---|
| A16 / UART0_TX | 串联 5 kΩ 电阻 / 5 kΩ series resistor | GPIO38 / UART1_RX |
| A17 / UART0_RX | 直连 / Direct | GPIO39 / UART1_TX |
| GND | 共地 / Common ground | GND |

- 串口参数 / UART settings：**115200 baud, 8N1**。
- 遥测格式 / Telemetry：换行分隔 JSON，包含序号、时间戳、人脸框、四类情绪概率、质量值和 CRC-8。
- 情绪顺序 / Emotion order：`[happy, sad, neutral, anger]`。
- MaixCAM Lite 的 UART0 同时可能输出系统日志；ESP32 接收器会重同步到以 `{` 开始、以换行结束的有效数据帧。

### 舵机与供电 / Servos and Power

| 功能 / Axis | ESP32-S3 PWM | 供电 / Power |
|---|---|---|
| 水平 Pan | GPIO41 | 外部 5 V |
| 俯仰 Tilt | GPIO18 | 外部 5 V |

两个 SG90 必须使用稳定的外部 5 V 供电，舵机电源地、ESP32-S3 地和 MaixCAM Lite 地必须共地。不要从 ESP32-S3 的 3.3 V 引脚给舵机供电，否则舵机启动电流可能触发 Brownout。

Both SG90 servos must use a stable external 5 V supply. The servo supply ground, ESP32-S3 ground, and MaixCAM Lite ground must be connected together. Do not power a servo from the ESP32-S3 3.3 V rail, because the startup current can reset the controller.

### MaixCAM Lite 运行参数 / Runtime Settings

- 摄像头输出 / Camera output：`640 × 480`，`buff_num=1`，`fps=60`。
- 传感器模式 / Sensor mode：GC4653 `1280 × 720 @ 60 fps`。
- 检测输入 / Detector input：`320 × 224 RGB`。
- 视觉上报周期 / Vision telemetry interval：约 180 ms。
- 当前脚本 / Current script：`MaixCam_Lite/main.py`。

### 实机验证 / Hardware Validation

2026-08-29 的连续联调记录确认：MaixCAM Lite、ESP32-S3、双轴舵机与远端服务器链路同时工作。15 秒串口窗口内统计为 `lines=593`、`parse_fail=0`、`crc_fail=0`、`drops=0`；服务器返回设备 `online=1`，融合结果能够持续更新。该记录证明通信链路已跑通，不代表情绪模型在目标人群上的最终准确率。

The 2026-08-29 integration run verified the complete MaixCAM Lite → ESP32-S3 → dual-servo → cloud path. During a 15-second serial window, the receiver reported `lines=593`, `parse_fail=0`, `crc_fail=0`, and `drops=0`; the server reported the device as `online=1`. This validates system connectivity, not final emotion-recognition accuracy for the target population.

---

## 参数配置

通过修改 `config.json`,或直接改 `config.py` 中的默认值来调整系统参数。

### 参数示例

```yaml
{
  "init_pitch": 50,                     # 俯仰轴初始位置 (0-100)
  "init_roll": 50,                      # 横滚轴初始位置 (0-100)
  "pitch_pid": [0.5, 0.02, 0.03, 5],    # 俯仰轴 PID 参数 [P, I, D, I_max]
  "roll_pid": [0.5, 0.02, 0.03, 10],    # 横滚轴 PID 参数 [P, I, D, I_max]
  "pitch_reverse": false,               # 俯仰轴反向控制 (true=反向, false=正向)
  "roll_reverse": true,                 # 横滚轴反向控制 (true=反向, false=正向)
  "audio_range": 10,                    # 音频检测输出范围 (误差放大系数)
  "ignore_threshold": 0.1,              # 忽略阈值 (声音强度低于此值将被忽略)
  "roll_range": [10, 90],               # 横滚轴运动范围限制 [最小角度, 最大角度]
  "lcd_rotation": 0,                    # LCD 屏幕旋转角度 (0/90/180/270)
  "pitch_scale": 1.8,                   # 俯仰轴显示比例系数 (LCD 可视化缩放)
  "roll_scale": 1.8,                    # 横滚轴显示比例系数 (LCD 可视化缩放)
  "main_timeout": 120,                  # 主程序超时时间 (秒, 运行此时长后自动退出)
  "loop_delay": 0.01                    # 主循环延迟 (秒, 控制循环频率)
}
```

### 关键参数调整

**`ignore_threshold`(忽略阈值)** — 声音强度低于此阈值的声源会被忽略。数值越大越不灵敏(过滤更多小声音),越小越灵敏。

```yaml
"ignore_threshold": 8    # 只响应强烈声源
"ignore_threshold": 2    # 能检测到轻微声音
"ignore_threshold": 0    # 不忽略任何声音
```

推荐值:养老院环境(过滤背景噪音)6–10;正常室内 3–5;安静环境(需检测轻声)1–2。

**`audio_range`(音频检测范围)** — 定义有效声源的方向范围 `[最小角度, 最大角度]`。范围越窄越不易触发(只响应特定方向),越宽越易触发。

```yaml
"audio_range": [-30, 30]     # 只检测正前方 ±30°
"audio_range": [-90, 90]     # 前方半球 ±90°
"audio_range": [-160, 160]   # 几乎全方位
```

推荐值:只关注正前方 `[-45, 45]` 或 `[-30, 30]`;前方半球 `[-90, 90]`;近全方位 `[-150, 150]`。

---

## 功能模块详解

### 1. 视觉情绪识别（MaixCAM Lite FER）

**模型选型：** MaixCAM Lite 先用 `yolov8n_face` 检测人脸，再将对齐后的人脸灰度图送入 `face_emotion_bf16` 分类器。原始七类输出会映射为 ESP32 融合引擎使用的四类 `[happy, sad, neutral, anger]`。

**低内存运行：** GC4653 使用 `640 × 480`、单缓冲和 60 FPS 配置，推理前显式缩放到 `320 × 224`。摄像头在神经网络模型之前初始化，避免 Lite 固件出现媒体缓冲不足或首帧超时。

**UART 协议设计：** 每一行 MaixCAM Lite→ESP32 数据都是带单调递增序号和 CRC-8 的独立 JSON 对象。ESP32 可通过序号检测丢包，并利用 CRC 防御舵机电源干扰引起的比特翻转。

The Lite vision pipeline combines YOLOv8 face detection with an on-device facial-expression classifier. Frames are emitted as newline-delimited, CRC-protected JSON packets so that the ESP32-S3 can recover from mixed UART boot logs and detect corruption without an ACK/NACK round trip.

### 2. 语音情绪识别(SER)

**为什么不用神经网络模型?** 完整的 SER 模型(如 wav2vec2 → 线性分类器)需要约 50 MB 权重、每帧 100+ MFLOPS,远超 ESP32-S3 能力。因此改为提取三种与基本情绪强相关的经典韵律特征。

**特征依据:**

- **基频(Pitch / F0)**:自相关法估计。老年说话者基频普遍偏低,设 `pitch_min_hz=60` 以适配年龄相关的嗓音变化。
- **能量(RMS)**:简单而有效——抑郁与悲伤与嗓音能量下降强相关。
- **MFCC(可选 TFLite 路径)**:13 维系数刻画频谱包络。未来若有训练好的 INT8 TFLite Micro 模型,可替换掉当前的启发式映射。

**内存预算:** SER 模块约占 54 KB 堆内存(环形缓冲 + FFT + Mel 滤波器),给 WiFi、AudioService 和融合引擎留有充裕空间。

### 3. D-S 证据融合引擎

#### 为什么用 Dempster-Shafer 而非贝叶斯融合?

贝叶斯融合需要已知先验分布,并假设各源相互独立。D-S 理论在本场景有两大关键优势:

1. **显式建模不确定性。** 当 MaixCAM Lite 未检测到人脸时,可直接赋 m(Θ) = 0.95(95% 不确定),而不是伪造一个均匀分布。融合会自动让语音模态占主导。
2. **量化冲突。** 冲突因子 K 直接度量面部与声音的分歧程度——这正是"掩饰型抑郁"检测所需的信号。

#### Dempster 合成规则

给定 Θ = {H, S, N, A} 上的两个 BPA:m₁(视觉)与 m₂(语音):

```
m₁₂(A) = [Σ_{B∩C=A} m₁(B)·m₂(C)] / (1 - K)

其中 K = Σ_{B∩C=∅} m₁(B)·m₂(C)
```

对我们受限的焦元集合(单元素 + Θ):

```
raw(θᵢ) = m₁(θᵢ)·m₂(θᵢ) + m₁(θᵢ)·m₂(Θ) + m₁(Θ)·m₂(θᵢ)
raw(Θ)  = m₁(Θ)·m₂(Θ)
K       = Σ_{i≠j} m₁(θᵢ)·m₂(θⱼ)
```

#### 冲突处理(Zadeh 悖论保护)

当 K 超过 0.85 时,标准 Dempster 规则可能给出反直觉结果:例如面部笃定"快乐"、声音笃定"悲伤",此时 K≈0.9,用 (1-K) 归一化会不可预测地放大微小残余质量。

我们的做法:当 K ≥ 阈值时,回退到**可靠度加权平均**;更重要的是在结果中置位 `high_conflict = true`——因为在养老场景里,这种冲突本身就是**临床上有意义的信号**:一个人面带微笑而声音颤抖,正是掩饰型抑郁的教科书式表现。

#### 由传感器概率构造 BPA

每个传感器的原始概率数组 `[p₁, p₂, p₃, p₄]` 用"简单支持函数"构造为 BPA:

```
m(θᵢ) = pᵢ × confidence
m(Θ)  = 1 - confidence
```

`confidence` 参数(视觉默认 0.75、语音默认 0.70)控制各传感器的影响力。当未检测到人脸时,视觉 confidence 降至 0.05,从而让语音成为唯一信息源。

#### 智能信任纠偏引擎(SNR / Lux 动态惩罚因子)

固定的 `confidence` 只是基线。真实场景里传感器会**动态失效**:光线太暗或人脸太远时视觉不可信,环境嘈杂时语音不可信。为此系统以环境**信噪比(SNR)** 与**光照强度(Lux)** 作为动态惩罚因子,实时调节各路的不确定度 m(Θ):

- **视觉环境差**(光暗 / 脸远):调高视觉不确定度 θ_V,系统转而采信声纹特征。
- **听觉环境差**(嘈杂):调高听觉不确定度 θ_A。
- **双优但冲突**:优先采信听觉——基频、共振峰等声纹特征比面部肌肉更难被人为伪造。

> **实现状态:** 🧪 该动态纠偏策略已在 PC 端 **5000 组高斯噪声蒙特卡洛**仿真中验证(见 `ds_monte_carlo_academic.png`),引入动态信任惩罚因子后较单模态(约 72%)取得约 **+13.5%** 的绝对提升;🚧 ESP32-S3 实机当前使用**静态**可靠度(`vision_reliability=0.6` / `audio_reliability=0.4`)与 `face_detected` 触发的置信降级,SNR/Lux 驱动的动态版本正在向 MCU 端全量移植(见[后期路线图](#后期路线图))。

### 4. 上行数据格式

ESP32 通过 `SendMcpMessage()` 将融合结果打包成如下 JSON,经现有 WebSocket / MQTT 通道上行至后端服务器:

```json
{
  "type":    "emotion_state",
  "ts":      1719500000000,
  "emotion": {
    "dominant":      "sad",
    "score":         0.72,
    "belief":        [0.08, 0.72, 0.15, 0.05],
    "conflict":      0.43,
    "high_conflict": false,
    "sources": {
      "vision": [0.60, 0.05, 0.10, 0.00],
      "audio":  [0.10, 0.56, 0.04, 0.00]
    }
  },
  "intent":  "我今天感觉还好",
  "device":  "SIEVOX-01"
}
```

`sources` 子对象保留两路原始输入以提供可解释性——后端服务器可据此记录日志,供看护复核与模型调参。

### 5. 早期研究原型：麦克风阵列声源定位

早期版本曾在 K210 上研究 MEMS7 麦克风阵列、GCC-PHAT、TDOA 和卡尔曼滤波声源追踪。该方案保留为研究资料，但**不属于当前 MaixCAM Lite + ESP32-S3 实机接线**。当前双轴云台由 MaixCAM Lite 输出的人脸边界框驱动。

- **频带分割优化**:数字滤波屏蔽低频底噪,仅锁定 **300–3400Hz** 核心人声频段运算,剔除冗余计算、压低延迟。
- **机电耦合校正**:引入**卡尔曼滤波**对 TDOA 输出做"预测-校正",超前补偿随动云台的物理惯性,解决传统声源追踪"寻而不稳"的抖动问题。
- **实测(阶段性成果):** 在 **5dB 低信噪比**极限抗噪环境下,方位角定位误差 **≤ 8°**,极限定位延迟低至 **220ms**,有效抑制室内多径回声。

> 以上声源定位指标对应早期原型；当前版本的实机状态以“硬件与接线 / Current Hardware”一节为准。

### 6. 端云协同与隐私

- **边缘侧预处理**:依托 ESP32-S3 在本地完成 **VAD**(语音活动检测)与降噪,过滤无效底噪,仅上传核心意图,降低网络传输量与延迟。
- **共情引擎**:云端接入轻量化大模型 **DeepSeek V3**,生成带情感色彩的回复文本,回端后由 **melotts** 合成情感语音。
- **隐私合规**:原始**音频 / 人脸数据绝不上云**(物理级销毁),仅上行情绪状态与意图文本,满足最严格的隐私要求。
- **网络延迟掩盖**(🚧 规划中):云端 API 往返约 1.5–2s,拟借助 FreeRTOS 多线程,在等待回传时先触发本地"点头"随动或"嗯嗯"微音频,用心理学反馈机制维持交互连贯。

---

## 串口通信与 MCP

### UART 通信

**MaixCAM Lite 端（`MaixCam_Lite/main.py`）**

```python
UART_DEVICE = "/dev/ttyS0"
UART_BAUD = 115200

pinmap.set_pin_function("A16", "UART0_TX")
pinmap.set_pin_function("A17", "UART0_RX")
ser = uart.UART(UART_DEVICE, UART_BAUD)

# Every packet begins with "{" and ends with "\n".
ser.write(encode_packet(packet).encode("ascii"))
```

`encode_packet()` 以不含 `crc` 字段的 JSON 主体计算 CRC-8（多项式 `0x07`），随后追加两位十六进制校验值。ESP32 会忽略 UART0 中夹杂的启动日志并自动重新同步到下一个合法 JSON 帧。

**ESP32-S3 端（`uart_k210.cc`，保留历史模块名）**

```cpp
#include "uart_k210.h"
#include <esp_log.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#define TAG "UART_VISION"

void UartK210::Init() {
    uart_config_t uart_config = {
        .baud_rate = BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE
    };

    ESP_ERROR_CHECK(uart_param_config(UART_NUM_, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(UART_NUM_, TX_PIN, RX_PIN,
                                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    ESP_ERROR_CHECK(uart_driver_install(UART_NUM_, BUF_SIZE, 0, 0, NULL, 0));

    ESP_LOGI(TAG, "UART initialized: TX=%d, RX=%d, Baud=%d",
             TX_PIN, RX_PIN, BAUD_RATE);
}

void UartK210::StartReceiveTask() {
    xTaskCreate([](void* param) {
        UartK210* uart = static_cast<UartK210*>(param);
        uint8_t buffer[BUF_SIZE];
        size_t index = 0;

        while (1) {
            uint8_t byte;
            int len = uart->ReceiveData(&byte, 1, 100);  // 每次读 1 字节
            if (len > 0) {
                if (byte == '\n') {
                    buffer[index] = '\0';
                    ESP_LOGI(TAG, "Received line: %s", buffer);
                    index = 0;                 // 收到完整一行, 重置缓冲区
                } else if (index < BUF_SIZE - 1) {
                    buffer[index++] = byte;
                } else {
                    ESP_LOGW(TAG, "Buffer overflow, resetting");
                    index = 0;                 // 缓冲区满, 丢弃
                }
            }
        }
    }, "uart_rx_task", 4096, this, 5, NULL);
}
```

### MCP 工具注册

`gimbal_controller.h` 中通过 MCP 暴露一组语音可调用的云台控制工具:

| MCP 工具 | 说明 | 下发命令 |
| -------- | ---- | -------- |
| `gimbal.get_state` | 获取云台状态(俯仰/横滚位置) | `GET_STATE` |
| `gimbal.roll.turn_left` | 横滚轴左转 | `ROLL_LEFT` |
| `gimbal.roll.turn_right` | 横滚轴右转 | `ROLL_RIGHT` |
| `gimbal.pitch.turn_up` | 俯仰轴上转 | `PITCH_UP` |
| `gimbal.pitch.turn_down` | 俯仰轴下转 | `PITCH_DOWN` |
| `gimbal.hold_position` | 保持当前位置(停止追踪) | `HOLD_POSITION` |
| `gimbal.reset` | 回归初始位置 | `RESET` |
| `gimbal.enable_tracking` | 启用音频追踪 | `ENABLE_TRACKING` |
| `gimbal.disable_tracking` | 禁用音频追踪 | `DISABLE_TRACKING` |

注册示例:

```cpp
void RegisterMcpTools() {
    auto& mcp_server = McpServer::GetInstance();

    // 获取云台状态
    mcp_server.AddTool("gimbal.get_state",
        "Get the current state of the gimbal (pitch and roll servo positions)",
        PropertyList(),
        [this](const PropertyList& properties) -> ReturnValue {
            SendCommand("GET_STATE");
            ESP_LOGI(TAG, "Request gimbal state");
            return true;
        });

    // 启用音频追踪
    mcp_server.AddTool("gimbal.enable_tracking",
        "Enable audio source tracking",
        PropertyList(),
        [this](const PropertyList& properties) -> ReturnValue {
            SendCommand("ENABLE_TRACKING");
            ESP_LOGI(TAG, "Enable audio tracking");
            return true;
        });

    // ……其余工具同理(见 gimbal_controller.h)
}
```

---

## 源码文件清单

情绪流水线分为**研究原型**（位于 `Smart-Aging-Acoustic-Perception-and-Optimized-Localization-System/`，含仿真与可视化脚本）和**当前部署代码**。ESP32-S3 固件位于 `HRI-SeniorCare/Main/main/`，MaixCAM Lite 程序位于仓库根目录的 `MaixCam_Lite/`。

| 环节 | 研究原型（Smart-Aging/） | 当前部署代码 | 语言 | 说明 |
|------|------------------------|--------------------------------------|------|------|
| 视觉 | — | `MaixCam_Lite/main.py` | Python (MaixPy) | Lite 摄像头、人脸检测、表情分类与 UART 遥测 |
| 语音 | `speech_emotion.{h,cc}` | `emotion/speech_emotion.{h,cc}` | C++ (ESP-IDF) | SER 特征提取 + 启发式映射 |
| 融合 | `ds_fusion_engine.{h,cc}` | `emotion/ds_fusion_engine.{h,cc}` | C++ (ESP-IDF) | Dempster 规则 + 冲突处理 |
| 融合 | `uart_k210.{h,cc}` | `uart_k210/uart_k210.{h,cc}` | C++ (ESP-IDF) | JSON 解析 + 丢包检测 |
| 上行 | `emotion_upstream.h` | `emotion/emotion_upstream.h` | C++ (ESP-IDF) | 上行 JSON 构造 |
| 上行 | `application_integration.cc` | *(已合并进 `application.cc`)* | C++ (ESP-IDF) | `application.cc` 接线指南 |

> Smart-Aging 目录另含 `ds_simulator.html`、`visualization*.py`、`ds_monte_carlo_academic.png` 等蒙特卡洛仿真与学术可视化资料。

---

## 集成步骤

将情绪流水线接入 ESP32 主固件的步骤:

1. **MaixCAM Lite 端：** 将 `MaixCam_Lite/main.py` 上传为 `/maixapp/main.py`，并确认 `/root/models/yolov8n_face.mud` 与 `/root/models/face_emotion.mud` 可用。
2. **ESP32 CMakeLists.txt:** 把 `speech_emotion.cc`、`ds_fusion_engine.cc` 及更新后的 `uart_k210.cc` 加入组件的 `SRCS` 列表。
3. **application.h:** 添加成员变量(SER、融合引擎、融合定时器)。
4. **application.cc `Start()`:** 注册视觉回调并初始化各模块。
5. **AudioService:** 将 `SER.FeedAudio()` 挂到 PCM 处理管线上。
6. **MainEventLoop:** 处理 `MAIN_EVENT_FUSION_TICK` 事件。
7. **VAD 状态切换:** 说话开始时 `Reset` SER,说话结束时触发一次融合。

> 上述接线已在本仓库 `HRI-SeniorCare/Main/main/application.{h,cc}` 中完成。

---

## 功能清单与阶段性成果

**基座能力(继承自 xiaozhi-esp32):**

- Wi-Fi / ML307 Cat.1 4G
- 离线语音唤醒([ESP-SR](https://github.com/espressif/esp-sr))
- 两种通信协议([WebSocket](docs/websocket.md) 或 MQTT+UDP)、OPUS 音频编解码
- 流式 ASR + LLM + TTS 语音交互
- 声纹识别([3D-Speaker](https://github.com/modelscope/3D-Speaker))
- OLED / LCD 显示屏(支持表情显示)、电量与电源管理
- 多语言(中/英/日),支持 ESP32-C3 / S3 / P4
- 设备端 MCP(音量、灯光、电机、GPIO 等)与云端 MCP 扩展

**本项目新增:**

- 麦克风阵列声源定位与云台追踪(6 麦环形阵列 + TDOA/GCC-PHAT + 卡尔曼 + PID 双轴云台 + LCD 可视化)
- MCP 语音控制舵机旋转与追踪开关
- 视觉 FER + 语音 SER 的 **D-S 多模态情绪融合** + SNR/Lux 智能信任纠偏
- 冲突量化与**掩饰型抑郁**预警
- 情绪状态 JSON 经 MCP 通道上行至后端服务器(DeepSeek V3 / Qwen),生成共情回复

### 阶段性成果(截至中期)

| 方向 | 指标 / 成果 | 状态 |
|------|-------------|------|
| 语音交互闭环 | ESP32-S3 本地 VAD + 云端 ASR/LLM/TTS，低延迟对话跑通 | ✅ 已实现 |
| 视觉与云台闭环 | MaixCAM Lite 人脸框经 UART 驱动 ESP32-S3 双 SG90 跟随 | ✅ 已实机验证 |
| 端云链路 | 情绪融合结果上传 `sievox.cn/resona`，服务器显示设备在线 | ✅ 已实机验证 |
| 声源定位研究原型 | K210 + MEMS7 的 TDOA/GCC-PHAT 方案，不属于当前实机接线 | 🧪 历史原型 |
| D-S 多模态融合(仿真) | 5000 组蒙特卡洛压测,引入动态信任惩罚因子后较单模态(约 72%)提升 **+13.5%** | 🧪 仿真验证 |
| D-S 引擎实机部署 | 静态可靠度版本已跑通;SNR/Lux 动态纠偏待全量移植 ESP32-S3 | 🚧 迁移中 |

> **状态图例:** ✅ 已在代码中实现 · 🧪 仅 PC 端仿真验证 · 🚧 规划 / 迁移中

---

## 开发环境与固件

**固件烧录:** 新手建议先不搭环境,直接使用免开发环境固件。固件默认接入 [xiaozhi.me](https://xiaozhi.me) 官方服务器,个人用户注册可免费使用 Qwen 实时模型。参见 [新手烧录固件教程](https://ccnphfhqs21z.feishu.cn/wiki/Zpz4wXBtdimBrLk25WdcXzxcnNS)。

**开发环境:**

- Cursor 或 VSCode + ESP-IDF 插件,SDK 版本 5.4 或以上
- Linux 编译速度快、免驱动困扰,优于 Windows
- 代码遵循 Google C++ 风格,提交前请确保符合规范

**开发者文档:**

- [自定义开发板指南](docs/custom-board.md)
- [MCP 协议物联网控制用法](docs/mcp-usage.md) / [MCP 协议交互流程](docs/mcp-protocol.md)
- [MQTT + UDP 混合通信协议](docs/mqtt-udp.md) / [WebSocket 通信协议](docs/websocket.md)
- 面包板手工制作教程见飞书文档:[《小智 AI 聊天机器人百科全书》](https://ccnphfhqs21z.feishu.cn/wiki/F5krwD16viZoF0kKkvDcrZNYnhb)

---

## 后期路线图

按中期检查规划,分三阶段推进:

**近期(2026.3–5)· 底层重构与固化**
- 硬件:PCB 画板与打样,取代杜邦线飞线,提升抗干扰与结构紧凑性。
- 结构:完成机器人实体外形,兼顾传感器布局与老年用户交互习惯。
- 算法:深化 SER 情感模型,将 **D-S 融合引擎(含 SNR/Lux 动态纠偏)全量部署至 ESP32-S3 实机**运行。

**中期(2026.6–8)· 场景联调与微调**
- 数据:构建面向老年群体的垂直助老语料库(日常对话 / 情绪波动 / 紧急求助)。
- 云端:用 **LoRA**(Low-Rank Adaptation)对开源大模型深度微调,替代简单 API 调用,提升共情回复的自然度与情感语境适配。
- 压测:多并发压力测试,彻底解决视听并行时的内存泄漏与资源抢占。

**远期(2026.9–10)· 实测验收与转化**
- 小样本真实老龄群体试用与闭环迭代;完成结题论文与技术报告;核心技术专利申报与软著登记。

**技术演进方向:**
- **TFLite Micro SER 模型**:用 RAVDESS / IEMOCAP 训练 3 层 MLP,量化 INT8 经 SPIFFS 部署,替换启发式映射。
- **时空对齐 + 时间平滑**:以 ESP32 为主时钟封装毫秒级时间戳、构建滑动时间窗对齐视听数据;融合结果做指数移动平均消抖。
- **扩展情绪类别**:将 Θ 扩展到含 {恐惧、惊讶、厌恶}——增大 BPA 数组(改 `kNumEmotions` 并重训模型)。
- **视觉模型优化**：在 MaixCAM Lite 内存预算内评估更稳健的人脸检测、表情分类和时间平滑方案。

---

## 致谢与开源协议

本项目基于虾哥开源的 [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32),以 **MIT 许可证**发布,允许任何人免费使用、修改或用于商业用途。小智 AI 聊天机器人作为语音交互入口,借助 Qwen / DeepSeek 等大模型能力,通过 MCP 协议实现多端控制;本项目在此基础上完成养老陪护方向的多模态情绪感知扩展。

**相关生态**(部署自有服务器可参考):

- [xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server)(Python)· [joey-zhou/xiaozhi-esp32-server-java](https://github.com/joey-zhou/xiaozhi-esp32-server-java)(Java)· [AnimeAIChat/xiaozhi-server-go](https://github.com/AnimeAIChat/xiaozhi-server-go)(Golang)
- 第三方客户端:[py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi)(Python)· [xiaozhi-android-client](https://github.com/TOM88812/xiaozhi-android-client)(Android)

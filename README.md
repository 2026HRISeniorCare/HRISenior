# 基于人机交互与模态识别的语音情感交流式助老机器人

> **Resona** · Multimodal Elderly Care Robot
> 北京化工大学 · 大学生创新创业训练计划项目(创新训练类)

> 在 [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 语音助手基座之上,扩展出「麦克风阵列声源定位云台」与「视觉 + 语音多模态情绪识别」两大能力,面向独居 / 空巢老人做情感陪护与**隐性抑郁**预警。
>
> 核心链路:**K210 视觉表情识别 → 串口上报 → ESP32-S3 Dempster-Shafer 证据融合 ← 板载语音情绪识别 → 经 MCP 通道上行 → 后端服务器(DeepSeek V3 / Qwen)生成共情回复 → melotts 语音合成**。

---

## 目录

- [项目概述](#项目概述)
- [系统架构](#系统架构)
- [硬件与接线](#硬件与接线)
- [参数配置](#参数配置)
- [功能模块详解](#功能模块详解)
  - [1. 视觉情绪识别(K210 / MaixCAM FER)](#1-视觉情绪识别k210--maixcam-fer)
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

**① 麦克风阵列声源定位与云台追踪**

- **声源定位**:MEMS7 麦克风环形阵列 + 轻量化 **TDOA / GCC-PHAT** 广义互相关,实时估计声源方位角。
- **双轴云台**:两个 SG90 舵机做俯仰(Pitch)/横滚(Roll)控制,自动追踪声源,并为后续加装摄像头预留位置。
- **串口通信**:ESP32-S3 与 K210 之间 UART 双向通信。
- **状态显示**:K210 LCD 实时显示云台角度与追踪状态。
- **MCP 语音控制**:通过语音指令控制舵机旋转与追踪开关。

**② 多模态情绪识别(SIEVOX 核心)**

将原有的"音频追踪云台"升级为**多模态情绪感知平台**:K210 摄像头做人脸表情识别(FER),ESP32 板载麦克风做语音情绪识别(SER),两路证据用 **Dempster-Shafer(D-S)证据理论**做决策级融合。系统再引入基于环境**信噪比(SNR)与光照(Lux)** 的**智能信任纠偏引擎**——谁的物理环境差就降低谁的权重,从而在复杂环境下抓住"面部微笑而声音颤抖"这类高**冲突**信号,识别老人的**掩饰型抑郁**并触发看护预警。

> 使用的开发板:ESP32-S3 N16R8(对应 `board->bread-compact-wifi`)、Sipeed Maixbit K210。

---

## 系统架构

```
┌─────────────────────┐            ┌──────────────────────────────────────┐
│   K210 / MaixCAM    │   UART     │         ESP32-S3 主控                 │
│                     │  115200    │                                      │
│  摄像头 → FER       │ ─────────→ │  uart_k210.cc (JSON 解析 + CRC)      │
│  fer_engine.py      │  JSON      │           │                          │
│  main.py            │  数据包    │           ▼                          │
│  uart_comm.py       │           │  ┌─────────────────────┐             │
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

### 引脚对接

#### Sipeed Maixbit K210 ↔ MEMS7 麦克风阵列

```python
mic.init(
    i2s_d0=22,
    i2s_d1=23,
    i2s_d2=21,
    i2s_d3=20,
    i2s_ws=19,
    i2s_sclk=18,   # MIC_CK
    sk9822_dat=10,
    sk9822_clk=9   # LED_CK
)
```

#### K210 ↔ 两个 SG90 云台 PWM

| K210 PWM | SG90  |
| -------- | ----- |
| IO7      | Pitch |
| IO8      | Roll  |

#### ESP32-S3 N16R8 ↔ Sipeed Maixbit K210 串口

| ESP32-S3<br>UART1 | K210<br>UARTHS  |
| ----------------- | --------------- |
| GPIO17 U1TXD      | IO4 ISP_RX (13) |
| GPIO18 U1RXD      | IO5 ISP_TX (12) |
| GND               | GND             |

### 硬件清单(K210 音频追踪模块)

- K210 开发板
- 6 麦克风环形阵列 + 1 个垂直麦克风
- 双轴舵机云台(俯仰 + 横滚)
- LCD 显示屏(320×240)
- LED 环用于方向指示

**技术特点:** 6 麦环形阵列声源定位;硬件 FFT 加速下的 **GCC-PHAT** 广义互相关 + **TDOA** 到达时间差解算方位角;**300–3400Hz** 频带分割滤除低频底噪;**卡尔曼滤波**对定位输出做"预测-校正",超前补偿云台机械惯性、抑制多径回声;参数可配 PID 驱动双轴云台;LCD 可视化追踪状态。

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

### 1. 视觉情绪识别(K210 / MaixCAM FER)

**模型选型:** K210 的 KPU 最多并行两个 INT8 模型。采用两级流水线——先用 YOLO 人脸检测器(约 200 KB)定位人脸框,再用 MobileNetV2-0.35 分类器(约 400 KB)将裁剪后的人脸映射到 4 类情绪。

**FER 节奏 vs 云台控制:** 若每帧都跑 KPU 推理,会抢占舵机控制回路的 CPU 时间。`fer_every_n`(默认 3)将 FER 节流到每 3 帧一次,使情绪更新维持约 6–8 FPS,同时云台追踪保持约 20 FPS 的流畅度。

**UART 协议设计:** 每一行 K210→ESP32 数据都是一个自包含的 JSON 对象,带**单调递增序号**和 **CRC-8**。这样一来,即使 ESP32 丢包(UART 缓冲溢出或忙于处理),也能凭序号缺口直接发现丢包,无需 ACK/NACK 往返;CRC 则防御云台电机电源轨 EMI 引起的比特翻转。

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

1. **显式建模不确定性。** 当 K210 未检测到人脸时,可直接赋 m(Θ) = 0.95(95% 不确定),而不是伪造一个均匀分布。融合会自动让语音模态占主导。
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

### 5. 麦克风阵列声源定位(TDOA + GCC-PHAT + 卡尔曼)

在 SRAM 极度受限的 K210 上,通过深度调度硬件 **FFT 加速器**,把 **GCC-PHAT**(广义互相关)算法轻量化落地,配合 **TDOA**(到达时间差)解算声源方位角:

- **频带分割优化**:数字滤波屏蔽低频底噪,仅锁定 **300–3400Hz** 核心人声频段运算,剔除冗余计算、压低延迟。
- **机电耦合校正**:引入**卡尔曼滤波**对 TDOA 输出做"预测-校正",超前补偿随动云台的物理惯性,解决传统声源追踪"寻而不稳"的抖动问题。
- **实测(阶段性成果):** 在 **5dB 低信噪比**极限抗噪环境下,方位角定位误差 **≤ 8°**,极限定位延迟低至 **220ms**,有效抑制室内多径回声。

> 声源定位与云台追踪逻辑运行在 K210(MaixPy)端;当前仓库 checkout 中未包含该端源码(部署在设备 SD 卡上)。

### 6. 端云协同与隐私

- **边缘侧预处理**:依托 ESP32-S3 在本地完成 **VAD**(语音活动检测)与降噪,过滤无效底噪,仅上传核心意图,降低网络传输量与延迟。
- **共情引擎**:云端接入轻量化大模型 **DeepSeek V3**,生成带情感色彩的回复文本,回端后由 **melotts** 合成情感语音。
- **隐私合规**:原始**音频 / 人脸数据绝不上云**(物理级销毁),仅上行情绪状态与意图文本,满足最严格的隐私要求。
- **网络延迟掩盖**(🚧 规划中):云端 API 往返约 1.5–2s,拟借助 FreeRTOS 多线程,在等待回传时先触发本地"点头"随动或"嗯嗯"微音频,用心理学反馈机制维持交互连贯。

---

## 串口通信与 MCP

### UART 通信

**K210 端(`uart_comm.py`)**

```python
class UartComm:
    def __init__(self):
        # 初始化 UARTHS, 波特率 115200
        # K210: IO4=RX(接ESP32的TX/GPIO17), IO5=TX(接ESP32的RX/GPIO18)

        # 先释放原来的映射，避免和 REPL 冲突
        for func in (fm.fpioa.UARTHS_RX, fm.fpioa.UARTHS_TX):
            try:
                fm.unregister(func)
            except ValueError:
                pass

        try:
            fm.register(board_info.PIN4, fm.fpioa.UARTHS_RX, force=True)  # IO4 ← ESP32 TX
            fm.register(board_info.PIN5, fm.fpioa.UARTHS_TX, force=True)  # IO5 → ESP32 RX
            print("(K210) UART pins registered: RX=IO4, TX=IO5")
        except:
            print("(K210) Failed to register UART1 pins")

        self.uart = UART(UART.UARTHS, 115200, read_buf_len=4096)
        print("(K210) UART initialized: 115200 baud")

        # 清空缓冲区
        if self.uart.any():
            self.uart.read()
            print("(K210) Cleared UART buffer")

    def send(self, data):
        """发送数据到 ESP32"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.uart.write(data)
        print("Sent to ESP32: {}".format(data))

    def receive_line(self, timeout_ms=1000):
        """接收一行数据(以 \n 结尾)"""
        start = time.ticks_ms()
        buffer = b''
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            if self.uart.any():
                char = self.uart.read(1)
                if char:
                    buffer += char
                    if char == b'\n':
                        try:
                            return buffer.decode('utf-8').strip()
                        except:
                            return buffer
            time.sleep_ms(10)
        if buffer:
            return buffer.decode('utf-8').strip()
        return None

    def start_receive_task(self, callback):
        """持续接收数据并调用回调处理"""
        while True:
            data = self.receive_line()
            if data:
                callback(data)
            time.sleep_ms(10)
```

**ESP32-S3 端(`uart_k210.cc`)**

```cpp
#include "uart_k210.h"
#include <esp_log.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#define TAG "UART_K210(ESP32)"

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

情绪流水线分为**研究原型**(位于 `Smart-Aging-Acoustic-Perception-and-Optimized-Localization-System/`,扁平存放,含仿真/可视化脚本)与**生产代码**(已移植进 `HRI-SeniorCare/Main/main/`)两份。

| 环节 | 研究原型(Smart-Aging/) | 生产代码(HRI-SeniorCare/Main/main/) | 语言 | 说明 |
|------|------------------------|--------------------------------------|------|------|
| 视觉 | `fer_engine.py` | *(部署在 K210 上)* | Python (MaixPy) | 人脸检测 + 表情分类 |
| 视觉 | `uart_comm.py` | — | Python (MaixPy) | 带 CRC-8 + 序号的 JSON 遥测 |
| 视觉 | `main.py` | — | Python (MaixPy) | 集成 FER 的主循环 |
| 语音 | `speech_emotion.{h,cc}` | `emotion/speech_emotion.{h,cc}` | C++ (ESP-IDF) | SER 特征提取 + 启发式映射 |
| 融合 | `ds_fusion_engine.{h,cc}` | `emotion/ds_fusion_engine.{h,cc}` | C++ (ESP-IDF) | Dempster 规则 + 冲突处理 |
| 融合 | `uart_k210.{h,cc}` | `uart_k210/uart_k210.{h,cc}` | C++ (ESP-IDF) | JSON 解析 + 丢包检测 |
| 上行 | `emotion_upstream.h` | `emotion/emotion_upstream.h` | C++ (ESP-IDF) | 上行 JSON 构造 |
| 上行 | `application_integration.cc` | *(已合并进 `application.cc`)* | C++ (ESP-IDF) | `application.cc` 接线指南 |

> Smart-Aging 目录另含 `ds_simulator.html`、`visualization*.py`、`ds_monte_carlo_academic.png` 等蒙特卡洛仿真与学术可视化资料。

---

## 集成步骤

将情绪流水线接入 ESP32 主固件的步骤:

1. **K210 端:** 将 `fer_engine.py`、`uart_comm.py`、`main.py` 拷入 SD 卡,并把 `face_detect.kmodel`、`fer_mobilenet.kmodel` 放到 `/sd/models/`。
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
| 语音交互闭环 | ESP32-S3 + K210 本地 VAD + 云端 DeepSeek V3 + melotts,低延迟对话跑通 | ✅ 已实现 |
| 声源定位感知基座 | 5dB 低信噪比下方位角误差 ≤ 8°、极限定位延迟 220ms、抑制多径回声 | ✅ 已实现 |
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
- **升级 MaixCAM**:其 RISC-V 核可运行更大的 FER 模型(如 MobileFaceNet)以提升精度。

---

## 致谢与开源协议

本项目基于虾哥开源的 [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32),以 **MIT 许可证**发布,允许任何人免费使用、修改或用于商业用途。小智 AI 聊天机器人作为语音交互入口,借助 Qwen / DeepSeek 等大模型能力,通过 MCP 协议实现多端控制;本项目在此基础上完成养老陪护方向的多模态情绪感知扩展。

**相关生态**(部署自有服务器可参考):

- [xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server)(Python)· [joey-zhou/xiaozhi-esp32-server-java](https://github.com/joey-zhou/xiaozhi-esp32-server-java)(Java)· [AnimeAIChat/xiaozhi-server-go](https://github.com/AnimeAIChat/xiaozhi-server-go)(Golang)
- 第三方客户端:[py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi)(Python)· [xiaozhi-android-client](https://github.com/TOM88812/xiaozhi-android-client)(Android)

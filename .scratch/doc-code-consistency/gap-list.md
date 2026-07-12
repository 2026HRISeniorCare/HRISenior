# 文档 ↔ 代码 差距清单(中期核对)

> 核对时间:2026-07-11
> 核对对象:
> - 文档:`大创中期检查 .pdf`、`中期答辩ppt.pdf`
> - 代码:`HRI-SeniorCare/`(ESP32 固件)、`Smart-Aging-.../`(研究原型 + 仿真)
>
> **状态图例:** ✅ 已在代码中实现 · 🧪 仅 PC 仿真/绘图 · 🚧 迁移/规划中 · ❌ 仓库内无对应代码 · ⚠️ 部分/依赖外部配置

---

## 一、总体结论

整体架构与文档技术路线**高度一致**。两项被文档当作"核心技术 / 阶段性成果"宣传的能力,在当前 checkout 里**找不到可追溯的实现**,需要在结题前补齐或明确口径:

1. **SNR/Lux 智能信任纠偏引擎(动态惩罚因子)** —— 代码里完全没有,连仿真也没有真正实现(θ 是手动滑块)。
2. **TDOA / GCC-PHAT / 卡尔曼 声源定位** —— 本仓库无源码(K210 端,应在设备/另一仓)。

另外,"5000 组蒙特卡洛 +13.5%" 只有**绘图脚本和结果图**,生成这些数字的仿真循环不在仓库里 —— 可追溯性缺失。

---

## 二、逐项核对表

| # | 文档主张(核心技术/成果) | 代码现状 | 证据 | 状态 |
|---|--------------------------|----------|------|------|
| 1 | AMP 非对称双核异构 ESP32-S3 + K210 | 固件 + K210 主循环齐备 | `application.cc`、`main.py` | ✅ |
| 2 | 带 Checksum 校验的 115200bps UART | UART + CRC 已实现 | `uart_k210/uart_k210.cc` | ✅ |
| 3 | ASR—LLM—TTS 语音闭环 | xiaozhi 基座提供 | 基座能力 | ✅ |
| 4 | K210 FER(YOLO + MobileNetV2 → H/S/N/A) | 已实现 | `fer_engine.py`、`main.py` | ✅ |
| 5 | ESP32 SER(Pitch/RMS/MFCC) | 已实现 | `emotion/speech_emotion.cc` | ✅ |
| 6 | D-S 决策级融合 + 冲突 K + 隐性抑郁预警 | 已实现 | `emotion/ds_fusion_engine.cc`、`application.cc` `high_conflict`/`Alert` | ✅ |
| 7 | 隐私:原始音/脸不上云,仅传意图 | 上行仅 `intent` + 概率,无 raw 音频/人脸 | `emotion/emotion_upstream.h` | ✅ |
| 8 | 共情引擎 DeepSeek V3 + melotts | 由后端服务器配置决定,固件侧不体现具体版本 | `SendMcpMessage` → 现有协议通道 | ⚠️ |
| 9 | **SNR/Lux 智能信任纠偏引擎(动态惩罚因子)** | **无实现**:固件用静态 `vision_reliability=0.6`/`audio_reliability=0.4`;C++ 原型同样静态;`ds_simulator.html` 的 θ = `1 - Σp`(手动滑块),**无 SNR/Lux 输入** | `ds_fusion_engine.h:117-118`、`application.cc:580-581`、`ds_simulator.html:175` | ❌ |
| 10 | **蒙特卡洛 5000 组,较单模态(72%)+13.5%** | 只有**结果图 + 绘图脚本**,生成数字的 5000 样本仿真循环**不在仓库** | `v2.py`/`v3.py`(仅 matplotlib 绘图)、`ds_monte_carlo_academic.png` | 🧪 |
| 11 | **TDOA + GCC-PHAT + 卡尔曼 声源定位**(5dB/≤8°/220ms) | **仓库无源码**:全仓 grep `tdoa/gcc-phat/kalman/声源` 零命中;`main.py` 用 `AudioTargetDetector`(未见 GCC-PHAT/卡尔曼) | `main.py`(K210 端定位逻辑缺失) | ❌ |
| 12 | 时空对齐:毫秒时间戳 + 滑动时间窗 | 部分:融合用 `vision/audio_stale_timeout_ms` 判过期,非严格时间戳对齐 | `ds_fusion_engine.h`、`application.cc` 融合配置 | ⚠️ |
| 13 | 网络延迟掩盖:本地"点头/嗯嗯" | 未实现 | —— | 🚧 |
| 14 | D-S 引擎全量部署 ESP32-S3 实机 | 静态版已跑通,动态(SNR/Lux)版待迁移 —— **与文档"近期计划"时间线一致** | `application.cc` | 🚧 |

---

## 三、需要澄清/补齐的动作项

- [ ] **#9 澄清 SNR/Lux 纠偏出处**:动态惩罚因子的仿真/公式到底在哪?若只有构想,需在答辩/结题口径上把它明确为"仿真设计 + 待实机",避免被质疑"成果无代码支撑"。
- [ ] **#10 补蒙特卡洛仿真脚本**:补上生成 `72% → +13.5%` 的 5000 样本仿真源码(含高斯噪声注入 + SNR/Lux→θ 映射),让结果可复现。
- [ ] **#11 定位并提交 K210 声源定位源码**:TDOA/GCC-PHAT/卡尔曼 目前只在设备 SD 卡上?建议纳入仓库(哪怕单独目录),否则"核心技术二"无源码。
- [ ] **#8 固化后端配置**:在文档/README 注明 DeepSeek V3 + melotts 的具体接入点(自建 xiaozhi-esp32-server 还是官方服务器)。
- [ ] **#12/#13 时空对齐 & 延迟掩盖**:列入近期开发排期(README 后期路线图已登记)。

---

## 四、文档内部/历史表述问题(已在 README 修正)

- **上行目标"树莓派"**:旧英文设计文档 + 初版整合 README 误述为 Raspberry Pi;实际走 `SendMcpMessage()` → 现有 WebSocket/MQTT 通道 → 后端服务器。→ ✅ README 已改。
- **PPT 2.1 "视觉骨骼点抽取"**:与实际的人脸表情识别(FER)措辞不符,建议答辩统一为 FER,避免评委追问骨骼点模型。

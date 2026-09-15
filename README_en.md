# Resona: Multimodal Elderly-Care Robot

Chinese version: [README.md](README.md)

Resona is a multimodal elderly-care prototype developed at Beijing University of Chemical Technology under the Undergraduate Innovation and Entrepreneurship Training Program. It extends the XiaoZhi ESP32 voice-assistant platform with local facial-expression recognition, speech-emotion analysis, Dempster–Shafer fusion, two-axis face tracking, and cloud-side emotion logging.

## Current system

- **Vision node:** Sipeed MaixCAM Lite with GC4653 camera, YOLOv8 face detection, and facial-expression classification.
- **Main controller:** ESP32-S3 N16R8 using the `bread-compact-wifi` board configuration.
- **Audio:** On-board microphone, VAD, speech-emotion feature extraction, cloud ASR/LLM/TTS interaction.
- **Display:** ST7789 LCD with LVGL status and cute-expression rendering.
- **Actuators:** Two SG90 servos for pan and tilt face tracking.
- **Cloud:** XiaoZhi conversational service and the Resona emotion dashboard at `https://sievox.cn/resona`.

The current firmware source is `HRI-SeniorCare/Main_ProductPins/`. The earlier `Main/` directory is retained as a historical engineering copy.

## Hardware wiring

| MaixCAM Lite | Connection | ESP32-S3 |
|---|---|---|
| A16 / UART0_TX | 5 kΩ series resistor | GPIO38 / UART1_RX |
| A17 / UART0_RX | Direct connection | GPIO39 / UART1_TX |
| GND | Common ground | GND |

UART settings are **115200 baud, 8N1**. The pan servo signal is connected to GPIO41 and the tilt servo signal to GPIO18. Both SG90 servos use a stable external 5 V supply. Servo ground, ESP32-S3 ground, and MaixCAM Lite ground must be common.

## Software pipeline

1. MaixCAM Lite captures frames and performs face detection and facial-expression inference locally.
2. The Lite sends newline-delimited JSON packets with face coordinates, emotion probabilities, sequence number, and CRC-8 over UART.
3. ESP32-S3 validates and parses the packets, updates the face-tracking controller, and combines visual evidence with speech-emotion evidence.
4. The Dempster–Shafer engine produces the fused emotion state and conflict score.
5. The device displays the state locally and uploads emotion records to the remote dashboard. Raw camera frames and raw audio are not uploaded by the emotion pipeline.

### System architecture

```text
MaixCAM Lite              ESP32-S3                         Cloud service
------------              --------                         ------------
GC4653 camera             UART parser + CRC validation      Emotion API
YOLOv8 face detector  ->  Face tracker and SG90 control  ->  Dashboard
Facial-expression FER     Speech-emotion analyser           Emotion history
                          D-S evidence fusion              Warning records
                          ST7789/LVGL display               LLM / ASR / TTS
```

The two modalities are asynchronous. Vision packets arrive periodically, while the speech-emotion result is produced at the end of a speech segment. The fusion layer therefore retains the latest valid visual evidence, applies confidence degradation when no face is detected, and combines it with the latest audio evidence at a fixed control interval.

### Emotion representation

The embedded four-class representation is ordered as `[happy, sad, neutral, anger]`. Each modality is converted into a basic probability assignment (BPA). A sensor confidence value controls the mass assigned to the four singleton classes; the remaining mass is assigned to the uncertainty set. The fusion output includes the dominant emotion, confidence score, belief vector, conflict value, and a high-conflict flag.

The current deployed firmware uses static baseline reliabilities together with face-detection confidence degradation. SNR/Lux-dependent reliability correction is retained as a research extension and is not presented as a fully deployed MCU feature.

### UART packet format

Each vision line is an ASCII JSON object terminated by `\n`. The payload contains a monotonic sequence number, timestamp, face bounding box, four-class probability vector, quality/confidence fields, and an uppercase two-digit CRC-8 value. The CRC is calculated over the JSON body before the `crc` field is appended. The ESP32-S3 receiver resynchronizes at `{`, ignores MaixCAM boot messages, and counts malformed lines, CRC failures, and sequence gaps.

Example structure:

```json
{
  "seq": 1824,
  "ts": 1719500000000,
  "face": {"x": 214, "y": 96, "w": 142, "h": 142},
  "emotion": [0.62, 0.08, 0.22, 0.08],
  "quality": 0.91,
  "crc": "A7"
}
```

## Deployment

### ESP32-S3

Use ESP-IDF 5.4 or newer and select the `bread-compact-wifi` configuration. The latest tested firmware is generated from:

```text
HRI-SeniorCare/Main_ProductPins/build/xiaozhi.bin
```

The current prototype was flashed and checked on COM11. The configuration hotspot prefix is `Resona-xxxx`; open `http://192.168.4.1` after connecting to the hotspot.

### MaixCAM Lite

Upload `MaixCam_Lite/main.py` as `/maixapp/main.py`. The following models must be present on the device:

```text
/root/models/yolov8n_face.mud
/root/models/face_emotion.mud
```

Run the script in the foreground during first-time validation. Confirm that UART line counts increase and that parse and CRC error counters remain zero before enabling automatic startup.

## Verification status before project completion

| Area | Status |
|---|---|
| Voice interaction loop | Completed on ESP32-S3 with VAD, ASR, LLM, and TTS |
| Vision-to-ESP32 UART link | Completed; CRC-protected packets received continuously |
| Two-axis face tracking | Completed with two SG90 servos |
| Cloud emotion reporting | Completed; fused state and conflict records are visible remotely |
| Dataset validation | Completed with actor-grouped RAVDESS five-fold evaluation, fusion comparisons, and confidence intervals |
| Conference paper | Accepted by ICHCI 2026; acceptance record is stored in `docs/publication/ICHCI_2026_ACCEPTANCE.md` |
| Product finishing | Prototype works; enclosure, PCB, long-duration regression, and final project materials remain to be closed before submission |

The dataset results, simulation results, communication tests, and end-to-end hardware tests are reported separately. Connectivity validation should not be interpreted as clinical emotion-recognition validation.

## Experimental evaluation

The evaluation is organized into four complementary layers:

1. **Dataset validation.** RAVDESS recordings are split by actor so that speakers do not appear in both training and test folds. Five-fold actor-grouped evaluation compares audio-only, vision-only, rule-based fusion, Dempster–Shafer fusion, and an MLP fusion baseline. Mean performance and 95% confidence intervals are reported across folds.
2. **Fusion analysis.** Controlled probability vectors and Monte Carlo perturbations are used to evaluate conflict handling, confidence degradation, and the effect of missing or unreliable modalities. These are simulation results, not additional human-subject experiments.
3. **Communication validation.** MaixCAM Lite to ESP32-S3 UART reception is checked using line count, parse-failure count, CRC-failure count, and packet-drop count. A representative 15-second integration window reached `lines=593`, `parse_fail=0`, `crc_fail=0`, and `drops=0`.
4. **End-to-end hardware validation.** The camera, display, audio path, cloud upload, and two servo axes are exercised together. The test verifies system integration and stability; it is not a clinical validation study.

The project does not claim a diagnostic capability. Emotion labels are used as interaction signals for an assistive prototype, and conflict records are intended for later review rather than automatic medical intervention.

## Cloud interface

The ESP32-S3 sends compact fused-state records to the remote service. The deployment endpoints are:

```text
POST https://sievox.cn/resona/emotion/write
GET  https://sievox.cn/resona/emotion/current
GET  https://sievox.cn/resona/emotion/history
GET  https://sievox.cn/resona/emotion/meta
```

The upload contains the device identifier, dominant emotion, score, belief vector, conflict value, high-conflict flag, and source summaries. Conflict events are recorded in the remote warning log and do not trigger a local audible alarm, so they cannot interrupt speech output.

## Finalization plan

1. Freeze the tested firmware, MaixCAM Lite script, and server interface versions.
2. Run a long-duration regression test and record resets, UART packet loss, cloud upload status, and servo behavior.
3. Complete wiring and enclosure documentation, safety notes, user instructions, and project photographs.
4. Archive experiment outputs, hardware logs, paper materials, acceptance documents, and the final project report.
5. Keep future work—dynamic SNR/Lux reliability correction, an embedded neural SER model, and larger-scale elderly-user studies—clearly separated from the completed prototype scope.

## Repository structure

```text
README.md                         Chinese project overview
README_en.md                      This English project overview
MaixCam_Lite/main.py              MaixCAM Lite vision and UART program
HRI-SeniorCare/Main_ProductPins/  Current ESP32-S3 firmware source
Smart-Aging-Acoustic-Perception... Research scripts and experiment outputs
docs/publication/                 Acceptance and publication records
apps/                             MaixCAM application examples and utilities
```

The historical K210 and MEMS-array experiments remain available under the research directory. They document earlier exploration and should not be confused with the current MaixCAM Lite hardware path.

## Troubleshooting

- **No vision packets:** check common ground, the 5 kΩ TX series resistor, A16→GPIO38 and A17←GPIO39 wiring, and verify that only one MaixCAM process owns `/dev/ttyS0`.
- **Increasing parse or CRC failures:** confirm both ends use 115200 8N1, keep UART wires short, and avoid powering servos from the 3.3 V rail.
- **Servo resets the ESP32-S3:** use a separate regulated 5 V supply and connect its ground to the ESP32-S3 ground.
- **No cloud update:** verify Wi-Fi provisioning, the server URL, and the serial log for upload responses before diagnosing the emotion model.
- **Repeated camera initialization:** stop duplicate MaixCAM processes and reboot the Lite so that the media pipeline is released before restarting `main.py`.

## Publication

The paper *Resona: When Smile Meets Trembling Voice — Edge Multimodal Conflict Detection for Eldercare* was accepted by the 2026 7th International Conference on Intelligent Computing and Human-Computer Interaction (ICHCI 2026). The manuscript number is `26080617134113593`, and the authors are Qihan Zhao, Yanfeng Qin, Liantong Feng, Guangtian Qin, Tianyu Gao, and Guohua Chen.

## License and acknowledgements

This project is based on the open-source [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) project and is released under the MIT license. See the Chinese README and the source directories for detailed implementation notes.

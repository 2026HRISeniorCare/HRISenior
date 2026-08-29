# MaixCAM Lite vision node / MaixCAM Lite 视觉节点

## 中文

本目录保存 Resona 当前实机使用的 MaixCAM Lite 视觉脚本。它在 Lite 上完成人脸检测和表情分类，通过 UART 向 ESP32-S3 持续发送换行分隔、带 CRC-8 的 JSON 数据，并以人脸边界框驱动双轴舵机跟随。

当前接线：

| MaixCAM Lite | 连接 | ESP32-S3 |
|---|---|---|
| A16 / UART0_TX | 串联 5 kΩ 电阻 | GPIO38 / UART1_RX |
| A17 / UART0_RX | 直连 | GPIO39 / UART1_TX |
| GND | 直连，共地 | GND |

串口参数为 `115200 8N1`。水平舵机信号接 ESP32-S3 GPIO41，俯仰舵机信号接 GPIO18；两个 SG90 使用独立稳定 5 V 电源，并与 ESP32-S3、MaixCAM Lite 共地。

部署前确认设备中存在：

- `/root/models/yolov8n_face.mud`
- `/root/models/face_emotion.mud`

将 `main.py` 上传并在前台运行：

```bash
scp main.py root@10.20.154.1:/maixapp/main.py
ssh -t root@10.20.154.1 "cd /maixapp && python3 -u main.py"
```

同一时刻只能有一个程序占用摄像头和 UART。首次验证时建议前台启动，确认模型加载成功且 ESP32-S3 的 `lines` 持续增长、`parse_fail=0`、`crc_fail=0` 后，再配置开机自启。

## English

This directory contains the MaixCAM Lite vision program used by the current Resona hardware prototype. The Lite performs face detection and facial-expression classification locally, then sends newline-delimited CRC-8-protected JSON frames to the ESP32-S3 over UART. The transmitted face bounding box also drives the two-axis servo tracker.

The UART link uses `115200 8N1`: MaixCAM Lite A16/UART0_TX connects through a 5 kΩ series resistor to ESP32-S3 GPIO38/UART1_RX; ESP32-S3 GPIO39/UART1_TX connects directly to A17/UART0_RX; both boards share ground. The pan and tilt servo signals use GPIO41 and GPIO18, respectively. Power both SG90 servos from a stable external 5 V supply with a common ground.

Before deployment, ensure that `/root/models/yolov8n_face.mud` and `/root/models/face_emotion.mud` are available on the Lite. Run the script in the foreground first and verify increasing UART line counts with zero parse and CRC failures before enabling automatic startup.

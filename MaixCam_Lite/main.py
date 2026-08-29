from maix import nn, camera, image, time, app, uart, pinmap, err
import json


# Resona MaixCam Lite -> ESP32-S3 UART vision bridge.
# UART output contract:
#   1. every telemetry frame starts with "{"
#   2. every frame ends with "\n"
#   3. no console/debug text is written to UART
#   4. emotion order is [happy, sad, neutral, anger]
#
# This Lite build is screenless by default. It does not call display.Display().

UART_DEVICE = "/dev/ttyS0"
UART_BAUD = 115200
UART_TX_PIN = "A16"
UART_RX_PIN = "A17"
UART_TX_FUNCTION = "UART0_TX"
UART_RX_FUNCTION = "UART0_RX"

# If UART0 causes boot-log or boot-mode problems, use UART1 instead:
# UART_DEVICE = "/dev/ttyS1"
# UART_TX_PIN = "A19"
# UART_RX_PIN = "A18"
# UART_TX_FUNCTION = "UART1_TX"
# UART_RX_FUNCTION = "UART1_RX"

VISION_SEND_INTERVAL_MS = 180
FACE_DETECT_THRESHOLD = 0.5
FACE_NMS_THRESHOLD = 0.45
EMOTION_CROP_SCALE = 0.9
TRACKER_FRAME_HEIGHT = 240
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Original model label order:
# 0 angry, 1 disgust, 2 fear, 3 happy, 4 sad, 5 surprise, 6 neutral
# ESP32 fusion expects: [happy, sad, neutral, anger]
EMOTION_TO_RESONA = {
    0: 3,  # angry -> anger
    1: 2,  # disgust -> neutral
    2: 2,  # fear -> neutral
    3: 0,  # happy -> happy
    4: 1,  # sad -> sad
    5: 2,  # surprise -> neutral
    6: 2,  # neutral -> neutral
}


def monotonic_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def crc8(data):
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            if value & 0x80:
                value = ((value << 1) ^ 0x07) & 0xFF
            else:
                value = (value << 1) & 0xFF
    return value


def encode_packet(packet):
    payload = json.dumps(packet, separators=(",", ":"))
    body = payload[:-1]
    checksum = crc8(body.encode("ascii"))
    return body + ',"crc":"' + ("%02X" % checksum) + '"}\n'


def send_packet(ser, seq, face, bbox, emo, quality):
    packet = {
        "seq": seq,
        "ts": monotonic_ms(),
        "face": face,
        "bbox": bbox,
        "emo": [round(float(v), 6) for v in emo],
        "quality": round(float(quality), 6),
    }
    ser.write(encode_packet(packet).encode("ascii"))


def initialize_uart():
    err.check_raise(
        pinmap.set_pin_function(UART_TX_PIN, UART_TX_FUNCTION),
        "UART TX pin mapping failed",
    )
    err.check_raise(
        pinmap.set_pin_function(UART_RX_PIN, UART_RX_FUNCTION),
        "UART RX pin mapping failed",
    )
    return uart.UART(UART_DEVICE, UART_BAUD)


def normalize(values):
    total = sum(values)
    if total <= 0:
        return [0.0, 0.0, 1.0, 0.0], 0.0
    return [v / total for v in values], total


def main():
    ser = initialize_uart()

    # Reserve the Lite camera channel before loading the neural-network
    # models. A single buffer keeps the media-memory peak low.
    cam = camera.Camera(
        CAMERA_WIDTH,
        CAMERA_HEIGHT,
        image.Format.FMT_RGB888,
        buff_num=1,
        fps=60,
    )
    cam.read()

    detector = nn.YOLOv8(model="/root/models/yolov8n_face.mud", dual_buff=False)
    landmarks_detector = nn.FaceLandmarks(model="")
    classifier = nn.Classifier(model="/root/models/face_emotion.mud", dual_buff=False)

    seq = 0
    last_send_ms = monotonic_ms() - VISION_SEND_INTERVAL_MS

    while not app.need_exit():
        img = cam.read()
        ai_img = img.resize(detector.input_width(), detector.input_height())
        faces = detector.detect(
            ai_img,
            conf_th=FACE_DETECT_THRESHOLD,
            iou_th=FACE_NMS_THRESHOLD,
            sort=1,
        )

        now_ms = monotonic_ms()
        send_due = (now_ms - last_send_ms) >= VISION_SEND_INTERVAL_MS

        face_found = False
        bbox = [0, 0, 0, 0]
        emo = [0.0, 0.0, 1.0, 0.0]
        quality = 0.0

        if len(faces) > 0:
            obj = faces[0]
            bbox = [
                int(obj.x),
                int(obj.y * TRACKER_FRAME_HEIGHT / detector.input_height()),
                int(obj.w),
                int(obj.h * TRACKER_FRAME_HEIGHT / detector.input_height()),
            ]
            bbox[0] = int(obj.x * 320 / detector.input_width())
            bbox[2] = int(obj.w * 320 / detector.input_width())
            face_found = True

            img_std = landmarks_detector.crop_image(
                ai_img,
                obj.x,
                obj.y,
                obj.w,
                obj.h,
                obj.points,
                classifier.input_width(),
                classifier.input_height(),
                EMOTION_CROP_SCALE,
            )

            if img_std:
                img_std_gray = img_std.to_format(image.Format.FMT_GRAYSCALE)
                raw_result = classifier.classify(img_std_gray, softmax=True)
                scores = [0.0, 0.0, 0.0, 0.0]
                for raw_idx, score in raw_result:
                    if raw_idx in EMOTION_TO_RESONA:
                        scores[EMOTION_TO_RESONA[raw_idx]] += float(score)
                emo, quality = normalize(scores)

        if send_due:
            send_packet(ser, seq, face_found, bbox, emo, quality)
            seq = (seq + 1) & 0xFFFFFFFF
            last_send_ms = now_ms


try:
    main()
except Exception:
    import traceback
    print(traceback.format_exc())
    while not app.need_exit():
        time.sleep_ms(100)

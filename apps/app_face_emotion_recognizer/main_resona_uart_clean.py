from maix import nn, camera, display, image, time, app, sys, uart, pinmap, err
import json


# Resona MaixCam Pro -> ESP32-S3 UART vision bridge.
# UART output contract:
#   1. every telemetry frame starts with "{"
#   2. every frame ends with "\n"
#   3. no console/debug text is written to UART
#   4. emotion order is [happy, sad, neutral, anger]

UART_DEVICE = "/dev/ttyS0"
UART_BAUD = 115200
UART_TX_PIN = "A16"
UART_RX_PIN = "A17"
UART_TX_FUNCTION = "UART0_TX"
UART_RX_FUNCTION = "UART0_RX"

VISION_SEND_INTERVAL_MS = 180
FACE_DETECT_THRESHOLD = 0.5
FACE_NMS_THRESHOLD = 0.45
FACE_RECOGNIZE_THRESHOLD = 0.85
EMOTION_CROP_SCALE = 0.9

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

RESONA_LABELS = ["happy", "sad", "neutral", "anger"]


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


def draw_status(img, face, emo, bbox):
    if face:
        img.draw_rect(bbox[0], bbox[1], bbox[2], bbox[3], image.COLOR_GREEN)
        best = 0
        for i in range(1, len(emo)):
            if emo[i] > emo[best]:
                best = i
        img.draw_string(
            bbox[0],
            max(0, bbox[1] - 18),
            "%s %.2f" % (RESONA_LABELS[best], emo[best]),
            image.COLOR_GREEN,
        )
    else:
        img.draw_string(4, 4, "No face -> neutral", image.COLOR_WHITE)

    img.draw_string(4, 24, "UART A16 TX 115200", image.COLOR_WHITE)


def main():
    disp = display.Display()

    loading = image.Image(disp.width(), disp.height())
    loading.draw_rect(0, 0, loading.width(), loading.height(), image.COLOR_BLACK, thickness=-1)
    loading.draw_string(8, 8, "Resona vision UART clean", image.COLOR_WHITE)
    loading.draw_string(8, 30, "loading models...", image.COLOR_WHITE)
    disp.show(loading)

    ser = initialize_uart()

    face_detect_model = (
        "/root/models/yolo11s_face.mud"
        if sys.device_name().lower() == "maixcam2"
        else "/root/models/yolov8n_face.mud"
    )
    recognizer = nn.FaceRecognizer(
        detect_model=face_detect_model,
        feature_model="/root/models/insghtface_webface_r50.mud",
        dual_buff=True,
    )
    landmarks_detector = nn.FaceLandmarks(model="")
    classifier = nn.Classifier(model="/root/models/face_emotion.mud", dual_buff=False)
    cam = camera.Camera(
        recognizer.input_width(),
        recognizer.input_height(),
        recognizer.input_format(),
    )

    seq = 0
    last_send_ms = monotonic_ms() - VISION_SEND_INTERVAL_MS

    while not app.need_exit():
        img = cam.read()
        faces = recognizer.recognize(
            img,
            FACE_DETECT_THRESHOLD,
            FACE_NMS_THRESHOLD,
            FACE_RECOGNIZE_THRESHOLD,
            False,
            False,
        )

        now_ms = monotonic_ms()
        send_due = (now_ms - last_send_ms) >= VISION_SEND_INTERVAL_MS

        face_found = False
        bbox = [0, 0, 0, 0]
        emo = [0.0, 0.0, 1.0, 0.0]
        quality = 0.0

        if len(faces) > 0:
            obj = faces[0]
            bbox = [int(obj.x), int(obj.y), int(obj.w), int(obj.h)]
            face_found = True

            img_std = landmarks_detector.crop_image(
                img,
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

        draw_status(img, face_found, emo, bbox)
        disp.show(img)


try:
    main()
except Exception as e:
    # Show the error on MaixCam screen only. Do not print it to UART.
    disp = display.Display()
    img = image.Image(disp.width(), disp.height())
    img.draw_rect(0, 0, img.width(), img.height(), image.COLOR_BLACK, thickness=-1)
    img.draw_string(0, 0, "Resona app error:", image.COLOR_RED)
    img.draw_string(0, 22, str(e), image.COLOR_WHITE)
    disp.show(img)
    while not app.need_exit():
        time.sleep_ms(100)

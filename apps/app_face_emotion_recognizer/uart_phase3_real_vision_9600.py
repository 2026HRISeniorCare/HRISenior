from maix import nn, camera, display, image, time, uart, pinmap, err, sys, app
import json
import math


origin_labels = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
target_labels = ["angry", "happy", "sad", "neutral"]
emo_map = {
    0: 0,
    1: 3,
    2: 3,
    3: 1,
    4: 2,
    5: 3,
    6: 3,
}

UART_DEVICE = "/dev/ttyS0"
UART_BAUD = 9600
UART_TX_PIN = "A16"
UART_RX_PIN = "A17"
UART_TX_FUNCTION = "UART0_TX"
UART_RX_FUNCTION = "UART0_RX"


def initialize_uart():
    err.check_raise(pinmap.set_pin_function(UART_TX_PIN, UART_TX_FUNCTION), "UART TX pin mapping failed")
    err.check_raise(pinmap.set_pin_function(UART_RX_PIN, UART_RX_FUNCTION), "UART RX pin mapping failed")
    return uart.UART(UART_DEVICE, UART_BAUD)


def slow_write(ser, text, gap_ms=5):
    for b in text.encode("ascii"):
        ser.write(bytes([b]))
        time.sleep_ms(gap_ms)


def send_packet(ser, seq, face, bbox, emo, quality):
    packet = {
        "seq": seq,
        "ts": int(time.ticks_ms()),
        "face": face,
        "bbox": bbox,
        "emo": [round(float(v), 6) for v in emo],
        "quality": round(float(quality), 6),
    }
    slow_write(ser, json.dumps(packet, separators=(",", ":")) + "\n", 5)


def main():
    disp = display.Display()
    ser = initialize_uart()

    face_detect_model = "/root/models/yolo11s_face.mud" if sys.device_name().lower() == "maixcam2" else "/root/models/yolov8n_face.mud"
    recognizer = nn.FaceRecognizer(
        detect_model=face_detect_model,
        feature_model="/root/models/insghtface_webface_r50.mud",
        dual_buff=True,
    )
    landmarks_detector = nn.FaceLandmarks(model="")
    classifier = nn.Classifier(model="/root/models/face_emotion.mud", dual_buff=False)
    cam = camera.Camera(recognizer.input_width(), recognizer.input_height(), recognizer.input_format())

    crop_scale = 0.9
    seq = 0
    last_tx_ms = 0

    while not app.need_exit():
        img = cam.read()
        faces = recognizer.recognize(img, 0.5, 0.45, 0.85, False, False)

        face = len(faces) > 0
        bbox = [0, 0, 0, 0]
        emo_probs = [0.0, 0.0, 1.0, 0.0]  # [happy, sad, neutral, anger]
        quality = 0.0

        if face:
            obj = faces[0]
            bbox = [int(obj.x), int(obj.y), int(obj.w), int(obj.h)]
            img.draw_rect(obj.x, obj.y, obj.w, obj.h, image.COLOR_GREEN)
            radius = math.ceil(obj.w / 10)
            img.draw_keypoints(obj.points, image.COLOR_GREEN, size=radius if radius < 5 else 4)

            img_std = landmarks_detector.crop_image(
                img, obj.x, obj.y, obj.w, obj.h, obj.points,
                classifier.input_width(), classifier.input_height(), crop_scale
            )
            if img_std:
                img_std_gray = img_std.to_format(image.Format.FMT_GRAYSCALE)
                res = classifier.classify(img_std_gray, softmax=True)
                score_buf = [0.0, 0.0, 0.0, 0.0]  # angry, happy, sad, neutral
                for raw_idx, score in res:
                    score_buf[emo_map[raw_idx]] += score
                total = sum(score_buf)
                if total > 0:
                    score_buf = [v / total for v in score_buf]
                    quality = total
                emo_probs = [score_buf[1], score_buf[2], score_buf[3], score_buf[0]]

                label_idx = max(range(len(emo_probs)), key=lambda i: emo_probs[i])
                label = ["happy", "sad", "neutral", "anger"][label_idx]
                img.draw_string(obj.x, max(0, obj.y - 20), "{} {:.2f}".format(label, emo_probs[label_idx]), image.COLOR_GREEN)

        now = time.ticks_ms()
        if now - last_tx_ms >= 1800:
            send_packet(ser, seq, face, bbox, emo_probs, quality)
            seq = (seq + 1) & 0xFFFFFFFF
            last_tx_ms = now

        img.draw_string(4, 4, "PHASE 3 real vision seq={}".format(seq), image.COLOR_YELLOW)
        disp.show(img)


if __name__ == "__main__":
    main()

from maix import nn, camera, display, image, time, uart, pinmap, err, sys, app
import json


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


def send_packet(ser, seq, face, bbox):
    packet = {
        "seq": seq,
        "ts": int(time.ticks_ms()),
        "face": face,
        "bbox": bbox,
        "emo": [0.0, 0.0, 1.0, 0.0],
        "quality": 0.80 if face else 0.0,
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
    cam = camera.Camera(recognizer.input_width(), recognizer.input_height(), recognizer.input_format())

    seq = 0
    last_tx_ms = 0

    while not app.need_exit():
        img = cam.read()
        faces = recognizer.recognize(img, 0.5, 0.45, 0.85, False, False)

        face = len(faces) > 0
        bbox = [0, 0, 0, 0]
        if face:
            obj = faces[0]
            bbox = [int(obj.x), int(obj.y), int(obj.w), int(obj.h)]
            img.draw_rect(obj.x, obj.y, obj.w, obj.h, image.COLOR_GREEN)
            img.draw_string(obj.x, max(0, obj.y - 20), "face bbox", image.COLOR_GREEN)

        now = time.ticks_ms()
        if now - last_tx_ms >= 1800:
            send_packet(ser, seq, face, bbox)
            seq = (seq + 1) & 0xFFFFFFFF
            last_tx_ms = now

        img.draw_string(4, 4, "PHASE 2 bbox seq={}".format(seq), image.COLOR_YELLOW)
        disp.show(img)


if __name__ == "__main__":
    main()

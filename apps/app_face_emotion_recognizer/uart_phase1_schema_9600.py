from maix import display, image, time, uart, pinmap, err
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


def slow_write(ser, text, gap_ms=3):
    for b in text.encode("ascii"):
        ser.write(bytes([b]))
        time.sleep_ms(gap_ms)


def encode_packet(seq):
    packet = {
        "seq": seq,
        "ts": int(time.ticks_ms()),
        "face": True,
        "bbox": [80, 60, 120, 120],
        "emo": [0.10, 0.10, 0.70, 0.10],
        "quality": 0.90,
    }
    return json.dumps(packet, separators=(",", ":")) + "\n"


def main():
    disp = display.Display()
    ser = initialize_uart()
    seq = 0
    last_ms = 0

    while True:
        now = time.ticks_ms()
        if now - last_ms >= 1200:
            slow_write(ser, encode_packet(seq), 3)
            seq += 1
            last_ms = now

            canvas = image.Image(disp.width(), disp.height(), image.Format.FMT_RGB888)
            canvas.draw_string(12, 24, "PHASE 1: SCHEMA", image.COLOR_GREEN)
            canvas.draw_string(12, 54, "9600 baud, slow JSON", image.COLOR_WHITE)
            canvas.draw_string(12, 84, "fake bbox + fake emotion", image.COLOR_WHITE)
            canvas.draw_string(12, 114, "ESP32: P/J grow, E/T=0", image.COLOR_YELLOW)
            canvas.draw_string(12, 144, "seq={}".format(seq), image.COLOR_YELLOW)
            disp.show(canvas)

        time.sleep_ms(10)


if __name__ == "__main__":
    main()

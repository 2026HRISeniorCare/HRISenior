from maix import display, image, time, uart, pinmap, err


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


def main():
    disp = display.Display()
    ser = initialize_uart()
    seq = 0
    last_ms = 0

    while True:
        now = time.ticks_ms()
        if now - last_ms >= 1000:
            ser.write(b"U\n")
            seq += 1
            last_ms = now

            canvas = image.Image(disp.width(), disp.height(), image.Format.FMT_RGB888)
            canvas.draw_string(12, 24, "UART BYTE TEST", image.COLOR_GREEN)
            canvas.draw_string(12, 54, "TX: A16 UART0_TX", image.COLOR_WHITE)
            canvas.draw_string(12, 84, "Baud: 9600", image.COLOR_WHITE)
            canvas.draw_string(12, 114, "Send: U  expected H=55", image.COLOR_YELLOW)
            canvas.draw_string(12, 144, "seq={}".format(seq), image.COLOR_YELLOW)
            disp.show(canvas)

        time.sleep_ms(10)


if __name__ == "__main__":
    main()

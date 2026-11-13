"""
uart_test.py — Quick UART smoke test for MaixCam Pro ↔ ESP32
=============================================================
Drop this on the SD card and run it to verify your wiring
before deploying the full main.py pipeline.

Usage (MaixCam Pro, via IDE serial terminal or MaixPy3 REPL):
    import uart_test
    uart_test.echo_test()       # test with a serial monitor on ESP32
    uart_test.send_json_test()  # send sample emotion packets
    uart_test.loopback_test()   # if you jumper TX→RX on MaixCam itself
"""

import time
from maix import pinmap, uart


# ── Pin config — must match your wiring ───────────────────────────────
UART_PORT = 1
TX_PIN    = "A19"    # MaixCam UART1_TX  →  ESP32 RX
RX_PIN    = "A18"    # MaixCam UART1_RX  ←  ESP32 TX
BAUD      = 115200


def _setup():
    """Configure pins and return a UART object."""
    pinmap.set_pin_function(TX_PIN, "UART1_TX")
    pinmap.set_pin_function(RX_PIN, "UART1_RX")
    ser = uart.UART(UART_PORT, BAUD)
    print("UART{} ready: TX={}, RX={}, baud={}".format(
        UART_PORT, TX_PIN, RX_PIN, BAUD))
    # Drain stale bytes
    time.sleep_ms(100)
    if ser.any():
        junk = ser.read(ser.any())
        print("Cleared {} stale bytes: {}".format(len(junk), junk))
    return ser


def echo_test(duration_s: int = 30):
    """
    Echo test — ESP32 sends, MaixCam echoes back.
    ==============================================
    Open a serial monitor on the ESP32 side (115200 baud).
    Type anything, MaixCam will receive it and echo it back.

    This confirms: TX and RX are correctly cross-connected.
    """
    ser = _setup()
    print("\n=== Echo test running for {}s ===".format(duration_s))
    print("On ESP32, send text via UART. MaixCam will echo it back.\n")

    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < duration_s * 1000:
        if ser.any():
            data = ser.read(ser.any())
            try:
                text = data.decode("utf-8").strip()
                print("RX [{} bytes]: {}".format(len(data), text))
                # Echo back
                ser.write(data)
                print("TX (echo): {}".format(text))
            except Exception as e:
                print("Decode error: {} | raw: {}".format(e, data))
        time.sleep_ms(10)

    print("\n=== Echo test finished ===")
    ser.deinit()


def send_json_test(interval_ms: int = 500, count: int = 20):
    """
    Send sample JSON telemetry packets to ESP32.
    =============================================
    Use this when you have the ESP32 running its UART receiver
    (uart_k210.cc).  Watch the ESP32 console for parsed packets.

    Every {interval_ms} ms, a sample emotion packet is sent.
    """
    import ujson

    ser = _setup()
    print("\n=== JSON send test: {} packets @ {}ms interval ===".format(
        count, interval_ms))

    for seq in range(count):
        packet = {
            "seq":   seq,
            "ts":    time.ticks_ms(),
            "face":  True,
            "bbox":  [100, 80, 60, 60],
            "emo":   [0.10, 0.05, 0.80, 0.05],
            "pitch": 50.0,
            "roll":  0.0,
            "trk":   False,
        }
        # Compute CRC-8 placeholder (real CRC would be computed pre-crc field)
        payload_str = ujson.dumps(packet)
        crc = _crc8(payload_str.encode("utf-8"))
        packet["crc"] = "{:02X}".format(crc)

        line = ujson.dumps(packet) + "\n"
        ser.write(line.encode("utf-8"))
        print("TX [{}]: {}".format(seq, payload_str[:60] + "..."))

        time.sleep_ms(interval_ms)

    print("\n=== JSON test finished ===")
    ser.deinit()


def loopback_test(count: int = 5):
    """
    Loopback test — jumper MaixCam TX→RX locally.
    ==============================================
    Physically connect MaixCam's A19 (TX) to A18 (RX) with a
    jumper wire.  MaixCam sends to itself and verifies receipt.
    No ESP32 needed — this validates the MaixCam UART hardware.
    """
    ser = _setup()
    print("\n=== Loopback test ({}) ===".format(
        "OK" if _UART_PORT_LOOPBACK else "please jumper TX→RX first"))
    print("Sending test messages and checking they come back...\n")

    test_msgs = [
        b"GET_STATE\n",
        b"PING\n",
        b"HELLO from MaixCam\n",
        b'{"cmd":"test"}\n',
    ]

    passed = 0
    for msg in test_msgs:
        ser.write(msg)
        time.sleep_ms(50)

        if ser.any():
            echo = ser.read(ser.any())
            if echo == msg:
                print("  PASS: '{}'".format(msg.decode().strip()))
                passed += 1
            else:
                print("  FAIL: sent '{}', got '{}'".format(
                    msg.decode().strip(), echo))
        else:
            print("  FAIL: no response for '{}'".format(msg.decode().strip()))

    print("\n=== Result: {}/{} passed ===".format(passed, len(test_msgs)))
    ser.deinit()


def monitor(duration_s: int = 60):
    """
    Passive monitor — just listen on UART and print everything.
    ============================================================
    Run this to see what the ESP32 is sending to MaixCam.
    """
    ser = _setup()
    print("\n=== Monitoring UART for {}s ===".format(duration_s))

    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < duration_s * 1000:
        if ser.any():
            data = ser.read(ser.any())
            try:
                text = data.decode("utf-8")
                print("RX: {}".format(text.rstrip()))
            except Exception:
                print("RX (hex): {}".format(data.hex()))
        time.sleep_ms(10)

    print("\n=== Monitor finished ===")
    ser.deinit()


# ── CRC-8 helper (same polynomial as uart_comm.py) ──────────────────

def _crc8(data: bytes) -> int:
    """CRC-8 with poly 0x07."""
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


# ======================================================================
if __name__ == "__main__":
    print("UART test utilities loaded.")
    print("  uart_test.echo_test()       — echo back ESP32 messages")
    print("  uart_test.send_json_test()  — send sample emotion packets")
    print("  uart_test.monitor()         — passive listener")
    print("  uart_test.loopback_test()   — self-test (jumper TX→RX)")

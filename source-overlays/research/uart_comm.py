"""
uart_comm.py — UART Communication Module (upgraded for emotion packets)
========================================================================
Project : SIEVOX — K210 / MaixCAM ↔ ESP32-S3 bridge
Changes : Added JSON-based emotion + tracking telemetry packet format
          with sequence numbers, CRC-8, and graceful drop handling.

Supports both K210 (MaixPy) and MaixCAM Pro (MaixPy3) via platform
auto-detection at import time.

K210 pinout:   RX=IO4,  TX=IO5  (UARTHS)
MaixCAM  pinout:   RX=A18,  TX=A19  (UART1) — recommended over UART0
                   to avoid boot-mode pin conflict on A16

Wire protocol (K210 / MaixCAM → ESP32):
    Each line is a JSON object terminated by '\n':
    {
        "seq": 42,                              // monotonic sequence number
        "ts":  123456,                          // K210 uptime in ms
        "face": true,                           // whether a face was detected
        "bbox": [80, 60, 120, 120],             // [x, y, w, h] or null
        "emo": [0.10, 0.70, 0.15, 0.05],       // [happy, sad, neutral, anger]
        "pitch": 45.0,                          // current gimbal pitch (°)
        "roll":  12.3,                          // current gimbal roll  (°)
        "trk":  true,                           // tracking enabled flag
        "crc":  "A3"                            // CRC-8 hex of the JSON before this field
    }

ESP32 → K210 / MaixCAM (commands):
    Plain-text line commands as before:  GET_STATE\n, ROLL_LEFT\n, etc.
"""

import time
import ujson

# --------------------------------------------------------------------------
# Platform-adaptive imports & pin configuration
# --------------------------------------------------------------------------
_PLATFORM = None          # "K210" or "MAIXCAM"

# ── K210 (MaixPy) path ────────────────────────────────────────────────────
try:
    from machine import UART
    from board import board_info
    from fpioa_manager import fm
    _PLATFORM = "K210"
except ImportError:
    pass

# ── MaixCAM Pro (MaixPy3) path ────────────────────────────────────────────
if _PLATFORM is None:
    try:
        from maix import pinmap, uart
        _PLATFORM = "MAIXCAM"
    except ImportError:
        raise ImportError(
            "[UART] Cannot detect platform — neither K210 (fpioa_manager) "
            "nor MaixCAM (maix.pinmap) imports succeeded."
        )

# ── Pin assignments per platform ──────────────────────────────────────────
_UART_PINS = {
    "K210": {
        "RX": 4,    # board_info.PIN4
        "TX": 5,    # board_info.PIN5
    },
    "MAIXCAM": {
        "RX": "A18",   # UART1_RX — safe, no boot conflict
        "TX": "A19",   # UART1_TX
    },
}


class UartComm:
    """
    Non-blocking UART bridge between K210/MaixCAM and ESP32-S3.

    Key design decisions
    --------------------
    * K210:  Uses UARTHS (high-speed UART) for minimum latency.
    * MaixCAM: Uses UART1 (pins A18/A19) to avoid UART0's boot-mode
      pin conflict on A16 and the boot-log noise on startup.
    * JSON framing with sequence numbers lets the ESP32 detect dropped
      packets without a full ACK/NACK handshake (saves round-trip time).
    * CRC-8 (polynomial 0x07) protects against single-byte corruption on
      the noisy gimbal power rail.
    """

    # CRC-8 lookup table (poly = 0x07, init = 0x00)
    _CRC_TABLE = None

    def __init__(self, baud: int = 115200):
        # ── Build CRC-8 table once ──────────────────────────────────────
        if UartComm._CRC_TABLE is None:
            UartComm._CRC_TABLE = self._build_crc8_table()

        self._platform = _PLATFORM
        pins = _UART_PINS[_PLATFORM]

        # ── Platform-specific init ──────────────────────────────────────
        if _PLATFORM == "K210":
            self._init_k210(pins, baud)
        else:
            self._init_maixcam(pins, baud)

        print("({}) UART initialised @ {} baud".format(
            _PLATFORM.lower(), baud))

        # Drain stale bytes left from a previous boot / brown-out
        if self.uart.any():
            self.uart.read()
            print("({}) Cleared stale UART buffer".format(
                _PLATFORM.lower()))

        # Monotonically increasing sequence counter (wraps at 2^31)
        self._seq = 0

    # ==================================================================
    #  Platform initialisation helpers
    # ==================================================================

    def _init_k210(self, pins, baud):
        """Initialise UARTHS on K210 using fpioa_manager."""
        # Release any prior mapping that might clash with the REPL UART
        for func in (fm.fpioa.UARTHS_RX, fm.fpioa.UARTHS_TX):
            try:
                fm.unregister(func)
            except ValueError:
                pass

        try:
            fm.register(pins["RX"], fm.fpioa.UARTHS_RX, force=True)
            fm.register(pins["TX"], fm.fpioa.UARTHS_TX, force=True)
            print("(k210) UART pins registered: RX=IO{}, TX=IO{}".format(
                pins["RX"], pins["TX"]))
        except Exception:
            print("(k210) WARNING: Failed to register UART pins")

        self.uart = UART(UART.UARTHS, baud, read_buf_len=4096)

    def _init_maixcam(self, pins, baud):
        """Initialise UART1 on MaixCAM Pro using pinmap."""
        try:
            pinmap.set_pin_function(pins["TX"], "UART1_TX")
            pinmap.set_pin_function(pins["RX"], "UART1_RX")
            print("(maixcam) UART1 pins configured: TX={}, RX={}".format(
                pins["TX"], pins["RX"]))
        except Exception as e:
            print("(maixcam) WARNING: Failed to set UART1 pin functions: {}".format(e))

        self.uart = uart.UART(1, baud)

    # ==================================================================
    #  Transmit — emotion telemetry packet
    # ==================================================================

    def send_emotion_packet(
        self,
        emo_probs: dict,
        bbox,
        pitch_val: float,
        roll_val:  float,
        tracking_enabled: bool
    ):
        """
        Build and transmit a JSON telemetry line to the ESP32.

        Parameters
        ----------
        emo_probs : dict  — {"happy": 0.1, "sad": 0.7, "neutral": 0.15, "anger": 0.05}
        bbox      : tuple — (x, y, w, h) or None if no face
        pitch_val : float — current servo pitch position (0-100 internal)
        roll_val  : float — current servo roll position  (0-100 internal)
        tracking_enabled : bool
        """
        # Ordered probability array — order matches EMOTION_LABELS on both sides
        emo_array = [
            round(emo_probs.get("happy",   0.0), 3),
            round(emo_probs.get("sad",     0.0), 3),
            round(emo_probs.get("neutral", 0.0), 3),
            round(emo_probs.get("anger",   0.0), 3),
        ]

        packet = {
            "seq":   self._seq,
            "ts":    time.ticks_ms(),
            "face":  bbox is not None,
            "bbox":  list(bbox) if bbox else None,
            "emo":   emo_array,
            "pitch": round(pitch_val, 1),
            "roll":  round(roll_val,  1),
            "trk":   tracking_enabled,
        }

        # Compute CRC-8 over the JSON payload *before* appending the crc field
        payload_str = ujson.dumps(packet)
        crc_val = self._crc8(payload_str.encode("utf-8"))
        packet["crc"] = "{:02X}".format(crc_val)

        # Final serialisation + newline terminator
        line = ujson.dumps(packet) + "\n"
        self.uart.write(line.encode("utf-8"))

        self._seq = (self._seq + 1) & 0x7FFFFFFF      # wrap safely

    # ==================================================================
    #  Transmit — legacy plain-text response (for command ACKs)
    # ==================================================================

    def send(self, data: str):
        """Send a plain UTF-8 string to ESP32 (for command responses)."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.uart.write(data)

    # ==================================================================
    #  Receive — non-blocking line reader
    # ==================================================================

    def receive_line(self, timeout_ms: int = 100):
        """
        Non-blocking line receiver.

        Reads bytes until '\n' or until *timeout_ms* elapses.
        Returns the decoded string (stripped) or None.

        The short default timeout (100 ms) ensures the main control loop
        is never blocked for long — critical for real-time gimbal tracking.
        """
        start  = time.ticks_ms()
        buffer = b""

        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            if self.uart.any():
                byte = self.uart.read(1)
                if byte:
                    buffer += byte
                    if byte == b"\n":
                        try:
                            return buffer.decode("utf-8").strip()
                        except Exception:
                            return None
            else:
                time.sleep_ms(5)            # yield to avoid busy-spin

        # Timeout — return partial data if any, else None
        if buffer:
            try:
                result = buffer.decode("utf-8").strip()
                print("(" + _PLATFORM.lower() + ") Partial line (timeout): [{}]".format(result))
                return result
            except Exception:
                return None
        return None

    # ==================================================================
    #  CRC-8 helpers
    # ==================================================================

    @staticmethod
    def _build_crc8_table(poly: int = 0x07):
        """Pre-compute a 256-entry CRC-8 lookup table."""
        table = []
        for i in range(256):
            crc = i
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ poly) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
            table.append(crc)
        return table

    @classmethod
    def _crc8(cls, data: bytes, init: int = 0x00) -> int:
        """Compute CRC-8 over a byte string."""
        crc = init
        for b in data:
            crc = cls._CRC_TABLE[(crc ^ b) & 0xFF]
        return crc

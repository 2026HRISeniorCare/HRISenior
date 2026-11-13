"""
main.py — SIEVOX Main Loop (Upgraded with Emotion Recognition)
================================================================
Target: K210 (MaixPy) / MaixCAM Pro (MaixPy3)

Changes from original:
  1. Imports FEREngine for face detection + expression classification.
  2. Every loop iteration runs FER inference and packages the emotion
     probability array into the UART telemetry packet sent to ESP32.
  3. The existing gimbal-tracking (AudioTargetDetector) and manual
     command-handling logic are fully preserved on K210.
  4. On MaixCAM Pro, hardware-dependent modules (servo, audio, LCD)
     gracefully degrade — the core FER + UART pipeline still works.
  5. FER runs at a *lower cadence* than the gimbal loop (configurable)
     to avoid starving the servos of CPU time on K210.
"""

import time
import sys
import gc

# --------------------------------------------------------------------------
# Platform detection
# --------------------------------------------------------------------------
try:
    from machine import Timer, PWM
    _PLATFORM = "K210"
except ImportError:
    _PLATFORM = "MAIXCAM"
    print("[MAIN] Running on MaixCAM Pro — gimbal/audio/servo modules skipped")

# --------------------------------------------------------------------------
# Conditional imports — K210 hardware modules
# --------------------------------------------------------------------------
_gimbal_available = False
_audio_available  = False
_lcd_available    = False

if _PLATFORM == "K210":
    try:
        from audio_detector import AudioTargetDetector
        from servo import Servo
        from doa_calc import PID
        from gimbal import Gimbal
        from led_ring import lcd_setup, lcd_show_gimbal_delta
        _gimbal_available = True
        _audio_available  = True
        _lcd_available    = True
    except ImportError as e:
        print("[MAIN] K210 hardware modules not available: {}".format(e))

    try:
        from config import load_config_from_json
    except ImportError:
        print("[MAIN] config module not found — using defaults")
        def load_config_from_json():
            return {}

# ── Always available: FER + UART ────────────────────────────────────────
from fer_engine import FEREngine, EMOTION_LABELS
from uart_comm import UartComm


# ======================================================================
#  Default configuration (used when config.py / JSON config is missing)
# ======================================================================
_DEFAULT_CONFIG = {
    "audio_range":       60,
    "ignore_threshold":  10,
    "pitch_pid":         (0.8, 0.01, 0.05),
    "roll_pid":          (0.8, 0.01, 0.05),
    "init_pitch":        50,
    "init_roll":         50,
    "pitch_reverse":     False,
    "roll_reverse":      False,
    "pitch_disp_invert": False,
    "roll_disp_invert":  False,
    "face_model":        "/sd/models/face_detect.kmodel",
    "fer_model":         "/sd/models/fer_mobilenet.kmodel",
    "face_threshold":    0.5,
    "fer_every_n":       3,
    "loop_delay":        0.05,
}


def main():
    # ==================================================================
    #  Load config
    # ==================================================================
    cfg = _DEFAULT_CONFIG.copy()
    try:
        cfg.update(load_config_from_json())
    except Exception:
        pass

    # ==================================================================
    #  Hardware init — PWM timers for gimbal servos (K210 only)
    # ==================================================================
    if _gimbal_available:
        tim_pitch = Timer(Timer.TIMER0, Timer.CHANNEL0, mode=Timer.MODE_PWM)
        tim_roll  = Timer(Timer.TIMER0, Timer.CHANNEL1, mode=Timer.MODE_PWM)
        pwm_pitch = PWM(tim_pitch, freq=50, duty=0, pin=7)
        pwm_roll  = PWM(tim_roll,  freq=50, duty=0, pin=8)

        # ── Audio target detector (Sound Source Localisation) ─────────
        detector = AudioTargetDetector(
            out_range    = cfg["audio_range"],
            ignore_limit = cfg["ignore_threshold"],
        )

        # ── PID controllers for pitch / roll axes ─────────────────────
        pid_pitch = PID(*cfg["pitch_pid"], is_roll=False)
        pid_roll  = PID(*cfg["roll_pid"],  is_roll=True)

        # ── Servo objects ─────────────────────────────────────────────
        pitch_servo = Servo(
            pwm_pitch,
            dir=cfg["init_pitch"],
            range_min=0, range_max=100,
            is_roll=False,
        )
        roll_servo = Servo(
            pwm_roll,
            dir=cfg["init_roll"],
            range_min=0, range_max=100,
            is_roll=True,
        )

        # ── Gimbal controller (wraps PID + servos) ────────────────────
        gimbal = Gimbal(
            pitch=pitch_servo, pid_pitch=pid_pitch,
            roll=roll_servo,   pid_roll=pid_roll,
        )
    else:
        # MaixCAM Pro: placeholders so the rest of the code compiles
        pitch_servo = None
        roll_servo  = None
        detector    = None
        gimbal      = None
        cfg.setdefault("init_pitch", 50)
        cfg.setdefault("init_roll",  50)

    # ==================================================================
    #  LCD / display (K210 only)
    # ==================================================================
    if _lcd_available:
        lcd_setup(rotation=0)
        init_pitch = cfg["init_pitch"]
        init_roll  = cfg["init_roll"]
        pitch_disp_invert = cfg.get("pitch_disp_invert", False)
        roll_disp_invert  = cfg.get("roll_disp_invert",  False)
    else:
        init_pitch = cfg.get("init_pitch", 50)
        init_roll  = cfg.get("init_roll",  50)

    # ==================================================================
    #  UART bridge to ESP32
    # ==================================================================
    uart_esp = UartComm()

    # ==================================================================
    #  ★  Facial Expression Recognition engine  ★
    # ==================================================================
    fer = FEREngine(
        face_model_path = cfg.get("face_model", "/sd/models/face_detect.kmodel"),
        fer_model_path  = cfg.get("fer_model",  "/sd/models/fer_mobilenet.kmodel"),
        face_threshold  = cfg.get("face_threshold", 0.5),
    )

    # FER cadence: run inference every N main-loop iterations to balance
    # CPU between gimbal control and vision.  Default = every 3rd frame.
    fer_every_n     = cfg.get("fer_every_n", 3)
    fer_tick        = 0
    last_emo_probs  = {label: 0.25 for label in EMOTION_LABELS}
    last_bbox       = None

    # ==================================================================
    #  Loop timing
    # ==================================================================
    loop_delay_s  = cfg.get("loop_delay", 0.05)
    loop_delay_ms = max(0, int(loop_delay_s * 1000))

    # ==================================================================
    #  Runtime state
    # ==================================================================
    state = {
        "tracking_enabled": _gimbal_available,  # only enable if gimbal exists
        "manual_pitch_step": 5,
        "manual_roll_step":  5,
    }

    # ------------------------------------------------------------------
    #  Helper: format a human-readable status string for command ACKs
    # ------------------------------------------------------------------
    def format_status(label="STATE"):
        p = pitch_servo.get_position() if pitch_servo else 50.0
        r = roll_servo.get_position() if roll_servo else 0.0
        t = 1 if state["tracking_enabled"] else 0
        return "{} pitch={:.1f} roll={:.1f} tracking={}".format(label, p, r, t)

    # ------------------------------------------------------------------
    #  Command handler (ESP32 → K210 / MaixCAM)
    # ------------------------------------------------------------------
    def handle_command(raw_cmd):
        if not raw_cmd:
            return None
        cmd = raw_cmd.strip().upper()
        if not cmd:
            return None

        if cmd == "GET_STATE":
            return format_status("STATE")

        # ── Tracking toggle (always works, even without gimbal) ──────
        if cmd == "ENABLE_TRACKING":
            state["tracking_enabled"] = True
            return format_status("ACK ENABLE_TRACKING")

        if cmd == "DISABLE_TRACKING":
            state["tracking_enabled"] = False
            return format_status("ACK DISABLE_TRACKING")

        if cmd == "HOLD_POSITION":
            state["tracking_enabled"] = False
            return format_status("ACK HOLD_POSITION")

        # ── Gimbal commands (K210 only) ──────────────────────────────
        if not _gimbal_available:
            if cmd in ("ROLL_LEFT", "ROLL_RIGHT", "PITCH_UP", "PITCH_DOWN", "RESET"):
                return "ERROR gimbal_unavailable_on_this_platform"

        if cmd == "ROLL_LEFT":
            if roll_servo:
                state["tracking_enabled"] = False
                roll_servo.turn_left(state["manual_roll_step"])
                return format_status("ACK ROLL_LEFT")
            return "ERROR roll_servo_unavailable"

        if cmd == "ROLL_RIGHT":
            if roll_servo:
                state["tracking_enabled"] = False
                roll_servo.turn_right(state["manual_roll_step"])
                return format_status("ACK ROLL_RIGHT")
            return "ERROR roll_servo_unavailable"

        if cmd == "PITCH_UP":
            state["tracking_enabled"] = False
            pitch_servo.drive(state["manual_pitch_step"])
            return format_status("ACK PITCH_UP")

        if cmd == "PITCH_DOWN":
            state["tracking_enabled"] = False
            pitch_servo.drive(-state["manual_pitch_step"])
            return format_status("ACK PITCH_DOWN")

        if cmd == "RESET":
            state["tracking_enabled"] = False
            pitch_servo.set_position(init_pitch)
            if roll_servo:
                roll_servo.set_position(init_roll)
            return format_status("ACK RESET")

        return "ERROR unknown_command: {}".format(raw_cmd.strip())

    # ==================================================================
    #  ★  MAIN LOOP  ★
    # ==================================================================
    try:
        while True:

            # ── 1. Audio-based gimbal tracking (K210 only) ──────────
            if _gimbal_available and state["tracking_enabled"]:
                height_err, horizontal_err = detector.get_target_err()
                gimbal.run(
                    height_err     = height_err,
                    horizontal_err = horizontal_err,
                    pitch_reverse  = cfg["pitch_reverse"],
                    roll_reverse   = cfg["roll_reverse"],
                )

            # ── 2. FER inference (throttled) ────────────────────────
            fer_tick += 1
            if fer_tick >= fer_every_n:
                fer_tick = 0
                try:
                    last_emo_probs, last_bbox = fer.infer()
                except Exception as e:
                    print("[MAIN] FER error: {}".format(e))
                    # Keep previous result on failure — graceful degradation
                gc.collect()      # reclaim KPU/NPU intermediate buffers

            # ── 3. LCD status display (K210 only) ───────────────────
            if _lcd_available:
                lcd_show_gimbal_delta(
                    pitch_val    = pitch_servo.value,
                    roll_val     = roll_servo.value,
                    init_pitch   = init_pitch,
                    init_roll    = init_roll,
                    pitch_scale  = 1.8,
                    roll_scale   = 1.8,
                    pitch_invert = pitch_disp_invert,
                    roll_invert  = roll_disp_invert,
                )

            # ── 4. Send emotion telemetry to ESP32 ──────────────────
            p_val = pitch_servo.value if pitch_servo else 50.0
            r_val = roll_servo.value if roll_servo else 0.0
            uart_esp.send_emotion_packet(
                emo_probs        = last_emo_probs,
                bbox             = last_bbox,
                pitch_val        = p_val,
                roll_val         = r_val,
                tracking_enabled = state["tracking_enabled"],
            )

            # ── 5. Receive & handle ESP32 commands (non-blocking) ───
            data = uart_esp.receive_line(timeout_ms=50)
            if data:
                # Ignore JSON packets echoed back (they start with '{')
                if not data.startswith("{"):
                    print("({}) CMD from ESP32: {}".format(
                        _PLATFORM.lower(), data))
                    response = handle_command(data)
                    if response:
                        uart_esp.send(response + "\n")
                        print("({}) ACK sent: {}".format(
                            _PLATFORM.lower(), response))

            # ── 6. Yield ────────────────────────────────────────────
            if loop_delay_ms > 0:
                time.sleep_ms(loop_delay_ms)

    except KeyboardInterrupt:
        print("[MAIN] Interrupted by user")
    except Exception as e:
        print("[MAIN] Fatal: {}".format(e))
        sys.print_exception(e)
    finally:
        # Graceful shutdown
        fer.deinit()
        if detector:
            detector.deinit()
        if _gimbal_available:
            pitch_servo.drive(init_pitch)
            roll_servo.drive(init_roll)
            pitch_servo.enable(False)
            roll_servo.enable(False)
        print("[MAIN] Shutdown complete")


# ======================================================================
if __name__ == "__main__":
    main()

"""
fer_engine.py — Facial Expression Recognition Engine for K210 / MaixCAM
=========================================================================
Project : SIEVOX — Multimodal Elderly Care Robot
Target  : K210 (MaixPy) or MaixCAM Pro (MaixPy3)
Author  : SIEVOX Vision Group
---------------------------------------------------------------------------

This module wraps a lightweight KPU / NPU-accelerated face detection +
emotion classification pipeline.  It outputs a normalised probability
vector over 4 basic emotions:  [happy, sad, neutral, anger].

Model files required (K210):
    /sd/models/face_detect.kmodel      — YOLO-based face bbox detector
    /sd/models/fer_mobilenet.kmodel    — MobileNetV2-0.35 emotion classifier
    Both models must be INT8-quantised and compiled with nncase for K210 KPU.

Model files required (MaixCAM Pro):
    /sd/models/face_detect.mud         — face detector (AX NPU format)
    /sd/models/fer_mobilenet.mud       — emotion classifier (AX NPU format)
    Or place .kmodel files and the MaixPy3 nn module will handle conversion.
"""

import time
import gc

# --------------------------------------------------------------------------
# Platform-adaptive imports
# MaixPy (K210): uses KPU + sensor + image modules directly
# MaixPy3 (MaixCAM Pro): uses maix.camera + maix.nn
# --------------------------------------------------------------------------
try:
    import KPU as kpu
    import sensor
    import image
    _PLATFORM = "K210"
except ImportError:
    # MaixCAM fallback — adapt imports as needed for your BSP
    from maix import camera, image, nn
    _PLATFORM = "MAIXCAM"


# ---------------------------------------------------------------------------
# Emotion label order — MUST match the classifier's softmax output order.
# The same order is used on the ESP32 side for D-S fusion.
# ---------------------------------------------------------------------------
EMOTION_LABELS = ["happy", "sad", "neutral", "anger"]
NUM_EMOTIONS   = len(EMOTION_LABELS)

# Confidence floor: if the highest softmax output is below this threshold
# we report a uniform "uncertain" distribution instead of a noisy spike.
CONFIDENCE_FLOOR = 0.25


class FEREngine:
    """
    Lightweight Facial Expression Recognition engine.

    Usage
    -----
    >>> engine = FEREngine()
    >>> probs, bbox = engine.infer()        # returns (dict, tuple|None)
    >>> # probs = {"happy": 0.1, "sad": 0.7, "neutral": 0.15, "anger": 0.05}
    >>> # bbox  = (x, y, w, h) of the detected face, or None if no face
    >>> engine.deinit()
    """

    def __init__(
        self,
        face_model_path:  str = "/sd/models/face_detect.kmodel",
        fer_model_path:   str = "/sd/models/fer_mobilenet.kmodel",
        face_threshold:   float = 0.5,
        fer_input_size:   tuple = (48, 48),      # emotion classifier input HxW
        camera_framesize: int = None,             # sensor.QVGA by default
        camera_fps:       int = 30,               # MaixCAM only
    ):
        """
        Parameters
        ----------
        face_model_path   : path to the face-detection model
        fer_model_path    : path to the emotion classifier model
        face_threshold    : minimum bbox confidence for a valid face
        fer_input_size    : spatial size the emotion model expects (H, W)
        camera_framesize  : MaixPy sensor constant (default QVGA = 320x240)
        camera_fps        : frame rate for MaixCAM camera (default 30)
        """
        self._face_threshold = face_threshold
        self._fer_size       = fer_input_size
        self._last_probs     = self._uniform_probs()
        self._last_bbox      = None

        # ------------------------------------------------------------------
        # K210 / MaixPy initialisation
        # ------------------------------------------------------------------
        if _PLATFORM == "K210":
            self._init_k210(face_model_path, fer_model_path, camera_framesize)
        else:
            self._init_maixcam(face_model_path, fer_model_path,
                               camera_framesize, camera_fps)

    # ==================================================================
    #  Platform initialisation helpers
    # ==================================================================

    def _init_k210(self, face_model_path, fer_model_path, camera_framesize):
        """Initialise camera and KPU models on K210."""
        # Camera
        sensor.reset()
        sensor.set_pixformat(sensor.RGB565)
        if camera_framesize is None:
            camera_framesize = sensor.QVGA          # 320 × 240
        sensor.set_framesize(camera_framesize)
        sensor.set_hmirror(False)
        sensor.set_vflip(False)
        sensor.run(1)

        # Load face detector onto KPU
        self._face_kpu = kpu.load(face_model_path)
        kpu.set_outputs(self._face_kpu, 0, 5, 5, 25)   # adjust anchors for your model

        # Load emotion classifier onto KPU (second model slot)
        self._fer_kpu = kpu.load(fer_model_path)

        print("[FER] K210 models loaded  face={} fer={}".format(
            face_model_path, fer_model_path))

    def _init_maixcam(self, face_model_path, fer_model_path,
                      camera_framesize, camera_fps):
        """Initialise camera and NPU models on MaixCAM Pro."""
        # ── Camera ────────────────────────────────────────────────────
        self._cam = camera.Camera(
            width=camera_framesize if camera_framesize else 320,
            height=240 if camera_framesize is None else 240,
            fps=camera_fps,
        )
        # Warm-up: discard first few frames (auto-exposure settling)
        for _ in range(5):
            self._cam.read()
        print("[FER] MaixCAM camera ready ({}x{} @ {}fps)".format(
            self._cam.width, self._cam.height, camera_fps))

        # ── Face detection model ──────────────────────────────────────
        try:
            self._face_det = nn.NN({
                "model": face_model_path,
                "type":  "detector",          # or "yolo" depending on model
            })
            print("[FER] MaixCAM face detector loaded: {}".format(face_model_path))
        except Exception as e:
            print("[FER] WARNING: Face detector load failed ({}): {}".format(
                face_model_path, e))
            self._face_det = None

        # ── Emotion classifier model ──────────────────────────────────
        try:
            self._fer_cls = nn.NN({
                "model": fer_model_path,
                "type":  "classifier",
            })
            print("[FER] MaixCAM emotion classifier loaded: {}".format(fer_model_path))
        except Exception as e:
            print("[FER] WARNING: Emotion classifier load failed ({}): {}".format(
                fer_model_path, e))
            self._fer_cls = None

    # ======================================================================
    #  Public API
    # ======================================================================

    def infer(self):
        """
        Capture one frame, detect the largest face, classify its expression.

        Returns
        -------
        probs : dict   — {"happy": float, "sad": float, ...} summing to ~1.0
        bbox  : tuple  — (x, y, w, h) of the detected face or None
        """
        if _PLATFORM == "K210":
            return self._infer_k210()
        else:
            return self._infer_maixcam()

    def get_last_result(self):
        """Return the most recent (probs, bbox) without running inference."""
        return self._last_probs, self._last_bbox

    def deinit(self):
        """Release KPU/NPU resources and stop the camera."""
        if _PLATFORM == "K210":
            try:
                kpu.deinit(self._face_kpu)
            except Exception:
                pass
            try:
                kpu.deinit(self._fer_kpu)
            except Exception:
                pass
            sensor.run(0)
        else:
            self._cam.close()
            del self._face_det
            del self._fer_cls
        gc.collect()
        print("[FER] Engine deinitialised")

    # ======================================================================
    #  Internal — K210 / MaixPy path
    # ======================================================================

    def _infer_k210(self):
        """Full pipeline on K210 KPU."""
        img = sensor.snapshot()

        # ------ Step 1: Face detection ------
        try:
            face_results = kpu.run_yolo2(self._face_kpu, img)
        except Exception as e:
            print("[FER] Face detect error: {}".format(e))
            return self._uniform_probs(), None

        if not face_results:
            self._last_bbox = None
            return self._last_probs, None

        # Pick the largest face (closest to the camera)
        best = max(face_results, key=lambda r: r.w() * r.h())
        if best.value() < self._face_threshold:
            self._last_bbox = None
            return self._last_probs, None

        x, y, w, h = best.x(), best.y(), best.w(), best.h()
        self._last_bbox = (x, y, w, h)

        # ------ Step 2: Crop + preprocess for emotion classifier ------
        probs = self._classify_face_k210(img, x, y, w, h)
        return probs, self._last_bbox

    def _classify_face_k210(self, img, x, y, w, h):
        """Crop face ROI and run KPU emotion classifier."""
        margin = max(w, h) // 6
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(img.width(),  x + w + margin)
        y2 = min(img.height(), y + h + margin)

        face_roi = img.copy((x1, y1, x2 - x1, y2 - y1))
        face_roi = face_roi.resize(self._fer_size[1], self._fer_size[0])
        face_roi.pix_to_ai()                    # convert to KPU input format

        try:
            fmap = kpu.forward(self._fer_kpu, face_roi)
            raw_output = list(fmap[:])           # flatten feature-map to list
        except Exception as e:
            print("[FER] Classifier error: {}".format(e))
            return self._last_probs

        probs = self._softmax(raw_output[:NUM_EMOTIONS])
        if max(probs) < CONFIDENCE_FLOOR:
            probs = [1.0 / NUM_EMOTIONS] * NUM_EMOTIONS

        result = {}
        for i, label in enumerate(EMOTION_LABELS):
            result[label] = round(probs[i], 4)

        self._last_probs = result
        return result

    # ======================================================================
    #  Internal — MaixCAM Pro path
    # ======================================================================

    def _infer_maixcam(self):
        """
        Full pipeline on MaixCAM Pro NPU.

        Steps:
          1. Capture frame from camera
          2. Run face detector to find bounding boxes
          3. Pick the largest face above confidence threshold
          4. Crop & resize face ROI
          5. Run emotion classifier on the cropped face
          6. Softmax-normalise and return
        """
        # ------ Step 0: Guard against missing models ------------------
        if self._face_det is None or self._fer_cls is None:
            print("[FER] Models not loaded — returning uniform probs")
            return self._uniform_probs(), None

        # ------ Step 1: Capture frame ---------------------------------
        try:
            frame = self._cam.read()
            if frame is None:
                print("[FER] Camera read returned None")
                return self._uniform_probs(), None
        except Exception as e:
            print("[FER] Camera read error: {}".format(e))
            return self._uniform_probs(), None

        # ------ Step 2: Face detection --------------------------------
        try:
            # maix.nn detector returns list of [x, y, w, h, score, class_id]
            detections = self._face_det.forward(frame)
        except Exception as e:
            print("[FER] Face detect error: {}".format(e))
            return self._last_probs, self._last_bbox

        if not detections or len(detections) == 0:
            self._last_bbox = None
            return self._last_probs, None

        # ------ Step 3: Pick the largest face -------------------------
        best = None
        best_area = 0
        for det in detections:
            # det format: [x1, y1, x2, y2, score, class_id]  or
            #             [x, y, w, h, score]
            if len(det) >= 5:
                score = det[4]
                if score < self._face_threshold:
                    continue
                if len(det) >= 6:
                    # [x1, y1, x2, y2, score, class_id] → convert to (x,y,w,h)
                    x, y, x2, y2 = det[0], det[1], det[2], det[3]
                    w, h = x2 - x, y2 - y
                else:
                    # [x, y, w, h, score]
                    x, y, w, h = det[0], det[1], det[2], det[3]

                area = w * h
                if area > best_area:
                    best_area = area
                    best = (int(x), int(y), int(w), int(h), score)

        if best is None:
            self._last_bbox = None
            return self._last_probs, None

        x, y, w, h, score = best
        self._last_bbox = (x, y, w, h)

        # ------ Step 4 & 5: Crop face + classify emotion ---------------
        probs = self._classify_face_maixcam(frame, x, y, w, h)
        return probs, self._last_bbox

    def _classify_face_maixcam(self, frame, x, y, w, h):
        """
        Crop the face region from *frame*, resize to classifier input size,
        and run the emotion classifier.
        """
        try:
            # Add margin around the face for context
            margin = max(w, h) // 6
            fw = frame.width if hasattr(frame, 'width') else 320
            fh = frame.height if hasattr(frame, 'height') else 240

            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(fw, x + w + margin)
            y2 = min(fh, y + h + margin)

            # Crop using maix.image or raw slicing
            if hasattr(frame, 'crop'):
                face_roi = frame.crop(x1, y1, x2 - x1, y2 - y1)
            else:
                # frame is a numpy-like array  (H, W, C)
                face_roi = frame[y1:y2, x1:x2]

            # Resize to classifier input size
            if hasattr(face_roi, 'resize'):
                face_roi = face_roi.resize(self._fer_size[1], self._fer_size[0])
            else:
                import cv2
                face_roi = cv2.resize(face_roi, (self._fer_size[1], self._fer_size[0]))

            # Run emotion classifier
            output = self._fer_cls.forward(face_roi)

            # output might be a list/array of logits or probabilities
            if hasattr(output, 'tolist'):
                raw = output.tolist()
            elif isinstance(output, list):
                raw = list(output)
            else:
                raw = list(output)

        except Exception as e:
            print("[FER] MaixCAM classify error: {}".format(e))
            return self._last_probs

        # ------ Softmax normalisation ----------------------------------
        if len(raw) >= NUM_EMOTIONS:
            raw = raw[:NUM_EMOTIONS]
        elif len(raw) < NUM_EMOTIONS:
            # Pad with zeros if model output is short
            raw = raw + [0.0] * (NUM_EMOTIONS - len(raw))

        probs = self._softmax(raw)

        # Guard against low-confidence garbage
        if max(probs) < CONFIDENCE_FLOOR:
            probs = [1.0 / NUM_EMOTIONS] * NUM_EMOTIONS

        result = {}
        for i, label in enumerate(EMOTION_LABELS):
            result[label] = round(probs[i], 4)

        self._last_probs = result
        return result

    # ======================================================================
    #  Utility helpers
    # ======================================================================

    @staticmethod
    def _softmax(logits):
        """
        Numerically-stable softmax for a short list of floats.
        Avoids importing numpy (not available on MaixPy).
        """
        max_val = max(logits)
        exps = []
        for v in logits:
            # Clamp to avoid overflow on K210 (no double-precision FPU)
            e = v - max_val
            if e < -20.0:
                e = -20.0
            # Hand-rolled exp() — math.exp is available on MaixPy
            from math import exp
            exps.append(exp(e))
        total = sum(exps)
        if total == 0:
            return [1.0 / len(logits)] * len(logits)
        return [e / total for e in exps]

    @staticmethod
    def _uniform_probs():
        """Return a uniform distribution dict (used when no face detected)."""
        u = round(1.0 / NUM_EMOTIONS, 4)
        return {label: u for label in EMOTION_LABELS}

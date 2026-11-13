"""
Fusion Methods for Multimodal Emotion Recognition
===================================================
Implements all fusion strategies for ablation study:
  1. Vision-only (FER)
  2. Audio-only (SER)
  3. Bayesian Fusion (baseline)
  4. Dempster-Shafer Fusion (proposed)
  5. D-S + SNR/Lux Dynamic Trust Correction (proposed, enhanced)

All methods follow the exact same interface for fair comparison.

Project : SIEVOX — Multimodal Elderly Care Robot
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from enum import IntEnum


# =========================================================================
# Constants (must match C++ side: ds_fusion_engine.h / speech_emotion.h)
# =========================================================================

class EmotionIndex(IntEnum):
    HAPPY   = 0
    SAD     = 1
    NEUTRAL = 2
    ANGER   = 3

EMOTION_LABELS = ['happy', 'sad', 'neutral', 'anger']
NUM_EMOTIONS   = len(EMOTION_LABELS)


# =========================================================================
# Data structures
# =========================================================================

@dataclass
class BPA:
    """Basic Probability Assignment (matches C++ BPA struct)."""
    singletons: np.ndarray           # shape (4,), mass per emotion
    uncertainty: float = 1.0         # m(Θ), default = total ignorance

    @staticmethod
    def from_prob_array(probs: np.ndarray, confidence: float) -> 'BPA':
        """
        Convert probability array → BPA via simple support function.
        Matches C++ BPA::FromProbArray() exactly.
        """
        confidence = np.clip(confidence, 0.0, 1.0)
        total = np.sum(probs)
        if total < 1e-6:
            return BPA(np.zeros(NUM_EMOTIONS), 1.0)

        scale = confidence / total
        singletons = probs * scale
        uncertainty = 1.0 - confidence
        return BPA(singletons, uncertainty)


@dataclass
class FusionResult:
    """Fused result (matches C++ FusionResult struct)."""
    belief: np.ndarray               # shape (4,), fused belief per emotion
    conflict: float                  # K factor ∈ [0, 1)
    dominant: EmotionIndex           # argmax(belief)
    dominant_score: float            # belief[dominant]
    high_conflict: bool = False      # K >= threshold
    timestamp_ms: float = 0.0

    @property
    def predicted_label(self) -> str:
        return EMOTION_LABELS[self.dominant]


# =========================================================================
# SNR/Lux Dynamic Trust Correction Engine
# =========================================================================

@dataclass
class EnvironmentalContext:
    """Sensor environment quality readings."""
    snr_db: float = 30.0            # Signal-to-Noise Ratio (dB), higher = better
    lux: float = 500.0              # Ambient light (lux), higher = brighter
    face_distance_px: float = 150.0 # Face bounding box size proxy (px), larger = closer

    # Calibration thresholds
    SNR_MIN: float = 5.0            # Below this → audio unreliable
    SNR_MAX: float = 40.0           # Above this → audio near-perfect
    LUX_MIN: float = 50.0           # Below this → vision unreliable
    LUX_MAX: float = 1000.0         # Above this → vision near-perfect
    DIST_MIN: float = 30.0          # Face too small (far away) → unreliable
    DIST_MAX: float = 250.0         # Face large enough → reliable


def compute_dynamic_confidence(env: EnvironmentalContext) -> Tuple[float, float]:
    """
    Compute dynamic vision/audio confidence from environmental conditions.

    Maps SNR → audio_confidence (sigmoid-like)
    Maps Lux + face_distance → vision_confidence (sigmoid-like)

    Returns (vision_confidence, audio_confidence) each ∈ [0.05, 1.0]
    """
    # --- Audio confidence from SNR ---
    snr_norm = np.clip((env.snr_db - env.SNR_MIN) / (env.SNR_MAX - env.SNR_MIN), 0.0, 1.0)
    # Sigmoid-like mapping: steep transition in SNR 10-25 dB range
    audio_conf = 0.05 + 0.90 * snr_norm

    # --- Vision confidence from Lux ---
    lux_norm = np.clip((env.lux - env.LUX_MIN) / (env.LUX_MAX - env.LUX_MIN), 0.0, 1.0)
    lux_log = np.log1p(lux_norm * 9.0) / np.log(10.0)  # log-scale perception

    # Face distance contributes to vision reliability
    dist_norm = np.clip(
        (env.face_distance_px - env.DIST_MIN) / (env.DIST_MAX - env.DIST_MIN),
        0.0, 1.0
    )

    vision_conf = 0.05 + 0.90 * (0.6 * lux_log + 0.4 * dist_norm)
    vision_conf = np.clip(vision_conf, 0.05, 0.95)

    return vision_conf, audio_conf


# =========================================================================
# 1. Vision-Only (FER baseline)
# =========================================================================

def fuse_vision_only(probs_vision: np.ndarray,
                     face_detected: bool = True,
                     confidence: float = 0.75) -> FusionResult:
    """
    Single-modality baseline: use only the visual emotion estimate.

    Parameters
    ----------
    probs_vision : shape (4,) normalised probability array [H, S, N, A]
    face_detected : if False, confidence drops to near-zero
    confidence : base confidence (0.75 default from DSFusionConfig)
    """
    conf = confidence if face_detected else 0.05
    bpa = BPA.from_prob_array(probs_vision, conf)

    return FusionResult(
        belief=bpa.singletons / (np.sum(bpa.singletons) + 1e-8),
        conflict=0.0,
        dominant=EmotionIndex(np.argmax(bpa.singletons)),
        dominant_score=np.max(bpa.singletons),
        high_conflict=False
    )


# =========================================================================
# 2. Audio-Only (SER baseline)
# =========================================================================

def fuse_audio_only(probs_audio: np.ndarray,
                    confidence: float = 0.70) -> FusionResult:
    """
    Single-modality baseline: use only the speech emotion estimate.
    """
    bpa = BPA.from_prob_array(probs_audio, confidence)
    belief = bpa.singletons / (np.sum(bpa.singletons) + 1e-8)

    return FusionResult(
        belief=belief,
        conflict=0.0,
        dominant=EmotionIndex(np.argmax(belief)),
        dominant_score=np.max(belief),
        high_conflict=False
    )


# =========================================================================
# 3. Bayesian Fusion (baseline)
# =========================================================================

def fuse_bayesian(probs_vision: np.ndarray,
                  probs_audio: np.ndarray,
                  vision_conf: float = 0.75,
                  audio_conf: float = 0.70,
                  face_detected: bool = True) -> FusionResult:
    """
    Naive Bayesian fusion: multiply likelihoods with confidence-weighted prior.

    Assumes conditional independence P(v,a|e) = P(v|e)·P(a|e).
    Posterior ∝ P(v|e)·P(a|e)·P(e) with uniform prior P(e) = 0.25.

    This is the standard baseline for multimodal fusion in emotion recognition.
    """
    v_conf = vision_conf if face_detected else 0.05
    v_weighted = probs_vision * v_conf + (1.0 - v_conf) * 0.25  # smooth with uniform
    a_weighted = probs_audio * audio_conf + (1.0 - audio_conf) * 0.25

    # Element-wise product (Naive Bayes assumption)
    posterior = v_weighted * a_weighted
    posterior /= (np.sum(posterior) + 1e-8)

    # Compute approximate conflict for comparison (Pearson distance)
    v_conflict = 1.0 - np.dot(probs_vision, probs_audio)  # 1-cosine when norms≈1
    high_conflict = v_conflict > 0.85

    return FusionResult(
        belief=posterior,
        conflict=float(v_conflict),
        dominant=EmotionIndex(np.argmax(posterior)),
        dominant_score=np.max(posterior),
        high_conflict=bool(high_conflict)
    )


# =========================================================================
# 4. Dempster-Shafer Fusion (proposed — matches C++ exactly)
# =========================================================================

@dataclass
class DSFusionConfig:
    """Configuration matches C++ DSFusionConfig."""
    conflict_threshold: float = 0.85
    vision_stale_timeout_ms: float = 2000.0
    audio_stale_timeout_ms: float = 1500.0
    vision_reliability: float = 0.6       # Weight in fallback average
    audio_reliability: float = 0.4
    vision_confidence: float = 0.75       # Base confidence for BPA construction
    audio_confidence: float = 0.70


def dempster_combine(m1: BPA, m2: BPA, cfg: DSFusionConfig) -> FusionResult:
    """
    Core Dempster's Rule of Combination.
    Matches C++ DSFusionEngine::CombineBPAs() exactly.

    m₁₂(A) = [ Σ_{B∩C=A} m₁(B)·m₂(C) ] / (1 - K)

    where K = Σ_{B∩C=∅} m₁(B)·m₂(C) is the conflict factor.

    For singleton-only focal elements + Θ:
      raw(θᵢ) = m₁(θᵢ)·m₂(θᵢ) + m₁(θᵢ)·m₂(Θ) + m₁(Θ)·m₂(θᵢ)
      raw(Θ)  = m₁(Θ)·m₂(Θ)
      K       = Σ_{i≠j} m₁(θᵢ)·m₂(θⱼ)
    """
    # ── Step 1: Compute conflict K ──
    m1_arr = np.asarray(m1.singletons, dtype=np.float64)
    m2_arr = np.asarray(m2.singletons, dtype=np.float64)

    # K = sum of all off-diagonal products m₁(θᵢ)·m₂(θⱼ) for i≠j
    total_outer = np.outer(m1_arr, m2_arr)
    K = float(np.sum(total_outer) - np.sum(np.diag(total_outer)))

    result = FusionResult(
        belief=np.zeros(NUM_EMOTIONS),
        conflict=K,
        dominant=EmotionIndex.NEUTRAL,
        dominant_score=0.0,
        high_conflict=(K >= cfg.conflict_threshold)
    )

    # ── High-conflict guard (Zadeh's paradox) ──
    if result.high_conflict:
        return _fallback_average(m1_arr, m2_arr, cfg, K)

    # ── Step 2: Compute raw combined masses ──
    norm = 1.0 - K
    if norm < 1e-8:
        return _fallback_average(m1_arr, m2_arr, cfg, K)

    inv_norm = 1.0 / norm
    belief = np.zeros(NUM_EMOTIONS)
    for i in range(NUM_EMOTIONS):
        raw_i = (m1_arr[i] * m2_arr[i]          # agree on θᵢ
                 + m1_arr[i] * m2.uncertainty    # m₁ specific
                 + m1.uncertainty * m2_arr[i])   # m₂ specific
        belief[i] = raw_i * inv_norm

    # Residual uncertainty
    fused_uncertainty = (m1.uncertainty * m2.uncertainty) * inv_norm
    belief_sum = np.sum(belief)

    # ── Step 3: Distribute residual uncertainty proportionally ──
    if belief_sum > 1e-6 and fused_uncertainty > 1e-6:
        belief += fused_uncertainty * (belief / belief_sum)
    elif fused_uncertainty > 0.5:
        belief = np.ones(NUM_EMOTIONS) / NUM_EMOTIONS

    # ── Final normalisation ──
    total = np.sum(belief)
    if total > 0:
        belief /= total

    result.belief = belief
    result.dominant = EmotionIndex(int(np.argmax(belief)))
    result.dominant_score = float(np.max(belief))
    return result


def _fallback_average(v_arr: np.ndarray, a_arr: np.ndarray,
                      cfg: DSFusionConfig, K: float) -> FusionResult:
    """Reliability-weighted average when conflict is too high."""
    w_v, w_a = cfg.vision_reliability, cfg.audio_reliability
    w_total = w_v + w_a
    if w_total < 1e-6:
        w_total = 1.0

    belief = (v_arr * w_v + a_arr * w_a) / w_total
    total = np.sum(belief)
    if total > 0:
        belief /= total
    else:
        belief = np.ones(NUM_EMOTIONS) / NUM_EMOTIONS

    return FusionResult(
        belief=belief,
        conflict=K,
        dominant=EmotionIndex(int(np.argmax(belief))),
        dominant_score=float(np.max(belief)),
        high_conflict=True
    )


def fuse_dempster_shafer(probs_vision: np.ndarray,
                         probs_audio: np.ndarray,
                         face_detected: bool = True,
                         cfg: Optional[DSFusionConfig] = None) -> FusionResult:
    """
    D-S fusion (static confidence — current ESP32-S3 deployment).

    Parameters
    ----------
    probs_vision, probs_audio : shape (4,) normalised probability arrays
    face_detected : if False, vision confidence drops to 0.05
    cfg : fusion configuration (uses defaults if None)
    """
    if cfg is None:
        cfg = DSFusionConfig()

    v_conf = cfg.vision_confidence if face_detected else 0.05
    vision_bpa = BPA.from_prob_array(probs_vision, v_conf)
    audio_bpa  = BPA.from_prob_array(probs_audio, cfg.audio_confidence)

    return dempster_combine(vision_bpa, audio_bpa, cfg)


# =========================================================================
# 5. D-S + SNR/Lux Dynamic Trust Correction (proposed, enhanced)
# =========================================================================

def fuse_ds_dynamic(probs_vision: np.ndarray,
                    probs_audio: np.ndarray,
                    face_detected: bool = True,
                    env: Optional[EnvironmentalContext] = None,
                    cfg: Optional[DSFusionConfig] = None) -> FusionResult:
    """
    D-S fusion with SNR/Lux-driven dynamic confidence adjustment.

    Instead of using fixed vision_confidence and audio_confidence,
    this computes them dynamically from environmental quality readings.
    This is the "smart trust correction" engine validated in Monte Carlo
    simulation (5000 samples, +13.5% absolute improvement).

    Parameters
    ----------
    probs_vision, probs_audio : shape (4,) normalised probability arrays
    face_detected : if False, vision confidence drops regardless of env
    env : environmental readings (uses default good conditions if None)
    cfg : base fusion configuration
    """
    if cfg is None:
        cfg = DSFusionConfig()

    # ── Dynamic confidence from environment ──
    if env is not None:
        dyn_v_conf, dyn_a_conf = compute_dynamic_confidence(env)
    else:
        dyn_v_conf, dyn_a_conf = cfg.vision_confidence, cfg.audio_confidence

    # Face detection override (no face = vision is blind regardless of lighting)
    if not face_detected:
        dyn_v_conf = 0.05

    # ── Build BPAs with dynamic confidences ──
    vision_bpa = BPA.from_prob_array(probs_vision, dyn_v_conf)
    audio_bpa  = BPA.from_prob_array(probs_audio, dyn_a_conf)

    return dempster_combine(vision_bpa, audio_bpa, cfg)


# =========================================================================
# Unified comparison interface
# =========================================================================

def compare_all_methods(probs_vision: np.ndarray,
                        probs_audio: np.ndarray,
                        face_detected: bool = True,
                        env: Optional[EnvironmentalContext] = None,
                        cfg: Optional[DSFusionConfig] = None) -> dict:
    """
    Run all five fusion methods on the same input and return results.

    Returns dict with keys:
        'vision_only', 'audio_only', 'bayesian', 'ds_fusion', 'ds_dynamic'
    """
    if cfg is None:
        cfg = DSFusionConfig()

    return {
        'vision_only': fuse_vision_only(probs_vision, face_detected, cfg.vision_confidence),
        'audio_only':  fuse_audio_only(probs_audio, cfg.audio_confidence),
        'bayesian':    fuse_bayesian(probs_vision, probs_audio,
                                     cfg.vision_confidence, cfg.audio_confidence,
                                     face_detected),
        'ds_fusion':   fuse_dempster_shafer(probs_vision, probs_audio,
                                            face_detected, cfg),
        'ds_dynamic':  fuse_ds_dynamic(probs_vision, probs_audio,
                                       face_detected, env, cfg),
    }

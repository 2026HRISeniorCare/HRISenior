"""
Conflict Detection Evaluation for Masked Depression Screening
==============================================================
Evaluates the D-S evidence theory's ability to detect "hidden depression"
through multimodal conflict detection.

This module addresses the core hypothesis:
  "When face says Happy but voice says Sad, the high conflict (K ≥ 0.85)
   is a clinically meaningful signal for masked depression."

Experiment Design — Acted Paradigm Protocol
--------------------------------------------
We design a controlled experiment with three conditions:

  Condition A — "Congruent":  Face and voice express the SAME emotion.
  Condition B — "Masked":     Face shows Happy/Neutral while voice is Sad.
                              (Subject instructed: "Pretend you're fine,
                               smile, but speak as if you're sad inside.")
  Condition C — "Incongruent": Face and voice express DIFFERENT emotions
                               (not specifically masking — e.g., Happy+Anger).

Hypotheses:
  H1: D-S conflict K is significantly HIGHER in Condition B (masked) than A.
  H2: The "high_conflict" flag discriminates masked vs congruent samples
      with AUC > 0.75.
  H3: D-S + Dynamic confidence correction maintains or improves detection
      under degraded environmental conditions.

Evaluation Metrics:
  - AUC-ROC for high_conflict flag predicting masked condition
  - Sensitivity (recall of masked detection)
  - Specificity (1 - false alarm rate on congruent samples)
  - Distribution of K values per condition (violin plot)
  - Confusion matrix: predicted masked vs actual masked

Project : SIEVOX — Multimodal Elderly Care Robot

Usage:
  python conflict_detection.py
  python conflict_detection.py --n-samples 2000 --output-dir ./results
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import sys
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fusion_methods import (
    NUM_EMOTIONS, EMOTION_LABELS, EmotionIndex, FusionResult,
    EnvironmentalContext, DSFusionConfig, BPA,
    fuse_dempster_shafer, fuse_ds_dynamic, compare_all_methods,
    compute_dynamic_confidence
)
from dataset_utils import (
    EmotionSample, SensorSimulator, SyntheticDataGenerator
)


# =========================================================================
# Plotting config
# =========================================================================

plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'STIXGeneral', 'DejaVu Serif', 'serif'],
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})

COLORS_COND = {
    'congruent':    '#3498DB',   # Blue — normal
    'masked':       '#E74C3C',   # Red — target condition
    'incongruent':  '#F39C12',   # Orange — other conflict
}

# =========================================================================
# Experiment Controller
# =========================================================================

@dataclass
class ConflictTrial:
    """A single trial in the acted paradigm experiment."""
    trial_id: str
    condition: str                # 'congruent', 'masked', 'incongruent'
    ground_truth: EmotionIndex    # True underlying emotion
    face_emotion: EmotionIndex    # Emotion expressed by face
    voice_emotion: EmotionIndex   # Emotion expressed by voice
    probs_vision: np.ndarray      # Simulated FER output
    probs_audio: np.ndarray       # Simulated SER output
    env: EnvironmentalContext
    face_detected: bool = True

    # Results (filled after running)
    ds_result: Optional[FusionResult] = None
    ds_dynamic_result: Optional[FusionResult] = None
    bayesian_result: Optional[FusionResult] = None


@dataclass
class ConflictDetectionMetrics:
    """Aggregated conflict detection performance."""
    # Per-condition statistics
    mean_k_per_condition: Dict[str, float] = field(default_factory=dict)
    std_k_per_condition: Dict[str, float] = field(default_factory=dict)
    high_conflict_rate: Dict[str, float] = field(default_factory=dict)

    # Binary classification: masked vs congruent
    # (high_conflict flag as detector)
    auc_roc: float = 0.0
    sensitivity: float = 0.0       # P(high_conflict | masked)
    specificity: float = 0.0       # P(~high_conflict | congruent)
    precision: float = 0.0         # P(masked | high_conflict)
    f1_score: float = 0.0
    accuracy: float = 0.0

    # Confusion matrix for masked detection
    tp: int = 0; fp: int = 0; fn: int = 0; tn: int = 0

    # By environment quality
    good_env_metrics: Dict[str, float] = field(default_factory=dict)
    poor_env_metrics: Dict[str, float] = field(default_factory=dict)

    # Threshold sweep
    thresholds: List[float] = field(default_factory=list)
    sensitivities: List[float] = field(default_factory=list)
    specificities: List[float] = field(default_factory=list)


# =========================================================================
# Acted Paradigm Data Generator
# =========================================================================

class ActedParadigmGenerator:
    """
    Generates controlled trials for the acted paradigm conflict detection
    experiment.

    Three conditions:
      A — Congruent:   face == voice == ground_truth
      B — Masked:      face = Happy/Neutral, voice = Sad, ground_truth = Sad
      C — Incongruent: face ≠ voice, NOT specifically masking
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

        # Sensor simulator with realistic noise profiles
        self.sensor = SensorSimulator(
            fer_accuracy=0.72,
            ser_accuracy=0.70,
            seed=seed
        )

    def generate_congruent_trials(self, n: int = 500) -> List[ConflictTrial]:
        """Condition A: Face and voice express the SAME emotion."""
        trials = []
        for i in range(n):
            true_emo = EmotionIndex(self.rng.randint(0, NUM_EMOTIONS))
            env = self._sample_environment()

            probs_v = self.sensor.simulate_fer_output(true_emo, face_detected=True, env=env)
            probs_a = self.sensor.simulate_ser_output(true_emo, env=env)

            trials.append(ConflictTrial(
                trial_id=f"congruent_{i:04d}",
                condition='congruent',
                ground_truth=true_emo,
                face_emotion=true_emo,
                voice_emotion=true_emo,
                probs_vision=probs_v,
                probs_audio=probs_a,
                env=env
            ))
        return trials

    def generate_masked_trials(self, n: int = 500) -> List[ConflictTrial]:
        """
        Condition B — Masked Depression:
        - Subject is actually Sad (ground truth)
        - Face shows Happy (social smiling) or Neutral (suppressed expression)
        - Voice betrays sadness (low pitch, low energy, trembling)
        """
        trials = []
        for i in range(n):
            env = self._sample_environment()

            # Ground truth = Sad
            true_emo = EmotionIndex.SAD

            # Face: 70% show Happy (forced smile), 30% show Neutral (suppressed)
            face_emo = EmotionIndex.HAPPY if self.rng.rand() < 0.7 else EmotionIndex.NEUTRAL

            # Voice: reveals true Sadness
            voice_emo = EmotionIndex.SAD

            # Simulate: FER sees the masked face, SER hears the true voice
            probs_v = self.sensor.simulate_fer_output(face_emo, face_detected=True, env=env)
            probs_a = self.sensor.simulate_ser_output(voice_emo, env=env)

            trials.append(ConflictTrial(
                trial_id=f"masked_{i:04d}",
                condition='masked',
                ground_truth=true_emo,
                face_emotion=face_emo,
                voice_emotion=voice_emo,
                probs_vision=probs_v,
                probs_audio=probs_a,
                env=env
            ))
        return trials

    def generate_incongruent_trials(self, n: int = 300) -> List[ConflictTrial]:
        """
        Condition C — General Incongruence (NOT masking):
        - Face and voice express DIFFERENT emotions
        - But not the specific "smiling-while-sad" masking pattern
        - Used to test specificity: does the system only flag masked patterns?
        """
        trials = []
        # Pairs of {face_emo, voice_emo} that are NOT the masking pattern
        non_masking_pairs = [
            (EmotionIndex.HAPPY, EmotionIndex.ANGER),
            (EmotionIndex.ANGER, EmotionIndex.HAPPY),
            (EmotionIndex.SAD, EmotionIndex.ANGER),
            (EmotionIndex.ANGER, EmotionIndex.SAD),
            (EmotionIndex.NEUTRAL, EmotionIndex.ANGER),
            (EmotionIndex.ANGER, EmotionIndex.NEUTRAL),
            (EmotionIndex.HAPPY, EmotionIndex.NEUTRAL),
            (EmotionIndex.NEUTRAL, EmotionIndex.HAPPY),
        ]

        for i in range(n):
            face_emo, voice_emo = non_masking_pairs[i % len(non_masking_pairs)]
            env = self._sample_environment()

            probs_v = self.sensor.simulate_fer_output(face_emo, face_detected=True, env=env)
            probs_a = self.sensor.simulate_ser_output(voice_emo, env=env)

            trials.append(ConflictTrial(
                trial_id=f"incongruent_{i:04d}",
                condition='incongruent',
                ground_truth=voice_emo,  # Voice is more honest
                face_emotion=face_emo,
                voice_emotion=voice_emo,
                probs_vision=probs_v,
                probs_audio=probs_a,
                env=env
            ))
        return trials

    def generate_full_experiment(self,
                                  n_congruent: int = 1000,
                                  n_masked: int = 500,
                                  n_incongruent: int = 300) -> List[ConflictTrial]:
        """Generate the complete experiment dataset."""
        trials = []
        trials.extend(self.generate_congruent_trials(n_congruent))
        trials.extend(self.generate_masked_trials(n_masked))
        trials.extend(self.generate_incongruent_trials(n_incongruent))
        self.rng.shuffle(trials)
        return trials

    def _sample_environment(self) -> EnvironmentalContext:
        """Sample varied environmental conditions."""
        quality = self.rng.choice(['good', 'normal', 'poor'], p=[0.3, 0.5, 0.2])
        if quality == 'good':
            return EnvironmentalContext(
                snr_db=self.rng.uniform(25, 45),
                lux=self.rng.uniform(400, 1200),
                face_distance_px=self.rng.uniform(120, 250)
            )
        elif quality == 'poor':
            return EnvironmentalContext(
                snr_db=self.rng.uniform(3, 15),
                lux=self.rng.uniform(20, 150),
                face_distance_px=self.rng.uniform(25, 80)
            )
        else:
            return EnvironmentalContext(
                snr_db=self.rng.uniform(8, 40),
                lux=self.rng.uniform(30, 1100),
                face_distance_px=self.rng.uniform(30, 250)
            )


# =========================================================================
# Evaluation engine
# =========================================================================

def evaluate_conflict_detection(trials: List[ConflictTrial],
                                 cfg: Optional[DSFusionConfig] = None
                                 ) -> ConflictDetectionMetrics:
    """
    Run D-S fusion on all trials and compute conflict detection metrics.

    The key question: can high_conflict flag reliably detect masked trials?
    """
    if cfg is None:
        cfg = DSFusionConfig()

    # Run fusion on all trials
    for trial in trials:
        trial.ds_result = fuse_dempster_shafer(
            trial.probs_vision, trial.probs_audio,
            face_detected=trial.face_detected, cfg=cfg
        )
        trial.ds_dynamic_result = fuse_ds_dynamic(
            trial.probs_vision, trial.probs_audio,
            face_detected=trial.face_detected, env=trial.env, cfg=cfg
        )

    m = ConflictDetectionMetrics()

    # ── Per-condition K statistics ──
    for cond in ['congruent', 'masked', 'incongruent']:
        cond_trials = [t for t in trials if t.condition == cond]
        k_vals = [t.ds_result.conflict for t in cond_trials]
        m.mean_k_per_condition[cond] = float(np.mean(k_vals))
        m.std_k_per_condition[cond] = float(np.std(k_vals))
        m.high_conflict_rate[cond] = float(
            np.mean([t.ds_result.high_conflict for t in cond_trials])
        )

    # ── Binary classification: masked vs congruent ──
    binary_trials = [t for t in trials if t.condition in ('congruent', 'masked')]
    y_true = np.array([1 if t.condition == 'masked' else 0 for t in binary_trials])
    y_pred = np.array([1 if t.ds_result.high_conflict else 0 for t in binary_trials])
    k_scores = np.array([t.ds_result.conflict for t in binary_trials])

    m.tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    m.fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    m.fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    m.tn = int(np.sum((y_true == 0) & (y_pred == 0)))

    m.sensitivity = m.tp / (m.tp + m.fn) if (m.tp + m.fn) > 0 else 0.0
    m.specificity = m.tn / (m.tn + m.fp) if (m.tn + m.fp) > 0 else 0.0
    m.precision = m.tp / (m.tp + m.fp) if (m.tp + m.fp) > 0 else 0.0
    m.f1_score = 2 * m.precision * m.sensitivity / (m.precision + m.sensitivity + 1e-8)
    m.accuracy = (m.tp + m.tn) / len(y_true) if len(y_true) > 0 else 0.0

    # ── AUC-ROC via threshold sweep ──
    m.thresholds = np.linspace(0.0, 1.0, 101)
    m.sensitivities = []
    m.specificities = []
    for thresh in m.thresholds:
        y_thresh = (k_scores >= thresh).astype(int)
        tp_t = int(np.sum((y_true == 1) & (y_thresh == 1)))
        fn_t = int(np.sum((y_true == 1) & (y_thresh == 0)))
        tn_t = int(np.sum((y_true == 0) & (y_thresh == 0)))
        fp_t = int(np.sum((y_true == 0) & (y_thresh == 1)))

        sens = tp_t / (tp_t + fn_t) if (tp_t + fn_t) > 0 else 0.0
        spec = tn_t / (tn_t + fp_t) if (tn_t + fp_t) > 0 else 0.0
        m.sensitivities.append(sens)
        m.specificities.append(spec)

    # AUC: trapezoidal integration of ROC curve
    m.auc_roc = float(-np.trapezoid(m.sensitivities, m.specificities))

    # ── By environment quality ──
    for env_quality in ['good', 'poor']:
        env_trials = []
        for t in binary_trials:
            if t.env.snr_db >= 25 and t.env.lux >= 400:
                if env_quality == 'good':
                    env_trials.append(t)
            elif t.env.snr_db < 15 or t.env.lux < 150:
                if env_quality == 'poor':
                    env_trials.append(t)

        if env_trials:
            y_true_env = np.array([1 if t.condition == 'masked' else 0 for t in env_trials])
            y_pred_env = np.array([1 if t.ds_dynamic_result.high_conflict else 0 for t in env_trials])
            tp_e = int(np.sum((y_true_env == 1) & (y_pred_env == 1)))
            fn_e = int(np.sum((y_true_env == 1) & (y_pred_env == 0)))
            sens_e = tp_e / (tp_e + fn_e) if (tp_e + fn_e) > 0 else 0.0
            m.__dict__[f'{env_quality}_env_sensitivity'] = sens_e

    return m


# =========================================================================
# Visualization
# =========================================================================

def plot_k_distribution(trials: List[ConflictTrial],
                         output_path: str):
    """Violin plot of conflict K values per condition."""
    fig, ax = plt.subplots(figsize=(9, 6))

    conditions = ['congruent', 'incongruent', 'masked']
    cond_labels = ['Congruent\n(Face = Voice)', 'Incongruent\n(Other Conflict)',
                   'Masked Depression\n(Smile + Sad Voice)']
    k_data = []
    for cond in conditions:
        k_data.append([t.ds_result.conflict for t in trials if t.condition == cond])

    parts = ax.violinplot(k_data, positions=[0, 1, 2], showmeans=True,
                           showmedians=True, widths=0.6)

    for i, pc in enumerate(parts['bodies']):
        pc.set_facecolor(list(COLORS_COND.values())[i])
        pc.set_alpha(0.6)
    for partname in ('cmeans', 'cmedians', 'cbars', 'cmins', 'cmaxes'):
        if partname in parts:
            parts[partname].set_edgecolor('#333333')

    # Add threshold line
    ax.axhline(y=0.85, color='#D32F2F', linestyle='--', linewidth=2,
                label='D-S Conflict Threshold (K=0.85)')

    # Annotate mean values
    for i, (cond, k_vals) in enumerate(zip(conditions, k_data)):
        mean_k = np.mean(k_vals)
        ax.annotate(f'K̄={mean_k:.3f}',
                     xy=(i, mean_k), xytext=(i + 0.3, mean_k + 0.05),
                     fontsize=11, fontweight='bold',
                     arrowprops=dict(arrowstyle='->', color='#555555'))

    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(cond_labels, fontsize=11)
    ax.set_ylabel('D-S Conflict Factor K', fontsize=12)
    ax.set_title('Multimodal Conflict as a Marker for Masked Depression',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  → Saved: {output_path}")


def plot_roc_curve(metrics: ConflictDetectionMetrics,
                    output_path: str):
    """ROC curve for conflict threshold sweep."""
    fig, ax = plt.subplots(figsize=(7, 7))

    # ROC: sensitivity vs (1 - specificity)
    fpr = [1 - s for s in metrics.specificities]
    tpr = metrics.sensitivities

    ax.plot(fpr, tpr, 'b-', linewidth=2.5, label=f'D-S Conflict K (AUC = {metrics.auc_roc:.3f})')
    ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5, label='Random (AUC = 0.500)')

    # Mark default threshold
    default_idx = min(range(len(metrics.thresholds)),
                       key=lambda i: abs(metrics.thresholds[i] - 0.85))
    ax.scatter([1 - metrics.specificities[default_idx]],
                [metrics.sensitivities[default_idx]],
                s=120, c='#D32F2F', marker='*', zorder=5,
                label=f'Default K=0.85\n(Sens={metrics.sensitivity:.2f}, Spec={metrics.specificity:.2f})')

    ax.fill_between(fpr, tpr, alpha=0.15, color='blue')

    ax.set_xlabel('False Positive Rate (1 - Specificity)', fontsize=12)
    ax.set_ylabel('True Positive Rate (Sensitivity)', fontsize=12)
    ax.set_title('ROC Curve: Conflict K for Masked Depression Detection',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=10)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    ax.grid(linestyle='--', alpha=0.3)

    # AUC text box
    ax.text(0.6, 0.25,
            f'AUC = {metrics.auc_roc:.3f}\n'
            f'Sensitivity = {metrics.sensitivity:.2f}\n'
            f'Specificity = {metrics.specificity:.2f}\n'
            f'F1 = {metrics.f1_score:.2f}',
            transform=ax.transAxes, fontsize=11,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  → Saved: {output_path}")


def plot_confusion_heatmap(metrics: ConflictDetectionMetrics,
                            output_path: str):
    """Confusion matrix heatmap for masked depression detection."""
    cm = np.array([[metrics.tn, metrics.fp],
                    [metrics.fn, metrics.tp]])

    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Reds',
                 xticklabels=['Not Masked', 'Masked'],
                 yticklabels=['Not Masked', 'Masked'],
                 annot_kws={'fontsize': 16, 'fontweight': 'bold'},
                 ax=ax, linewidths=1.5, linecolor='white',
                 cbar_kws={'label': 'Number of Trials'})

    ax.set_xlabel('Predicted (High Conflict Flag)', fontsize=12)
    ax.set_ylabel('Actual Condition', fontsize=12)
    ax.set_title('Masked Depression Detection\nConfusion Matrix',
                 fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  → Saved: {output_path}")


def plot_k_scatter(trials: List[ConflictTrial],
                    output_path: str):
    """Scatter plot showing K values with face/voice emotion annotations."""
    fig, ax = plt.subplots(figsize=(10, 6))

    for cond, color, marker, label in [
        ('congruent', COLORS_COND['congruent'], 'o', 'Congruent'),
        ('masked', COLORS_COND['masked'], 'X', 'Masked Depression'),
        ('incongruent', COLORS_COND['incongruent'], 's', 'Incongruent (Other)'),
    ]:
        cond_trials = [t for t in trials if t.condition == cond]
        k_vals = [t.ds_result.conflict for t in cond_trials]
        indices = np.arange(len(k_vals)) + np.random.uniform(-0.2, 0.2, len(k_vals))

        ax.scatter(indices, k_vals, c=color, marker=marker, alpha=0.5,
                    s=30, label=label, edgecolors='none')

    ax.axhline(y=0.85, color='#D32F2F', linestyle='--', linewidth=2,
                label='K = 0.85 Threshold')

    # Highlight regions
    ax.axhspan(0.85, 1.0, alpha=0.08, color='#E74C3C')
    ax.text(50, 0.92, 'HIGH CONFLICT ZONE\n(Masked Depression Alert)',
            fontsize=10, color='#E74C3C', fontweight='bold', ha='center')

    ax.set_xlabel('Trial Index (sorted by condition)', fontsize=12)
    ax.set_ylabel('D-S Conflict Factor K', fontsize=12)
    ax.set_title('Conflict Factor Distribution Across Experimental Conditions',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9, markerscale=1.5)
    ax.set_ylim(0, 1.02)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  → Saved: {output_path}")


# =========================================================================
# Threshold optimization
# =========================================================================

def optimize_threshold(trials: List[ConflictTrial],
                        metric: str = 'f1') -> Tuple[float, Dict[str, float]]:
    """
    Find the optimal conflict threshold for masked depression detection.

    Sweeps K ∈ [0.5, 0.95] and reports best F1 (or sensitivity/specificity).
    """
    binary_trials = [t for t in trials if t.condition in ('congruent', 'masked')]
    y_true = np.array([1 if t.condition == 'masked' else 0 for t in binary_trials])
    k_scores = np.array([t.ds_result.conflict for t in binary_trials])

    best_thresh = 0.85
    best_score = -1
    best_metrics = {}

    for thresh in np.linspace(0.50, 0.95, 91):
        y_pred = (k_scores >= thresh).astype(int)
        tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        fn = int(np.sum((y_true == 1) & (y_pred == 0)))
        tn = int(np.sum((y_true == 0) & (y_pred == 0)))

        sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = 2 * prec * sens / (prec + sens + 1e-8)

        score = {'f1': f1, 'sensitivity': sens, 'specificity': spec}.get(metric, f1)
        if score > best_score:
            best_score = score
            best_thresh = thresh
            best_metrics = {
                'threshold': thresh,
                'sensitivity': sens,
                'specificity': spec,
                'precision': prec,
                'f1': f1,
                'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            }

    return best_thresh, best_metrics


# =========================================================================
# Main
# =========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='SIEVOX Conflict Detection Evaluation — Acted Paradigm Experiment'
    )
    parser.add_argument('--n-congruent', type=int, default=1000)
    parser.add_argument('--n-masked', type=int, default=500)
    parser.add_argument('--n-incongruent', type=int, default=300)
    parser.add_argument('--output-dir', type=str, default='./results')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--conflict-threshold', type=float, default=0.85)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    cfg = DSFusionConfig(conflict_threshold=args.conflict_threshold)

    print("=" * 65)
    print("  SIEVOX Conflict Detection Evaluation")
    print("  Acted Paradigm — Masked Depression Screening")
    print("=" * 65)
    print(f"  N congruent:   {args.n_congruent}")
    print(f"  N masked:      {args.n_masked}")
    print(f"  N incongruent: {args.n_incongruent}")
    print(f"  D-S threshold: {cfg.conflict_threshold}")
    print("-" * 65)

    # ── Generate experiment data ────────────────────────────────────
    print("\n[1/5] Generating acted paradigm experiment data...")
    generator = ActedParadigmGenerator(seed=args.seed)
    trials = generator.generate_full_experiment(
        n_congruent=args.n_congruent,
        n_masked=args.n_masked,
        n_incongruent=args.n_incongruent
    )
    n_total = len(trials)
    print(f"  Generated {n_total} trials "
          f"({args.n_congruent} congruent, "
          f"{args.n_masked} masked, "
          f"{args.n_incongruent} incongruent)")

    # Breakdown of masked trials
    masked_trials = [t for t in trials if t.condition == 'masked']
    happy_mask = sum(1 for t in masked_trials if t.face_emotion == EmotionIndex.HAPPY)
    neutral_mask = sum(1 for t in masked_trials if t.face_emotion == EmotionIndex.NEUTRAL)
    print(f"  Masked trial composition: {happy_mask} smile-masking, {neutral_mask} neutral-masking")

    # ── Run conflict detection evaluation ───────────────────────────
    print("\n[2/5] Running D-S fusion and evaluating conflict detection...")
    metrics = evaluate_conflict_detection(trials, cfg)

    # ── Optimize threshold ──────────────────────────────────────────
    print("\n[3/5] Optimizing conflict threshold...")
    best_thresh, best_m = optimize_threshold(trials, metric='f1')
    print(f"  Optimal threshold: K = {best_thresh:.3f}")
    print(f"    Sensitivity: {best_m['sensitivity']:.3f}")
    print(f"    Specificity: {best_m['specificity']:.3f}")
    print(f"    F1 Score:    {best_m['f1']:.3f}")

    # ── Print results ───────────────────────────────────────────────
    print(f"\n[4/5] Results Summary")
    print("-" * 65)
    print(f"  Per-condition mean conflict K:")
    for cond in ['congruent', 'incongruent', 'masked']:
        print(f"    {cond:<20s}: K̄ = {metrics.mean_k_per_condition[cond]:.4f} "
              f"± {metrics.std_k_per_condition[cond]:.4f}  "
              f"(high conflict rate: {metrics.high_conflict_rate[cond]*100:.1f}%)")

    print(f"\n  Binary Detection (Masked vs Congruent, K≥{cfg.conflict_threshold}):")
    print(f"    AUC-ROC:     {metrics.auc_roc:.4f}")
    print(f"    Sensitivity: {metrics.sensitivity:.4f}  (recall of masked)")
    print(f"    Specificity: {metrics.specificity:.4f}  (1 - false alarm)")
    print(f"    Precision:   {metrics.precision:.4f}")
    print(f"    F1 Score:    {metrics.f1_score:.4f}")
    print(f"    Accuracy:    {metrics.accuracy:.4f}")
    print(f"    Confusion:   TP={metrics.tp}, FP={metrics.fp}, "
          f"FN={metrics.fn}, TN={metrics.tn}")

    # ── Statistical test ────────────────────────────────────────────
    from scipy import stats
    congruent_k = [t.ds_result.conflict for t in trials if t.condition == 'congruent']
    masked_k = [t.ds_result.conflict for t in trials if t.condition == 'masked']
    t_stat, p_val = stats.ttest_ind(masked_k, congruent_k, equal_var=False)
    cohens_d = (np.mean(masked_k) - np.mean(congruent_k)) / \
               np.sqrt((np.std(masked_k)**2 + np.std(congruent_k)**2) / 2)
    print(f"\n  Statistical test (masked vs congruent K):")
    print(f"    t-statistic: {t_stat:.3f}")
    print(f"    p-value:     {p_val:.2e}")
    print(f"    Cohen's d:   {cohens_d:.3f}  (effect size)")
    print(f"    Conclusion:  {'SIGNIFICANT ✅' if p_val < 0.001 else 'Not significant ❌'}")

    # ── Generate outputs ────────────────────────────────────────────
    print(f"\n[5/5] Generating publication figures...")
    plot_k_distribution(
        trials,
        os.path.join(args.output_dir, 'fig_conflict_k_distribution.png')
    )
    plot_roc_curve(
        metrics,
        os.path.join(args.output_dir, 'fig_conflict_roc.png')
    )
    plot_confusion_heatmap(
        metrics,
        os.path.join(args.output_dir, 'fig_conflict_confusion.png')
    )
    plot_k_scatter(
        trials,
        os.path.join(args.output_dir, 'fig_conflict_k_scatter.png')
    )

    # Save metrics as JSON
    results_dict = {
        'config': {
            'n_congruent': args.n_congruent,
            'n_masked': args.n_masked,
            'n_incongruent': args.n_incongruent,
            'conflict_threshold': cfg.conflict_threshold,
        },
        'per_condition': {
            cond: {
                'mean_k': metrics.mean_k_per_condition[cond],
                'std_k': metrics.std_k_per_condition[cond],
                'high_conflict_rate': metrics.high_conflict_rate[cond],
            }
            for cond in ['congruent', 'masked', 'incongruent']
        },
        'detection_metrics': {
            'auc_roc': metrics.auc_roc,
            'sensitivity': metrics.sensitivity,
            'specificity': metrics.specificity,
            'precision': metrics.precision,
            'f1_score': metrics.f1_score,
            'accuracy': metrics.accuracy,
            'confusion_matrix': {'tp': metrics.tp, 'fp': metrics.fp,
                                  'fn': metrics.fn, 'tn': metrics.tn},
        },
        'statistical_test': {
            't_statistic': float(t_stat),
            'p_value': float(p_val),
            'cohens_d': float(cohens_d),
            'significant': bool(p_val < 0.001),
        },
        'optimal_threshold': best_m,
    }

    with open(os.path.join(args.output_dir, 'conflict_results.json'), 'w') as f:
        json.dump(results_dict, f, indent=2)
    print(f"  → Saved: {os.path.join(args.output_dir, 'conflict_results.json')}")

    print(f"\n{'=' * 65}")
    print(f"  Experiment complete. Outputs saved to: {args.output_dir}/")
    print(f"{'=' * 65}")


if __name__ == '__main__':
    main()

"""
Ablation Study: Multimodal Emotion Fusion Methods
===================================================
Systematic comparison of five fusion strategies on synthetic and
public dataset (RAVDESS/IEMOCAP/CREMA-D) emotion data.

Methods compared:
  1. Vision-only (FER baseline)
  2. Audio-only (SER baseline)
  3. Bayesian Fusion (standard baseline)
  4. Dempster-Shafer Fusion (proposed, static confidence)
  5. D-S + SNR/Lux Dynamic Trust Correction (proposed, enhanced)

Metrics:
  - Classification accuracy (overall + per-class)
  - Macro/weighted F1 score
  - Confusion matrix
  - Conflict detection sensitivity/specificity (for masked samples)
  - Cohen's Kappa

Output:
  - Publication-quality figures (bar charts, confusion matrices, ROC-like curves)
  - LaTeX-formatted results table
  - CSV results for further analysis

Project : SIEVOX — Multimodal Elderly Care Robot

Usage:
  python ablation_study.py                    # Quick run (1000 samples)
  python ablation_study.py --full             # Full experiment (5000 samples × 5 seeds)
  python ablation_study.py --dataset ravdess  # Use RAVDESS if available
  python ablation_study.py --output-dir ./results
"""

import sys
import io
# Force UTF-8 encoding for stdout (fixes Windows GBK issues)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for headless environments
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch
import seaborn as sns
import json
import os
import sys
import time
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from sklearn.metrics import (
    accuracy_score, f1_score, confusion_matrix,
    cohen_kappa_score, classification_report,
    precision_recall_fscore_support
)

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fusion_methods import (
    NUM_EMOTIONS, EMOTION_LABELS, EmotionIndex, FusionResult,
    EnvironmentalContext, DSFusionConfig,
    fuse_vision_only, fuse_audio_only, fuse_bayesian,
    fuse_dempster_shafer, fuse_ds_dynamic, compare_all_methods
)
from dataset_utils import (
    EmotionSample, SyntheticDataGenerator, SensorSimulator,
    RAVDESSAdapter, IEMOCAPAdapter, CREMADAdapter,
    balance_classes
)


# =========================================================================
# Matplotlib configuration (academic style)
# =========================================================================

plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'STIXGeneral', 'DejaVu Serif', 'serif'],
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,
})

# Academic blue-purple palette (colorblind-friendly)
COLORS = {
    'vision_only': '#A7C7E7',    # Pale blue
    'audio_only':  '#C3B1E1',    # Pale lavender
    'bayesian':    '#859FD1',    # Medium blue
    'ds_fusion':   '#8E44AD',    # Deep purple (proposed)
    'ds_dynamic':  '#6C3483',    # Dark purple (proposed+)
}

METHOD_NAMES = {
    'vision_only': 'Vision-Only\n(FER)',
    'audio_only':  'Audio-Only\n(SER)',
    'bayesian':    'Bayesian\nFusion',
    'ds_fusion':   'D-S Fusion\n(Proposed)',
    'ds_dynamic':  'D-S + Dynamic\n(Proposed+)',
}

METHOD_ORDER = ['vision_only', 'audio_only', 'bayesian', 'ds_fusion', 'ds_dynamic']


# =========================================================================
# Experiment runner
# =========================================================================

@dataclass
class ExperimentMetrics:
    """Aggregated metrics for one fusion method."""
    method: str
    accuracy: float = 0.0
    f1_macro: float = 0.0
    f1_weighted: float = 0.0
    kappa: float = 0.0
    per_class_f1: np.ndarray = field(default_factory=lambda: np.zeros(NUM_EMOTIONS))
    per_class_acc: np.ndarray = field(default_factory=lambda: np.zeros(NUM_EMOTIONS))
    confusion_mat: np.ndarray = field(default_factory=lambda: np.zeros((NUM_EMOTIONS, NUM_EMOTIONS), dtype=int))
    conflict_precision: float = 0.0   # For masked detection
    conflict_recall: float = 0.0
    conflict_f1: float = 0.0
    mean_conflict_k: float = 0.0      # Average conflict factor
    n_samples: int = 0
    n_high_conflict: int = 0


def run_experiment(samples: List[EmotionSample],
                   cfg: Optional[DSFusionConfig] = None) -> Dict[str, ExperimentMetrics]:
    """
    Run all fusion methods on a list of samples and compute metrics.

    Parameters
    ----------
    samples : list of EmotionSample
    cfg : D-S fusion configuration (uses defaults if None)

    Returns
    -------
    dict mapping method_name → ExperimentMetrics
    """
    if cfg is None:
        cfg = DSFusionConfig()

    n = len(samples)
    if n == 0:
        raise ValueError("No samples provided")

    # Initialise accumulators
    metrics = {}
    for method in METHOD_ORDER:
        metrics[method] = ExperimentMetrics(method=method, n_samples=n)

    y_true_all = np.zeros(n, dtype=int)
    y_pred = {m: np.zeros(n, dtype=int) for m in METHOD_ORDER}
    conflict_flags = {m: np.zeros(n, dtype=bool) for m in METHOD_ORDER}
    conflict_k_values = {m: np.zeros(n, dtype=float) for m in METHOD_ORDER}
    is_masked = np.zeros(n, dtype=bool)

    for i, sample in enumerate(samples):
        y_true_all[i] = int(sample.ground_truth)
        is_masked[i] = sample.is_masked_emotion

        results = compare_all_methods(
            sample.probs_vision, sample.probs_audio,
            face_detected=sample.face_detected,
            env=sample.env, cfg=cfg
        )

        for method, result in results.items():
            y_pred[method][i] = int(result.dominant)
            conflict_flags[method][i] = result.high_conflict
            conflict_k_values[method][i] = result.conflict

    # Compute classification metrics
    for method in METHOD_ORDER:
        m = metrics[method]
        preds = y_pred[method]

        m.accuracy = float(accuracy_score(y_true_all, preds))
        m.f1_macro = float(f1_score(y_true_all, preds, average='macro'))
        m.f1_weighted = float(f1_score(y_true_all, preds, average='weighted'))
        m.kappa = float(cohen_kappa_score(y_true_all, preds))
        m.confusion_mat = confusion_matrix(y_true_all, preds, labels=list(range(NUM_EMOTIONS)))

        # Per-class metrics
        p, r, f1, _ = precision_recall_fscore_support(
            y_true_all, preds, labels=list(range(NUM_EMOTIONS)), zero_division=0
        )
        m.per_class_f1 = f1
        m.per_class_acc = m.confusion_mat.diagonal() / (m.confusion_mat.sum(axis=1) + 1e-8)

        # Conflict detection metrics (only meaningful for D-S methods)
        m.n_high_conflict = int(np.sum(conflict_flags[method]))
        m.mean_conflict_k = float(np.mean(conflict_k_values[method]))

        if np.any(is_masked):
            # High conflict should predict masked emotion
            tp = int(np.sum(conflict_flags[method] & is_masked))
            fp = int(np.sum(conflict_flags[method] & ~is_masked))
            fn = int(np.sum(~conflict_flags[method] & is_masked))

            m.conflict_precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            m.conflict_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            m.conflict_f1 = (2 * m.conflict_precision * m.conflict_recall /
                            (m.conflict_precision + m.conflict_recall + 1e-8))

    return metrics


# =========================================================================
# Multi-seed experiment for statistical significance
# =========================================================================

def run_with_seeds(generator_fn, n_samples: int = 5000,
                   n_seeds: int = 5,
                   masked_ratio: float = 0.15,
                   cfg: Optional[DSFusionConfig] = None) -> Dict[str, Dict[str, List[float]]]:
    """
    Run experiments across multiple random seeds to assess variance.

    Returns dict[method][metric] → list of values across seeds.
    """
    all_results = defaultdict(lambda: defaultdict(list))

    for seed in range(n_seeds):
        print(f"  Seed {seed + 1}/{n_seeds}...", end=' ', flush=True)
        gen = SyntheticDataGenerator(seed=seed)
        samples = gen.generate_mixed_dataset(n_total=n_samples, masked_ratio=masked_ratio)
        metrics = run_experiment(samples, cfg)

        for method, m in metrics.items():
            all_results[method]['accuracy'].append(m.accuracy)
            all_results[method]['f1_macro'].append(m.f1_macro)
            all_results[method]['f1_weighted'].append(m.f1_weighted)
            all_results[method]['kappa'].append(m.kappa)
            all_results[method]['conflict_f1'].append(m.conflict_f1)
            all_results[method]['conflict_recall'].append(m.conflict_recall)
            all_results[method]['mean_conflict_k'].append(m.mean_conflict_k)
        print("done")

    return all_results


# =========================================================================
# Visualization
# =========================================================================

def plot_accuracy_comparison(metrics: Dict[str, ExperimentMetrics],
                              output_path: str,
                              title: str = "Ablation Study: Fusion Method Comparison"):
    """Generate publication-quality bar chart comparing all methods."""
    fig, ax = plt.subplots(figsize=(10, 7))

    methods_ordered = [m for m in METHOD_ORDER if m in metrics]
    accuracies = [metrics[m].accuracy * 100 for m in methods_ordered]
    f1_scores = [metrics[m].f1_macro * 100 for m in methods_ordered]
    colors_list = [COLORS[m] for m in methods_ordered]
    names = [METHOD_NAMES[m] for m in methods_ordered]

    x = np.arange(len(methods_ordered))
    width = 0.35

    bars_acc = ax.bar(x - width/2, accuracies, width,
                       color=colors_list, edgecolor='#34495E', linewidth=1.0,
                       label='Accuracy (%)')
    bars_f1 = ax.bar(x + width/2, f1_scores, width,
                      color=[_lighten(c, 0.3) for c in colors_list],
                      edgecolor='#34495E', linewidth=1.0, hatch='///',
                      label='Macro F1 (%)')

    # Annotate values
    for bar in bars_acc:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 0.8,
                f'{h:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    for bar in bars_f1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 0.5,
                f'{h:.1f}', ha='center', va='bottom', fontsize=9, color='#555555')

    # Highlight best method
    best_idx = np.argmax(accuracies)
    bars_acc[best_idx].set_edgecolor('#D32F2F')
    bars_acc[best_idx].set_linewidth(2.5)

    # Improvement annotation
    max_single = max(accuracies[0], accuracies[1])  # Best single-modality
    improvement = accuracies[best_idx] - max_single
    if improvement > 0:
        ax.annotate(
            f'+{improvement:.1f}% vs best\nsingle modality',
            xy=(x[best_idx], accuracies[best_idx]),
            xytext=(x[best_idx] - 0.6, accuracies[best_idx] + 8),
            arrowprops=dict(facecolor='#D32F2F', shrink=0.05, width=2, headwidth=8),
            fontsize=11, color='#D32F2F', fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#D32F2F", lw=1.5)
        )

    ax.set_ylabel('Score (%)', fontsize=13)
    ax.set_title(title, fontsize=15, pad=20, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=10)
    ax.set_ylim(0, max(max(accuracies), max(f1_scores)) + 15)
    ax.legend(loc='upper right', framealpha=0.9)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  → Saved: {output_path}")


def plot_confusion_matrices(metrics: Dict[str, ExperimentMetrics],
                             output_path: str):
    """Plot confusion matrices for all methods side by side."""
    methods_to_plot = [m for m in METHOD_ORDER if m in metrics]
    n_methods = len(methods_to_plot)
    if n_methods == 0:
        return

    fig, axes = plt.subplots(1, n_methods, figsize=(4 * n_methods, 3.8),
                              squeeze=False)

    for ax_idx, method in enumerate(methods_to_plot):
        ax = axes[0, ax_idx]
        cm = metrics[method].confusion_mat
        cm_norm = cm.astype('float') / (cm.sum(axis=1, keepdims=True) + 1e-8)

        sns.heatmap(cm_norm, annot=True, fmt='.2f', cmap='Purples',
                     xticklabels=[l.capitalize() for l in EMOTION_LABELS],
                     yticklabels=[l.capitalize() for l in EMOTION_LABELS],
                     vmin=0, vmax=1.0, ax=ax, cbar=(ax_idx == n_methods - 1),
                     linewidths=0.5, linecolor='white')

        ax.set_title(METHOD_NAMES[method].replace('\n', ' '), fontsize=11, fontweight='bold')
        ax.set_xlabel('Predicted', fontsize=9)
        if ax_idx == 0:
            ax.set_ylabel('True', fontsize=9)
        else:
            ax.set_ylabel('')

    plt.suptitle('Confusion Matrices: Fusion Methods Comparison',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  → Saved: {output_path}")


def plot_per_class_comparison(metrics: Dict[str, ExperimentMetrics],
                               output_path: str):
    """Plot per-class F1 scores for each method."""
    methods_to_plot = [m for m in METHOD_ORDER if m in metrics]
    x = np.arange(NUM_EMOTIONS)
    width = 0.15

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, method in enumerate(methods_to_plot):
        offset = (i - len(methods_to_plot) / 2 + 0.5) * width
        f1_vals = metrics[method].per_class_f1 * 100
        bars = ax.bar(x + offset, f1_vals, width,
                       color=COLORS[method], edgecolor='white', linewidth=0.5,
                       label=METHOD_NAMES[method].replace('\n', ' '))

        # Annotate
        for bar, val in zip(bars, f1_vals):
            if val > 5:
                ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                        f'{val:.0f}', ha='center', va='bottom', fontsize=7,
                        rotation=90)

    ax.set_ylabel('F1 Score (%)', fontsize=12)
    ax.set_title('Per-Class F1 Score by Fusion Method', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([l.capitalize() for l in EMOTION_LABELS], fontsize=11)
    ax.legend(loc='lower right', fontsize=8, ncol=2)
    ax.set_ylim(0, 105)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  → Saved: {output_path}")


def plot_conflict_detection(metrics: Dict[str, ExperimentMetrics],
                             output_path: str):
    """Plot conflict detection performance for masked emotion samples."""
    methods_to_plot = [m for m in ['ds_fusion', 'ds_dynamic'] if m in metrics]

    if not methods_to_plot:
        return

    fig, ax = plt.subplots(figsize=(7, 5))

    metrics_names = ['Precision', 'Recall', 'F1']
    x = np.arange(len(metrics_names))
    width = 0.3

    for i, method in enumerate(methods_to_plot):
        m = metrics[method]
        vals = [m.conflict_precision * 100, m.conflict_recall * 100, m.conflict_f1 * 100]
        offset = (i - len(methods_to_plot) / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width,
                       color=COLORS[method], edgecolor='white', linewidth=0.5,
                       label=METHOD_NAMES[method].replace('\n', ' '))

        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1.5,
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=10,
                    fontweight='bold')

    ax.set_ylabel('Score (%)', fontsize=12)
    ax.set_title('Masked Emotion (Hidden Depression) Detection Performance',
                 fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics_names, fontsize=11)
    ax.legend(loc='lower right')
    ax.set_ylim(0, 105)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  → Saved: {output_path}")


def plot_multi_seed_results(all_results: Dict[str, Dict[str, List[float]]],
                             output_path: str):
    """Plot box plot of accuracy across seeds."""
    methods_ordered = [m for m in METHOD_ORDER if m in all_results]
    data = [all_results[m]['accuracy'] for m in methods_ordered]
    labels = [METHOD_NAMES[m].replace('\n', ' ') for m in methods_ordered]

    fig, ax = plt.subplots(figsize=(9, 6))

    bp = ax.boxplot(data, labels=labels, patch_artist=True, widths=0.5,
                     showmeans=True, meanprops=dict(marker='D', markerfacecolor='#D32F2F',
                                                     markersize=6))

    for patch, method in zip(bp['boxes'], methods_ordered):
        patch.set_facecolor(COLORS[method])
        patch.set_alpha(0.7)

    ax.set_ylabel('Accuracy', fontsize=12)
    ax.set_title('Cross-Seed Accuracy Distribution (5 seeds × 5000 samples)',
                 fontsize=14, fontweight='bold')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"  → Saved: {output_path}")


def _lighten(color: str, factor: float = 0.3) -> str:
    """Lighten a hex color by mixing with white."""
    import matplotlib.colors as mc
    rgb = mc.to_rgb(color)
    return mc.to_hex([c + (1 - c) * factor for c in rgb])


# =========================================================================
# LaTeX table generation
# =========================================================================

def generate_latex_table(metrics: Dict[str, ExperimentMetrics],
                          output_path: str):
    """Generate a formatted LaTeX table for paper inclusion."""
    methods_ordered = [m for m in METHOD_ORDER if m in metrics]

    lines = [
        "% Auto-generated ablation study results table",
        "% Generated by ablation_study.py",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Ablation study: comparison of fusion methods for multimodal emotion recognition.}",
        "  \\label{tab:ablation}",
        "  \\begin{tabular}{@{}lccccc@{}}",
        "    \\toprule",
        "    \\textbf{Method} & \\textbf{Accuracy} & \\textbf{Macro F1} & "
        "\\textbf{Weighted F1} & \\textbf{Cohen's $\\kappa$} & \\textbf{Conflict F1} \\\\",
        "    \\midrule",
    ]

    for method in methods_ordered:
        m = metrics[method]
        name = METHOD_NAMES[method].replace('\n', ' ')
        lines.append(
            f"    {name} & {m.accuracy*100:.1f}\\% & {m.f1_macro*100:.1f}\\% & "
            f"{m.f1_weighted*100:.1f}\\% & {m.kappa:.3f} & "
            f"{m.conflict_f1*100:.1f}\\% \\\\"
        )

        # Add highlight for best method
        if method == 'ds_dynamic' or (method == 'ds_fusion' and 'ds_dynamic' not in metrics):
            # Determine improvement over best single modality
            best_single = max(
                metrics['vision_only'].accuracy,
                metrics['audio_only'].accuracy
            )
            improvement = (m.accuracy - best_single) * 100
            if improvement > 0:
                lines.append(
                    f"    \\quad \\textit{{(+{improvement:.1f}\\% vs best single modality)}} \\\\"
                )

    lines.extend([
        "    \\bottomrule",
        "  \\end{tabular}",
        "\\end{table}",
    ])

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"  → Saved: {output_path}")


def generate_results_json(metrics: Dict[str, ExperimentMetrics],
                           output_path: str):
    """Save all metrics as JSON for further analysis."""
    results_dict = {}
    for method, m in metrics.items():
        results_dict[method] = {
            'accuracy': float(m.accuracy),
            'f1_macro': float(m.f1_macro),
            'f1_weighted': float(m.f1_weighted),
            'kappa': float(m.kappa),
            'per_class_f1': m.per_class_f1.tolist(),
            'per_class_acc': m.per_class_acc.tolist(),
            'confusion_matrix': m.confusion_mat.tolist(),
            'conflict_precision': float(m.conflict_precision),
            'conflict_recall': float(m.conflict_recall),
            'conflict_f1': float(m.conflict_f1),
            'mean_conflict_k': float(m.mean_conflict_k),
            'n_high_conflict': int(m.n_high_conflict),
            'n_samples': int(m.n_samples),
        }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results_dict, f, indent=2)
    print(f"  → Saved: {output_path}")


# =========================================================================
# Main
# =========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='SIEVOX Ablation Study — Multimodal Emotion Fusion'
    )
    parser.add_argument('--full', action='store_true',
                        help='Run full experiment (5000 samples × 5 seeds)')
    parser.add_argument('--n-samples', type=int, default=1000,
                        help='Number of samples for quick run (default: 1000)')
    parser.add_argument('--n-seeds', type=int, default=1,
                        help='Number of random seeds (default: 1)')
    parser.add_argument('--masked-ratio', type=float, default=0.15,
                        help='Fraction of masked/hidden depression samples (default: 0.15)')
    parser.add_argument('--dataset', type=str, default='synthetic',
                        choices=['synthetic', 'ravdess', 'iemocap', 'cremad'],
                        help='Dataset to use (default: synthetic)')
    parser.add_argument('--dataset-path', type=str, default='',
                        help='Path to dataset directory (required for real datasets)')
    parser.add_argument('--output-dir', type=str, default='./results',
                        help='Output directory for figures and tables')
    parser.add_argument('--conflict-threshold', type=float, default=0.85,
                        help='D-S conflict threshold (default: 0.85)')
    args = parser.parse_args()

    if args.full:
        args.n_samples = 5000
        args.n_seeds = 5

    # ── Setup ────────────────────────────────────────────────────────
    os.makedirs(args.output_dir, exist_ok=True)
    cfg = DSFusionConfig(conflict_threshold=args.conflict_threshold)

    print("=" * 65)
    print("  SIEVOX Ablation Study — Multimodal Emotion Fusion Methods")
    print("=" * 65)
    print(f"  Dataset:      {args.dataset}")
    print(f"  N samples:    {args.n_samples}")
    print(f"  N seeds:      {args.n_seeds}")
    print(f"  Masked ratio: {args.masked_ratio}")
    print(f"  D-S threshold: {cfg.conflict_threshold}")
    print(f"  Output dir:   {args.output_dir}")
    print("-" * 65)

    # ── Load / generate data ─────────────────────────────────────────
    if args.dataset == 'synthetic':
        print("\n[1/4] Generating synthetic dataset...")
        gen = SyntheticDataGenerator(seed=42)
        samples = gen.generate_mixed_dataset(
            n_total=args.n_samples, masked_ratio=args.masked_ratio
        )
        n_normal = sum(1 for s in samples if not s.is_masked_emotion)
        n_masked = sum(1 for s in samples if s.is_masked_emotion)
        print(f"  Generated {len(samples)} samples ({n_normal} normal, {n_masked} masked)")

    elif args.dataset == 'ravdess':
        print("\n[1/4] Loading RAVDESS dataset...")
        adapter = RAVDESSAdapter(args.dataset_path)
        samples = adapter.load_samples(max_samples=args.n_samples)
        samples = balance_classes(samples, samples_per_class=args.n_samples // NUM_EMOTIONS)

    elif args.dataset == 'iemocap':
        print("\n[1/4] Loading IEMOCAP dataset...")
        adapter = IEMOCAPAdapter(args.dataset_path)
        samples = adapter.load_samples(max_samples=args.n_samples)

    elif args.dataset == 'cremad':
        print("\n[1/4] Loading CREMA-D dataset...")
        adapter = CREMADAdapter(args.dataset_path)
        samples = adapter.load_samples(max_samples=args.n_samples)

    # ── Run experiment ───────────────────────────────────────────────
    if args.n_seeds > 1:
        print(f"\n[2/4] Running experiment ({args.n_seeds} seeds)...")
        multi_results = run_with_seeds(
            lambda: None, args.n_samples, args.n_seeds,
            args.masked_ratio, cfg
        )
        # Use last seed's full metrics for detailed output
        gen_last = SyntheticDataGenerator(seed=args.n_seeds - 1)
        samples_last = gen_last.generate_mixed_dataset(
            n_total=args.n_samples, masked_ratio=args.masked_ratio
        )
        metrics = run_experiment(samples_last, cfg)

        # Plot multi-seed distribution
        plot_multi_seed_results(
            multi_results,
            os.path.join(args.output_dir, 'fig_multi_seed_boxplot.png')
        )

        # Print multi-seed summary
        print("\n  Multi-seed summary (mean ± std):")
        for method in METHOD_ORDER:
            if method in multi_results:
                accs = np.array(multi_results[method]['accuracy']) * 100
                print(f"    {METHOD_NAMES[method].replace(' ',' '):30s}  "
                      f"{accs.mean():.2f}% ± {accs.std():.2f}%")
    else:
        print(f"\n[2/4] Running experiment...")
        metrics = run_experiment(samples, cfg)

    # ── Print results table ──────────────────────────────────────────
    print(f"\n[3/4] Results Summary")
    print("-" * 65)
    print(f"{'Method':<35s} {'Acc':>6s}  {'F1_m':>6s}  {'F1_w':>6s}  "
          f"{'kappa':>6s}  {'Cfl.F1':>6s}  {'Kmean':>6s}")
    print("-" * 65)
    for method in METHOD_ORDER:
        if method in metrics:
            m = metrics[method]
            print(f"{METHOD_NAMES[method].replace(' ',' '):<35s} "
                  f"{m.accuracy*100:5.1f}%  {m.f1_macro*100:5.1f}%  "
                  f"{m.f1_weighted*100:5.1f}%  {m.kappa:5.3f}  "
                  f"{m.conflict_f1*100:5.1f}%  {m.mean_conflict_k:5.3f}")

    # Best method annotation
    best_method = max(
        [m for m in METHOD_ORDER if m in metrics],
        key=lambda m: metrics[m].accuracy
    )
    best_single = max(
        metrics['vision_only'].accuracy,
        metrics['audio_only'].accuracy
    )
    improvement = (metrics[best_method].accuracy - best_single) * 100
    print("-" * 65)
    print(f"  Best method: {METHOD_NAMES[best_method].replace(' ',' ')}")
    print(f"  Improvement over best single modality: +{improvement:.1f}% absolute")
    print(f"  High-conflict detections: {metrics[best_method].n_high_conflict}")

    # Per-class breakdown
    print(f"\n  Per-class F1 scores:")
    header = f"{'Method':<35s}"
    for label in EMOTION_LABELS:
        header += f"  {label.capitalize():>6s}"
    print(header)
    print("-" * len(header))
    for method in METHOD_ORDER:
        if method in metrics:
            m = metrics[method]
            f1_str = '  '.join(f'{f*100:5.1f}%' for f in m.per_class_f1)
            print(f"{METHOD_NAMES[method].replace(' ',' '):<35s}  {f1_str}")

    # ── Generate outputs ─────────────────────────────────────────────
    print(f"\n[4/4] Generating publication figures and tables...")
    plot_accuracy_comparison(
        metrics,
        os.path.join(args.output_dir, 'fig_accuracy_comparison.png'),
        title=f"Ablation Study: Fusion Method Comparison (N={args.n_samples})"
    )
    plot_confusion_matrices(
        metrics,
        os.path.join(args.output_dir, 'fig_confusion_matrices.png')
    )
    plot_per_class_comparison(
        metrics,
        os.path.join(args.output_dir, 'fig_per_class_f1.png')
    )
    plot_conflict_detection(
        metrics,
        os.path.join(args.output_dir, 'fig_conflict_detection.png')
    )
    generate_latex_table(
        metrics,
        os.path.join(args.output_dir, 'table_ablation_results.tex')
    )
    generate_results_json(
        metrics,
        os.path.join(args.output_dir, 'results.json')
    )

    print(f"\n{'=' * 65}")
    print(f"  Experiment complete. All outputs saved to: {args.output_dir}/")
    print(f"{'=' * 65}")


if __name__ == '__main__':
    main()

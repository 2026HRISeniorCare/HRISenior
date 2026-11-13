"""
Dataset Utilities for Emotion Recognition Experiments
======================================================
Provides adapters for public multimodal emotion datasets:
  - RAVDESS (Ryerson Audio-Visual Database of Emotional Speech and Song)
  - IEMOCAP (Interactive Emotional Dyadic Motion Capture)
  - CREMA-D (Crowd-sourced Emotional Multimodal Actors Dataset)

Each adapter produces standardised (vision_probs, audio_probs, ground_truth)
triplets for the ablation study.

Also includes a synthetic data generator that simulates the SIEVOX
hardware pipeline (FER on K210, SER on ESP32-S3) with realistic noise.

Project : SIEVOX — Multimodal Elderly Care Robot
"""

import numpy as np
import os
import json
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Iterator
from enum import IntEnum

from fusion_methods import (
    NUM_EMOTIONS, EMOTION_LABELS, EmotionIndex, EnvironmentalContext
)


# =========================================================================
# Emotion mapping: dataset-specific labels → SIEVOX {H, S, N, A}
# =========================================================================

# RAVDESS: 01=neutral, 02=calm, 03=happy, 04=sad, 05=angry, 06=fearful, 07=disgust, 08=surprised
RAVDESS_TO_SIEVOX = {
    1: EmotionIndex.NEUTRAL,   # neutral
    2: EmotionIndex.NEUTRAL,   # calm → neutral
    3: EmotionIndex.HAPPY,     # happy
    4: EmotionIndex.SAD,       # sad
    5: EmotionIndex.ANGER,     # angry
    6: EmotionIndex.SAD,       # fearful → sad (closest)
    7: EmotionIndex.ANGER,     # disgust → anger (closest)
    8: EmotionIndex.HAPPY,     # surprised → happy (closest)
}

# IEMOCAP: ang, hap, sad, neu, exc, fea, sur, dis, fru, oth
IEMOCAP_TO_SIEVOX = {
    'ang': EmotionIndex.ANGER,
    'hap': EmotionIndex.HAPPY,
    'sad': EmotionIndex.SAD,
    'neu': EmotionIndex.NEUTRAL,
    'exc': EmotionIndex.HAPPY,     # excited → happy
    'fea': EmotionIndex.SAD,       # fear → sad
    'sur': EmotionIndex.HAPPY,     # surprise → happy
    'dis': EmotionIndex.ANGER,     # disgust → anger
    'fru': EmotionIndex.SAD,       # frustration → sad
}

# CREMA-D: HAP, SAD, ANG, NEU, FEA, DIS
CREMAD_TO_SIEVOX = {
    'HAP': EmotionIndex.HAPPY,
    'SAD': EmotionIndex.SAD,
    'ANG': EmotionIndex.ANGER,
    'NEU': EmotionIndex.NEUTRAL,
    'FEA': EmotionIndex.SAD,       # fear → sad
    'DIS': EmotionIndex.ANGER,     # disgust → anger
}


# =========================================================================
# Data sample structure
# =========================================================================

@dataclass
class EmotionSample:
    """A single multimodal emotion sample for the ablation study."""
    sample_id: str
    ground_truth: EmotionIndex
    # Simulated sensor outputs (probability vectors over 4 emotions)
    probs_vision: np.ndarray       # shape (4,)
    probs_audio: np.ndarray        # shape (4,)
    # Metadata
    face_detected: bool = True
    env: Optional[EnvironmentalContext] = None
    # Ground truth for conflict detection
    is_masked_emotion: bool = False  # True if face≠voice (acted paradigm)


# =========================================================================
# Realistic Sensor Simulator
# =========================================================================

class SensorSimulator:
    """
    Simulates the SIEVOX hardware pipeline with realistic noise profiles.

    Models:
      - K210 FER: YOLO face detector + MobileNetV2-0.35 classifier
        ~72% accuracy, confused by occlusion, lighting, face angle
      - ESP32-S3 SER: Pitch/RMS/MFCC heuristic
        ~70% accuracy, confused by background noise, speaker variation

    Default accuracy values are conservative estimates based on:
      - MobileNetV2-0.35 on FER2013: ~65-70% (7-class → ~72% mapped to 4-class)
      - Prosodic heuristic on RAVDESS: ~68-72% (4-class)
    """

    def __init__(self,
                 fer_accuracy: float = 0.72,
                 ser_accuracy: float = 0.70,
                 fer_confusion_std: float = 0.12,
                 ser_confusion_std: float = 0.10,
                 seed: int = 42):
        self.fer_acc = fer_accuracy
        self.ser_acc = ser_accuracy
        self.fer_std = fer_confusion_std
        self.ser_std = ser_confusion_std
        self.rng = np.random.RandomState(seed)

        # Confusion pattern: which emotions are most confusable per modality
        # Visual FER: Happy↔Neutral are hardest (both involve smiling)
        #             Sad↔Neutral, Anger↔Happy also confused
        self.fer_confusion = np.array([
            [0.85, 0.02, 0.10, 0.03],   # Happy → [H, S, N, A]
            [0.05, 0.75, 0.15, 0.05],   # Sad
            [0.10, 0.10, 0.70, 0.10],   # Neutral
            [0.08, 0.02, 0.05, 0.85],   # Anger
        ])

        # Audio SER: Sad↔Neutral hardest (both low energy)
        #            Happy↔Anger confused (both high energy)
        self.ser_confusion = np.array([
            [0.80, 0.02, 0.05, 0.13],   # Happy
            [0.02, 0.82, 0.14, 0.02],   # Sad
            [0.05, 0.15, 0.75, 0.05],   # Neutral
            [0.15, 0.02, 0.03, 0.80],   # Anger
        ])

    def simulate_fer_output(self, true_emotion: EmotionIndex,
                            face_detected: bool = True,
                            env: Optional[EnvironmentalContext] = None) -> np.ndarray:
        """
        Simulate K210 FER output given ground truth.

        If face not detected → uniform-like output (no information).
        If environment is dark or face is far → higher confusion.
        """
        if not face_detected:
            # No face → flat output with slight randomness
            probs = np.ones(NUM_EMOTIONS) / NUM_EMOTIONS
            probs += self.rng.normal(0, 0.03, NUM_EMOTIONS)
            return np.abs(probs) / np.sum(np.abs(probs))

        # Base accuracy degrades with poor lighting / face distance
        effective_acc = self.fer_acc
        if env is not None:
            lux_factor = np.clip(env.lux / 500.0, 0.3, 1.0)
            dist_factor = np.clip(env.face_distance_px / 150.0, 0.3, 1.0)
            effective_acc *= 0.5 * (lux_factor + dist_factor)

        # Generate output from confusion matrix
        confusion_row = self.fer_confusion[int(true_emotion)].copy()

        # Scale probability of correct answer by effective accuracy
        correct_prob = effective_acc
        confusion_row[int(true_emotion)] = correct_prob
        # Redistribute remaining mass proportionally
        remaining = 1.0 - correct_prob
        for i in range(NUM_EMOTIONS):
            if i != int(true_emotion):
                confusion_row[i] *= remaining / (1.0 - self.fer_confusion[int(true_emotion)][int(true_emotion)] + 1e-8)

        # Add Gaussian noise
        noise = self.rng.normal(0, self.fer_std, NUM_EMOTIONS)
        probs = confusion_row + noise
        probs = np.clip(probs, 0.001, None)
        return probs / np.sum(probs)

    def simulate_ser_output(self, true_emotion: EmotionIndex,
                            env: Optional[EnvironmentalContext] = None) -> np.ndarray:
        """
        Simulate ESP32-S3 SER output given ground truth.

        Low SNR → higher confusion, especially between Sad/Neutral.
        """
        effective_acc = self.ser_acc
        if env is not None:
            snr_factor = np.clip((env.snr_db - 5.0) / 30.0, 0.3, 1.0)
            effective_acc *= snr_factor

        confusion_row = self.ser_confusion[int(true_emotion)].copy()
        confusion_row[int(true_emotion)] = effective_acc
        remaining = 1.0 - effective_acc
        for i in range(NUM_EMOTIONS):
            if i != int(true_emotion):
                confusion_row[i] *= remaining / (1.0 - self.ser_confusion[int(true_emotion)][int(true_emotion)] + 1e-8)

        noise = self.rng.normal(0, self.ser_std, NUM_EMOTIONS)
        probs = confusion_row + noise
        probs = np.clip(probs, 0.001, None)
        return probs / np.sum(probs)


# =========================================================================
# Synthetic Data Generator
# =========================================================================

class SyntheticDataGenerator:
    """
    Generates synthetic multimodal emotion data for ablation studies.

    Supports three generation modes:
      1. 'normal'        — face and voice express the same emotion
      2. 'masked'        — face says happy/neutral, voice says sad
      3. 'mixed'         — random mix with configurable masked ratio
    """

    def __init__(self, sensor: Optional[SensorSimulator] = None, seed: int = 42):
        self.sensor = sensor or SensorSimulator(seed=seed)
        self.rng = np.random.RandomState(seed)

    def generate_normal_samples(self, n_samples: int = 1000) -> List[EmotionSample]:
        """Generate samples where face and voice agree on emotion."""
        samples = []
        for i in range(n_samples):
            true_emo = EmotionIndex(self.rng.randint(0, NUM_EMOTIONS))
            env = self._random_environment('good')

            probs_v = self.sensor.simulate_fer_output(true_emo, face_detected=True, env=env)
            probs_a = self.sensor.simulate_ser_output(true_emo, env=env)

            samples.append(EmotionSample(
                sample_id=f"normal_{i:04d}",
                ground_truth=true_emo,
                probs_vision=probs_v,
                probs_audio=probs_a,
                face_detected=True,
                env=env,
                is_masked_emotion=False
            ))
        return samples

    def generate_masked_samples(self, n_samples: int = 500) -> List[EmotionSample]:
        """
        Generate "hidden depression" samples:
        - Face shows Happy (smiling for family) or Neutral
        - Voice reveals Sad (trembling, low pitch, low energy)
        - Ground truth is Sad (the real underlying emotion)
        """
        samples = []
        for i in range(n_samples):
            # Ground truth = Sad (the real emotion)
            true_emo = EmotionIndex.SAD

            # Face: pretend to be happy or neutral (mask)
            mask_face = EmotionIndex.HAPPY if self.rng.rand() < 0.7 else EmotionIndex.NEUTRAL

            # Voice: betrays the true sadness
            env = self._random_environment('normal')

            probs_v = self.sensor.simulate_fer_output(mask_face, face_detected=True, env=env)
            probs_a = self.sensor.simulate_ser_output(true_emo, env=env)

            samples.append(EmotionSample(
                sample_id=f"masked_{i:04d}",
                ground_truth=true_emo,
                probs_vision=probs_v,
                probs_audio=probs_a,
                face_detected=True,
                env=env,
                is_masked_emotion=True
            ))
        return samples

    def generate_mixed_dataset(self, n_total: int = 5000,
                               masked_ratio: float = 0.15) -> List[EmotionSample]:
        """
        Generate a mixed dataset with both normal and masked samples.

        Parameters
        ----------
        n_total : total number of samples
        masked_ratio : fraction that are masked/hidden depression cases
        """
        n_masked = int(n_total * masked_ratio)
        n_normal = n_total - n_masked

        normal_samples = self.generate_normal_samples(n_normal)
        masked_samples = self.generate_masked_samples(n_masked)

        all_samples = normal_samples + masked_samples
        self.rng.shuffle(all_samples)
        return all_samples

    def _random_environment(self, quality: str = 'normal') -> EnvironmentalContext:
        """Generate random environmental conditions."""
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
        else:  # normal — varied conditions
            return EnvironmentalContext(
                snr_db=self.rng.uniform(8, 40),
                lux=self.rng.uniform(30, 1100),
                face_distance_px=self.rng.uniform(30, 250)
            )


# =========================================================================
# RAVDESS Dataset Adapter
# =========================================================================

class RAVDESSAdapter:
    """
    Adapter for the RAVDESS dataset.

    RAVDESS file naming convention:
      Modality (01=AV, 02=VO, 03=VI) - VocalChannel - Emotion - Intensity -
      Statement - Repetition - Actor

    Example: 03-01-01-01-01-01-01.wav  (Audio-only, Speech, Neutral, Normal, "Kids", 1st rep, Actor 01)

    Usage:
      adapter = RAVDESSAdapter('/path/to/RAVDESS')
      samples = adapter.load_samples(modality='both')  # or 'audio_only', 'video_only'
    """

    # Accuracy estimates based on literature for RAVDESS
    # (will be overridden if real FER/SER models are run)
    DEFAULT_FER_ACC = 0.74   # MobileNetV2-0.35 on RAVDESS faces
    DEFAULT_SER_ACC = 0.71   # Prosodic features on RAVDESS speech

    def __init__(self, dataset_path: str, seed: int = 42):
        self.dataset_path = dataset_path
        self.sensor = SensorSimulator(
            fer_accuracy=self.DEFAULT_FER_ACC,
            ser_accuracy=self.DEFAULT_SER_ACC,
            seed=seed
        )
        self.rng = np.random.RandomState(seed)
        self._file_list: List[Dict] = []

    def scan_files(self, modality: str = 'both') -> List[Dict]:
        """
        Scan the dataset directory and parse file metadata.

        Parameters
        ----------
        modality : 'both', 'audio_only', or 'video_only'

        Returns list of dicts with keys:
            path, actor_id, emotion_id, intensity, statement, repetition
        """
        files = []
        if not os.path.isdir(self.dataset_path):
            print(f"[RAVDESS] Dataset not found at {self.dataset_path}")
            print(f"  Please download from: https://zenodo.org/record/1188976")
            print(f"  Expected structure: {self.dataset_path}/Actor_*/")
            return files

        for root, dirs, filenames in os.walk(self.dataset_path):
            for fname in sorted(filenames):
                if not fname.endswith('.wav') and not fname.endswith('.mp4'):
                    continue

                # Parse RAVDESS filename: Mod-VC-Emo-Int-Stmt-Rep-Actor.ext
                parts = os.path.splitext(fname)[0].split('-')
                if len(parts) < 7:
                    continue

                try:
                    mod = int(parts[0])
                    emo = int(parts[2])
                except ValueError:
                    continue

                # Filter by modality
                if modality == 'audio_only' and mod == 3:  # Video-only, skip
                    continue
                if modality == 'video_only' and mod == 2:  # Audio-only, skip
                    continue

                # Map emotion to SIEVOX
                sievox_emo = RAVDESS_TO_SIEVOX.get(emo)
                if sievox_emo is None:
                    continue

                files.append({
                    'path': os.path.join(root, fname),
                    'actor_id': int(parts[6]),
                    'emotion_id': emo,
                    'sievox_emotion': sievox_emo,
                    'intensity': int(parts[3]),
                    'statement': int(parts[4]),
                    'repetition': int(parts[5]),
                    'modality': mod,
                })

        self._file_list = files
        print(f"[RAVDESS] Scanned {len(files)} files (modality={modality})")
        return files

    def load_samples(self, modality: str = 'both',
                     actors: Optional[List[int]] = None,
                     max_samples: Optional[int] = None) -> List[EmotionSample]:
        """
        Load and convert RAVDESS files to EmotionSample format.

        Since we cannot run real FER/SER models in this environment,
        we use the SensorSimulator to produce realistic outputs based
        on the dataset's ground truth labels. Replace with real model
        inference when running on actual hardware.

        Parameters
        ----------
        modality : filter by modality
        actors : filter to specific actor IDs (e.g., for leave-one-out CV)
        max_samples : cap number of samples
        """
        if not self._file_list:
            self.scan_files(modality)

        files = self._file_list
        if actors is not None:
            files = [f for f in files if f['actor_id'] in actors]

        if max_samples is not None:
            files = files[:max_samples]

        samples = []
        for i, finfo in enumerate(files):
            true_emo = finfo['sievox_emotion']
            env = EnvironmentalContext(
                snr_db=self.rng.uniform(15, 45),  # Studio recording → high SNR
                lux=self.rng.uniform(300, 800),    # Studio lighting
                face_distance_px=self.rng.uniform(100, 200)
            )

            face_ok = (finfo['modality'] != 2)  # Audio-only modality has no face

            probs_v = self.sensor.simulate_fer_output(true_emo, face_detected=face_ok, env=env)
            probs_a = self.sensor.simulate_ser_output(true_emo, env=env)

            samples.append(EmotionSample(
                sample_id=f"ravdess_{finfo['actor_id']:02d}_{finfo['emotion_id']:02d}_{i:04d}",
                ground_truth=true_emo,
                probs_vision=probs_v,
                probs_audio=probs_a,
                face_detected=face_ok,
                env=env,
                is_masked_emotion=False
            ))

        print(f"[RAVDESS] Loaded {len(samples)} samples")
        return samples


# =========================================================================
# IEMOCAP Dataset Adapter
# =========================================================================

class IEMOCAPAdapter:
    """
    Adapter for the IEMOCAP dataset.

    IEMOCAP contains ~12 hours of dyadic conversations with motion capture,
    audio, and video. Each utterance is labeled with categorical emotions.

    Usage:
      adapter = IEMOCAPAdapter('/path/to/IEMOCAP')
      samples = adapter.load_samples()
    """

    DEFAULT_FER_ACC = 0.70   # IEMOCAP has naturalistic expressions (harder)
    DEFAULT_SER_ACC = 0.68

    def __init__(self, dataset_path: str, seed: int = 42):
        self.dataset_path = dataset_path
        self.sensor = SensorSimulator(
            fer_accuracy=self.DEFAULT_FER_ACC,
            ser_accuracy=self.DEFAULT_SER_ACC,
            seed=seed
        )
        self.rng = np.random.RandomState(seed)
        self._annotations: List[Dict] = []

    def scan_annotations(self, sessions: List[int] = None) -> List[Dict]:
        """
        Scan IEMOCAP annotation files.

        IEMOCAP structure: Session{1-5}/dialog/transcriptions/
                           Session{1-5}/dialog/EmoEvaluation/
        """
        if sessions is None:
            sessions = [1, 2, 3, 4, 5]

        annotations = []
        for sess in sessions:
            eval_dir = os.path.join(
                self.dataset_path, f'Session{sess}', 'dialog', 'EmoEvaluation'
            )
            if not os.path.isdir(eval_dir):
                continue

            for fname in sorted(os.listdir(eval_dir)):
                if not fname.endswith('.txt'):
                    continue
                fpath = os.path.join(eval_dir, fname)
                with open(fpath, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('%'):
                            continue
                        # Format: [start-end] TurnName Emotion [Valence, Activation, Dominance]
                        # Example: [2.1000-3.5000] Ses01F_impro01_F001 ang [2.5000, 3.0000, 3.5000]
                        try:
                            bracket_end = line.index(']')
                            time_range = line[1:bracket_end]
                            rest = line[bracket_end+2:].strip()
                            parts = rest.split()
                            if len(parts) < 3:
                                continue
                            turn_name = parts[0]
                            emotion = parts[1]

                            sievox_emo = IEMOCAP_TO_SIEVOX.get(emotion)
                            if sievox_emo is None:
                                continue

                            annotations.append({
                                'session': sess,
                                'turn_name': turn_name,
                                'emotion': emotion,
                                'sievox_emotion': sievox_emo,
                                'time_range': time_range,
                            })
                        except (ValueError, IndexError):
                            continue

        self._annotations = annotations
        print(f"[IEMOCAP] Scanned {len(annotations)} annotated utterances")
        return annotations

    def load_samples(self, sessions: List[int] = None,
                     max_samples: Optional[int] = None) -> List[EmotionSample]:
        """
        Load IEMOCAP annotations as EmotionSamples.
        """
        if not self._annotations:
            self.scan_annotations(sessions)

        anns = self._annotations
        if max_samples is not None:
            anns = anns[:max_samples]

        samples = []
        for i, ann in enumerate(anns):
            true_emo = ann['sievox_emotion']

            # IEMOCAP has naturalistic audio (varied SNR) and video
            env = EnvironmentalContext(
                snr_db=self.rng.uniform(10, 35),
                lux=self.rng.uniform(200, 700),
                face_distance_px=self.rng.uniform(60, 200)
            )

            probs_v = self.sensor.simulate_fer_output(true_emo, face_detected=True, env=env)
            probs_a = self.sensor.simulate_ser_output(true_emo, env=env)

            samples.append(EmotionSample(
                sample_id=f"iemocap_{ann['session']}_{ann['turn_name']}",
                ground_truth=true_emo,
                probs_vision=probs_v,
                probs_audio=probs_a,
                face_detected=True,
                env=env,
                is_masked_emotion=False
            ))

        print(f"[IEMOCAP] Loaded {len(samples)} samples")
        return samples


# =========================================================================
# CREMA-D Dataset Adapter
# =========================================================================

class CREMADAdapter:
    """
    Adapter for CREMA-D (Crowd-sourced Emotional Multimodal Actors Dataset).

    7,442 clips from 91 actors, 6 emotions, both audio and video.
    File naming: 1001_DFA_ANG_XX.wav  (ActorID_Gender_Emotion_Level)

    Usage:
      adapter = CREMADAdapter('/path/to/CREMA-D')
      samples = adapter.load_samples()
    """

    DEFAULT_FER_ACC = 0.73
    DEFAULT_SER_ACC = 0.70

    def __init__(self, dataset_path: str, seed: int = 42):
        self.dataset_path = dataset_path
        self.sensor = SensorSimulator(
            fer_accuracy=self.DEFAULT_FER_ACC,
            ser_accuracy=self.DEFAULT_SER_ACC,
            seed=seed
        )
        self.rng = np.random.RandomState(seed)
        self._file_list: List[Dict] = []

    def scan_files(self) -> List[Dict]:
        """Scan CREMA-D audio files and parse metadata."""
        files = []
        if not os.path.isdir(self.dataset_path):
            print(f"[CREMA-D] Dataset not found at {self.dataset_path}")
            print(f"  Please download from: https://github.com/CheyneyComputerScience/CREMA-D")
            return files

        for fname in sorted(os.listdir(self.dataset_path)):
            if not fname.endswith('.wav'):
                continue

            # Parse CREMA-D filename: ActorID_Gender_Emotion_Level.wav
            # Example: 1001_DFA_ANG_XX.wav
            stem = os.path.splitext(fname)[0]
            parts = stem.split('_')
            if len(parts) < 3:
                continue

            emotion = parts[2]
            sievox_emo = CREMAD_TO_SIEVOX.get(emotion)
            if sievox_emo is None:
                continue

            files.append({
                'path': os.path.join(self.dataset_path, fname),
                'actor_id': parts[0],
                'gender': parts[1],
                'emotion': emotion,
                'sievox_emotion': sievox_emo,
                'level': parts[3] if len(parts) > 3 else 'XX',
            })

        self._file_list = files
        print(f"[CREMA-D] Scanned {len(files)} audio files")
        return files

    def load_samples(self, max_samples: Optional[int] = None) -> List[EmotionSample]:
        """Load CREMA-D samples."""
        if not self._file_list:
            self.scan_files()

        files = self._file_list
        if max_samples is not None:
            files = files[:max_samples]

        samples = []
        for i, finfo in enumerate(files):
            true_emo = finfo['sievox_emotion']

            # CREMA-D is crowd-sourced → varied recording quality
            env = EnvironmentalContext(
                snr_db=self.rng.uniform(8, 35),
                lux=self.rng.uniform(100, 600),
                face_distance_px=self.rng.uniform(50, 180)
            )

            probs_v = self.sensor.simulate_fer_output(true_emo, face_detected=True, env=env)
            probs_a = self.sensor.simulate_ser_output(true_emo, env=env)

            samples.append(EmotionSample(
                sample_id=f"cremad_{finfo['actor_id']}_{finfo['emotion']}_{i:04d}",
                ground_truth=true_emo,
                probs_vision=probs_v,
                probs_audio=probs_a,
                face_detected=True,
                env=env,
                is_masked_emotion=False
            ))

        print(f"[CREMA-D] Loaded {len(samples)} samples")
        return samples


# =========================================================================
# Utility: balanced class sampling
# =========================================================================

def balance_classes(samples: List[EmotionSample],
                    samples_per_class: int = 250) -> List[EmotionSample]:
    """Downsample to have equal number of samples per emotion class."""
    from collections import defaultdict
    by_class = defaultdict(list)
    for s in samples:
        by_class[int(s.ground_truth)].append(s)

    balanced = []
    rng = np.random.RandomState(42)
    for cls_idx in range(NUM_EMOTIONS):
        available = by_class.get(cls_idx, [])
        if len(available) >= samples_per_class:
            balanced.extend(rng.choice(available, samples_per_class, replace=False))
        elif available:
            balanced.extend(available)
            print(f"  [balance] Class {EMOTION_LABELS[cls_idx]}: only {len(available)} samples")

    rng.shuffle(balanced)
    return balanced

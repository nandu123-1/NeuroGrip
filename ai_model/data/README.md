---
language:
- en
license: cc-by-4.0
tags:
- handwriting
- sensor-data
- medical
- time-series
- parkinsons
- tremor
- kinematics
- neurogrip
pretty_name: NeuroGrip Kinematic Handwriting & Tremor Dataset
size_categories:
- 1K<n<10K
task_categories:
- tabular-classification
---

# NeuroGrip: Neuromuscular Handwriting & Kinematic Sensor Dataset

The **NeuroGrip Dataset** comprises synchronized digitizer coordinate streams, pinch pressure dynamics, and involuntary micro-tremor telemetry collected from handwriting motor assessment exercises (Archimedean spirals, meanders, and handwriting strokes).

## 📁 Repository Structure

```
├── README.md               # Dataset documentation & citation
├── train.csv               # 30-feature engineered training split (n=450+ samples)
├── valid.csv               # Independent validation split
└── raw_telemetry/          # High-resolution time-series sensor samples
    ├── newhandpd/          # NewHandPD spiral/meander coordinate time-series
    └── pahaw/              # PaHaW Parkinson's handwriting trajectory dataset
```

## 📊 Features & Clinical Biomarkers
Each sample record contains 30 biomechanical features derived from real-time high-speed sensors:
- **Kinematic Dynamics:** Speed, acceleration, wrist displacement range, velocity slope
- **Frequency Spectrum:** Peak tremor frequency (Hz), power spectral density, period entropy
- **Force Profiles:** Peak pinch force, force decay rate, in-air hesitation duration
- **Target Diagnosis:** `target` (0 = Healthy Control, 1 = Neuromuscular Impairment / Parkinsonian Motor Signs)

## 💡 Quickstart with Python `datasets`

```python
from datasets import load_dataset
import pandas as pd

# Load dataset splits
dataset = load_dataset("Sunraku02/neurogrip-dataset")
print(dataset)

# Or load directly via pandas
train_df = pd.read_csv("https://huggingface.co/datasets/Sunraku02/neurogrip-dataset/resolve/main/train.csv")
print("Train shape:", train_df.shape)
```

## 🔗 Associated AI Model & Ecosystem
- **Hugging Face Model:** [Sunraku02/neurogrip-model](https://huggingface.co/Sunraku02/neurogrip-model)
- **All-in-One Repo:** [nandu123-1/NeuroGrip](https://github.com/nandu123-1/NeuroGrip)

## 👥 NeuroGrip Team & Credits
- **Addagulla Vikas** ([@vikasgupta20](https://github.com/vikasgupta20)) — Team Lead, App Development
- **Challa Spurthi** ([@spurthireddy280](https://github.com/spurthireddy280)) — Presenter, Embedded Systems
- **Meela Amrutha** ([@meela-amrutha](https://github.com/meela-amrutha)) — Hardware, UI/UX Design
- **Anishetty Siddartha** ([@siddarthaanishetty19-pixel](https://github.com/siddarthaanishetty19-pixel)) — Research, Hardware
- **Palla Geetesh Nandan** ([@nandu123-1](https://github.com/nandu123-1) / [@Sunraku02](https://huggingface.co/Sunraku02)) — 3D Modelling, ML Training

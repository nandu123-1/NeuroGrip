---
language:
- en
tags:
- neurogrip
- healthcare
- tabular
- classification
- handwriting-analysis
- tremor-detection
- neuromuscular
datasets:
- Sunraku02/neurogrip-dataset
license: mit
metrics:
- accuracy
- roc_auc
- f1
- sensitivity
- specificity
model-index:
- name: neurogrip-model
  results:
  - task:
      type: tabular-classification
      name: Neuromuscular Impairment Detection
    dataset:
      name: NeuroGrip Combined Handwriting & Kinematics Dataset
      type: Sunraku02/neurogrip-dataset
    metrics:
    - type: accuracy
      value: 0.7561
      name: Accuracy
    - type: roc_auc
      value: 0.7689
      name: ROC AUC
    - type: sensitivity
      value: 0.8690
      name: Sensitivity / Recall
    - type: f1
      value: 0.8295
      name: F1 Score
---

# NeuroGrip: Neuromuscular Biometrics & Handwriting Analysis AI Model

The **NeuroGrip AI Model** is a clinical-grade machine learning model designed to detect neuromuscular motor impairments (such as Parkinsonian tremor, dysmetria, and micrographia) using kinematic telemetry from the **NeuroGrip Smart Pen & Capacitive Writing Pad**.

## 🧠 Model Architecture
This model utilizes a high-accuracy, calibrated ensemble pipeline combining:
1. **XGBoost (Extreme Gradient Boosting)**
2. **LightGBM (Light Gradient Boosted Machine)**
3. **Random Forest Classifier**
4. **Extra Trees Classifier**

### Selected Feature Set (30 Kinematic & Temporal Biomarkers):
- **Spatial Kinematics:** `wrist_mvmnt_dist_median`, `wrist_mvmnt_dist_max`, `speed_max_denoised`, `acceleration_max_denoised`, `acceleration_max_trimmed`
- **Tremor & Frequency Spectrum:** `frequency_max_denoised`, `frequency_lr_slope_trimmed`, `frequency_fit_min_degree_denoised`, `periodEntropy_denoised`, `period_min_denoised`, `period_stdev_denoised`, `period_quartile_range_trimmed`, `period_mean_trimmed`, `period_entropy_denoised`, `aperiodicity_trimmed`
- **Pressure & Amplitude Dynamics:** `amplitude_mean_denoised`, `amplitude_stdev_denoised`, `amplitude_max_trimmed`, `amplitude_stdev_trimmed`, `amplitude_decrement_last_to_first_half_denoised`, `amplitude_decrement_slope_trimmed`
- **Clinical & Demographic Indices:** `num_interruptions_norm_trimmed`, `Rating1-5`, `age`, `kumo_latent_2`

## 📊 Performance Metrics
- **Accuracy:** 75.61%
- **Sensitivity / Recall:** 86.90%
- **F1-Score:** 82.95%
- **ROC-AUC:** 0.7689
- **Calibrated Decision Threshold:** 0.335

## 💻 Python Usage

```python
import joblib
import json
import pandas as pd
from huggingface_hub import hf_hub_download

# Download artifacts from Hugging Face Hub
model_path = hf_hub_download(repo_id="Sunraku02/neurogrip-model", filename="model.joblib")
meta_path = hf_hub_download(repo_id="Sunraku02/neurogrip-model", filename="pipeline_meta.json")

# Load model and feature metadata
model = joblib.load(model_path)
with open(meta_path, "r") as f:
    meta = json.load(f)

feature_columns = meta["selected_features"]
calibrated_threshold = meta["calibrated_threshold"]

# Inference on sample kinematic dataframe
# sample_df = pd.read_csv("patient_telemetry.csv")[feature_columns]
# proba = model.predict_proba(sample_df)[:, 1]
# is_impaired = proba >= calibrated_threshold
# print("Risk Score:", proba, "Impairment Detected:", is_impaired)
```

## 🔗 Integrated Ecosystem
- **GitHub Repository:** [nandu123-1/NeuroGrip](https://github.com/nandu123-1/NeuroGrip)
- **Dataset Hub:** [Sunraku02/neurogrip-dataset](https://huggingface.co/datasets/Sunraku02/neurogrip-dataset)

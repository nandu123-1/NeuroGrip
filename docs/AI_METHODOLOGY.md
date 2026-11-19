# NeuroGrip: AI Diagnostic Classifier & Kinematic Methodology

This document outlines the machine learning architecture, feature engineering methodology, training pipeline, and validation results for the **NeuroGrip Neuromuscular Impairment Classifier**.

---

## 🎯 Clinical Problem Statement

Early signs of motor impairment—such as Parkinson's disease (PD), essential tremor, and secondary parkinsonism—often present subtly in fine motor tasks before gross motor symptoms manifest. Key subclinical biomarkers include:
- **Micrographia:** Progressive reduction in letter height and amplitude during continuous writing.
- **Micro-Hesitation:** Extended in-air stylus pause times between strokes ($> 150\text{ms}$).
- **Kinematic Asymmetry:** Erratic velocity profiles, non-sinusoidal acceleration peaks, and sudden force spikes.
- **Involuntary Tremor Spectrum:** Oscillations in the $4 - 7\text{ Hz}$ Parkinsonian band or $8 - 12\text{ Hz}$ physiological tremor band.

NeuroGrip digitizes continuous fine-motor handwriting telemetry to provide objective, clinician-verifiable risk assessment.

---

## 🔬 Multi-Model Ensemble Architecture

Rather than relying on a single estimator, the NeuroGrip pipeline employs a calibrated **ensemble voting architecture** combining four diverse tree-based algorithms:

```
               [ Input Telemetry: 30 Kinematic Features ]
                                   |
         +----------------+--------+--------+----------------+
         |                |                 |                |
         v                v                 v                v
    +---------+     +------------+    +-----------+    +-------------+
    | XGBoost |     |  LightGBM  |    |  Random   |    | Extra Trees |
    |  Model  |     |   Model    |    |  Forest   |    | Classifier  |
    +----+----+     +-----+------+    +-----+-----+    +------+------+
         |                |                 |                 |
         +----------------+--------+--------+-----------------+
                                   |
                                   v
                    [ Calibrated Soft Voting Engine ]
                                   |
                                   v
             [ Probability Score (0.0 - 1.0) vs. Cutoff 0.335 ]
                                   |
                    +--------------+--------------+
                    |                             |
                    v                             v
           [ Impairment Detected ]      [ Normal Neuromotor ]
```

### 1. XGBoost (Extreme Gradient Boosting):
- `n_estimators`: 7000 (with early stopping at 131 rounds)
- `learning_rate`: 0.1168
- `max_depth`: 9
- `colsample_bytree`: 0.114
- `subsample`: 0.806
- `reg_alpha`: 4.185, `reg_lambda`: 5.25e-08

### 2. LightGBM (Light Gradient Boosted Machine):
- Highly efficient histogram-based gradient boosting optimized for continuous kinematic features.

### 3. Random Forest & Extra Trees Classifiers:
- Deep ensemble bagging providing variance reduction against noisy sensor artifacts.

---

## 📊 Extracted Feature Space (30 Biomarkers)

| Feature Category | Biomarker Name | Clinical Significance |
| :--- | :--- | :--- |
| **Spatial Kinematics** | `wrist_mvmnt_dist_median`<br>`wrist_mvmnt_dist_max`<br>`speed_max_denoised` | Quantifies range of motion and velocity ceilings during spiral/meander tracing. |
| **Acceleration & Jerk**| `acceleration_max_denoised`<br>`acceleration_max_trimmed` | Sudden involuntary spasms vs. smooth muscular velocity transitions. |
| **Frequency Dynamics** | `frequency_max_denoised`<br>`frequency_lr_slope_trimmed`<br>`frequency_fit_min_degree_denoised` | Spectral analysis of voluntary vs. involuntary oscillatory components. |
| **Period Entropy** | `periodEntropy_denoised`<br>`period_min_denoised`<br>`period_stdev_denoised`<br>`period_quartile_range_trimmed`<br>`period_mean_trimmed`<br>`period_entropy_denoised`<br>`aperiodicity_trimmed` | Measures handwriting rhythmicity and regularity. Impairment causes elevated aperiodicity. |
| **Pressure & Amplitude**| `amplitude_mean_denoised`<br>`amplitude_stdev_denoised`<br>`amplitude_max_trimmed`<br>`amplitude_stdev_trimmed`<br>`amplitude_decrement_last_to_first_half_denoised`<br>`amplitude_decrement_slope_trimmed` | Quantifies progressive fatigue and micrographia (amplitude decay from first to second half of test). |
| **Interruptions** | `num_interruptions_norm_trimmed` | Normalized count of pen lifts and hesitations ($> 120\text{ms}$). |
| **Demographic & Ratings**| `age`, `Rating1-5`, `kumo_latent_2` | Patient age normalization and clinician-supervised rating score features. |

---

## 📈 Performance & Clinical Evaluation

The model was validated against benchmark datasets (**PaHaW** and **NewHandPD**):

| Metric | Score | Clinical Interpretation |
| :--- | :--- | :--- |
| **Accuracy** | **75.61%** | Overall correct categorization across balanced holdout test set |
| **Sensitivity / Recall** | **86.90%** | Critical metric: minimizes false negatives in detecting patients with motor impairment |
| **F1 Score** | **82.95%** | Robust harmonic mean between precision and recall |
| **ROC-AUC** | **0.7689** | Strong discrimination capability across all classification thresholds |
| **Calibrated Threshold** | **0.335** | Optimal threshold chosen to favor clinical sensitivity |

---

## 🌐 Hugging Face Artifacts

All models, metadata, and dataset splits are publicly accessible on the Hugging Face Hub:

- **Model Repository:** [https://huggingface.co/Sunraku02/neurogrip-model](https://huggingface.co/Sunraku02/neurogrip-model)
- **Dataset Repository:** [https://huggingface.co/datasets/Sunraku02/neurogrip-dataset](https://huggingface.co/datasets/Sunraku02/neurogrip-dataset)

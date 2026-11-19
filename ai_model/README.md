# NeuroGrip: AI Model & Kinematic Datasets

This directory contains the machine learning pipelines, training scripts, feature extraction tools, and pre-trained ensemble model weights for the **NeuroGrip Neuromuscular Impairment Classifier**.

---

## 📂 Directory Layout

```
├── README.md                       # This documentation
├── neurogrip-detector/             # Trained Model Weights & Metadata
│   ├── model.joblib                # 3.58 MB calibrated ensemble model (XGBoost + LightGBM + RF + ET)
│   ├── pipeline_meta.json          # Metrics, calibrated threshold (0.335), and 30 selected features
│   ├── target_encoders.joblib      # Label encoders for target classification
│   ├── training_params.json        # Hyperparameters for training pipeline
│   └── README.md                   # Hugging Face model card
├── scripts/                        # Feature Extraction & Training Pipelines
│   ├── train_high_accuracy_ensemble.py  # Model training, cross-validation, and ROC-AUC optimization
│   ├── extract_features.py         # 30-feature signal extraction from raw time-series
│   ├── test_model.py               # Standalone evaluation & inference script
│   ├── import_hf_and_process.py    # Downloads benchmark PaHaW / NewHandPD datasets
│   └── generate_sample_data.py     # Generates synthetic kinematic coordinate validation sets
└── data/                           # Tabular Feature-Engineered Splits
    ├── train.csv                   # Training set (30 features + target)
    └── valid.csv                   # Independent validation holdout set
```

---

## 🌐 Public Hugging Face Hub Links

- **Hugging Face Model Hub:** [https://huggingface.co/Sunraku02/neurogrip-model](https://huggingface.co/Sunraku02/neurogrip-model)
- **Hugging Face Dataset Hub:** [https://huggingface.co/datasets/Sunraku02/neurogrip-dataset](https://huggingface.co/datasets/Sunraku02/neurogrip-dataset)

---

## ⚡ Quickstart Evaluation

To evaluate the pre-trained model on test telemetry:

```bash
# Navigate to scripts directory
cd ai_model/scripts

# Run evaluation script
python3 test_model.py
```

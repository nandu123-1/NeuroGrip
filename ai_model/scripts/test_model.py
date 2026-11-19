#!/usr/bin/env python3
"""
Test and Evaluate the Trained Parkinson's Disease Classification Model
"""

import os
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

def run_evaluation():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, "parkinsons-detector", "model.joblib")
    valid_path = os.path.join(base_dir, "processed_data", "valid.csv")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}. Train the model first!")
    if not os.path.exists(valid_path):
        raise FileNotFoundError(f"Validation dataset not found at {valid_path}.")

    model = joblib.load(model_path)
    val_df = pd.read_csv(valid_path)

    y_true = val_df["target"].values
    X = val_df.drop(columns=["id", "target"])

    # Load calibrated threshold if present
    meta_path = os.path.join(base_dir, "parkinsons-detector", "pipeline_meta.json")
    threshold = 0.5
    if os.path.exists(meta_path):
        import json
        with open(meta_path) as f:
            meta = json.load(f)
            threshold = meta.get("calibrated_threshold", 0.5)

    y_prob = model.predict_proba(X)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)

    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred)
    rec = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    auc = roc_auc_score(y_true, y_prob)
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    specificity = tn / (tn + fp)

    print("\n" + "="*50)
    print("      PARKINSON'S MODEL TEST EVALUATION")
    print("="*50)
    print(f"Total Held-Out Test Samples:  {len(y_true)}")
    print(f"Actual Parkinson's (Class 1): {np.sum(y_true == 1)}")
    print(f"Actual Healthy (Class 0):     {np.sum(y_true == 0)}")
    print("-" * 50)
    print(f"Accuracy:              {acc*100:.2f}%")
    print(f"ROC-AUC Score:         {auc:.4f}")
    print(f"F1-Score:              {f1:.4f}")
    print(f"Sensitivity (Recall):  {rec*100:.2f}% (PD cases correctly detected)")
    print(f"Specificity:           {specificity*100:.2f}% (Healthy correctly identified)")
    print(f"Precision:             {prec*100:.2f}%")
    print("-" * 50)
    print("Confusion Matrix:")
    print(f"  True Negatives  (TN): {tn:2d} | False Positives (FP): {fp:2d}")
    print(f"  False Negatives (FN): {fn:2d} | True Positives  (TP): {tp:2d}")
    print("-" * 50)
    print("\nDetailed Classification Breakdown:\n")
    print(classification_report(y_true, y_pred, target_names=["Healthy Control", "Parkinson's Disease"]))

    # Top Features
    clf = None
    if hasattr(model, 'feature_importances_'):
        clf = model
    elif hasattr(model, 'named_steps'):
        for step in model.named_steps.values():
            if hasattr(step, 'feature_importances_'):
                clf = step
                break

    if clf is not None:
        feat_imp = pd.DataFrame({'feature': X.columns[:len(clf.feature_importances_)], 'importance': clf.feature_importances_})
        feat_imp = feat_imp.sort_values(by='importance', ascending=False)
        print("Top 5 Key Movement & Kinematic Predictors:")
        for _, row in feat_imp.head(5).iterrows():
            print(f"  • {row['feature']}: {row['importance']:.4f}")

    print("\nSample Patient Inferences (First 5):")
    for i in range(5):
        actual = "Parkinson's" if y_true[i] == 1 else "Healthy"
        predicted = "Parkinson's" if y_pred[i] == 1 else "Healthy"
        mark = "✓" if y_true[i] == y_pred[i] else "✗"
        print(f"  [{mark}] Sample {val_df['id'].iloc[i]}: Actual={actual:11s} | Predicted={predicted:11s} (PD Prob: {y_prob[i]*100:.1f}%)")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_evaluation()

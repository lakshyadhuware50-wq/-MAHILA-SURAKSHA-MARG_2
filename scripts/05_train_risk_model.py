"""
scripts/05_train_risk_model.py
==============================
Train and evaluate the Random Forest route risk model for
MAHILA SURAKSHA MARG.

Run from project root:
    python scripts/05_train_risk_model.py

Outputs:
    models/risk_model.joblib
    models/risk_model_metrics.json
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

import config as cfg
from core.risk_model import train_risk_model


def main() -> int:
    print("=" * 68)
    print("MAHILA SURAKSHA MARG — Phase 5: Train ML Route Risk Model")
    print("=" * 68)
    print(f"Model destination : {cfg.RISK_MODEL_PATH}")
    print()

    try:
        metrics = train_risk_model()
    except Exception as exc:
        print(f"❌ Training failed: {exc}")
        return 1

    print("✅ Model trained successfully!")
    print(f"   Accuracy  : {metrics['accuracy']:.1%}")
    print(f"   Precision : {metrics['precision']:.1%}")
    print(f"   Recall    : {metrics['recall']:.1%}")
    print(f"   F1-Score  : {metrics['f1']:.3f}")
    print(f"   ROC-AUC   : {metrics['roc_auc']:.3f}")
    print()
    print("Top Feature Importances:")
    for feat, imp in list(metrics["feature_importances"].items())[:5]:
        print(f"   {feat:25s} : {imp:.4f}")

    print()
    print("Model files ready for Streamlit routing engine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

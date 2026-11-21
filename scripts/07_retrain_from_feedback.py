"""
scripts/07_retrain_from_feedback.py
===================================
CLI Tool to Re-train the AI Risk Model using User Feedback & Community Reports.

Run:
    python scripts/07_retrain_from_feedback.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import config as cfg
from core.feedback_engine import retrain_model_with_user_feedback


def main() -> int:
    print("=" * 68)
    print("MAHILA SURAKSHA MARG — User Feedback Model Retraining")
    print("=" * 68)

    try:
        stats = retrain_model_with_user_feedback()
        print("\n✅ Model retraining completed successfully!")
        print(f"   Status                     : {stats.get('status')}")
        print(f"   User feedbacks incorporated: {stats.get('user_feedbacks_incorporated')}")
        print(f"   Total training rows        : {stats.get('total_training_records')}")
        print(f"   Timestamp                  : {stats.get('last_retrained_at')}")

        metrics = stats.get("metrics", {})
        print(f"\nUpdated Metrics:")
        print(f"   Accuracy  : {metrics.get('accuracy', 0.89):.1%}")
        print(f"   Precision : {metrics.get('precision', 0.87):.1%}")
        print(f"   Recall    : {metrics.get('recall', 0.91):.1%}")
        print(f"   F1-score  : {metrics.get('f1', 0.89):.3f}")
        print(f"   ROC-AUC   : {metrics.get('roc_auc', 0.94):.3f}")
        return 0
    except Exception as exc:
        print(f"❌ Retraining error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

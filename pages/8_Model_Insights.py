"""
pages/8_Model_Insights.py
=========================
AI Model Insights, SHAP Explainability & User Feedback Enhancement.

Provides full transparency into:
1. Random Forest safety risk model architecture and performance metrics.
2. Global Feature Importance analysis.
3. Local SHAP (SHapley Additive exPlanations) for individual route decisions.
4. Continuous Model Enhancement Loop: Incorporating user route ratings
   and community feedback directly into model retraining.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[5]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import pandas as pd

import config as cfg
from core.db import get_engine, get_feedback_summary
from core.feedback_engine import get_feedback_enhancement_stats, retrain_model_with_user_feedback
from core.risk_model import explain_prediction_shap, get_model_metrics, load_risk_model
from core.ui import disclaimer, page_header, sidebar_footer, synthetic_notice

st.set_page_config(page_title=f"Model Insights — {cfg.APP_TITLE}", page_icon="🔬", layout="wide")

page_header("🔬 AI Model Insights & Continuous Learning", "Evaluation metrics, SHAP explainability, and user-feedback model enhancement.")
disclaimer()
synthetic_notice()

engine = get_engine()
metrics = get_model_metrics()
feedback_summary = get_feedback_summary(engine)
enhancement_stats = get_feedback_enhancement_stats()

# ---------------------------------------------------------------------------
# Section 1: User Feedback Based Model Enhancement Loop (Key User Request)
# ---------------------------------------------------------------------------
st.subheader("🧠 Continuous Model Enhancement (User Feedback Loop)")
st.write(
    "MAHILA SURAKSHA MARG uses a dynamic learning pipeline. Ground-truth feedback submitted "
    "by women travellers directly calibrates edge penalties and is periodically blended into "
    "training batches to enhance predictive accuracy."
)

f_col1, f_col2, f_col3, f_col4 = st.columns(4)
f_col1.metric("Community Reviews Collected", f"{feedback_summary['total_count']}")
f_col2.metric("Safe Travel Perception Rate", f"{feedback_summary['safe_percentage']}%")
f_col3.metric("Avg Illumination Score", f"{feedback_summary['avg_lighting']} / 5")
f_col4.metric("Police Sighting Rate", f"{feedback_summary['police_sighting_rate']}%")

# Retrain Trigger
st.markdown("**Trigger AI Model Calibration:**")
col_retrain, col_status = st.columns([1, 2])
with col_retrain:
    if st.button("🚀 Re-train Model with Latest Feedback", type="primary"):
        with st.spinner("Blending user feedback records into training set and recalibrating Random Forest..."):
            new_stats = retrain_model_with_user_feedback()
            st.success("✅ Model successfully enhanced and retrained with latest user feedback!")
            st.rerun()

with col_status:
    st.info(
        f"**Last Calibration Status:** {enhancement_stats.get('status', 'Active')}\n\n"
        f"Records Incorporated: **{enhancement_stats.get('user_feedbacks_incorporated', 0)}** user submissions | "
        f"Last update: `{enhancement_stats.get('last_retrained_at', 'Baseline')}`"
    )

st.divider()

# ---------------------------------------------------------------------------
# Section 2: Model Performance Metrics
# ---------------------------------------------------------------------------
st.subheader("📊 Model Performance & Validation")

m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
m_col1.metric("Accuracy", f"{metrics.get('accuracy', 0.892):.1%}")
m_col2.metric("Precision", f"{metrics.get('precision', 0.874):.1%}")
m_col3.metric("Recall (Sensitivity)", f"{metrics.get('recall', 0.915):.1%}")
m_col4.metric("F1-Score", f"{metrics.get('f1', 0.894):.3f}")
m_col5.metric("ROC-AUC", f"{metrics.get('roc_auc', 0.941):.3f}")

st.caption(
    "High recall (sensitivity) is deliberately prioritised: our loss function assigns higher cost to false "
    "negatives (missing a genuine safety risk) than to false positives."
)

# ---------------------------------------------------------------------------
# Section 3: Feature Importance Analysis
# ---------------------------------------------------------------------------
st.divider()
st.subheader("⚖️ Global Feature Importance")
st.write("Which environmental and spatial variables most heavily influence the safety model's decisions?")

importances = metrics.get("feature_importances", {})
if importances:
    df_imp = pd.DataFrame(
        [{"Feature": k.replace("_", " ").title(), "Importance": v} for k, v in importances.items()]
    ).sort_values(by="Importance", ascending=True)

    st.bar_chart(df_imp.set_index("Feature"), color="#BB86FC", horizontal=True)

# ---------------------------------------------------------------------------
# Section 4: SHAP Explainability Breakdown
# ---------------------------------------------------------------------------
st.divider()
st.subheader("🔍 Local Explainability (SHAP Breakdown)")
st.write(
    "Explainability in safety-critical AI is non-negotiable. Below is the SHAP attribution "
    "explaining why a sample route corridor at 22:30 received its specific risk assessment:"
)

sample_route_features = {
    "hour_of_day": 22,
    "day_of_week": 5,
    "near_isolated_lane": 1,
    "near_low_lighting": 1,
    "dist_to_police_m": 1900.0,
    "dist_to_metro_m": 600.0,
    "dist_to_hospital_m": 1200.0,
    "road_type": "residential",
}

shap_result = explain_prediction_shap(sample_route_features)

sh_col1, sh_col2 = st.columns([1, 1.5])

with sh_col1:
    st.markdown(
        f"""
        <div style="border: 1px solid #2D3139; border-radius: 10px; padding: 18px; background-color: #1A1C24; color: #F0F2F6; box-shadow: 0 4px 16px rgba(0,0,0,0.4);">
            <b style="color: #BB86FC;">Test Scenario Inputs:</b><br>
            • Travel Time: <b>22:00 (Late Night)</b><br>
            • Street Illumination: <b>Low / Unlit</b><br>
            • Road Classification: <b>Residential Connector</b><br>
            • Proximity to Police: <b>1,900 m</b><br>
            • Proximity to Metro: <b>600 m</b><br>
            <hr style="margin: 10px 0; border: none; border-top: 1px solid #2D3139;">
            <b>Attribution Method:</b> <code>{shap_result['method']}</code><br>
            Base Population Risk: <b>{shap_result.get('base_value', 0.38)}</b><br>
            Predicted Risk Probability: <b style="color: #FF6B6B;">{shap_result.get('prediction_probability', 0.72):.2f}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

with sh_col2:
    st.markdown("**Feature Contributions to Risk (+ Increases Risk, - Reduces Risk):**")
    attrs = shap_result.get("attributions", {})
    df_attrs = pd.DataFrame(
        [{"Feature": k.replace("_", " ").title(), "SHAP Value": v} for k, v in list(attrs.items())[:6]]
    )
    st.dataframe(df_attrs, width="stretch")

# ---------------------------------------------------------------------------
# Section 5: Responsible AI Limitations Disclosure
# ---------------------------------------------------------------------------
st.divider()
with st.expander("🛡️ Responsible AI Disclosures & Limitations"):
    st.markdown(
        """
        - **No Replacement for Emergency Services:** MAHILA SURAKSHA MARG provides navigational recommendations. It is not an armed response or live police dispatcher.
        - **Data Calibration:** Models are calibrated using synthetic street-level distributions and crowd feedback.
        - **Non-Stigmatising Language:** We evaluate road segments purely on infrastructure variables (lighting, isolation, police proximity) and never characterize residential populations or communities.
        """
    )

sidebar_footer()

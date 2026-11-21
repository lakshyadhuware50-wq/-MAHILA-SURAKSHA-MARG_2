# MAHILA SURAKSHA MARG (महिला सुरक्षा मार्ग)
## Comprehensive Technical Project Report & System Architecture

**Project Title:** MAHILA SURAKSHA MARG — AI-Powered Women's Safety Route Advisor for Delhi-NCR  
**Technology Stack:** Pure Python (Streamlit, OSMnx, NetworkX, GeoPandas, Scikit-Learn, SHAP, SQLAlchemy)  
**Target Region:** Delhi-NCR Pilot Zone (Connaught Place, Lajpat Nagar, Nehru Place, Saket)  

---

## 1. Executive Summary & Objective

Every woman travelling through metropolitan urban centers like Delhi-NCR navigates an unwritten mental map of safety: assessing street lighting, avoiding deserted alleys, staying near bustling transit hubs, and planning departures around safe hours. Commercial navigation applications (such as Google Maps or Apple Maps) optimize exclusively for **shortest travel time** or **minimal fuel consumption**, frequently routing women through unlit, isolated service lanes or secluded shortcuts to save a few minutes.

**MAHILA SURAKSHA MARG** bridges this critical safety gap. Built entirely in Python with zero third-party frontend frameworks, it provides an intelligent, responsible multi-objective navigation system that computes:
1. **Safest Route:** Prioritising wide, well-illuminated arterial corridors, high pedestrian footfall, and immediate proximity to police stations and 24/7 metro stations.
2. **Balanced Route:** An optimal compromise between travel time and personal security.
3. **Fastest Route:** The direct physical trajectory with clear cautionary annotations.

Crucially, the system features a **continuous user-feedback learning loop**: direct ratings and community hazard reports dynamically update routing edge penalties and trigger automated retraining of the machine learning risk model.

---

## 2. System Architecture & Technical Stack

```
                                  [ User Interface ]
                       Streamlit Multi-Page App (Pure Python)
             ┌────────────────────────────────────────────────────────┐
             │  • 1_Plan_My_Route.py       • 2_SOS.py                 │
             │  • 3_Fake_Call.py           • 4_Safe_Spots.py          │
             │  • 5_Helplines.py           • 6_Trip_Sharing.py        │
             │  • 7_Community_Reports.py   • 8_Model_Insights.py      │
             └───────────────────────────┬────────────────────────────┘
                                         │
                                         ▼
                                 [ Core Engines ]
       ┌──────────────────┬──────────────────┬─────────────────┬─────────────────┐
       │   Route Engine   │  Safety Scoring  │  Risk ML Model  │ Feedback Engine │
       │  (OSMnx+NetworkX)│    (Formula)     │(RandomForest+SHAP)│ (Continuous ML) │
       └────────┬─────────┴────────┬─────────┴────────┬────────┴────────┬────────┘
                │                  │                  │                 │
                ▼                  ▼                  ▼                 ▼
       ┌─────────────────────────────────────────────────────────────────────────┐
       │                             Data Layer                                  │
       │  • OSM Street Graph (.graphml)      • Overpass GeoJSON Safety Spots     │
       │  • SQLite via SQLAlchemy (Reports, Contacts, Trips, Route Feedbacks)     │
       │  • Calibrated Synthetic Street Dataset • Nominatim Geocode Cache        │
       └─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Layer & Kaggle Dataset Honest Assessment

### Kaggle Dataset Reality Check
The historical raw crime datasets available in `archive/` (`crime_statistics_district_annual.csv`, `crime_statistics_state_annual.csv`, and `CRIME_DETAILS.csv`) provide district- and state-level annual FIR counts from the National Crime Records Bureau (NCRB).
- **Critical Finding:** None of these datasets contain micro-level street coordinates, time of day, street lighting status, or road classification.
- **Responsible AI Stance:** We **refuse** to fabricate fake street coordinates from district-level totals. Instead, the NCRB data is used solely to **calibrate** the temporal and categorical priors of our synthetic generator (e.g. higher vulnerability between 21:00–05:00, incident-type distributions).
- **Synthetic Ground Truth:** Every computer-generated record is explicitly tagged `is_synthetic=True`, and prominent warning banners inform users that the data supports student research.

---

## 4. Multi-Factor Safety Scoring Formula

The safety score $S \in [5, 98]$ is calculated as:

$$\text{Safety Score} = \max\left(5, \min\left(98, 100 \times (1 - \text{Total Penalty})\right)\right)$$

Where:
$$\text{Total Penalty} = \left(\sum_{i} w_i \cdot P_i\right) \times M_{\text{night}} + \Delta_{\text{feedback}}$$

### Weights Breakdown ($w_i$):
1. **Incident Density ($w_{\text{inc}} = 0.35$):** Density of historical/synthetic hazards with 90-day time decay.
2. **Street Lighting ($w_{\text{light}} = 0.20$):** OpenStreetMap `lit=yes` (0.05 penalty) vs `lit=no` (0.90 penalty).
3. **Police Proximity ($w_{\text{pol}} = 0.15$):** Normalized Euclidean distance to nearest verified police post.
4. **Transit & Metro Proximity ($w_{\text{transit}} = 0.10$):** Distance to operational DMRC metro stations.
5. **Hospital / Pharmacy ($w_{\text{hosp}} = 0.08$):** Distance to 24/7 medical trauma hubs.
6. **Road Classification ($w_{\text{road}} = 0.07$):** Primary arterial (0.10) vs residential (0.45) vs footway/service lane (0.80).
7. **Time of Day ($w_{\text{time}} = 0.05$):** Baseline diurnal traffic activity level.
8. **Night Risk Multiplier ($M_{\text{night}} = 1.30\times$):** Applied between 21:00 and 05:00.
9. **Feedback Modifier ($\Delta_{\text{feedback}} \in [-0.15, +0.25]$):** Live adjustment derived from community reviews.

---

## 5. User Feedback Model Enhancement Engine

A core innovation in MAHILA SURAKSHA MARG is the **Continuous Learning Pipeline**:
1. **Trip Rating Submissions:** Upon completing a route, women can submit an evaluation (1–5 stars, illumination rating, crowd activity, police sighting, and comments).
2. **Dynamic Edge Correction:** Corridors with high ratings and confirmed police presence receive immediate penalty discounts ($\Delta_{\text{feedback}} < 0$). Corridors with repeated discomfort receive safety warnings and positive penalty surcharges.
3. **Automated ML Retraining:** Users can trigger model retraining via the **Model Insights** page or CLI script (`scripts/07_retrain_from_feedback.py`). The engine converts real route feedback and community hazard reports into labeled training instances, oversamples user inputs, and re-fits the Random Forest model and SHAP attribution baselines.

---

## 6. Emergency Safety Toolkit

1. **One-Tap Emergency SOS:**
   - Prominent `tel:112`, `tel:1091`, and `tel:181` direct calling.
   - GPS broadcast generating instant Google Maps pin links (`https://www.google.com/maps?q={lat},{lon}`).
   - Automatic Twilio SMS dispatch with instant WhatsApp pre-filled link fallback.
2. **Disarming Fake Call Screen:**
   - Realistic incoming phone call simulation with customizable caller persona (e.g. *Inspector Rajesh Sharma* or *Dad*).
   - Audio script prompts to speak aloud and deter unsolicited approaches.
3. **Verified Safe Spots:**
   - Folium map with interactive filters for police stations, 24/7 hospitals, pharmacies, and CISF-monitored DMRC metro stations.
4. **Live Trip Sharing:**
   - Unique tokenized tracking link that family members can monitor in real time without downloading third-party tracking apps.
5. **Anonymous Community Reports:**
   - Crowdsourced hazard audit (poor lighting, harassment, isolated stretch, broken CCTV) protected by Hinglish NLP spam classifiers and 90-day time decay.

---

## 7. Responsible AI & Ethical Design

- **Supportive, Not Replacing:** Prominent disclaimers remind users on every page: *"Safer does not mean safe. This supports, not replaces, 112 and official emergency services."*
- **Non-Stigmatising Language:** We classify road segments by infrastructure variables (e.g., "Moderate Caution due to unlit stretch") and never stigmatise neighbourhoods or resident populations.
- **Privacy by Default:** Zero account creation required. Trusted contacts are stored strictly in local SQLite and can be completely wiped using the **"Delete My Data"** button.

---

## 8. Deployment & Add-to-Home-Screen (PWA)

### Streamlit Community Cloud Deployment
1. Push the repository to GitHub.
2. Link the repository to [share.streamlit.io](https://share.streamlit.io).
3. Set main file path: `app.py`.
4. Add any optional secrets (such as Twilio keys) in the Streamlit Cloud Secrets dashboard.

### Mobile Installation (Add to Home Screen)
1. Open the deployed web app URL in Chrome (Android) or Safari (iOS).
2. **On Android:** Tap browser menu (⋮) ➔ **"Add to Home Screen"** / **"Install App"**.
3. **On iOS:** Tap Share icon (⎋) ➔ **"Add to Home Screen"**.
4. The application installs as a standalone native-like mobile web app powered by `static/manifest.json`.

---

## 9. Future Roadmap & Production Scaling

1. **Integration with Delhi Police ERSS-112 CAD:** Direct API dispatch to police control rooms.
2. **Computer Vision CCTV Illumination Feeds:** Real-time ingestion of municipal CCTV luminosity sensors to automatically update street lighting tags.
3. **Offline Mobile Mesh SOS:** Bluetooth Low Energy (BLE) peer-to-peer alerting when cellular internet is unavailable.

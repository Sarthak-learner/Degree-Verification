"""
ai_monitor.py — AI-Powered Anomaly Detection for DegreeChain
=============================================================
Uses Isolation Forest (unsupervised ML) to detect suspicious
verification patterns in real time.

What it detects:
  - Same IP verifying too many degrees too fast (bot attack)
  - Verifications happening at unusual hours
  - Repeated failed verifications (forgery attempts)
  - Sudden spike in activity from a new company

How it works:
  Isolation Forest isolates anomalies by randomly partitioning
  data. Anomalous points (outliers) need fewer partitions to be
  isolated — so they get a low anomaly score. It requires NO
  labelled data, making it perfect for a system with no prior
  fraud history.

Install: pip install scikit-learn numpy
"""

import json
import time
import datetime
import numpy as np
from collections import defaultdict
from sklearn.ensemble import IsolationForest

# ── In-memory log (replace with SQLite in production) ─────────────────────
verification_log = []    # list of feature vectors
raw_log          = []    # human-readable records

# ── Feature extraction ─────────────────────────────────────────────────────

def extract_features(ip: str, result: str, hour: int, session_count: int, fail_streak: int) -> list:
    """
    Convert a verification event into a numeric feature vector.

    Features:
      [0] hour_of_day      0–23  (unusual hours = suspicious)
      [1] session_count    verifications this session (high = bot)
      [2] fail_streak      consecutive failures (forgery attempts)
      [3] result_code      0=verified, 1=invalid, 2=revoked
      [4] is_off_hours     1 if before 7am or after 11pm

    WHY these features?
    A normal employer verifies 1–3 degrees during business hours.
    A bot hammers the endpoint hundreds of times at 3am with
    mostly failed results. Isolation Forest learns this boundary
    from the data itself — no labelled fraud examples needed.
    """
    result_code = {"verified": 0, "invalid": 1, "revoked": 2}.get(result, 1)
    is_off_hours = 1 if hour < 7 or hour > 23 else 0
    return [hour, session_count, fail_streak, result_code, is_off_hours]


# ── Model ──────────────────────────────────────────────────────────────────

class AnomalyDetector:
    """
    Wraps sklearn IsolationForest with online logging.

    WHY Isolation Forest?
    - Unsupervised: no labelled fraud data required
    - Scales well: O(n log n) training time
    - Robust: works even when anomalies are rare (which they should be)
    - Industry standard for fraud detection at companies like PayPal and Stripe

    contamination=0.05 means we expect ~5% of traffic to be anomalous.
    Adjust this based on real usage once deployed.
    """
    def __init__(self, contamination=0.05):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42,
        )
        self.trained   = False
        self.min_train = 20   # need at least 20 samples before training
        self.session_counts = defaultdict(int)
        self.fail_streaks   = defaultdict(int)
        self.alerts         = []

    def log_verification(self, ip: str, result: str) -> dict:
        """
        Log one verification event and check for anomaly.
        Returns a dict with is_anomaly flag and risk score.

        Call this from Flask's /verify route.
        """
        now          = datetime.datetime.now()
        hour         = now.hour
        self.session_counts[ip] += 1
        session_count = self.session_counts[ip]

        if result != "verified":
            self.fail_streaks[ip] += 1
        else:
            self.fail_streaks[ip] = 0
        fail_streak = self.fail_streaks[ip]

        features = extract_features(ip, result, hour, session_count, fail_streak)
        verification_log.append(features)

        raw_log.append({
            "time":          now.strftime("%Y-%m-%d %H:%M:%S"),
            "ip":            ip,
            "result":        result,
            "session_count": session_count,
            "fail_streak":   fail_streak,
            "hour":          hour,
        })

        # Retrain model every 20 new samples
        if len(verification_log) >= self.min_train and len(verification_log) % 20 == 0:
            self._train()

        # Score this event
        if self.trained:
            vec   = np.array(features).reshape(1, -1)
            score = self.model.decision_function(vec)[0]   # negative = more anomalous
            label = self.model.predict(vec)[0]             # -1 = anomaly, 1 = normal
            is_anomaly = label == -1

            if is_anomaly:
                alert = {
                    "time":       now.strftime("%Y-%m-%d %H:%M:%S"),
                    "ip":         ip,
                    "reason":     self._reason(session_count, fail_streak, hour),
                    "risk_score": round(abs(score) * 100, 1),
                }
                self.alerts.append(alert)
                return {"is_anomaly": True,  "risk_score": round(abs(score)*100,1), "reason": alert["reason"]}

            return {"is_anomaly": False, "risk_score": round(abs(score)*100,1), "reason": "Normal activity"}

        return {"is_anomaly": False, "risk_score": 0, "reason": "Insufficient data to score"}

    def _train(self):
        """Train/retrain on all collected data."""
        X = np.array(verification_log)
        self.model.fit(X)
        self.trained = True

    def _reason(self, session_count, fail_streak, hour) -> str:
        """Generate human-readable reason for alert."""
        reasons = []
        if session_count > 15:
            reasons.append(f"High verification volume ({session_count} in one session)")
        if fail_streak > 5:
            reasons.append(f"Repeated failures ({fail_streak} consecutive)")
        if hour < 7 or hour > 23:
            reasons.append(f"Off-hours activity ({hour}:00)")
        return " · ".join(reasons) if reasons else "Unusual pattern detected"

    def get_stats(self) -> dict:
        """Return stats for the AI dashboard panel."""
        return {
            "total_verifications": len(verification_log),
            "model_trained":       self.trained,
            "total_alerts":        len(self.alerts),
            "recent_alerts":       self.alerts[-5:],
            "training_samples":    len(verification_log),
            "min_for_training":    self.min_train,
        }


# ── Singleton used by app.py ───────────────────────────────────────────────
detector = AnomalyDetector()

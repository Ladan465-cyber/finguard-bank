# ML Roadmap: From Rule Engine to Trained Model

The current FinShield engine (`backend/app/services/fraud_engine.py`) is a
**transparent, weighted rule-based system** — not machine learning. This is
intentional for a hackathon MVP: it's explainable, auditable, and doesn't
need a training dataset to work correctly on day one.

The module is structured so it can evolve into the pipeline below without
changing the API layer, the database schema, or the frontend:

```
Historical data (transactions, behaviour profiles)
        |
        v
Feature engineering  -- extract_features() in fraud_engine.py
        |                (already isolated from scoring logic)
        v
   ML model           -- would replace score_transaction()'s rule loop
        |                with model.predict_proba(features)
        v
Fraud probability / anomaly score  (0-100, same scale as today)
        |
        v
Decision engine       -- UNCHANGED: transaction_service.py's
        |                LOW/MEDIUM/HIGH/CRITICAL -> action mapping
        v
Verification / block / approval
```

## Why the split matters

`extract_features()` returns a plain `FeatureSet` dataclass -- a fixed set
of numeric/boolean fields per transaction. `score_transaction()` is the
only function that currently turns those features into a score. Swapping
rule-based scoring for a model means replacing the body of
`score_transaction()` with something like:

```python
def score_transaction(db, features, rule_version):
    X = features_to_vector(features)          # same FeatureSet in
    fraud_probability = model.predict_proba(X)[0][1]
    score = fraud_probability * 100
    factors = explain_with_shap(model, X)      # feature attribution
    ...
```

Nothing upstream (transaction_service.py) or downstream (the routers, the
frontend, the admin dashboard) needs to change, because they only consume
`RiskAssessment` (score + level + factor list).

## Suggested approach for a real model

1. **Data**: once enough real (or synthetic, e.g. PaySim-style) labelled
   transactions exist, export `transactions` + `user_behavior_profiles` as
   training data.
2. **Labels**: use `fraud_events.status` (`resolved_fraud` /
   `resolved_legitimate`) as ground truth -- this is exactly what the admin
   "Confirmed fraud / Confirmed legitimate" buttons produce, so the system
   is already collecting its own training labels as it operates.
3. **Model**: start with a supervised classifier (e.g. XGBoost /
   scikit-learn GradientBoosting) on the same features
   `extract_features()` already computes, or an unsupervised anomaly
   detector (e.g. Isolation Forest) if labelled fraud examples are scarce.
4. **Explainability**: keep per-transaction reason codes (e.g. via SHAP
   values or simple feature-importance thresholds) so the admin dashboard
   can keep showing "why was this flagged" -- this is a hard requirement
   for a banking fraud product, not a nice-to-have.
5. **Rollout**: run the model in shadow mode (score every transaction with
   both the rule engine and the model, log both, compare) before switching
   `score_transaction()` over, and keep `fraud_rule_version` /
   a new `model_version` field so every historical decision stays
   auditable against the exact logic that produced it.

Do not present the current rule engine as if it were the trained model --
it isn't, and reviewers who ask about the ML approach should be told
plainly that this MVP uses a transparent rule engine with the architecture
above intentionally left ready for a model to be dropped in.

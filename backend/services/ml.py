"""
services/ml.py
==============
Loads trained XGBoost models at startup and exposes predict_price().
Called by routers/ml.py.
"""

import os
import numpy as np
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_DIR = os.path.join(BASE_DIR, "models_store")

_models = {}


def load_models():
    """Load both buy and rent models from disk. Called on server startup."""
    global _models
    for purpose in ["buy", "rent"]:
        path = os.path.join(STORE_DIR, f"price_model_{purpose}.joblib")
        if os.path.exists(path):
            _models[purpose] = joblib.load(path)
            print(f"[ML] Loaded '{purpose}' model  R²={_models[purpose]['r2']:.3f}  MAE=₹{_models[purpose]['mae']:,.0f}")
        else:
            print(f"[ML] Warning: No model for '{purpose}' at {path}")
            print(f"[ML] Run: python -m backend.scripts.train_model")
        
def predict_price(
    city: str,
    property_type: str,
    purpose: str,
    bedrooms: int   = 2,
    bathrooms: int  = 2,
    area: float     = 1000.0,
    furnishing: int = 1,   # 0=Unfurnished 1=Semi-Furnished 2=Furnished
    locality: str   = None,
) -> dict:
    """
    Predict property price.

    Returns:
        predicted_price : int
        price_range     : { low: int, high: int }  — ±error band, capped at 50%
        confidence      : "high" | "medium" | "low"
        model_r2        : float
    """
    if purpose not in _models:
        return {"error": f"Model for '{purpose}' not loaded. Run train_model.py first."}

    payload      = _models[purpose]
    model        = payload["model"]
    encoders     = payload["encoders"]
    locality_map = payload["locality_map"]
    global_med   = payload["global_median"]
    r2           = payload["r2"]
    mae          = payload["mae"]

    def safe_encode(le, value):
        classes = list(le.classes_)
        return le.transform([value])[0] if value in classes else 0

    city_enc    = safe_encode(encoders["city"],          city.strip().title())
    type_enc    = safe_encode(encoders["property_type"], property_type)
    purpose_enc = safe_encode(encoders["purpose"],       purpose)

    loc_key        = locality.strip().title() if locality else city.strip().title()
    locality_price = locality_map.get(loc_key, global_med)

    X = np.array([[city_enc, type_enc, purpose_enc,
                   bedrooms, bathrooms, area, furnishing, locality_price]])

    log_pred  = model.predict(X)[0]
    predicted = int(np.expm1(log_pred))

    # ── Price range: MAE expressed as a % of this specific prediction ──────
    error_pct = mae / max(predicted, 1)   # relative error for this prediction
    error_pct = min(error_pct, 0.5)        # cap at ±50% to avoid absurd ranges

    low  = max(0, int(predicted * (1 - error_pct)))
    high = int(predicted * (1 + error_pct))

    if r2 >= 0.80:
        confidence = "high"
    elif r2 >= 0.65:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "predicted_price": predicted,
        "price_range":     {"low": low, "high": high},
        "confidence":      confidence,
        "model_r2":        round(r2, 3),
        "model_mae":       int(mae),
    }
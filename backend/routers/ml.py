"""
routers/ml.py — ML-powered endpoints
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from .. import oauth2
from ..database import get_db
from ..services.ml import predict_price
from typing import Optional
from enum import Enum

router = APIRouter(prefix="/ml", tags=["ML"])


class FurnishingStatus(str, Enum):
    unfurnished  = "unfurnished"
    semi         = "semi-furnished"
    furnished    = "furnished"


FURNISHING_MAP = {
    "unfurnished":   0,
    "semi-furnished": 1,
    "furnished":     2,
}

PROPERTY_TYPE_MAP = {
    "flat":       "apartment",
    "apartment":  "apartment",
    "house":      "house",
    "plot":       "house",
    "commercial": "house",
}


@router.get("/price-estimate")
def get_price_estimate(
    city:          str            = Query(...,    description="City e.g. Delhi, Mumbai, Bangalore"),
    property_type: str            = Query(...,    description="apartment | flat | house | plot | commercial"),
    purpose:       str            = Query(...,    description="buy | rent"),
    bedrooms:      Optional[int]  = Query(2,      ge=1, le=10),
    bathrooms:     Optional[int]  = Query(2,      ge=1, le=10),
    area:          Optional[float]= Query(1000.0, ge=100, description="Carpet area in sq ft"),
    furnishing:    Optional[str]  = Query("semi-furnished", description="unfurnished | semi-furnished | furnished"),
    locality:      Optional[str]  = Query(None,   description="Neighbourhood e.g. Lajpat Nagar (optional)"),
    db: Session = Depends(get_db),
    current_user  = Depends(oauth2.get_current_user),
):
    """
    Predict property price based on location and property features.

    Example:
        GET /ml/price-estimate?city=Delhi&property_type=apartment&purpose=buy&bedrooms=3&area=1200&furnishing=furnished&locality=Lajpat Nagar
    """
    purpose_clean = purpose.lower().strip()
    if purpose_clean not in ("buy", "rent"):
        raise HTTPException(400, "purpose must be 'buy' or 'rent'")

    mapped_type       = PROPERTY_TYPE_MAP.get(property_type.lower(), "apartment")
    furnishing_int    = FURNISHING_MAP.get((furnishing or "semi-furnished").lower(), 1)

    result = predict_price(
        city          = city,
        property_type = mapped_type,
        purpose       = purpose_clean,
        bedrooms      = bedrooms,
        bathrooms     = bathrooms,
        area          = area,
        furnishing    = furnishing_int,
        locality      = locality,
    )

    if "error" in result:
        raise HTTPException(503, detail=result["error"])

    return {
        "input": {
            "city":          city,
            "locality":      locality,
            "property_type": property_type,
            "purpose":       purpose,
            "bedrooms":      bedrooms,
            "bathrooms":     bathrooms,
            "area_sqft":     area,
            "furnishing":    furnishing,
        },
        "predicted_price": result["predicted_price"],
        "price_range":     result["price_range"],
        "confidence":      result["confidence"],
        "model_r2":        result["model_r2"],
        "note": (
            f"Estimate for {purpose} properties in "
            f"{locality + ', ' if locality else ''}{city}. "
            f"Model R²: {result['model_r2']} | "
            f"Typical error: ₹{result['model_mae']:,}"
        ),
    }


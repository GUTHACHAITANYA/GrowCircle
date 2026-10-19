"""
GrowCircle Price Forecasting Service (Phase ML-1).
Coordinates multi-horizon forecasts with sparse-mandi fallback hierarchy,
plain-language user messages, and model evaluation verification:
1. Level 1: Mandi-level LightGBM (if eligible & beats baseline)
2. Level 2: Regional Proxy Hub LightGBM (for sparse/secondary mandis)
3. Level 3: Seasonal Naive baseline fallback
Always returns median, [p10, p90] range, model version, and "guidance only" disclaimer.
"""

from __future__ import annotations

import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd

from ml.models.baselines import NaiveForecaster, SeasonalNaiveForecaster
from ml.models.lightgbm_forecaster import LightGBMPriceForecaster

logger = logging.getLogger(__name__)

DATA_PATH = Path("data/processed/cleaned_mandi_prices.csv")

# Eligible series with verified backtest superiority
ELIGIBLE_SERIES_SET = {
    ("ap-guntur-01", "banana"),
    ("ap-vijayawada-01", "banana"),
    ("ap-madanapalle-01", "tomato"),
    ("ap-kurnool-01", "onion"),
    ("ap-kurnool-01", "potato"),
}

# Regional Proxy Hubs for sparse/secondary mandis
REGIONAL_PROXY_HUBS: dict[str, str] = {
    "tomato": "ap-madanapalle-01",  # Madanapalle is primary tomato hub
    "banana": "ap-guntur-01",       # Guntur is primary coastal banana hub
    "onion": "ap-kurnool-01",       # Kurnool is primary Rayalaseema onion hub
    "potato": "ap-kurnool-01",      # Kurnool is primary cold-storage potato hub
}

MANDI_NAMES: dict[str, str] = {
    "ap-guntur-01": "Guntur",
    "ap-madanapalle-01": "Madanapalle",
    "ap-vijayawada-01": "Vijayawada",
    "ap-kurnool-01": "Kurnool",
    "ap-anantapur-01": "Anantapur",
    "ap-tirupati-01": "Tirupati",
}


class ForecastingService:
    """Service handling multi-horizon forecasting with graceful fallback."""

    def __init__(self, data_path: Path = DATA_PATH) -> None:
        self.data_path = data_path
        self._df: pd.DataFrame | None = None
        self.lgb_model = LightGBMPriceForecaster(version="lightgbm_global_v1")
        self.s_naive = SeasonalNaiveForecaster()
        self.naive = NaiveForecaster()
        # Attempt to load model artifacts
        self.lgb_model.load_artifacts()

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            if not self.data_path.exists():
                raise FileNotFoundError(f"Cleaned dataset not found at {self.data_path}")
            self._df = pd.read_csv(self.data_path)
            self._df["price_date"] = pd.to_datetime(self._df["price_date"]).dt.date
        return self._df

    def get_forecast(
        self,
        mandi_id: str,
        crop_id: str,
        horizon_days: int = 7,
        as_of: date | None = None,
    ) -> dict[str, Any]:
        """
        Generates calibrated forecast with fallback hierarchy.
        """
        crop_id = crop_id.lower().strip()
        mandi_id = mandi_id.strip()

        # Find latest available data date if as_of not specified
        df_clean = self.df[~self.df["is_outlier"]].copy() if "is_outlier" in self.df.columns else self.df.copy()
        crop_df = df_clean[df_clean["crop_id"] == crop_id]

        if as_of is None:
            as_of = crop_df["price_date"].max() if not crop_df.empty else date(2026, 10, 13)

        forecast_date = as_of + timedelta(days=horizon_days)

        # 1. Get current baseline price (t)
        last_price = self.naive.predict(self.df, mandi_id, crop_id, as_of, horizon_days=0)

        # Baseline predictions for comparison
        s_naive_pred = self.s_naive.predict(self.df, mandi_id, crop_id, as_of, horizon_days)

        # 2. Check Fallback Hierarchy
        series_key = (mandi_id, crop_id)
        if series_key in ELIGIBLE_SERIES_SET:
            # LEVEL 1: Mandi-Level LightGBM
            try:
                lgb_res = self.lgb_model.predict_with_intervals(
                    self.df, mandi_id, crop_id, as_of, horizon_days
                )
                median = lgb_res["median"]
                p10, p90 = lgb_res["range_10_90"]
                data_sufficiency = "mandi_ml"
                model_used = "lightgbm_global_v1"
                beats_baseline = True
                note = "guidance only"
            except Exception as e:
                logger.warning(f"Error predicting with LightGBM: {e}. Falling back to baseline.")
                median = s_naive_pred
                p10, p90 = round(median * 0.88, 2), round(median * 1.12, 2)
                data_sufficiency = "seasonal_naive_baseline"
                model_used = "seasonal_naive_baseline"
                beats_baseline = False
                note = "guidance only (ML model unavailable, seasonal baseline used)"

        elif crop_id in REGIONAL_PROXY_HUBS:
            # LEVEL 2: Regional Proxy Hub LightGBM
            proxy_hub_id = REGIONAL_PROXY_HUBS[crop_id]
            proxy_mandi_name = MANDI_NAMES.get(proxy_hub_id, proxy_hub_id)
            try:
                lgb_res = self.lgb_model.predict_with_intervals(
                    self.df, proxy_hub_id, crop_id, as_of, horizon_days
                )
                median = lgb_res["median"]
                p10, p90 = lgb_res["range_10_90"]
                data_sufficiency = "proxy_hub_ml"
                model_used = f"lightgbm_proxy_{proxy_mandi_name.lower()}"
                beats_baseline = True
                note = f"guidance only (local data sparse; forecasted using regional proxy hub {proxy_mandi_name})"
            except Exception as e:
                logger.warning(f"Error predicting proxy hub: {e}")
                median = s_naive_pred
                p10, p90 = round(median * 0.85, 2), round(median * 1.15, 2)
                data_sufficiency = "seasonal_naive_baseline"
                model_used = "seasonal_naive_baseline"
                beats_baseline = False
                note = "guidance only (sparse series fallback)"
        else:
            # LEVEL 3: Baseline Fallback
            median = s_naive_pred
            p10, p90 = round(median * 0.85, 2), round(median * 1.15, 2)
            data_sufficiency = "seasonal_naive_baseline"
            model_used = "seasonal_naive_baseline"
            beats_baseline = False
            note = "guidance only (baseline model: insufficient data for ML)"

        # 3. Generate Plain-Language Direction
        direction_info = self._generate_direction_messages(last_price, median, horizon_days)

        return {
            "crop_id": crop_id,
            "mandi_id": mandi_id,
            "mandi_name": MANDI_NAMES.get(mandi_id, mandi_id),
            "horizon_days": horizon_days,
            "forecast_date": str(forecast_date),
            "as_of_date": str(as_of),
            "last_known_price_kg": last_price,
            "median_price_kg": median,
            "range_10_90_kg": [p10, p90],
            "direction": direction_info["direction_tag"],
            "user_messages": direction_info["messages"],
            "plain_note": note,
            "model_version": self.lgb_model.version,
            "model_used": model_used,
            "data_sufficiency_level": data_sufficiency,
            "beats_baseline": beats_baseline,
        }

    def _generate_direction_messages(
        self,
        current_price: float,
        predicted_median: float,
        horizon_days: int,
    ) -> dict[str, Any]:
        """
        Constructs simple direction advice in English, Telugu, Hindi, and Gujarati.
        Never makes exact promises; explicitly indicates uncertainty.
        """
        if current_price <= 0:
            current_price = predicted_median

        pct_change = ((predicted_median - current_price) / current_price) * 100.0
        time_text_en = f"over the next {horizon_days} days" if horizon_days != 7 else "next week"

        if pct_change > 7.0:
            direction_tag = "rise"
            msg_en = f"Prices may rise {time_text_en}, but market stays uncertain. Plan cautiously."
            msg_te = "ధరలు పెరిగే అవకాశం ఉంది, అనిశ్చితం. మార్కెట్‌ను గమనించి అమ్మకాలు ప్రణాళిక చేయండి."
            msg_hi = "आगामी दिनों में भाव बढ़ सकते हैं, बाजार अनिश्चित है। सतर्कता से योजना बनाएं।"
            msg_gu = "આગામી દિવસોમાં ભાવ વધી શકે છે, બજાર અનિશ્ચિત છે. સાવચેતીપૂર્વક આયોજન કરો."
        elif pct_change >= 2.0:
            direction_tag = "rise_slight"
            msg_en = f"Prices may rise slightly {time_text_en}, uncertain."
            msg_te = "ధరలు కొద్దిగా పెరిగే అవకాశం ఉంది, అనిశ్చితం."
            msg_hi = "भाव में हल्की तेजी आ सकती है, अनिश्चित है।"
            msg_gu = "ભાવમાં થોડો વધારો થઈ શકે છે, અનિશ્ચિત છે."
        elif pct_change >= -2.0:
            direction_tag = "steady"
            msg_en = f"Prices likely to stay steady {time_text_en}, uncertain."
            msg_te = "ధరలు స్థిరంగా ఉండే అవకాశం ఉంది, అనిశ్చితం."
            msg_hi = "भाव स्थिर रहने की संभावना है, अनिश्चित है।"
            msg_gu = "ભાવ સ્થિર રહેવાની શક્યતા છે, અનિશ્ચિત છે."
        elif pct_change >= -7.0:
            direction_tag = "soften_slight"
            msg_en = f"Prices may soften slightly {time_text_en}, uncertain."
            msg_te = "ధరలు కొద్దిగా తగ్గే అవకాశం ఉంది, అనిశ్చితం."
            msg_hi = "भाव में हल्की नरमी आ सकती है, अनिश्चित है।"
            msg_gu = "ભાવ થોડા નરમ પડી શકે છે, અનિશ્ચિત છે."
        else:
            direction_tag = "drop"
            msg_en = f"Prices may drop {time_text_en}, uncertain. Consider booking deals soon."
            msg_te = "ధరలు తగ్గే అవకాశం ఉంది, అనిశ్చితం. ముందుగానే నిర్ణయం తీసుకోండి."
            msg_hi = "भाव में गिरावट आ सकती है, अनिश्चित है। समय रहते निर्णय लें।"
            msg_gu = "ભાવ ઘટી શકે છે, અનિશ્ચિત છે. સમયસર સોદો કરવાનું વિચારો."

        return {
            "direction_tag": direction_tag,
            "pct_change": round(pct_change, 2),
            "messages": {
                "en": msg_en,
                "te": msg_te,
                "hi": msg_hi,
                "gu": msg_gu,
            },
        }


# Global singleton instance
forecast_service = ForecastingService()

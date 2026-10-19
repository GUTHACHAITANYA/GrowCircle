"""
Consumer Service: Seasonality analysis ("Is it expensive this month?"),
multilingual crops catalog, and price alert management.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.crop import Crop
from backend.app.models.price import Price
from backend.app.models.price_alert import PriceAlert
from backend.app.schemas.consumer import (
    CropOut,
    PriceAlertCreate,
    PriceAlertOut,
    SeasonalityAnalysis,
)

# Standard benchmark modal prices (₹/kg) across seasons in Andhra Pradesh (fallback if history < 14 days)
SEASONAL_BENCHMARKS_KG: dict[str, float] = {
    "banana": 24.0,
    "tomato": 28.0,
    "onion": 32.0,
    "chilli": 65.0,
}


class ConsumerService:
    @staticmethod
    async def get_all_crops(db: AsyncSession) -> list[CropOut]:
        """Returns all available crops with localized names."""
        result = await db.execute(select(Crop).order_by(Crop.category, Crop.name_en))
        crops = result.scalars().all()
        return [CropOut.model_validate(c) for c in crops]

    @staticmethod
    async def analyze_seasonality(
        db: AsyncSession, crop_id: str, district: str = "Guntur"
    ) -> SeasonalityAnalysis:
        """
        Determines whether a crop is expensive, fair, or cheap this month.
        Compares latest modal mandi price against past 60-day historical average.
        """
        crop_slug = crop_id.lower().strip()
        now_date = datetime.now(UTC).date()
        cutoff_date = now_date - timedelta(days=60)

        # 1. Fetch latest modal price
        latest_price_obj = await db.scalar(
            select(Price)
            .where(Price.crop_id == crop_slug)
            .order_by(desc(Price.price_date))
            .limit(1)
        )
        current_modal = float(latest_price_obj.modal_price_kg) if latest_price_obj else 26.0

        # 2. Fetch benchmark average from prior dates (excluding today/latest date)
        latest_date = latest_price_obj.price_date if latest_price_obj else now_date
        count_history = await db.scalar(
            select(func.count(Price.id)).where(
                Price.crop_id == crop_slug,
                Price.price_date >= cutoff_date,
                Price.price_date < latest_date,
            )
        )

        if count_history and count_history >= 3:
            history_avg = await db.scalar(
                select(func.avg(Price.modal_price_kg)).where(
                    Price.crop_id == crop_slug,
                    Price.price_date >= cutoff_date,
                    Price.price_date < latest_date,
                )
            )
            benchmark = float(history_avg) if history_avg else SEASONAL_BENCHMARKS_KG.get(crop_slug, 25.0)
        else:
            benchmark = SEASONAL_BENCHMARKS_KG.get(crop_slug, 25.0)

        diff = current_modal - benchmark
        pct_diff = round((diff / benchmark) * 100, 1)

        if pct_diff > 10.0:
            status = "expensive"
            is_expensive = True
            verdict = (
                f"Expensive this month (+{pct_diff}% vs seasonal benchmark). "
                f"Current: ₹{current_modal:.1f}/kg (typical: ₹{benchmark:.1f}/kg)."
            )
            tip = (
                "Supply is temporarily tighter due to lower market arrivals. "
                "Consider buying in moderate quantities or waiting for next week's harvests."
            )
        elif pct_diff < -10.0:
            status = "cheap"
            is_expensive = False
            verdict = (
                f"Affordable / Great time to buy ({pct_diff}% below seasonal benchmark). "
                f"Current: ₹{current_modal:.1f}/kg (typical: ₹{benchmark:.1f}/kg)."
            )
            tip = (
                "Peak harvesting season in nearby mandis! "
                "Excellent time to stock up for families, hostels, and bulk buyers."
            )
        else:
            status = "fair"
            is_expensive = False
            verdict = (
                f"Fair / Normal market price this month (within {abs(pct_diff)}% of baseline). "
                f"Current: ₹{current_modal:.1f}/kg."
            )
            tip = "Prices are stable with steady daily arrivals across regional mandis."

        return SeasonalityAnalysis(
            crop_id=crop_slug,
            district=district,
            current_modal_price_kg=round(current_modal, 2),
            benchmark_price_kg=round(benchmark, 2),
            percentage_difference=pct_diff,
            is_expensive=is_expensive,
            status=status,
            plain_language_verdict=verdict,
            seasonality_tip=tip,
        )

    @staticmethod
    async def create_alert(db: AsyncSession, alert_data: PriceAlertCreate) -> PriceAlertOut:
        """Subscribes a consumer for WhatsApp / Telegram price alerts without requiring login."""
        alert = PriceAlert(
            user_phone=alert_data.user_phone.strip(),
            channel=alert_data.channel.lower().strip(),
            telegram_chat_id=alert_data.telegram_chat_id,
            crop_id=alert_data.crop_id.lower().strip(),
            district=alert_data.district.strip(),
            alert_type=alert_data.alert_type.lower().strip(),
            target_price_kg=alert_data.target_price_kg,
            is_active=True,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        return PriceAlertOut.model_validate(alert)

    @staticmethod
    async def list_user_alerts(db: AsyncSession, phone: str) -> list[PriceAlertOut]:
        """Lists active alerts for a user phone."""
        result = await db.execute(
            select(PriceAlert)
            .where(PriceAlert.user_phone == phone.strip())
            .order_by(desc(PriceAlert.created_at))
        )
        alerts = result.scalars().all()
        return [PriceAlertOut.model_validate(a) for a in alerts]

    @staticmethod
    async def delete_alert(db: AsyncSession, alert_id: int, phone: str) -> bool:
        """Unsubscribes / deletes an alert."""
        alert = await db.scalar(
            select(PriceAlert).where(
                PriceAlert.id == alert_id,
                PriceAlert.user_phone == phone.strip(),
            )
        )
        if not alert:
            return False
        await db.delete(alert)
        await db.commit()
        return True

"""
Seed script for Phase 1: Andhra Pradesh Mandis and Banana Prices.
Inserts:
- Banana crop with multilingual translations
- AP mandis with PostGIS coordinates
- Today's prices + 30-day price history for charts
"""

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select

from backend.app.db.session import get_sync_db
from backend.app.models.crop import Crop
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price
from backend.app.services.agmarknet import AgmarknetService
from backend.app.services.data_quality import quintal_to_kg, quintal_to_ton

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def seed() -> None:
    db = get_sync_db()
    try:
        logger.info("Seeding Phase 1 data...")

        # 1. Seed Banana Crop
        crop = db.scalar(select(Crop).where(Crop.id == "banana"))
        if not crop:
            crop = Crop(
                id="banana",
                name_en="Banana",
                name_te="అరటిపండు",
                name_hi="केला",
                name_gu="કેળા",
                icon="banana",
                category="fruit",
            )
            db.add(crop)
            db.commit()
            logger.info("Seeded Banana crop record.")

        # 2. Ingest today's sample prices
        sample_file = DATA_DIR / "sample_ap_banana.json"
        if sample_file.exists():
            with open(sample_file, encoding="utf-8") as f:
                records = json.load(f)
                AgmarknetService.ingest_records(db, records)
                logger.info(f"Ingested {len(records)} active mandi records.")

        # 3. Seed 30-day historical time-series for Guntur mandi (for charts in demo mode only)
        import os
        if os.getenv("APP_MODE") == "production":
            logger.info("APP_MODE=production: skipping synthetic price history seeding.")
            return

        guntur = db.scalar(select(Mandi).where(Mandi.name == "Guntur"))
        if guntur:
            today = date.today()
            # Historical base price ~2400 with realistic agricultural fluctuation
            base_modal = 2450.0
            import math

            for days_ago in range(1, 31):
                past_date = today - timedelta(days=days_ago)
                # Seasonal curve + slight daily noise
                fluctuation = int(120 * math.sin(days_ago / 4.0) + (days_ago % 5) * 15)
                modal_q = base_modal + fluctuation
                min_q = modal_q - 250
                max_q = modal_q + 300

                # Check if exists
                existing = db.scalar(
                    select(Price).where(
                        Price.mandi_id == guntur.id,
                        Price.crop_id == "banana",
                        Price.price_date == past_date,
                    )
                )
                if not existing:
                    hist_price = Price(
                        mandi_id=guntur.id,
                        crop_id="banana",
                        variety="Amruthapani",
                        grade="FAQ",
                        price_date=past_date,
                        min_price_quintal=min_q,
                        max_price_quintal=max_q,
                        modal_price_quintal=modal_q,
                        min_price_kg=quintal_to_kg(min_q),
                        max_price_kg=quintal_to_kg(max_q),
                        modal_price_kg=quintal_to_kg(modal_q),
                        modal_price_ton=quintal_to_ton(modal_q),
                        arrival_tonnes=round(40.0 + (days_ago % 7) * 4.5, 1),
                        source="demo",
                    )
                    db.add(hist_price)

            db.commit()
            logger.info("Seeded 30-day demo price series for Guntur Mandi (source='demo').")

        logger.info("Seed process completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

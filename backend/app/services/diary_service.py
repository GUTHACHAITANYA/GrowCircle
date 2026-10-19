"""
Farm Diary Service: Economics calculations, voice parsing & read-back generation,
Mandi benchmark comparison, and CSV/JSON export.
"""

import csv
import io
import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.farm_diary import FarmDiaryEntry, FarmSeason
from backend.app.models.price import Price
from backend.app.schemas.diary import (
    FarmDiaryEntryCreate,
    MandiComparison,
    SeasonFinancialMetrics,
    VoiceConfirmationReadBack,
)


class FarmDiaryService:
    @staticmethod
    def parse_voice_entry(
        transcript: str, entry_date: date | None = None
    ) -> VoiceConfirmationReadBack:
        """
        Parses spoken farmer entry into a structured FarmDiaryEntryCreate
        and generates multilingual read-back confirmation strings.
        e.g. "Spent 8000 on labour for weeding" -> category: labour, amount: 8000
        """
        text = transcript.lower().strip()
        record_date = entry_date or date.today()

        # Extract number (amount or quantity)
        numbers = re.findall(r"\b\d+(?:\.\d+)?\b", text)
        first_num = float(numbers[0]) if numbers else 0.0

        # Classify entry type & category
        entry_type = "cost"
        category = "other"
        amount_inr = 0.0
        quantity_kg = 0.0
        unit_price = 0.0

        if any(w in text for w in ["harvest", "picked", "yield", "కోత", "దిగుబడి", "उपज", "કાપણી"]):
            entry_type = "yield_log"
            category = "harvest"
            quantity_kg = first_num
        elif any(w in text for w in ["sold", "sale", "అమ్మాము", "విక్రయం", "बेचा", "વેચાણ"]):
            entry_type = "sale_revenue"
            category = "sale"
            if len(numbers) >= 2:
                quantity_kg = float(numbers[0])
                unit_price = float(numbers[1])
                amount_inr = quantity_kg * unit_price
            else:
                amount_inr = first_num
        elif any(w in text for w in ["labour", "worker", "coolie", "కూలీ", "మజ్దూర్", "मजदूर", "મજૂર"]):
            entry_type = "cost"
            category = "labour"
            amount_inr = first_num
        elif any(w in text for w in ["seed", "sapling", "plants", "విత్తనాలు", "మొక్కలు", "बीज", "બિયારણ"]):
            entry_type = "cost"
            category = "seeds"
            amount_inr = first_num
        elif any(w in text for w in ["fertilizer", "urea", "dap", "ఎరువులు", "ఎరువు", "उर्वरक", "ખાતર"]):
            entry_type = "cost"
            category = "fertilizer"
            amount_inr = first_num
        elif any(w in text for w in ["irrigation", "water", "నీరు", "తడి", "सिंचाई", "પાણી"]):
            entry_type = "cost"
            category = "irrigation"
            amount_inr = first_num
        elif any(w in text for w in ["tractor", "diesel", "machine", "ట్రాక్టర్", "యంత్రం", "ट्रैक्टर", "ટ્રેક્ટર"]):
            entry_type = "cost"
            category = "machinery"
            amount_inr = first_num
        elif any(w in text for w in ["transport", "auto", "lorry", "రవాణా", "परिवहन", "વાહન"]):
            entry_type = "cost"
            category = "transport"
            amount_inr = first_num
        else:
            entry_type = "cost"
            category = "other"
            amount_inr = first_num

        parsed = FarmDiaryEntryCreate(
            entry_type=entry_type,
            category=category,
            amount_inr=amount_inr,
            quantity_kg=quantity_kg,
            unit_price_inr=unit_price,
            entry_date=record_date,
            notes=transcript,
            voice_raw_text=transcript,
            readback_confirmed=True,
        )

        # Multilingual read-back confirmation phrasing
        if entry_type == "cost":
            readback_en = (
                f"Confirming cost: ₹{int(amount_inr)} spent on {category.title()} on {record_date}. Save this entry?"
            )
            readback_te = f"ధృవీకరణ: {record_date}న {category} కోసం ₹{int(amount_inr)} ఖర్చు నమోదు చేయమంటారా?"
            readback_hi = (
                f"पुष्टि करें: {record_date} को {category} पर ₹{int(amount_inr)} का खर्च दर्ज करें?"
            )
            readback_gu = (
                f"ખાતરી કરો: {record_date} ના રોજ {category} પાછળ ₹{int(amount_inr)} નો ખર્ચ નોંધવો છે?"
            )
        elif entry_type == "yield_log":
            readback_en = (
                f"Confirming harvest: {int(quantity_kg)} kg logged on {record_date}. Save this entry?"
            )
            readback_te = f"ధృవీకరణ: {record_date}న {int(quantity_kg)} కిలోల దిగుబడి నమోదు చేయమంటారా?"
            readback_hi = (
                f"पुष्टि करें: {record_date} को {int(quantity_kg)} किग्रा उपज दर्ज करें?"
            )
            readback_gu = (
                f"ખાતરી કરો: {record_date} ના રોજ {int(quantity_kg)} કિગ્રા પાક નોંધવો છે?"
            )
        else:
            readback_en = (
                f"Confirming produce sale: ₹{int(amount_inr)} revenue logged on {record_date}. Save this entry?"
            )
            readback_te = f"ధృవీకరణ: {record_date}న ₹{int(amount_inr)} అమ్మకం ఆదాయం నమోదు చేయమంటారా?"
            readback_hi = (
                f"पुष्टि करें: {record_date} को ₹{int(amount_inr)} की बिक्री आय दर्ज करें?"
            )
            readback_gu = (
                f"ખાતરી કરો: {record_date} ના રોજ ₹{int(amount_inr)} નું વેચાણ નોંધવું છે?"
            )

        token = f"CONFIRM-{int(record_date.strftime('%Y%m%d'))}-{int(amount_inr or quantity_kg)}"

        return VoiceConfirmationReadBack(
            transcription=transcript,
            parsed_entry=parsed,
            readback_text_en=readback_en,
            readback_text_te=readback_te,
            readback_text_hi=readback_hi,
            readback_text_gu=readback_gu,
            confirmation_token=token,
        )

    @staticmethod
    async def calculate_season_metrics(
        db: AsyncSession, season_id: int
    ) -> SeasonFinancialMetrics:
        """
        Calculates profit and loss per acre, break-even price, and
        compares actual sale price with the district mandi average over the season.
        """
        season = await db.scalar(select(FarmSeason).where(FarmSeason.id == season_id))
        if not season:
            raise ValueError(f"FarmSeason #{season_id} not found")

        entries_result = await db.execute(
            select(FarmDiaryEntry).where(FarmDiaryEntry.season_id == season_id)
        )
        entries = entries_result.scalars().all()

        total_cost = 0.0
        cost_breakdown: dict[str, float] = {
            "seeds": 0.0,
            "fertilizer": 0.0,
            "labour": 0.0,
            "irrigation": 0.0,
            "machinery": 0.0,
            "transport": 0.0,
            "other": 0.0,
        }
        total_yield_kg = 0.0
        total_revenue = 0.0
        total_sold_kg = 0.0

        for entry in entries:
            if entry.entry_type == "cost":
                total_cost += entry.amount_inr
                cat = entry.category if entry.category in cost_breakdown else "other"
                cost_breakdown[cat] += entry.amount_inr
            elif entry.entry_type == "yield_log":
                total_yield_kg += entry.quantity_kg
            elif entry.entry_type == "sale_revenue":
                total_revenue += entry.amount_inr
                total_sold_kg += entry.quantity_kg

        # Area and P&L
        area_acres = max(season.area_acres, 0.1)
        net_profit_loss = total_revenue - total_cost
        profit_loss_per_acre = round(net_profit_loss / area_acres, 2)

        # Break-even price (₹/kg)
        effective_yield_kg = total_yield_kg if total_yield_kg > 0 else season.expected_yield_kg
        if effective_yield_kg > 0:
            break_even_price = round(total_cost / effective_yield_kg, 2)
        else:
            break_even_price = 0.0

        # Actual Farmer Sale Price vs Mandi Average over same season dates
        farmer_actual_price_per_kg = (
            round(total_revenue / total_sold_kg, 2) if total_sold_kg > 0 else 0.0
        )

        # Query average mandi modal price for the crop in this district during cultivation period
        end_date = season.harvest_date or date.today()
        mandi_avg_query = select(func.avg(Price.modal_price_kg)).where(
            Price.crop_id == season.crop_id,
            Price.price_date >= season.planting_date,
            Price.price_date <= end_date,
        )
        avg_res = await db.scalar(mandi_avg_query)

        if avg_res is not None and float(avg_res) > 0:
            mandi_avg = round(float(avg_res), 2)
        else:
            # Fallback to recent crop price if historical span had no direct matches
            recent_price = await db.scalar(
                select(Price.modal_price_kg)
                .where(Price.crop_id == season.crop_id)
                .order_by(Price.price_date.desc())
                .limit(1)
            )
            mandi_avg = round(float(recent_price), 2) if recent_price else 24.50

        # Premium comparison
        if farmer_actual_price_per_kg > 0:
            premium_inr = round(farmer_actual_price_per_kg - mandi_avg, 2)
            premium_pct = round((premium_inr / mandi_avg) * 100, 1)
            if premium_inr >= 0:
                summary = (
                    f"You earned an extra ₹{premium_inr:.2f}/kg (+{premium_pct}%) above the "
                    f"mandi average of ₹{mandi_avg:.2f}/kg by direct selling!"
                )
            else:
                summary = (
                    f"Your realized price was ₹{abs(premium_inr):.2f}/kg below the mandi average "
                    f"of ₹{mandi_avg:.2f}/kg."
                )
        else:
            premium_inr = 0.0
            premium_pct = 0.0
            summary = (
                f"Current benchmark mandi average is ₹{mandi_avg:.2f}/kg. "
                f"Target sale price above your ₹{break_even_price:.2f}/kg break-even to ensure profit."
            )

        mandi_comparison = MandiComparison(
            farmer_actual_price_per_kg=farmer_actual_price_per_kg,
            mandi_average_price_per_kg=mandi_avg,
            price_premium_inr=premium_inr,
            price_premium_percent=premium_pct,
            comparison_summary=summary,
        )

        return SeasonFinancialMetrics(
            season_id=season.id,
            season_name=season.season_name,
            crop_id=season.crop_id,
            area_acres=season.area_acres,
            total_cost_inr=round(total_cost, 2),
            cost_breakdown={k: round(v, 2) for k, v in cost_breakdown.items()},
            total_yield_kg=round(total_yield_kg, 2),
            total_revenue_inr=round(total_revenue, 2),
            total_sold_kg=round(total_sold_kg, 2),
            net_profit_loss_inr=round(net_profit_loss, 2),
            profit_loss_per_acre_inr=profit_loss_per_acre,
            break_even_price_per_kg=break_even_price,
            mandi_comparison=mandi_comparison,
        )

    @staticmethod
    async def export_season_records_csv(db: AsyncSession, season_id: int) -> str:
        """
        Exports the farmer's complete diary records into CSV format.
        Fulfills DPDP Act data portability rights.
        """
        season = await db.scalar(select(FarmSeason).where(FarmSeason.id == season_id))
        if not season:
            raise ValueError(f"FarmSeason #{season_id} not found")

        metrics = await FarmDiaryService.calculate_season_metrics(db, season_id)

        entries_result = await db.execute(
            select(FarmDiaryEntry)
            .where(FarmDiaryEntry.season_id == season_id)
            .order_by(FarmDiaryEntry.entry_date.asc())
        )
        entries = entries_result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Header summary
        writer.writerow(["GrowCircle Farm Diary Export"])
        writer.writerow(["Season Name", season.season_name])
        writer.writerow(["Crop", season.crop_id.title()])
        writer.writerow(["Area (Acres)", season.area_acres])
        writer.writerow(["Planting Date", season.planting_date.isoformat()])
        writer.writerow(["Total Expenses (INR)", metrics.total_cost_inr])
        writer.writerow(["Total Yield Harvested (kg)", metrics.total_yield_kg])
        writer.writerow(["Total Revenue (INR)", metrics.total_revenue_inr])
        writer.writerow(["Net Profit / Loss (INR)", metrics.net_profit_loss_inr])
        writer.writerow(["Profit / Loss Per Acre (INR)", metrics.profit_loss_per_acre_inr])
        writer.writerow(["Break-Even Price (INR/kg)", metrics.break_even_price_per_kg])
        writer.writerow(["Mandi Average Price (INR/kg)", metrics.mandi_comparison.mandi_average_price_per_kg])
        writer.writerow(["Realized Farmer Price (INR/kg)", metrics.mandi_comparison.farmer_actual_price_per_kg])
        writer.writerow([])

        # Entries table
        writer.writerow([
            "Entry ID",
            "Date",
            "Type",
            "Category",
            "Amount (INR)",
            "Quantity (kg)",
            "Unit Price (INR/kg)",
            "Notes / Voice Raw",
            "Read-Back Confirmed",
        ])

        for e in entries:
            writer.writerow([
                e.id,
                e.entry_date.isoformat(),
                e.entry_type,
                e.category,
                e.amount_inr,
                e.quantity_kg,
                e.unit_price_inr,
                e.notes or e.voice_raw_text or "",
                "YES" if e.readback_confirmed else "NO",
            ])

        return output.getvalue()

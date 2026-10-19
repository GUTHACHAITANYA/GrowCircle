"""
Unit tests for PriceSource adapters and PriceReconciler data quality and priority rules.
"""

from datetime import date, datetime
import pytest

from backend.app.services.price_sources.base import NormalizedPriceRecord
from backend.app.services.price_sources.agmarknet_csv_adapter import AgmarknetPortalCsvAdapter
from backend.app.services.price_sources.ceda_adapter import CedaAgriAdapter
from backend.app.services.price_sources.data_gov_adapter import DataGovInAdapter
from backend.app.services.price_sources.reconciler import PriceReconciler, SOURCE_PRIORITY


def test_normalized_price_record_structure():
    rec = NormalizedPriceRecord(
        state="Andhra Pradesh",
        district="Guntur",
        mandi="Guntur",
        commodity="Banana",
        variety="Amruthapani",
        grade="FAQ",
        reported_date=date(2026, 10, 15),
        min_price=2200.0,
        max_price=2800.0,
        modal_price=2500.0,
        unit="Quintal",
        source_name="data.gov.in",
        fetched_at=datetime(2026, 10, 15, 10, 0, 0),
        raw_data={"raw": "test"},
    )
    assert rec.state == "Andhra Pradesh"
    assert rec.modal_price == 2500.0
    assert rec.source_name == "data.gov.in"
    assert rec.unit == "Quintal"
    assert rec.raw_data == {"raw": "test"}


def test_reconciler_quality_gates():
    reconciler = PriceReconciler(db=None)  # db not needed for pure validation logic

    base_record = NormalizedPriceRecord(
        state="Andhra Pradesh",
        district="Guntur",
        mandi="Guntur",
        commodity="Banana",
        variety="Amruthapani",
        grade="FAQ",
        reported_date=date(2026, 10, 15),
        min_price=2000.0,
        max_price=2600.0,
        modal_price=2300.0,
        unit="Quintal",
        source_name="data.gov.in",
    )

    # 1. Valid record should be clean
    status, reason = reconciler.validate_quality(base_record)
    assert status == "clean"
    assert reason is None

    # 2. Negative price
    neg_rec = NormalizedPriceRecord(
        state="AP", district="Guntur", mandi="Guntur", commodity="Banana",
        variety="FAQ", grade="FAQ", reported_date=date.today(),
        min_price=-100.0, max_price=2000.0, modal_price=1500.0,
        unit="Quintal", source_name="test",
    )
    status, reason = reconciler.validate_quality(neg_rec)
    assert status == "quarantined_negative"
    assert "Non-positive" in reason

    # 3. Min > Max
    inverted_rec = NormalizedPriceRecord(
        state="AP", district="Guntur", mandi="Guntur", commodity="Banana",
        variety="FAQ", grade="FAQ", reported_date=date.today(),
        min_price=3000.0, max_price=2000.0, modal_price=2500.0,
        unit="Quintal", source_name="test",
    )
    status, reason = reconciler.validate_quality(inverted_rec)
    assert status == "quarantined_min_gt_max"

    # 4. Modal outside min-max
    out_of_range = NormalizedPriceRecord(
        state="AP", district="Guntur", mandi="Guntur", commodity="Banana",
        variety="FAQ", grade="FAQ", reported_date=date.today(),
        min_price=1000.0, max_price=2000.0, modal_price=2500.0,
        unit="Quintal", source_name="test",
    )
    status, reason = reconciler.validate_quality(out_of_range)
    assert status == "quarantined_modal_range"

    # 5. Invalid unit
    bad_unit = NormalizedPriceRecord(
        state="AP", district="Guntur", mandi="Guntur", commodity="Banana",
        variety="FAQ", grade="FAQ", reported_date=date.today(),
        min_price=1000.0, max_price=2000.0, modal_price=1500.0,
        unit="Bags", source_name="test",
    )
    status, reason = reconciler.validate_quality(bad_unit)
    assert status == "quarantined_unit"

    # 6. 10x jump anomaly from previous price
    status, reason = reconciler.validate_quality(base_record, prev_modal_quintal=200.0)
    assert status == "quarantined_10x_spike"
    assert "10x anomaly spike detected" in reason

    # Normal variation (e.g. 2300 vs 2100) should pass
    status, reason = reconciler.validate_quality(base_record, prev_modal_quintal=2100.0)
    assert status == "clean"


def test_source_priority():
    # agmarknet_portal_csv (1) > data.gov.in (2) > ceda_ashoka (3) > manual (4) > demo (99)
    assert SOURCE_PRIORITY["agmarknet_portal_csv"] < SOURCE_PRIORITY["data.gov.in"]
    assert SOURCE_PRIORITY["data.gov.in"] < SOURCE_PRIORITY["ceda_ashoka"]
    assert SOURCE_PRIORITY["ceda_ashoka"] < SOURCE_PRIORITY["manual"]
    assert SOURCE_PRIORITY["manual"] < SOURCE_PRIORITY["demo"]


def test_agmarknet_portal_csv_adapter(tmp_path):
    csv_content = (
        "State,District,Market,Commodity,Variety,Grade,Min Price,Max Price,Modal Price,Price Date\n"
        "Andhra Pradesh,Guntur,Guntur,Banana,Amruthapani,FAQ,2200,2800,2500,15/10/2026\n"
        "Andhra Pradesh,NTR,Vijayawada,Tomato,Hybrid,FAQ,1200,1600,1400,2026-10-15\n"
    )
    test_csv = tmp_path / "test_agmarknet.csv"
    test_csv.write_text(csv_content, encoding="utf-8")

    adapter = AgmarknetPortalCsvAdapter(storage_dir=str(tmp_path / "raw_backup"))
    records = adapter.parse_csv_file(str(test_csv))

    assert len(records) == 2
    r1 = records[0]
    assert r1.state == "Andhra Pradesh"
    assert r1.mandi == "Guntur"
    assert r1.commodity == "Banana"
    assert r1.min_price == 2200.0
    assert r1.max_price == 2800.0
    assert r1.modal_price == 2500.0
    assert r1.reported_date == date(2026, 10, 15)
    assert r1.source_name == "agmarknet_portal_csv"

    r2 = records[1]
    assert r2.mandi == "Vijayawada"
    assert r2.commodity == "Tomato"
    assert r2.reported_date == date(2026, 10, 15)


def test_ceda_adapter_license_and_terms():
    adapter = CedaAgriAdapter()
    terms = adapter.get_terms_and_licence()
    assert "Ashoka University" in terms["source"]
    assert terms["non_commercial_only"] is True
    assert "attribution_required" in terms
    assert terms["attribution_required"] is True

"""
Unit and integration tests for ground-truth manual phone audit verification.
Tests:
- Manual phone check submission
- Difference and percentage calculation against displayed prices
- Missing / late price detection
- CSV template generation and CSV upload
- Aggregated accuracy reporting
"""

from datetime import date, timedelta
import io
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.mandi import Mandi
from backend.app.models.price import Price


@pytest.mark.asyncio
async def test_ground_truth_flow(client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]):
    client.headers.update(admin_headers)
    # 1. Fetch available mandi from fixture
    mandi = (await db_session.execute(select(Mandi))).scalars().first()
    assert mandi is not None

    # Verify existing price in fixture is ₹25/kg for banana
    today = date.today()

    # 2. Test CSV Template download
    resp = await client.get("/admin/ground-truth/template.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "mandi_id,mandi_name,crop_id" in resp.text

    # 3. Submit a manual phone audit check:
    # App has price 25.0 kg. Mandi secretary told us 26.0 kg.
    payload = {
        "mandi_id": mandi.id,
        "crop_id": "banana",
        "variety": "Amruthapani",
        "grade": "FAQ",
        "check_date": today.isoformat(),
        "price_quoted_kg": 26.0,
        "contact_role": "secretary",
        "contact_name": "Sri Rama Rao",
        "contact_phone": "+919848011223",
        "notes": "Morning phone call confirmation",
    }
    resp = await client.post("/admin/ground-truth", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["mandi_id"] == mandi.id
    assert data["price_shown_kg"] == 25.0
    assert data["price_quoted_kg"] == 26.0
    # diff_kg = 25.0 - 26.0 = -1.0
    assert data["difference_kg"] == -1.0
    # diff_pct = (-1.0 / 26.0) * 100 = -3.85%
    assert data["difference_pct"] == pytest.approx(-3.85, abs=0.1)
    assert data["is_price_missing"] is False
    assert data["is_price_late"] is False

    # 4. Check for a crop with NO reported price (missing price detection)
    payload_missing = {
        "mandi_id": mandi.id,
        "crop_id": "chilli",
        "variety": "Teja",
        "grade": "FAQ",
        "check_date": today.isoformat(),
        "price_quoted_kg": 180.0,
        "contact_role": "trader",
        "contact_name": "K. Venkatesh",
        "notes": "No chilli price was in app",
    }
    resp_missing = await client.post("/admin/ground-truth", json=payload_missing)
    assert resp_missing.status_code == 201
    missing_data = resp_missing.json()
    assert missing_data["is_price_missing"] is True
    assert missing_data["price_shown_kg"] is None

    # 5. Check CSV bulk upload
    csv_data = (
        "mandi_id,crop_id,variety,grade,check_date,price_quoted_kg,contact_role,contact_name,contact_phone,notes\n"
        f"{mandi.id},banana,Amruthapani,FAQ,{today.isoformat()},25.5,secretary,Secretary Sharma,+919999999999,Bulk test\n"
    )
    files = {"file": ("test_audit.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    resp_upload = await client.post("/admin/ground-truth/upload-csv", files=files)
    assert resp_upload.status_code == 200
    upload_res = resp_upload.json()
    assert upload_res["records_imported"] == 1
    assert upload_res["errors_count"] == 0

    # 6. Check report endpoint
    resp_report = await client.get("/admin/ground-truth/report")
    assert resp_report.status_code == 200
    report = resp_report.json()
    assert report["total_checks"] == 3
    assert report["missing_price_count"] == 1
    assert report["missing_price_rate_pct"] == pytest.approx(33.33, abs=0.5)
    assert len(report["mandi_breakdown"]) >= 1

    # 7. Check list endpoint
    resp_list = await client.get("/admin/ground-truth")
    assert resp_list.status_code == 200
    checks = resp_list.json()
    assert len(checks) == 3

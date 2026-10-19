"""
Mandal Mapping and Hierarchy Synchronization Service.
Maps mandis to Local Government Directory (LGD) mandals and calculates
nearest reporting mandis for mandals without local physical markets.
"""

import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.hierarchy import DistrictMaster, MandalMaster, StateMaster
from backend.app.models.mandi import Mandi
from backend.app.services.mandi_master.lgd_data import (
    LGD_AP_DISTRICTS_AND_MANDALS,
    LGD_STATES_DATA,
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two GPS coordinates in kilometers."""
    r = 6371.0  # Earth's radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)


class MandalMapper:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_lgd_hierarchy_seeded(self) -> None:
        """Seeds StateMaster, DistrictMaster, and MandalMaster from canonical LGD datasets."""
        # 1. States
        for s_data in LGD_STATES_DATA:
            state = await self.db.get(StateMaster, s_data["id"])
            if not state:
                state = StateMaster(
                    id=s_data["id"],
                    name=s_data["name"],
                    lgd_code=s_data["lgd_code"],
                    min_lat=s_data["min_lat"],
                    max_lat=s_data["max_lat"],
                    min_lon=s_data["min_lon"],
                    max_lon=s_data["max_lon"],
                )
                self.db.add(state)
        await self.db.flush()

        # 2. Districts & Mandals
        for dist_name, dist_info in LGD_AP_DISTRICTS_AND_MANDALS.items():
            dist = await self.db.scalar(
                select(DistrictMaster).where(
                    DistrictMaster.state_id == "AP", DistrictMaster.name == dist_name
                )
            )
            if not dist:
                dist = DistrictMaster(
                    state_id="AP",
                    name=dist_name,
                    lgd_code=dist_info.get("lgd_code"),
                )
                self.db.add(dist)
                await self.db.flush()

            for m_info in dist_info.get("mandals", []):
                mandal = await self.db.scalar(
                    select(MandalMaster).where(
                        MandalMaster.district_id == dist.id,
                        MandalMaster.name == m_info["name"],
                    )
                )
                if not mandal:
                    mandal = MandalMaster(
                        district_id=dist.id,
                        name=m_info["name"],
                        lgd_code=m_info.get("lgd_code"),
                        latitude=m_info.get("latitude"),
                        longitude=m_info.get("longitude"),
                    )
                    self.db.add(mandal)

        await self.db.commit()

    async def map_mandi_to_mandal(self, mandi: Mandi) -> tuple[MandalMaster | None, float | None]:
        """
        Maps a mandi to the most appropriate mandal within its district.
        1. Checks for direct or substring name match (e.g. 'Guntur' -> 'Guntur').
        2. If verified coordinates exist, computes closest mandal by Haversine distance.
        Updates mandi attributes with matched mandal and LGD codes.
        """
        # Resolve state & district masters
        state_row = await self.db.scalar(
            select(StateMaster).where(StateMaster.name.ilike(mandi.state.strip()))
        )
        if state_row:
            mandi.state_id = state_row.id
            mandi.state_lgd_code = state_row.lgd_code

        district_row = None
        if state_row:
            district_row = await self.db.scalar(
                select(DistrictMaster).where(
                    DistrictMaster.state_id == state_row.id,
                    DistrictMaster.name.ilike(mandi.district.strip()),
                )
            )
            if district_row:
                mandi.district_id = district_row.id
                mandi.district_lgd_code = district_row.lgd_code

        if not district_row:
            return None, None

        # Fetch mandals in this district
        mandals = (
            await self.db.execute(
                select(MandalMaster).where(MandalMaster.district_id == district_row.id)
            )
        ).scalars().all()

        if not mandals:
            return None, None

        c_name = (mandi.canonical_name or mandi.name).strip().lower()

        # 1. Exact or high-match name search
        for m in mandals:
            m_name_clean = m.name.strip().lower()
            if m_name_clean == c_name or m_name_clean in c_name or c_name in m_name_clean:
                mandi.mandal_id = m.id
                mandi.mandal = m.name
                mandi.mandal_lgd_code = m.lgd_code
                return m, 0.0

        # 2. Distance-based nearest mandal (if mandi coordinates are available)
        if mandi.latitude and mandi.longitude:
            best_mandal: MandalMaster | None = None
            min_dist = float("inf")

            for m in mandals:
                if m.latitude and m.longitude:
                    d = haversine_km(mandi.latitude, mandi.longitude, m.latitude, m.longitude)
                    if d < min_dist:
                        min_dist = d
                        best_mandal = m

            if best_mandal:
                mandi.mandal_id = best_mandal.id
                mandi.mandal = best_mandal.name
                mandi.mandal_lgd_code = best_mandal.lgd_code
                return best_mandal, min_dist

        return None, None

    async def get_mandal_market_overview(self, mandal_id: int) -> dict[str, Any]:
        """
        Returns physical market information for a mandal:
        - If mandal has a verified mandi: returns local mandis.
        - If mandal has NO mandi (normal across rural India): finds nearest verified
          reporting mandis and provides an explicit status message with distance.
        """
        mandal = await self.db.get(MandalMaster, mandal_id)
        if not mandal:
            return {"error": f"Mandal ID {mandal_id} not found"}

        # Fetch district and state
        dist = await self.db.get(DistrictMaster, mandal.district_id)
        state = await self.db.get(StateMaster, dist.state_id) if dist else None
        dist_name = dist.name if dist else "Unknown"
        state_name = state.name if state else "Unknown"

        # Check for verified active mandis in this mandal
        local_mandis = (
            await self.db.execute(
                select(Mandi).where(
                    Mandi.mandal_id == mandal.id,
                    Mandi.is_active == True,
                    Mandi.location_verified == True,
                )
            )
        ).scalars().all()

        if local_mandis:
            return {
                "mandal_id": mandal.id,
                "mandal_name": mandal.name,
                "district_name": dist_name,
                "state_name": state_name,
                "has_local_mandi": True,
                "status_message": f"Verified local mandi available in {mandal.name} mandal.",
                "local_mandis": [
                    {
                        "id": m.id,
                        "name": m.canonical_name or m.name,
                        "latitude": m.latitude,
                        "longitude": m.longitude,
                        "location_verified": m.location_verified,
                    }
                    for m in local_mandis
                ],
                "nearest_mandis": [],
            }

        # No local mandi -> Find nearest verified active mandis
        verified_mandis = (
            await self.db.execute(
                select(Mandi).where(
                    Mandi.is_active == True,
                    Mandi.location_verified == True,
                    Mandi.latitude.isnot(None),
                    Mandi.longitude.isnot(None),
                )
            )
        ).scalars().all()

        if not mandal.latitude or not mandal.longitude or not verified_mandis:
            return {
                "mandal_id": mandal.id,
                "mandal_name": mandal.name,
                "district_name": dist_name,
                "state_name": state_name,
                "has_local_mandi": False,
                "status_message": f"No mandi in {mandal.name} mandal.",
                "local_mandis": [],
                "nearest_mandis": [],
            }

        ranked_mandis = []
        for m in verified_mandis:
            d = haversine_km(mandal.latitude, mandal.longitude, m.latitude, m.longitude)
            ranked_mandis.append((d, m))

        ranked_mandis.sort(key=lambda x: x[0])
        top_nearest = ranked_mandis[:3]

        nearest_summary_str = ", ".join(
            f"{m.canonical_name or m.name} ({dist:.1f} km away)" for dist, m in top_nearest
        )
        msg = f"No mandi in {mandal.name} mandal. Nearest reporting mandis: {nearest_summary_str}."

        return {
            "mandal_id": mandal.id,
            "mandal_name": mandal.name,
            "district_name": dist_name,
            "state_name": state_name,
            "has_local_mandi": False,
            "status_message": msg,
            "local_mandis": [],
            "nearest_mandis": [
                {
                    "id": m.id,
                    "name": m.canonical_name or m.name,
                    "district": m.district,
                    "distance_km": dist,
                    "latitude": m.latitude,
                    "longitude": m.longitude,
                }
                for dist, m in top_nearest
            ],
        }

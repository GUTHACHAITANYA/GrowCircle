"""
PriceSource abstract interface and NormalizedPriceRecord model for GrowCircle.
All sources (data.gov.in, CEDA Ashoka, Agmarknet Portal CSV) must adhere to this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any


@dataclass(frozen=True)
class NormalizedPriceRecord:
    state: str
    district: str
    mandi: str
    commodity: str
    variety: str
    grade: str
    reported_date: date
    min_price: float
    max_price: float
    modal_price: float
    unit: str  # 'quintal', 'kg', 'ton'
    source_name: str
    raw_data: dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def key(self) -> tuple[str, str, str, str, str, date]:
        """Unique compound key for deduplication and reconciliation."""
        return (
            self.state.strip().lower(),
            self.district.strip().lower(),
            self.mandi.strip().lower(),
            self.commodity.strip().lower(),
            self.variety.strip().lower(),
            self.reported_date,
        )


class PriceSource(ABC):
    """Abstract interface for all mandi price source adapters."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Canonical identifier for the data source (e.g. 'data.gov.in', 'agmarknet_portal_csv')."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """
        Priority rank for source reconciliation (lower number = higher priority).
        1: Official Agmarknet Portal Direct CSV
        2: data.gov.in Agmarknet API
        3: CEDA Agri Market API (Ashoka University)
        """
        pass

    @abstractmethod
    async def fetch_prices(
        self,
        state: str | None = None,
        commodity: str | None = None,
        district: str | None = None,
        target_date: date | None = None,
    ) -> list[NormalizedPriceRecord]:
        """Fetch and return standardized, normalized price records."""
        pass

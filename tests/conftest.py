from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixture_dir() -> Path:
    return FIXTURES


@pytest.fixture
def cfg() -> dict:
    return {
        "team_id": 12345,
        "h2h_league_ids": [1001, 1002],
        "half_deadline_gw": 19,
        "max_days_to_deadline": 8,
    }


@pytest.fixture
def now_near_deadline() -> datetime:
    """27 hours before the GW7 deadline in the fixture."""
    return datetime(2026, 9, 25, 7, 0, tzinfo=timezone.utc)


@pytest.fixture
def now_far_from_deadline() -> datetime:
    return datetime(2026, 9, 10, 7, 0, tzinfo=timezone.utc)

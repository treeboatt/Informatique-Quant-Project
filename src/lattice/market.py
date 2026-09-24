from dataclasses import dataclass
from datetime import datetime

DAYS_PER_YEAR = 365.0


def year_fraction(d1: datetime, d2: datetime) -> float:
    return (d2 - d1).total_seconds() / 86400 / DAYS_PER_YEAR


@dataclass(frozen=True)
class Market:
    s0: float
    rate: float
    vol: float
    dividend: float = 0.0
    div_ex_date: datetime | None = None

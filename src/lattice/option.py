from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OptionTrade:
    strike: float
    maturity: datetime
    is_call: bool = True
    is_american: bool = False

    def payoff(self, s: float) -> float:
        if self.is_call:
            return max(s - self.strike, 0.0)
        return max(self.strike - s, 0.0)

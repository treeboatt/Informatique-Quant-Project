from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OptionTrade:
    strike: float
    maturity: datetime
    is_call: bool = True
    is_american: bool = False
    # une binaire paie 1 euro ou rien. le strike sert alors de barriere
    is_binary: bool = False

    def payoff(self, s: float) -> float:
        if self.is_binary:
            touche = s >= self.strike if self.is_call else s <= self.strike
            return 1.0 if touche else 0.0
        if self.is_call:
            return max(s - self.strike, 0.0)
        return max(self.strike - s, 0.0)


# le one-touch paie 1 euro des que la barriere est touchee. c'est exactement une
# binaire americaine : le pricer prend deja max(garder, exercer) a chaque noeud,
# et au-dessus de la barriere le payoff vaut 1, donc il encaisse tout de suite
def one_touch(barrier: float, maturity: datetime, is_up: bool = True) -> OptionTrade:
    return OptionTrade(barrier, maturity, is_call=is_up, is_american=True, is_binary=True)

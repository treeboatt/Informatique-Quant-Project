from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from lattice.market import Market, year_fraction
from lattice.option import OptionTrade

MAT = datetime(2027, 9, 15)


# test of the fraction of year
def test_year_fraction():
    assert year_fraction(datetime(2026, 9, 15), datetime(2027, 9, 15)) == pytest.approx(1.0)
    assert year_fraction(datetime(2026, 9, 15), datetime(2026, 11, 27)) == pytest.approx(0.2)


# test of the market's default data


def test_market_default():
    mkt = Market(s0=100, rate=0.03, vol=0.25)
    assert mkt.dividend == 0.0
    assert mkt.div_ex_date is None


def test_market_not_modifiable():
    mkt = Market(s0=100, rate=0.03, vol=0.25)
    with pytest.raises(FrozenInstanceError):
        mkt.vol = 0.3


def test_call_payoff():
    call = OptionTrade(strike=100, maturity=MAT, is_call=True)
    assert call.payoff(120) == 20
    assert call.payoff(80) == 0


def test_put_payoff():
    put = OptionTrade(strike=100, maturity=MAT, is_call=False)
    assert put.payoff(120) == 0
    assert put.payoff(80) == 20

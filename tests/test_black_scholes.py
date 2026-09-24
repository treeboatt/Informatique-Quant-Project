import math

import pytest

from lattice.black_scholes import bs_price, norm_cdf


# test the CDF of normal distribution
def test_norm_cdf():
    assert norm_cdf(0.0) == pytest.approx(0.5)
    assert norm_cdf(1.96) == pytest.approx(0.975, abs=1e-4)


def test_bs_price():
    assert bs_price(100, 100, 1, 0.05, 0.2, True) == pytest.approx(10.4506, abs=1e-4)
    assert bs_price(100, 100, 1, 0.05, 0.2, False) == pytest.approx(5.5735, abs=1e-4)

    assert bs_price(100, 100, 0.5, 0.05, 0.2, True) == pytest.approx(6.8887, abs=1e-4)
    assert bs_price(100, 100, 0.5, 0.05, 0.2, False) == pytest.approx(4.4197, abs=1e-4)


@pytest.mark.parametrize("strike, rate", [(80, 0.03), (100, 0.0), (120, -0.01)])
def test_parity_strike_100(strike, rate):
    call = bs_price(100, strike, 1.0, rate, 0.2, is_call=True)
    put = bs_price(100, strike, 1.0, rate, 0.2, is_call=False)
    assert call - put == pytest.approx(100 - strike * math.exp(-rate), abs=1e-10)

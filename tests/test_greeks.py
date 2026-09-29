import math

import pytest

from lattice.black_scholes import bs_price, norm_cdf
from lattice.greeks import OneDimDerivative

S0, STRIKE, MATURITY, RATE, VOL = 100.0, 100.0, 1.0, 0.05, 0.20


# derivative 2x, second derivative 2
def square(param, x):
    return x * x


# Black-Scholes with the f(param, x) signature
def bs_call(param, s):
    strike, maturity, rate, vol = param
    return bs_price(s, strike, maturity, rate, vol, is_call=True)


# needed by both the delta and the gamma
def bs_d1():
    return (math.log(S0 / STRIKE) + (RATE + VOL**2 / 2) * MATURITY) / (VOL * math.sqrt(MATURITY))


def test_first_derivative_on_a_known_function():
    d = OneDimDerivative(square, None, shift=0.01)
    assert d.first(3.0) == pytest.approx(6.0)
    assert d.first(-2.0) == pytest.approx(-4.0)


def test_second_derivative_on_a_known_function():
    d = OneDimDerivative(square, None, shift=0.01)
    assert d.second(3.0) == pytest.approx(2.0)


# a centred derivative is exact on a straight line, whatever the shift
@pytest.mark.parametrize("shift", [0.01, 1.0, 50.0])
def test_derivatives_are_exact_on_a_straight_line(shift):
    d = OneDimDerivative(lambda param, x: 3.0 * x + 7.0, None, shift=shift)
    assert d.first(10.0) == pytest.approx(3.0)
    # approx(0.0) alone is a relative tolerance
    assert d.second(10.0) == pytest.approx(0.0, abs=1e-9)


# the delta of a call is N(d1)
def test_delta_matches_black_scholes():
    d = OneDimDerivative(bs_call, (STRIKE, MATURITY, RATE, VOL), shift=0.5)
    assert d.first(S0) == pytest.approx(norm_cdf(bs_d1()), abs=1e-4)


# gamma = density(d1) / (S * vol * sqrt(T))
def test_gamma_matches_black_scholes():
    d = OneDimDerivative(bs_call, (STRIKE, MATURITY, RATE, VOL), shift=0.5)
    d1 = bs_d1()
    density = math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi)
    assert d.second(S0) == pytest.approx(density / (S0 * VOL * math.sqrt(MATURITY)), abs=1e-6)


def test_shift_defaults_to_one():
    assert OneDimDerivative(square, None).shift == 1.0

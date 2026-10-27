import math

import pytest

from lattice.black_scholes import bs_price, norm_cdf
from lattice.greeks import OneDimDerivative, TwoDimDerivative

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


def bs_call_spot_vol(param, s, v):
    strike, maturity, rate = param
    return bs_price(s, strike, maturity, rate, v, is_call=True)


def bs_vanna():
    d1 = bs_d1()
    d2 = d1 - VOL * math.sqrt(MATURITY)
    density = math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi)
    return -density * d2 / VOL


# le vanna croise le spot et la vol, OneDimDerivative ne peut pas le donner
def test_vanna_matches_black_scholes():
    d = TwoDimDerivative(bs_call_spot_vol, (STRIKE, MATURITY, RATE),
                         shift_x=1.0, shift_y=0.01)
    assert d.cross(S0, VOL) == pytest.approx(bs_vanna(), abs=1e-3)


# sur un produit x*y la derivee croisee vaut 1, quelle que soit la taille du pas
@pytest.mark.parametrize("shift_x, shift_y", [(0.01, 0.01), (1.0, 0.5), (10.0, 5.0)])
def test_cross_derivative_on_a_known_function(shift_x, shift_y):
    d = TwoDimDerivative(lambda param, x, y: x * y, None, shift_x, shift_y)
    assert d.cross(3.0, 7.0) == pytest.approx(1.0)


# sans terme croise, la derivee croisee est nulle
def test_cross_derivative_is_zero_without_a_crossed_term():
    d = TwoDimDerivative(lambda param, x, y: x * x + y * y, None, 0.5, 0.5)
    assert d.cross(2.0, 5.0) == pytest.approx(0.0, abs=1e-9)


def bs_vomma():
    d1 = bs_d1()
    d2 = d1 - VOL * math.sqrt(MATURITY)
    density = math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi)
    vega = S0 * density * math.sqrt(MATURITY)
    return vega * d1 * d2 / VOL


# le vomma est une derivee seconde sur la seule volatilite : pas besoin de
# TwoDimDerivative, OneDimDerivative.second suffit
def test_vomma_matches_black_scholes():
    d = OneDimDerivative(black_par_vol_only, None, shift=0.005)
    assert d.second(VOL) == pytest.approx(bs_vomma(), rel=1e-3)


def black_par_vol_only(param, v):
    return bs_price(S0, STRIKE, MATURITY, RATE, v, is_call=True)

import math
from datetime import datetime

import pytest

from lattice.api import price
from lattice.black_scholes import bs_digital
from lattice.market import Market
from lattice.option import OptionTrade, one_touch

T0 = datetime(2026, 9, 15)
MAT = datetime(2027, 9, 15)
FLAT = Market(100.0, 0.03, 0.30)


def binary(strike, is_call=True):
    return OptionTrade(strike, MAT, is_call=is_call, is_american=False, is_binary=True)


def test_the_payoff_is_one_or_nothing():
    call = binary(100.0)
    assert call.payoff(100.01) == 1.0
    assert call.payoff(150.0) == 1.0           # peu importe de combien on gagne
    assert call.payoff(99.99) == 0.0


def test_the_binary_put_is_the_mirror():
    put = binary(100.0, is_call=False)
    assert put.payoff(99.0) == 1.0
    assert put.payoff(101.0) == 0.0


# la binaire europeenne a une formule fermee : exp(-rT) N(d2)
def test_the_binary_call_converges_to_its_closed_form():
    exact = bs_digital(100.0, 105.0, 1.0, 0.03, 0.30)
    tree = price(FLAT, binary(105.0), T0, 1500, prune=True)
    assert tree == pytest.approx(exact, abs=0.004)


# toucher une binaire call et une binaire put, c'est toucher a coup sur : la
# somme des deux vaut un euro actualise
def test_call_and_put_binaries_sum_to_the_discount_factor():
    call = price(FLAT, binary(100.0), T0, 800, prune=True)
    put = price(FLAT, binary(100.0, is_call=False), T0, 800, prune=True)
    assert call + put == pytest.approx(math.exp(-0.03), abs=1e-3)


# toucher une fois est plus facile que finir au-dessus : le one-touch vaut plus
def test_the_one_touch_is_worth_more_than_the_european_binary():
    touch = price(FLAT, one_touch(115.0, MAT), T0, 800, prune=True)
    european = price(FLAT, binary(115.0), T0, 800, prune=True)
    assert touch > european


# barriere deja franchie aujourd'hui : on encaisse tout de suite, sans attendre
def test_a_barrier_already_crossed_pays_one_euro_now():
    assert price(FLAT, one_touch(90.0, MAT), T0, 50) == pytest.approx(1.0)


# barriere hors d'atteinte : l'arbre ne monte jamais si haut
def test_an_unreachable_barrier_is_worthless():
    assert price(FLAT, one_touch(100000.0, MAT), T0, 50) == pytest.approx(0.0)


# le one-touch bas se declenche quand on descend, pas quand on monte
def test_the_down_touch_waits_for_a_fall():
    bas = one_touch(80.0, MAT, is_up=False)
    assert bas.payoff(75.0) == 1.0
    assert bas.payoff(120.0) == 0.0
    assert 0.0 < price(FLAT, bas, T0, 500, prune=True) < 1.0

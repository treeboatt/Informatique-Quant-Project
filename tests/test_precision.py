from datetime import datetime

import pytest

from lattice.api import price
from lattice.black_scholes import bs_price
from lattice.market import Market
from lattice.option import OptionTrade
from lattice.precision import error_constant, expected_gap, steps_for_precision

T0 = datetime(2026, 9, 15)
MAT = datetime(2027, 9, 15)
FLAT = Market(100.0, 0.0, 0.30)
CALL = OptionTrade(100.0, MAT)
BS_FLAT = bs_price(100.0, 100.0, 1.0, 0.0, 0.30)


def measured_gap(nb_steps, kind="trinomial"):
    return abs(price(FLAT, CALL, T0, nb_steps, kind=kind) - BS_FLAT)


# controle du cours : T = 1 an, vol = 30%, r = 0 donne 0,4% a N=10 et 0,004% a N=1000
@pytest.mark.parametrize("nb_steps, relative", [(10, 0.004), (1000, 0.00004)])
def test_the_slide_figures_are_reproduced(nb_steps, relative):
    gap = expected_gap(FLAT, 1.0, nb_steps)
    assert gap / FLAT.s0 == pytest.approx(relative, rel=0.15)


def test_the_gap_decreases_like_one_over_n():
    assert expected_gap(FLAT, 1.0, 200) == pytest.approx(expected_gap(FLAT, 1.0, 100) / 2.0)


# le trinomial se trompe moins que le binomial, dans le rapport 3/8 sur 1/2
def test_the_trinomial_is_announced_as_more_precise():
    ratio = error_constant(FLAT, 1.0, "trinomial") / error_constant(FLAT, 1.0, "binomial")
    assert ratio == pytest.approx(0.75)


# la formule ne compte qu'un seul noeud, elle surestime : on verifie l'ordre de
# grandeur, pas l'egalite
@pytest.mark.parametrize("nb_steps", [100, 200, 400])
def test_the_formula_has_the_right_order_of_magnitude(nb_steps):
    assert 1.0 <= expected_gap(FLAT, 1.0, nb_steps) / measured_gap(nb_steps) <= 2.0


# comme la formule surestime, le nombre de pas demande est toujours suffisant
@pytest.mark.parametrize("target", [0.1, 0.01])
def test_the_number_of_steps_reaches_the_target(target):
    assert measured_gap(steps_for_precision(FLAT, 1.0, target)) <= target


def test_a_tighter_target_asks_for_more_steps():
    assert steps_for_precision(FLAT, 1.0, 0.001) > steps_for_precision(FLAT, 1.0, 0.01)


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        error_constant(FLAT, 1.0, "quadnomial")


def test_a_negative_target_is_refused():
    with pytest.raises(ValueError):
        steps_for_precision(FLAT, 1.0, 0.0)

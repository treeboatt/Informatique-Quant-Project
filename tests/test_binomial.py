import math
from datetime import datetime

import pytest

from lattice.black_scholes import bs_price
from lattice.market import Market
from lattice.option import OptionTrade
from lattice.pricer import Pricer, column
from lattice.tree import BinomialTree

T0 = datetime(2026, 9, 15)
MAT = datetime(2027, 9, 15)
MARKET = Market(100.0, 0.05, 0.20)
FLAT = Market(100.0, 0.0, 0.30)
BS_FLAT = bs_price(100.0, 100.0, 1.0, 0.0, 0.30)


def build(market, nb_steps):
    """Un arbre binomial construit, pret a etre price."""
    tree = BinomialTree(market, T0, MAT, nb_steps)
    tree.build_tree()
    return tree


def trunks(tree):
    """Parcourt les troncs, de la racine jusqu'a la maturite."""
    trunk = tree.root
    while trunk is not None:
        yield trunk
        trunk = trunk.next_mid


def test_alpha_matches_the_binomial_equation():
    # alpha + 1/alpha = 1 + exp(vol^2 dt)
    tree = build(MARKET, 50)
    expected = 1.0 + math.exp(MARKET.vol**2 * tree.dt)
    assert tree.alpha + 1.0 / tree.alpha == pytest.approx(expected)


def test_there_is_no_middle_branch():
    tree = build(MARKET, 50)
    assert tree.p_mid == 0.0
    assert tree.p_up + tree.p_down == pytest.approx(1.0)
    assert tree.p_up == pytest.approx(1.0 / (tree.alpha + 1.0))


@pytest.mark.parametrize("nb_steps", [20, 50, 100, 200])
def test_price_converges_to_black_scholes(nb_steps):
    price = Pricer(build(FLAT, nb_steps), OptionTrade(100.0, MAT)).price_backward()
    assert abs((price - BS_FLAT) * nb_steps) < 3.3


@pytest.mark.parametrize("nb_steps", [20, 50, 100, 200])
def test_an_even_number_of_steps_stays_below_black_scholes(nb_steps):
    # le binomial converge en oscillant avec la parite de N, contrairement au trinomial
    price = Pricer(build(FLAT, nb_steps), OptionTrade(100.0, MAT)).price_backward()
    assert price < BS_FLAT


@pytest.mark.parametrize("nb_steps", [21, 51, 101, 201])
def test_an_odd_number_of_steps_stays_above_black_scholes(nb_steps):
    price = Pricer(build(FLAT, nb_steps), OptionTrade(100.0, MAT)).price_backward()
    assert price > BS_FLAT


def test_proba_reach_sums_to_one_on_every_column():
    tree = build(MARKET, 30)
    for trunk in trunks(tree):
        total = sum(node.proba_reach for node in column(trunk))
        assert total == pytest.approx(1.0, abs=1e-12)


def test_call_put_parity_holds_on_the_tree():
    tree = build(MARKET, 200)
    call = Pricer(tree, OptionTrade(100.0, MAT, True)).price_backward()
    put = Pricer(tree, OptionTrade(100.0, MAT, False)).price_backward()
    assert call - put == pytest.approx(100.0 - 100.0 * math.exp(-0.05), abs=1e-10)


def test_american_call_equals_european_when_the_rate_is_positive():
    tree = build(MARKET, 100)
    european = Pricer(tree, OptionTrade(100.0, MAT, True)).price_backward()
    american = Pricer(tree, OptionTrade(100.0, MAT, True, True)).price_backward()
    assert american == pytest.approx(european, abs=1e-12)


def test_american_put_is_worth_more_when_the_rate_is_positive():
    tree = build(MARKET, 100)
    european = Pricer(tree, OptionTrade(100.0, MAT, False)).price_backward()
    american = Pricer(tree, OptionTrade(100.0, MAT, False, True)).price_backward()
    assert american > european

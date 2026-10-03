from datetime import datetime

import pytest

from lattice.api import price
from lattice.black_scholes import bs_price
from lattice.market import Market, year_fraction
from lattice.option import OptionTrade
from lattice.pricer import Pricer
from lattice.tree import BinomialTree, Tree

T0 = datetime(2026, 9, 15)
MAT = datetime(2027, 9, 15)
HALF = datetime(2027, 3, 15)
MARKET = Market(100.0, 0.05, 0.20)
CALL = OptionTrade(100.0, MAT)


def test_trinomial_gives_the_same_price_as_the_tree_built_by_hand():
    tree = Tree(MARKET, T0, MAT, 100)
    tree.build_tree()
    expected = Pricer(tree, CALL).price_backward()
    assert price(MARKET, CALL, T0, 100) == pytest.approx(expected, abs=1e-12)


def test_binomial_gives_the_same_price_as_the_tree_built_by_hand():
    tree = BinomialTree(MARKET, T0, MAT, 100)
    tree.build_tree()
    expected = Pricer(tree, CALL).price_backward()
    assert price(MARKET, CALL, T0, 100, kind="binomial") == pytest.approx(expected, abs=1e-12)


def test_the_default_kind_is_the_trinomial():
    assert price(MARKET, CALL, T0, 60) == price(MARKET, CALL, T0, 60, kind="trinomial")


# c'est le role de api.price : l'arbre est bati sur la maturite de l'option,
# donc les deux ne peuvent pas diverger
def test_the_tree_is_built_on_the_maturity_of_the_option():
    half = OptionTrade(100.0, HALF)
    reference = bs_price(100.0, 100.0, year_fraction(T0, HALF), 0.05, 0.20)
    assert price(MARKET, half, T0, 400) == pytest.approx(reference, abs=1e-2)


@pytest.mark.parametrize("kind", ["trinomial", "binomial"])
def test_both_trees_converge_to_black_scholes(kind):
    flat = Market(100.0, 0.0, 0.30)
    computed = price(flat, CALL, T0, 200, kind=kind)
    assert computed == pytest.approx(bs_price(100.0, 100.0, 1.0, 0.0, 0.30), abs=2e-2)


def test_an_american_put_is_worth_more_than_the_european_one():
    european = OptionTrade(100.0, MAT, False, False)
    american = OptionTrade(100.0, MAT, False, True)
    assert price(MARKET, american, T0, 100) > price(MARKET, european, T0, 100)


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        price(MARKET, CALL, T0, 50, kind="quadnomial")


def test_an_unknown_method_is_refused():
    with pytest.raises(ValueError):
        price(MARKET, CALL, T0, 50, method="recursive")

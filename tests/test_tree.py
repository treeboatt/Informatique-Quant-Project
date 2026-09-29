import math
from datetime import datetime

import pytest

from lattice.black_scholes import bs_price
from lattice.market import Market
from lattice.option import OptionTrade
from lattice.pricer import Pricer, column
from lattice.tree import Tree

T0 = datetime(2026, 9, 15)
MAT = datetime(2027, 9, 15)
MARKET = Market(100.0, 0.05, 0.20)


def build(market, nb_steps):
    """Un arbre construit, pret a etre price."""
    tree = Tree(market, T0, MAT, nb_steps)
    tree.build_tree()
    return tree


def trunks(tree):
    """Parcourt les troncs, de la racine jusqu'a la maturite."""
    trunk = tree.root
    while trunk is not None:
        yield trunk
        trunk = trunk.next_mid


@pytest.mark.parametrize("nb_steps", [20, 50, 100, 200])
def test_price_converges_to_black_scholes(nb_steps):
    # l'erreur decroit en 1/N : ecart x N reste autour de -2,96
    market = Market(100.0, 0.0, 0.30)
    price = Pricer(build(market, nb_steps), OptionTrade(100.0, MAT)).price_backward()
    erreur = price - bs_price(100.0, 100.0, 1.0, 0.0, 0.30)
    assert abs(erreur * nb_steps) < 3.2


def test_the_error_shrinks_when_nb_steps_grows():
    market = Market(100.0, 0.0, 0.30)
    reference = bs_price(100.0, 100.0, 1.0, 0.0, 0.30)
    ecarts = [
        abs(Pricer(build(market, n), OptionTrade(100.0, MAT)).price_backward() - reference)
        for n in (20, 50, 100, 200)
    ]
    assert ecarts == sorted(ecarts, reverse=True)


def test_each_column_has_two_n_plus_one_nodes():
    # preuve que l'arbre recombine et qu'aucune colonne n'a de trou
    tree = build(MARKET, 30)
    for index, trunk in enumerate(trunks(tree)):
        assert sum(1 for _ in column(trunk)) == 2 * index + 1


def test_proba_reach_sums_to_one_on_every_column():
    tree = build(MARKET, 30)
    for trunk in trunks(tree):
        total = sum(node.proba_reach for node in column(trunk))
        assert total == pytest.approx(1.0, abs=1e-12)


def test_every_node_has_valid_probabilities():
    tree = build(MARKET, 30)
    for trunk in trunks(tree):
        if trunk.next_mid is None:
            continue
        for node in column(trunk):
            assert node.p_up + node.p_mid + node.p_down == pytest.approx(1.0)
            for probability in (node.p_up, node.p_mid, node.p_down):
                assert 0.0 <= probability <= 1.0


def test_call_put_parity_holds_on_the_tree():
    # C - P = S0 - K e^(-rT), exact quel que soit le nombre de pas
    tree = build(MARKET, 200)
    call = Pricer(tree, OptionTrade(100.0, MAT, True)).price_backward()
    put = Pricer(tree, OptionTrade(100.0, MAT, False)).price_backward()
    assert call - put == pytest.approx(100.0 - 100.0 * math.exp(-0.05), abs=1e-10)


def test_american_call_equals_european_when_the_rate_is_positive():
    # sans dividende et avec r >= 0, exercer un call par anticipation n'apporte rien
    tree = build(MARKET, 100)
    european = Pricer(tree, OptionTrade(100.0, MAT, True)).price_backward()
    american = Pricer(tree, OptionTrade(100.0, MAT, True, True)).price_backward()
    assert american == pytest.approx(european, abs=1e-12)


def test_american_put_is_worth_more_when_the_rate_is_positive():
    # la ou le call n'y gagne rien, le put exerce par anticipation
    tree = build(MARKET, 100)
    european = Pricer(tree, OptionTrade(100.0, MAT, False)).price_backward()
    american = Pricer(tree, OptionTrade(100.0, MAT, False, True)).price_backward()
    assert american > european

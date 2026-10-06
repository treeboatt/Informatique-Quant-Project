import math
from datetime import datetime

import pytest

from lattice.market import Market, year_fraction
from lattice.option import OptionTrade
from lattice.pricer import Pricer
from lattice.tree import Tree

T0 = datetime(2026, 9, 15)
MAT = datetime(2027, 9, 15)
EX = datetime(2027, 3, 15)
DIVIDEND = 3.0
RATE = 0.05
VOL = 0.20

WITH_DIV = Market(100.0, RATE, VOL, DIVIDEND, EX)
T_EX = year_fraction(T0, EX)
MATURITY = year_fraction(T0, MAT)

# le prix du sous-jacent prive de la valeur actuelle du dividende
SPOT_EX_DIV = 100.0 - DIVIDEND * math.exp(-RATE * T_EX)


def build(market, nb_steps):
    """Un arbre construit, pret a etre price."""
    tree = Tree(market, T0, MAT, nb_steps)
    tree.build_tree()
    return tree


def priced(tree, strike, is_call=True):
    return Pricer(tree, OptionTrade(strike, MAT, is_call)).price_backward()


# un call de strike nul vaut le sous-jacent moins le dividende actualise,
# et c'est exact quel que soit le nombre de pas
@pytest.mark.parametrize("nb_steps", [10, 50, 200])
def test_a_call_with_a_zero_strike_is_worth_the_spot_minus_the_dividend(nb_steps):
    tree = build(WITH_DIV, nb_steps)
    assert priced(tree, 0.0) == pytest.approx(SPOT_EX_DIV, abs=1e-10)


# C - P = S0 - D e^(-r t_ex) - K e^(-rT), exact lui aussi
@pytest.mark.parametrize("nb_steps", [10, 50, 200])
def test_call_put_parity_holds_with_a_dividend(nb_steps):
    tree = build(WITH_DIV, nb_steps)
    expected = SPOT_EX_DIV - 100.0 * math.exp(-RATE * MATURITY)
    assert priced(tree, 100.0) - priced(tree, 100.0, False) == pytest.approx(expected, abs=1e-10)


# cas demande par l'enonce : avec r = 0, la parite se reduit a P - C = D
def test_with_a_zero_rate_the_put_exceeds_the_call_by_the_dividend():
    tree = build(Market(100.0, 0.0, VOL, DIVIDEND, EX), 200)
    call = priced(tree, 100.0)
    put = priced(tree, 100.0, False)
    assert put - call == pytest.approx(DIVIDEND, abs=1e-10)


# toujours avec r = 0 : le dividende fait baisser le call et monter le put
def test_with_a_zero_rate_the_dividend_lowers_the_call_and_raises_the_put():
    without = build(Market(100.0, 0.0, VOL), 200)
    with_div = build(Market(100.0, 0.0, VOL, DIVIDEND, EX), 200)
    assert priced(with_div, 100.0) < priced(without, 100.0)
    assert priced(with_div, 100.0, False) > priced(without, 100.0, False)


# un detachement apres la maturite ne doit rien changer du tout
def test_an_ex_date_outside_the_tree_changes_nothing():
    late = build(Market(100.0, RATE, VOL, DIVIDEND, datetime(2028, 3, 15)), 100)
    without = build(Market(100.0, RATE, VOL), 100)
    assert priced(late, 100.0) == priced(without, 100.0)


# avec un dividende raisonnable, aucun noeud ne doit etre impossible a apparier
def test_no_node_is_invalid_with_a_reasonable_dividend():
    assert build(WITH_DIV, 200).nb_invalid_nodes == 0

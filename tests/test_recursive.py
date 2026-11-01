import sys
from datetime import datetime

import pytest

from lattice.api import price
from lattice.market import Market
from lattice.option import OptionTrade, one_touch
from lattice.pricer import Pricer
from lattice.tree import Tree

T0 = datetime(2026, 9, 15)
MAT = datetime(2027, 9, 15)
EXDIV = datetime(2027, 3, 15)
FLAT = Market(100.0, 0.05, 0.25)
AVEC_DIV = Market(100.0, 0.05, 0.25, 3.0, EXDIV)


def les_deux(market, option, nb_steps=40, kind="trinomial"):
    """Le meme prix calcule dans les deux sens."""
    arriere = price(market, option, T0, nb_steps, kind=kind, method="backward")
    avant = price(market, option, T0, nb_steps, kind=kind, method="recursive")
    return arriere, avant


# les deux methodes parcourent le meme arbre et font la meme arithmetique dans
# le meme ordre : on attend l'egalite au bit pres, pas une approximation
def test_european_call_matches_backward():
    arriere, avant = les_deux(FLAT, OptionTrade(100.0, MAT))
    assert avant == arriere


def test_american_put_matches_backward():
    arriere, avant = les_deux(FLAT, OptionTrade(100.0, MAT, is_call=False, is_american=True))
    assert avant == arriere


def test_dividend_matches_backward():
    arriere, avant = les_deux(AVEC_DIV, OptionTrade(100.0, MAT))
    assert avant == arriere


def test_binomial_matches_backward():
    arriere, avant = les_deux(FLAT, OptionTrade(100.0, MAT), kind="binomial")
    assert avant == arriere


def test_binary_and_one_touch_match_backward():
    binaire = OptionTrade(105.0, MAT, True, False, True)
    assert les_deux(FLAT, binaire)[0] == les_deux(FLAT, binaire)[1]

    touche = one_touch(105.0, MAT)
    arriere, avant = les_deux(FLAT, touche)
    assert avant == arriere


# la recursion memorise dans option_value : si on oublie de remettre a None,
# le deuxieme prix rendu est celui de la premiere option
def test_a_second_option_on_the_same_tree_is_not_the_first():
    tree = Tree(FLAT, T0, MAT, 40)
    tree.build_tree()

    call = Pricer(tree, OptionTrade(100.0, MAT)).price_recursive()
    put = Pricer(tree, OptionTrade(100.0, MAT, is_call=False)).price_recursive()

    assert call != put
    assert put == pytest.approx(Pricer(tree, OptionTrade(100.0, MAT,
                                                        is_call=False)).price_backward())


def test_recursive_after_backward_on_the_same_tree():
    """Le backward laisse des valeurs derriere lui : la recursion doit les oublier."""
    tree = Tree(FLAT, T0, MAT, 40)
    tree.build_tree()

    call = OptionTrade(100.0, MAT)
    attendu = Pricer(tree, call).price_backward()

    Pricer(tree, OptionTrade(80.0, MAT)).price_backward()      # on salit l'arbre
    assert Pricer(tree, call).price_recursive() == attendu


def test_a_tree_deeper_than_the_recursion_limit_is_refused():
    """Le backward n'a pas cette limite : c'est l'interet de le garder."""
    trop = sys.getrecursionlimit()
    with pytest.raises(RecursionError, match="trop profond"):
        price(FLAT, OptionTrade(100.0, MAT), T0, trop, method="recursive")

    # le meme arbre passe sans probleme en backward
    assert price(FLAT, OptionTrade(100.0, MAT), T0, trop, method="backward") > 0.0


def test_an_unknown_method_is_refused():
    with pytest.raises(ValueError, match="unknown method"):
        price(FLAT, OptionTrade(100.0, MAT), T0, 20, method="monte-carlo")

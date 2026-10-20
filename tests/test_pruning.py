from datetime import datetime

import pytest

from lattice.market import Market
from lattice.option import OptionTrade
from lattice.pricer import Pricer, column
from lattice.tree import BinomialTree, Tree

T0 = datetime(2026, 9, 15)
MAT = datetime(2027, 9, 15)
MARKET = Market(100.0, 0.05, 0.20)
CALL = OptionTrade(100.0, MAT)


def build(nb_steps, prune=False, threshold=1e-7, cls=Tree):
    tree = cls(MARKET, T0, MAT, nb_steps, prune_threshold=threshold, prune=prune)
    tree.build_tree()
    return tree


def trunks(tree):
    trunk = tree.root
    while trunk is not None:
        yield trunk
        trunk = trunk.next_mid


def nb_nodes(tree):
    return sum(sum(1 for _ in column(trunk)) for trunk in trunks(tree))


def priced(tree):
    return Pricer(tree, CALL).price_backward()


# par defaut l'arbre est complet : le pruning se demande
def test_pruning_is_off_by_default():
    tree = build(30)
    assert tree.prune is False
    for index, trunk in enumerate(trunks(tree)):
        assert sum(1 for _ in column(trunk)) == 2 * index + 1


def test_pruning_removes_a_lot_of_nodes():
    assert nb_nodes(build(200, prune=True)) < 0.5 * nb_nodes(build(200))


# la probabilite du noeud elague est transmise a son next_mid, donc rien ne se perd
def test_proba_reach_still_sums_to_one_on_every_column():
    for trunk in trunks(build(200, prune=True)):
        total = sum(node.proba_reach for node in column(trunk))
        assert total == pytest.approx(1.0, abs=1e-12)


# un noeud elague suit tout droit et ne cree pas de successeurs haut et bas
def test_a_pruned_node_goes_straight_ahead():
    tree = build(100, prune=True)
    pruned = [n for trunk in trunks(tree) for n in column(trunk)
              if n.next_mid is not None and n.next_up is None]
    assert pruned, "aucun noeud elague, le seuil est trop bas"
    for node in pruned:
        assert (node.p_up, node.p_mid, node.p_down) == (0.0, 1.0, 0.0)
        assert node.next_down is None


def test_the_price_barely_moves():
    assert priced(build(200, prune=True)) == pytest.approx(priced(build(200)), abs=1e-6)


# le seuil est un arbitrage : plus il est bas, moins on elague mais plus on est juste
@pytest.mark.parametrize("threshold", [1e-10, 1e-8, 1e-6])
def test_a_lower_threshold_means_a_smaller_bias(threshold):
    reference = priced(build(200))
    loose = abs(priced(build(200, prune=True, threshold=1e-4)) - reference)
    tight = abs(priced(build(200, prune=True, threshold=threshold)) - reference)
    assert tight <= loose


def test_the_binomial_tree_can_be_pruned_too():
    full = nb_nodes(build(200, cls=BinomialTree))
    assert nb_nodes(build(200, prune=True, cls=BinomialTree)) < full

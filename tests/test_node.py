import math
from datetime import datetime, timedelta

import pytest

from lattice.node import Node, TrunkNode

ALPHA = 1.25

class FakeTree:
    def __init__(self, alpha = ALPHA, step_timedelta = timedelta(days = 30), nb_steps = 12):
        self.alpha = alpha
        self.step_timedelta = step_timedelta
        self.nb_steps = nb_steps

def build_node_with_next_column(vol = 0.25, r= 0.02, dt=1/12, s = 100.0):
    tree = FakeTree(alpha = math.exp(vol * math.sqrt(3*dt)))
    node = Node(s, tree)
    node.next_mid = Node(s, tree)
    fwd = s * math.exp(r*dt)
    var = s * s * math.exp(2*r*dt) * (math.exp(vol**2 * dt)-1)
    node.compute_probabilities(fwd, var)
    return node, fwd, var

def test_a_new_node_has_no_option_value():
    assert Node(100.0, FakeTree()).option_value is None

def test_get_or_create_up_creates_the_node_above_and_links_both_ways():
    node = Node(100.0, FakeTree())
    up_node = node.get_or_create_up()
    assert up_node.price == pytest.approx(125.0)
    assert node.up is up_node
    assert up_node.down is node

def test_get_or_create_down_creates_the_node_below_and_links_both_ways():
    node = Node(100.0, FakeTree())
    down_node = node.get_or_create_down()
    assert down_node.price == pytest.approx(80.0)
    assert node.down is down_node
    assert down_node.up is node

def test_get_or_create_never_creates_the_same_neighbour_twice():
    node = Node(100.0, FakeTree())
    assert node.get_or_create_down() is node.get_or_create_down()
    assert node.get_or_create_up() is node.get_or_create_up()

def test_find_closest_stays_put_when_the_node_is_already_the_closest():
    node = Node(100.0, FakeTree())
    assert node.find_closest(101.0) is node

def test_find_closest_climbs_to_the_nearest_node_above():
    node = Node(100.0, FakeTree())
    assert node.find_closest(130.0).price == pytest.approx(125.0)

def test_find_closest_descends_and_creates_the_missing_nodes():
    node = Node(100.0, FakeTree())
    found = node.find_closest(70.0)
    assert found.price == pytest.approx(64.0)
    assert node.down.price == pytest.approx(80)

def test_find_closest_refuses_a_negative_forward():
    node = Node(100.0, FakeTree())
    with pytest.raises(AssertionError):
        node.find_closest(-5.0)

def test_probabilities_sum_to_one_and_stay_between_zero_and_one():
    node, _, _ = build_node_with_next_column()
    assert node.p_up + node.p_mid + node.p_down == pytest.approx(1.0)
    for proba in (node.p_up,node.p_mid,node.p_down):
        assert 0.0 <= proba <= 1.0

def test_probabilities_reproduce_the_forward():
    node, fwd, _ = build_node_with_next_column()
    alpha = node.tree.alpha
    s_mid = node.next_mid.price
    moment = (alpha * s_mid * node.p_up +  s_mid * node.p_mid + s_mid * node.p_down / alpha)
    assert moment == pytest.approx(fwd, rel=1e-12)

def test_probabilities_reproduce_the_variance():
    node, fwd, var = build_node_with_next_column()
    s_mid = node.next_mid.price
    alpha = node.tree.alpha
    moment = (
        node.p_up * (s_mid * alpha)**2
        + node.p_mid * s_mid**2
        + node.p_down * (s_mid / alpha)**2
    )
    assert moment == pytest.approx(var + fwd**2, rel=1e-12)

def test_the_middle_probability_is_close_to_two_thirds():
    node, _, _ = build_node_with_next_column()
    assert node.p_mid == pytest.approx(2/3, abs = 0.01)

def test_next_date_advances_by_one_step():
    tree = FakeTree(step_timedelta=timedelta(days = 30))
    trunk = TrunkNode(100.0, tree, None, datetime(2026, 10, 24))
    assert trunk.next_date() == datetime(2026, 11, 23)


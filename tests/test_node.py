import math
from datetime import datetime, timedelta

import pytest

from lattice.market import Market
from lattice.node import Node, TrunkNode

ALPHA = 1.25

class FakeTree:
    def __init__(self, alpha = ALPHA, step_timedelta = timedelta(days = 30), nb_steps = 12,
                 market = Market(s0 = 100.0, rate = 0.02, vol = 0.25)):
        self.alpha = alpha
        self.step_timedelta = step_timedelta
        self.nb_steps = nb_steps
        self.market = market
        self.p_up, self.p_mid, self.p_down = 0.15, 0.65, 0.2
        self.prune_threshold = 1e-7
        self.nb_invalid_nodes = 0

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

COLUMN_DATE = datetime(2026, 10, 24)
NEXT_DATE = datetime(2026, 11, 23)

def trunk_with_dividend_on(ex_date):
    market = Market(s0 = 100.0, rate = 0.02, vol = 0.25, dividend = 3.0, div_ex_date = ex_date)
    return TrunkNode(100.0, FakeTree(market = market), None, COLUMN_DATE)

def test_no_dividend_in_the_period_without_ex_date():
    trunk = TrunkNode(100.0, FakeTree(), None, COLUMN_DATE)
    assert trunk.is_div_in_next_period is False

def test_dividend_strictly_inside_the_period():
    assert trunk_with_dividend_on(COLUMN_DATE + timedelta(days = 10)).is_div_in_next_period

def test_dividend_on_the_next_date_belongs_to_this_period():
    assert trunk_with_dividend_on(NEXT_DATE).is_div_in_next_period

def test_dividend_on_the_column_date_belongs_to_the_previous_period():
    assert not trunk_with_dividend_on(COLUMN_DATE).is_div_in_next_period

def test_dividend_before_or_after_the_period_is_ignored():
    assert not trunk_with_dividend_on(COLUMN_DATE - timedelta(days = 1)).is_div_in_next_period
    assert not trunk_with_dividend_on(NEXT_DATE + timedelta(days = 1)).is_div_in_next_period

def test_dates_equal_up_to_the_tolerance_are_the_same():
    # t0 + n * dt can miss the ex-date by a few microseconds
    almost_next = NEXT_DATE - timedelta(microseconds = 3)
    assert trunk_with_dividend_on(almost_next).is_div_in_next_period
    almost_column = COLUMN_DATE + timedelta(microseconds = 3)
    assert not trunk_with_dividend_on(almost_column).is_div_in_next_period

def test_constant_probabilities_are_copied_from_the_tree():
    node = Node(100.0, FakeTree())
    node.set_constant_probabilities()
    assert (node.p_up, node.p_mid, node.p_down) == (0.15, 0.65, 0.2)

def node_with_forward_two_nodes_above(proba_reach):
    node = Node(100.0, FakeTree())
    node.proba_reach = proba_reach
    node.next_mid = Node(100.0, node.tree)
    # forward 2 nodes above next_mid: impossible with probabilities in [0, 1]
    node.compute_probabilities(ALPHA**2 * 100.0, 1.0)
    return node

def test_invalid_probabilities_on_a_reachable_node_raise():
    with pytest.raises(ValueError):
        node_with_forward_two_nodes_above(proba_reach = 0.01)

def test_invalid_probabilities_on_an_unreachable_node_are_pruned_and_counted():
    node = node_with_forward_two_nodes_above(proba_reach = 1e-30)
    assert (node.p_up, node.p_mid, node.p_down) == (0.0, 1.0, 0.0)
    assert node.tree.nb_invalid_nodes == 1

def test_valid_probabilities_are_not_pruned():
    node, _, _ = build_node_with_next_column()
    assert node.has_valid_probabilities()
    assert node.tree.nb_invalid_nodes == 0

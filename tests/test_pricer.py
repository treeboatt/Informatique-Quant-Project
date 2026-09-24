from datetime import datetime

import pytest

from lattice.option import OptionTrade
from lattice.pricer import Pricer, column

MATURITY = datetime(2027, 1, 1)

P_UP, P_MID, P_DOWN = 0.2, 0.55, 0.25 

class FakeNode:
    def __init__(self, price):
        self.price = price
        self.up = None
        self.option_value = None
        self.down = None
        self.next_down = None
        self.next_mid = None
        self.next_up = None
        self.prec_mid = None
        self.p_up = 0.0
        self.p_mid = 0.0
        self.p_down = 0.0

class FakeTree:
    def __init__(self, root, df):
        self.root = root
        self.df = df

def set_probabilities(node):
    node.p_up = P_UP
    node.p_mid = P_MID
    node.p_down = P_DOWN

def build_two_step_tree():

    # 2nd column
    end_uu = FakeNode(156.25)
    end_u = FakeNode(125.0)
    end_m = FakeNode(100.0)
    end_d = FakeNode(80.0)
    end_dd = FakeNode(64.0)
    end_uu.down, end_u.up = end_u, end_uu
    end_u.down, end_m.up = end_m, end_u
    end_m.down, end_d.up = end_d, end_m
    end_d.down, end_dd.up = end_dd, end_d

    # 1st column
    mid_u = FakeNode(125.0)
    mid_m = FakeNode(100.0)
    mid_d = FakeNode(80.0)
    mid_u.down, mid_m.up = mid_m, mid_u
    mid_m.down, mid_d.up = mid_d, mid_m
    mid_u.next_up, mid_u.next_mid, mid_u.next_down = end_uu, end_u, end_m
    mid_m.next_up, mid_m.next_mid, mid_m.next_down = end_u, end_m, end_d
    mid_d.next_up, mid_d.next_mid, mid_d.next_down = end_m, end_d, end_dd

    root = FakeNode(100.0)
    root.next_up, root.next_mid, root.next_down = mid_u, mid_m, mid_d

    mid_m.prec_mid = root
    end_m.prec_mid = mid_m

    for node in (root, mid_u, mid_m, mid_d):
        set_probabilities(node)

    return FakeTree(root, df= 1.0)

def test_column_visits_every_node_of_the_column():
    tree = build_two_step_tree()
    last_trunk = tree.root.next_mid.next_mid
    prices = sorted(node.price for node in column(last_trunk))
    assert prices == [64.0, 80.0, 100.0, 125.0, 156.25]

def test_european_call_on_the_two_step_tree():
    tree = build_two_step_tree()
    option = OptionTrade(strike=100.0, maturity=MATURITY, is_call=True)
    price = Pricer(tree,option).price_backward()
    assert price == pytest.approx(7.75, abs=1e-12)

def test_european_put_on_the_two_step_tree():
    tree = build_two_step_tree()
    option = OptionTrade(strike=100.0, maturity=MATURITY, is_call=False)
    price = Pricer(tree,option).price_backward()
    assert price == pytest.approx(7.75, abs=1e-12)

def test_call_put_parity_with_zero_rate():
    call = OptionTrade(strike=100.0, maturity=MATURITY, is_call=True)
    put = OptionTrade(strike=100.0, maturity=MATURITY, is_call=False)
    call_price = Pricer(build_two_step_tree(), call).price_backward()
    put_price = Pricer(build_two_step_tree(), put).price_backward()
    assert call_price - put_price == pytest.approx(0.0, abs=1e-12)

@pytest.mark.parametrize("is_call", [True, False])
def test_american_equals_european_when_rate_is_zero(is_call):
    eu_call = OptionTrade(strike=100.0, maturity=MATURITY, is_call=is_call)
    us_call = OptionTrade(strike=100.0, maturity=MATURITY, is_call=is_call, is_american=True)
    eu_price = Pricer(build_two_step_tree(), eu_call).price_backward()
    us_price = Pricer(build_two_step_tree(), us_call).price_backward()
    assert eu_price == pytest.approx(us_price, abs=1e-12)

def test_american_node_exercises_when_deep_in_the_money():
        node = FakeNode(50.0)
        node.next_up, node.next_mid, node.next_down = FakeNode(60.0), FakeNode(50.0), FakeNode(40.0)
        node.next_up.option_value = 40.0
        node.next_mid.option_value = 45.0
        node.next_down.option_value = 50.0
        set_probabilities(node)
        Tree = FakeTree(node, df = 0.9)

        European_Put = OptionTrade(strike=100.0, maturity=MATURITY, is_call=False)
        American_Put = OptionTrade(strike=100.0, maturity=MATURITY, is_call=False, is_american=True)
        assert Pricer(Tree, European_Put)._node_value(node) == pytest.approx(40.725)
        assert Pricer(Tree, American_Put)._node_value(node) == pytest.approx(50.0)
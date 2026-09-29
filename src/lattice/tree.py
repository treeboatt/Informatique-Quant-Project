import math

from lattice.market import year_fraction
from lattice.node import TrunkNode


class Tree:
    def __init__(self, market, pricing_date, maturity, nb_steps, prune_threshold=1e-7):
        self.market = market
        self.pricing_date = pricing_date
        self.prune_threshold = prune_threshold
        self.nb_steps = nb_steps

        # time period of a step : in calendar days and in fraction of years
        self.step_timedelta  = (maturity - pricing_date)/nb_steps
        self.dt = year_fraction(pricing_date, maturity)/nb_steps

        self.alpha = math.exp(market.vol * math.sqrt(3*self.dt))
        self.df = math.exp(-market.rate * self.dt)
        self.growth = math.exp(market.rate * self.dt)
        self.var_factor = math.exp(2*market.rate*self.dt) * (math.exp(market.vol**2 *self.dt) -1)

        # without dividend, every node has the same probabilities: computed once here
        # (more precise than the general formula when fwd ~ s_mid, and faster)
        alpha = self.alpha
        self.p_down = (math.exp(market.vol**2 * self.dt) - 1) / ((1 - alpha) * (alpha**-2 - 1))
        self.p_up = self.p_down / alpha
        self.p_mid = 1.0 - self.p_up - self.p_down

        # nodes pruned because their probabilities could not be matched
        self.nb_invalid_nodes = 0

        self.root = TrunkNode(market.s0, self, None, pricing_date)
        self.root.proba_reach = 1.0

    def forward_and_variance(self, s, trunk):

        # if there are no dividend
        if not trunk.is_div_in_next_period:
            return s * self.growth, s * s * self.var_factor

        market = self.market
        t_to_end = year_fraction(market.div_ex_date, trunk.next_date())

        # if there are dividends
        fwd = s * self.growth - market.dividend * math.exp(market.rate * t_to_end)
        var = (s - (t_to_end / self.dt) * market.dividend)**2 * self.var_factor
        return fwd, var

    def link_successors(self, node, fwd, var, trunk):
        if not trunk.is_div_in_next_period:
            node.set_constant_probabilities()
        elif fwd <= 0.0:
            node.prune_invalid()
        else:
            node.compute_probabilities(fwd, var)
        node.next_up = node.next_mid.get_or_create_up()
        node.next_down = node.next_mid.get_or_create_down()

        node.next_up.proba_reach += node.proba_reach * node.p_up
        node.next_down.proba_reach += node.proba_reach * node.p_down
        node.next_mid.proba_reach += node.proba_reach * node.p_mid

    def build_tree(self):
        trunk = self.root
        for _ in range(self.nb_steps):
            trunk = self.build_next_column(trunk)
 
    def build_next_column(self, trunk):
        fwd, var = self.forward_and_variance(trunk.price, trunk)
        new_trunk = TrunkNode(fwd, self, trunk, trunk.next_date())
        trunk.next_mid = new_trunk
        self.link_successors(trunk, fwd, var, trunk)

        # We go up the column, node by node
        previous, node = trunk, trunk.up
        while node is not None:
            fwd, var = self.forward_and_variance(node.price, trunk)
            node.next_mid = previous.next_mid.find_closest(fwd)
            self.link_successors(node, fwd, var, trunk)
            previous, node = node, node.up

        # We go down the column, node by node
        previous, node = trunk, trunk.down
        while node is not None:
            fwd, var = self.forward_and_variance(node.price, trunk)
            # a large dividend can give a forward <= 0 at the bottom: no closest node,
            # the node keeps its neighbour's mid and is pruned in link_successors
            if fwd > 0.0:
                node.next_mid = previous.next_mid.find_closest(fwd)
            else:
                node.next_mid = previous.next_mid
            self.link_successors(node, fwd, var, trunk)
            previous, node = node, node.down

        return new_trunk

    
class BinomialTree(Tree):
    def __init__(self, market, pricing_date, maturity, nb_steps, prune_threshold=1e-7):
        super().__init__(market, pricing_date, maturity, nb_steps, prune_threshold)

        # binomial alpha: alpha + 1/alpha = 1 + exp(vol^2 dt)
        a = (1.0 + math.exp(market.vol**2 * self.dt)) / 2.0
        self.alpha = a + math.sqrt(a * a - 1.0)

        # two successors only, so no middle probability
        self.p_up = 1.0 / (self.alpha + 1.0)
        self.p_mid = 0.0
        self.p_down = 1.0 - self.p_up
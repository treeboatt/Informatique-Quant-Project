def column(trunk):
    yield trunk
    node = trunk.up
    while node is not None:
        yield node
        node = node.up
    node = trunk.down
    while node is not None:
        yield node
        node = node.down

class Pricer:
    def __init__(self, tree, option):
        self.tree = tree
        self.option = option

    def price_backward(self):

        # go to the last column
        trunk = self.tree.root
        while trunk.next_mid is not None:
            trunk = trunk.next_mid

        # at maturity, the price of an option is the value of its payoff
        for node in column(trunk):
            node.option_value = self.option.payoff(node.price)

        # backward_pricing column by column
        trunk = trunk.prec_mid
        while trunk is not None:
            for node in column(trunk):
                node.option_value =  self._node_value(node)
            trunk = trunk.prec_mid

        # we return the value of the root which is the price we are looking for
        return self.tree.root.option_value


    # value of the option at a particular node
    def _node_value(self, node):

        value = node.next_mid.option_value * node.p_mid
        if node.next_up is not None:
            value += node.next_up.option_value * node.p_up
        if node.next_down is not None:
            value += node.next_down.option_value * node.p_down

        # we actualize
        value *= self.tree.df

        if self.option.is_american:
            value = max(value, self.option.payoff(node.price))
        return value
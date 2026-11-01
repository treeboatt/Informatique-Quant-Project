import sys


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


    def price_recursive(self):
        """
        Meme prix que price_backward, mais en partant de la racine.

        On demande sa valeur a la racine, qui la demande a ses successeurs, et
        ainsi de suite jusqu'a la maturite. Sans memorisation, un arbre
        recombinant serait reparcouru 3^N fois : on retient donc la valeur dans
        option_value, et un noeud deja calcule la rend directement.
        """
        # une colonne = un niveau de recursion. python s'arrete vers 1000, et
        # c'est precisement l'argument en faveur du backward
        if self.tree.nb_steps + 50 > sys.getrecursionlimit():
            raise RecursionError(
                f"arbre trop profond pour la methode recursive : {self.tree.nb_steps} pas "
                f"pour une limite de recursion de {sys.getrecursionlimit()}. "
                f"price_backward n'a pas cette limite.")

        self._forget_values()
        return self._recursive_value(self.tree.root)

    def _forget_values(self):
        """
        Remet option_value a None partout.

        Indispensable avant une recursion : la memorisation considere qu'un
        noeud est deja calcule des que sa valeur n'est plus None. Sans cet
        oubli, le prix d'une option precedente serait rendu tel quel.
        """
        trunk = self.tree.root
        while trunk is not None:
            for node in column(trunk):
                node.option_value = None
            trunk = trunk.next_mid

    def _recursive_value(self, node):
        # deja calcule : c'est tout l'interet de la memorisation
        if node.option_value is not None:
            return node.option_value

        # pas de successeur : on est a la maturite, la valeur est le payoff
        if node.next_mid is None:
            node.option_value = self.option.payoff(node.price)
            return node.option_value

        # on fait calculer les successeurs avant de se servir de leurs valeurs
        for successor in (node.next_up, node.next_mid, node.next_down):
            if successor is not None:
                self._recursive_value(successor)

        node.option_value = self._node_value(node)
        return node.option_value

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
from lattice.pricer import Pricer
from lattice.tree import BinomialTree, Tree


# single entry point of the project. the tree is built on the maturity of the
# option, so the two can never disagree
def price(market, option, pricing_date, nb_steps, kind="trinomial", method="backward"):
    if kind == "trinomial":
        tree = Tree(market, pricing_date, option.maturity, nb_steps)
    elif kind == "binomial":
        tree = BinomialTree(market, pricing_date, option.maturity, nb_steps)
    else:
        raise ValueError(f"unknown kind: {kind}")

    if method != "backward":
        raise ValueError(f"unknown method: {method}")

    tree.build_tree()
    return Pricer(tree, option).price_backward()

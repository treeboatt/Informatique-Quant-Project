import matplotlib.pyplot as plt

from lattice.pricer import column


# on parcourt l'arbre uniquement par les pointeurs. les listes servent a
# matplotlib, jamais a retrouver un noeud
def plot_tree(tree, title="Arbre"):
    """Dessine les noeuds et les branches. La taille d'un noeud suit sa proba_reach."""
    fig, ax = plt.subplots(figsize=(9, 6))

    reached_x, reached_y, sizes = [], [], []
    empty_x, empty_y = [], []

    trunk = tree.root
    step = 0
    while trunk is not None:
        for node in column(trunk):
            if node.proba_reach > 0.0:
                reached_x.append(step)
                reached_y.append(node.price)
                sizes.append(20.0 + 500.0 * node.proba_reach)
            else:
                empty_x.append(step)
                empty_y.append(node.price)

            # une branche n'est tracee que si elle a une chance d'etre prise
            for successor, proba in ((node.next_up, node.p_up),
                                     (node.next_mid, node.p_mid),
                                     (node.next_down, node.p_down)):
                if successor is not None and proba > 0.0:
                    ax.plot([step, step + 1], [node.price, successor.price],
                            color="0.85", linewidth=0.6, zorder=1)

        trunk = trunk.next_mid
        step += 1

    ax.scatter(empty_x, empty_y, s=12, color="0.8", zorder=2, label="jamais atteint")
    ax.scatter(reached_x, reached_y, s=sizes, color="tab:blue", zorder=3,
               edgecolor="white", linewidth=0.5, label="atteint")

    ax.set_xlabel("pas")
    ax.set_ylabel("prix de l'action")
    ax.set_title(title)
    if empty_x:
        ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    return fig

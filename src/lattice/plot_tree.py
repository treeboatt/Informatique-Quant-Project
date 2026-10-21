import matplotlib.pyplot as plt

from lattice.pricer import column


# on parcourt l'arbre uniquement par les pointeurs. les listes servent a
# matplotlib, jamais a retrouver un noeud
def plot_tree(tree, title="Arbre", dark=False):
    """
    Dessine les noeuds et les branches. La taille d'un noeud suit sa proba_reach.
    dark=True pour l'application, qui a un fond sombre ; False pour le rapport.
    """
    fond = "#0F1318" if dark else "white"
    encre = "#E8EDF5" if dark else "black"
    plein = "#00E5A0" if dark else "tab:blue"
    vide = "#3A4252" if dark else "0.8"
    branche = "#1E2530" if dark else "0.85"

    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor(fond)
    ax.set_facecolor(fond)
    ax.tick_params(colors=encre)
    for cote in ax.spines.values():
        cote.set_color(encre)

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
                            color=branche, linewidth=0.6, zorder=1)

        trunk = trunk.next_mid
        step += 1

    ax.scatter(empty_x, empty_y, s=12, color=vide, zorder=2, label="jamais atteint")
    ax.scatter(reached_x, reached_y, s=sizes, color=plein, zorder=3,
               edgecolor=fond, linewidth=0.5, label="atteint")

    ax.set_xlabel("pas", color=encre)
    ax.set_ylabel("prix de l'action", color=encre)
    ax.set_title(title, color=encre)
    if empty_x:
        legende = ax.legend(loc="upper left", fontsize=8, facecolor=fond, edgecolor=branche)
        for texte in legende.get_texts():
            texte.set_color(encre)
    fig.tight_layout()
    return fig

import matplotlib.pyplot as plt

from lattice.pricer import column


def is_exercised(node, option):
    """
    Vrai si a ce noeud il vaut mieux exercer PAR ANTICIPATION que garder.

    On le repere sans rien stocker en plus : le pricer a pris le maximum entre
    garder et exercer, donc si la valeur du noeud est exactement le payoff,
    c'est qu'on a exerce.

    La derniere colonne est exclue : a maturite on exerce forcement si on est
    dans la monnaie, ce n'est pas de l'exercice anticipe.
    """
    if node.option_value is None or node.next_mid is None:
        return False
    paye = option.payoff(node.price)
    return paye > 0.0 and abs(node.option_value - paye) < 1e-12


# on parcourt l'arbre uniquement par les pointeurs. les listes servent a
# matplotlib, jamais a retrouver un noeud
def plot_tree(tree, title="Arbre", dark=False, option=None):
    """
    Dessine les noeuds et les branches. La taille d'un noeud suit sa proba_reach.
    dark=True pour l'application, qui a un fond sombre ; False pour le rapport.
    Si on passe une option americaine deja pricee, les noeuds ou il vaut mieux
    exercer sont colories differemment.
    """
    fond = "#0F1318" if dark else "white"
    encre = "#E8EDF5" if dark else "black"
    garder = "#00E5A0" if dark else "tab:blue"
    exercer = "#FF4D6A" if dark else "tab:red"
    vide = "#3A4252" if dark else "0.8"
    branche = "#1E2530" if dark else "0.85"

    # on ne colorie la frontiere que si l'option est americaine et deja pricee
    frontiere = option is not None and option.is_american

    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor(fond)
    ax.set_facecolor(fond)
    ax.tick_params(colors=encre)
    for cote in ax.spines.values():
        cote.set_color(encre)

    gardes_x, gardes_y, gardes_s = [], [], []
    exerces_x, exerces_y, exerces_s = [], [], []
    vides_x, vides_y = [], []

    trunk = tree.root
    step = 0
    while trunk is not None:
        for node in column(trunk):
            taille = 20.0 + 500.0 * node.proba_reach
            if node.proba_reach <= 0.0:
                vides_x.append(step)
                vides_y.append(node.price)
            elif frontiere and is_exercised(node, option):
                exerces_x.append(step)
                exerces_y.append(node.price)
                exerces_s.append(taille)
            else:
                gardes_x.append(step)
                gardes_y.append(node.price)
                gardes_s.append(taille)

            # une branche n'est tracee que si elle a une chance d'etre prise
            for successor, proba in ((node.next_up, node.p_up),
                                     (node.next_mid, node.p_mid),
                                     (node.next_down, node.p_down)):
                if successor is not None and proba > 0.0:
                    ax.plot([step, step + 1], [node.price, successor.price],
                            color=branche, linewidth=0.6, zorder=1)

        trunk = trunk.next_mid
        step += 1

    ax.scatter(vides_x, vides_y, s=12, color=vide, zorder=2, label="jamais atteint")
    ax.scatter(gardes_x, gardes_y, s=gardes_s, color=garder, zorder=3,
               edgecolor=fond, linewidth=0.5, label="garder" if frontiere else "atteint")
    if exerces_x:
        ax.scatter(exerces_x, exerces_y, s=exerces_s, color=exercer, zorder=4,
                   edgecolor=fond, linewidth=0.5, label="exercer")

    ax.set_xlabel("pas", color=encre)
    ax.set_ylabel("prix de l'action", color=encre)
    ax.set_title(title, color=encre)
    if vides_x or exerces_x:
        legende = ax.legend(loc="upper left", fontsize=8, facecolor=fond, edgecolor=branche)
        for texte in legende.get_texts():
            texte.set_color(encre)
    fig.tight_layout()
    return fig

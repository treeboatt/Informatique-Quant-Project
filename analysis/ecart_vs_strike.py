"""
Ecart arbre / Black-Scholes en fonction du strike, a nombre de pas fixe.
Montre la dent de scie : l'erreur depend de la position du strike par rapport
aux noeuds de la derniere colonne.
Produit la figure de la section "erreur et strike" du rapport.

    python analysis/ecart_vs_strike.py
"""

from datetime import datetime

import matplotlib.pyplot as plt

from lattice.black_scholes import bs_price
from lattice.market import Market
from lattice.option import OptionTrade
from lattice.pricer import Pricer, column
from lattice.tree import BinomialTree, Tree

T0 = datetime(2026, 1, 1)
MAT = datetime(2027, 1, 1)
ANNEES = 1.0

MARKET = Market(100.0, 0.0, 0.30)
NB_STEPS = 100

# on balaie finement autour de la monnaie pour voir la dent de scie
STRIKES = [85.0 + 0.1 * i for i in range(301)]


def prix_derniere_colonne(tree, bas, haut):
    """
    Les prix des noeuds de la derniere colonne, entre bas et haut.

    On y accede uniquement par pointeurs. La liste ne sert qu'a dessiner des
    traits verticaux : on ne s'en sert jamais pour retrouver un noeud.
    """
    trunk = tree.root
    while trunk.next_mid is not None:
        trunk = trunk.next_mid
    return sorted(n.price for n in column(trunk) if bas <= n.price <= haut)


def construire(sorte):
    """Un seul arbre par sorte : il sert ensuite a pricer tous les strikes."""
    classe = Tree if sorte == "trinomial" else BinomialTree
    tree = classe(MARKET, T0, MAT, NB_STEPS, prune=True)
    tree.build_tree()
    return tree


def mesures():
    """Pour chaque sorte d'arbre, l'ecart a Black-Scholes strike par strike."""
    ecarts, arbres = {}, {}
    for sorte in ("trinomial", "binomial"):
        tree = construire(sorte)
        arbres[sorte] = tree
        ecarts[sorte] = []
        for strike in STRIKES:
            call = OptionTrade(strike, MAT)
            exact = bs_price(MARKET.s0, strike, ANNEES, MARKET.rate, MARKET.vol, True)
            ecarts[sorte].append(Pricer(tree, call).price_backward() - exact)
    return arbres, ecarts


def tableau(arbres, ecarts):
    """On compare un strike pose sur un noeud et un strike entre deux noeuds."""
    noeuds = prix_derniere_colonne(arbres["trinomial"], STRIKES[0], STRIKES[-1])
    print("=== NOEUDS DE LA DERNIERE COLONNE DANS LA FENETRE BALAYEE ===")
    print("  ".join(f"{p:.3f}" for p in noeuds))
    voisins = [b - a for a, b in zip(noeuds, noeuds[1:])]
    print(f"decalage entre deux noeuds voisins : {sum(voisins) / len(voisins):.4f} EUR")

    print()
    print("=== ECART SELON LA POSITION DU STRIKE ===")
    print(f"{'sorte':>10} | {'ecart max':>10} {'ecart min':>10} {'amplitude':>10}")
    for sorte in ("trinomial", "binomial"):
        serie = ecarts[sorte]
        print(f"{sorte:>10} | {max(serie):+10.4f} {min(serie):+10.4f} "
              f"{max(serie) - min(serie):10.4f}")


def figure(arbres, ecarts):
    """La dent de scie, avec les noeuds de la derniere colonne en pointilles."""
    fig, axe = plt.subplots(figsize=(11, 4.5))
    axe.axhline(0.0, color="black", linewidth=0.8)

    # les traits verticaux marquent les noeuds : les creux tombent dessus
    for i, prix_noeud in enumerate(prix_derniere_colonne(arbres["trinomial"],
                                                         STRIKES[0], STRIKES[-1])):
        axe.axvline(prix_noeud, color="0.85", linewidth=0.8, zorder=0,
                    label="noeud de la derniere colonne" if i == 0 else None)

    for sorte in ("trinomial", "binomial"):
        axe.plot(STRIKES, ecarts[sorte], linewidth=1.2, label=sorte)

    axe.set_xlabel("strike (EUR)")
    axe.set_ylabel("arbre - Black-Scholes (EUR)")
    axe.set_title(f"Erreur en fonction du strike, {NB_STEPS} pas, spot a {MARKET.s0:.0f}")
    # on degage le haut du cadre pour que la legende ne couvre pas les courbes
    bas, haut = axe.get_ylim()
    axe.set_ylim(bas, haut + 0.45 * (haut - bas))
    axe.legend(loc="upper center", ncol=3)
    axe.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("results/ecart_strike.png", dpi=140)
    print()
    print("figure ecrite dans results/ecart_strike.png")


if __name__ == "__main__":
    tous_arbres, tous_ecarts = mesures()
    tableau(tous_arbres, tous_ecarts)
    figure(tous_arbres, tous_ecarts)

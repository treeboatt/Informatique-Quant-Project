"""
Pourquoi une binaire converge beaucoup moins bien qu'une vanille, et ce que
rapporte le one-touch par rapport a la binaire europeenne.

Une vanille a un angle au strike : l'arbre le rabote et se trompe d'un ecart
regulier en 1/N, d'ou le "tunnel". Une binaire a un saut : selon que la
barriere tombe sur un noeud ou entre deux noeuds, le prix bascule, et
l'erreur ne se range pas dans un tunnel.

Produit la figure de la section "binaires" du rapport.

    python analysis/convergence_binaire.py
"""

import math
from datetime import datetime

import matplotlib.pyplot as plt

from lattice.api import price
from lattice.black_scholes import bs_digital, bs_price
from lattice.market import Market
from lattice.option import OptionTrade, one_touch
from lattice.pricer import Pricer
from lattice.tree import Tree

T0 = datetime(2026, 1, 1)
MAT = datetime(2027, 1, 1)
ANNEES = 1.0

# le cas de reference du projet, ou le tunnel de la vanille est parfaitement
# plat : le strike tombe sur un noeud a chaque N, donc rien ne vient brouiller
# la comparaison avec la binaire
MARKET = Market(100.0, 0.0, 0.30)
STRIKE = 100.0
NB_STEPS = 500

PAS = list(range(20, 301, 10))
BARRIERES = [100.0 + 1.0 * i for i in range(31)]


def mesures_convergence():
    """Ecart a la formule fermee, pour la vanille et pour la binaire."""
    vanille = OptionTrade(STRIKE, MAT)
    binaire = OptionTrade(STRIKE, MAT, is_call=True, is_american=False, is_binary=True)

    exact_v = bs_price(MARKET.s0, STRIKE, ANNEES, MARKET.rate, MARKET.vol, True)
    exact_b = bs_digital(MARKET.s0, STRIKE, ANNEES, MARKET.rate, MARKET.vol, True)

    ecarts = {"vanille": [], "binaire": []}
    for n in PAS:
        ecarts["vanille"].append(price(MARKET, vanille, T0, n, prune=True) - exact_v)
        ecarts["binaire"].append(price(MARKET, binaire, T0, n, prune=True) - exact_b)

    # on rapporte l'ecart au prix exact : 1 centime sur une vanille de 12 EUR
    # et 1 centime sur une binaire de 0,47 EUR ne sont pas la meme erreur
    relatifs = {"vanille": exact_v, "binaire": exact_b}

    print(f"=== CONVERGENCE (vanille {exact_v:.6f}, binaire {exact_b:.6f}) ===")
    print(f"{'N':>5} | {'vanille':>12} {'rel x N':>9} | {'binaire':>12} {'rel x N':>9}")
    for i, n in enumerate(PAS):
        if n % 50 == 0 or n == 20:
            ev, eb = ecarts["vanille"][i], ecarts["binaire"][i]
            print(f"{n:5d} | {ev:+12.6f} {ev / exact_v * n:+9.3f} | "
                  f"{eb:+12.6f} {eb / exact_b * n:+9.3f}")

    for nom in ("vanille", "binaire"):
        produits = [e / relatifs[nom] * n for e, n in zip(ecarts[nom], PAS)]
        print(f"{nom:>8} : erreur relative x N de {min(produits):+.3f} a "
              f"{max(produits):+.3f}, soit une amplitude de {max(produits) - min(produits):.3f}")

    # l'erreur x N de la binaire ne se stabilise pas, mais l'erreur x racine(N)
    # oui : la binaire converge en 1/racine(N), pas en 1/N
    print()
    print("=== LA BINAIRE CONVERGE EN 1/RACINE(N) ===")
    print(f"{'N':>5} | {'erreur x N':>11} {'erreur x rac(N)':>16}")
    for i, n in enumerate(PAS):
        if n % 50 == 0 or n == 20:
            ecart = ecarts["binaire"][i]
            print(f"{n:5d} | {ecart * n:+11.3f} {ecart * math.sqrt(n):+16.4f}")
    return ecarts


def mesures_barriere():
    """One-touch contre binaire europeenne, sur un seul arbre."""
    tree = Tree(MARKET, T0, MAT, NB_STEPS, prune=True)
    tree.build_tree()

    europeennes, touches = [], []
    for barriere in BARRIERES:
        binaire = OptionTrade(barriere, MAT, True, False, True)
        europeennes.append(Pricer(tree, binaire).price_backward())
        touches.append(Pricer(tree, one_touch(barriere, MAT)).price_backward())

    print()
    print(f"=== ONE-TOUCH CONTRE BINAIRE EUROPEENNE ({NB_STEPS} pas) ===")
    print(f"{'barriere':>9} | {'europeenne':>11} {'one-touch':>11} {'rapport':>8}")
    for barriere, eu, us in zip(BARRIERES, europeennes, touches):
        if barriere % 5 == 0:
            print(f"{barriere:9.0f} | {eu:11.6f} {us:11.6f} {us / eu:8.2f}")
    return europeennes, touches


def figure(ecarts, europeennes, touches):
    """A gauche le tunnel qui n'existe pas, a droite la prime du one-touch."""
    fig, (gauche, droite) = plt.subplots(1, 2, figsize=(11, 4))

    gauche.axhline(0.0, color="black", linewidth=0.8)
    for nom in ("vanille", "binaire"):
        # on normalise par le prix exact pour comparer deux produits qui ne
        # valent pas du tout la meme chose (12 EUR contre 0,5 EUR)
        reference = bs_price(MARKET.s0, STRIKE, ANNEES, MARKET.rate, MARKET.vol, True) \
            if nom == "vanille" \
            else bs_digital(MARKET.s0, STRIKE, ANNEES, MARKET.rate, MARKET.vol, True)
        gauche.plot(PAS, [e / reference * n for e, n in zip(ecarts[nom], PAS)],
                    "o-", markersize=3, label=f"{nom}, erreur x N")

        # pour la binaire on trace aussi l'erreur x racine(N) : c'est elle qui
        # se stabilise, donc c'est la le bon ordre de convergence
        if nom == "binaire":
            gauche.plot(PAS, [e / reference * math.sqrt(n)
                              for e, n in zip(ecarts[nom], PAS)],
                        "s--", markersize=3, color="tab:green",
                        label="binaire, erreur x racine(N)")

    gauche.set_xlabel("nombre de pas")
    gauche.set_ylabel("erreur relative x N  ou  x racine(N)")
    gauche.set_title("La vanille converge en 1/N,\nla binaire seulement en 1/racine(N)")

    droite.plot(BARRIERES, europeennes, "o-", markersize=3, label="binaire europeenne")
    droite.plot(BARRIERES, touches, "o-", markersize=3, label="one-touch")
    droite.set_xlabel("barriere (EUR)")
    droite.set_ylabel("prime (EUR)")
    droite.set_title("Toucher une fois rapporte toujours plus\nque finir au-dessus")

    for axe in (gauche, droite):
        axe.legend()
        axe.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("results/binaire.png", dpi=140)
    print()
    print("figure ecrite dans results/binaire.png")


if __name__ == "__main__":
    tous_ecarts = mesures_convergence()
    prix_eu, prix_us = mesures_barriere()
    figure(tous_ecarts, prix_eu, prix_us)

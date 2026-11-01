"""
Les deux methodes de valorisation : backward (par colonnes) contre recursive
(depuis la racine, avec memorisation).

Elles rendent le meme prix au bit pres, mais pas au meme cout : la recursion
empile un niveau par colonne, donc elle paie des appels de fonction que le
backward n'a pas, et elle bute sur la limite de recursion de Python.
Produit la figure de la section "deux parcours" du rapport.

    python analysis/backward_vs_recursif.py
"""

import sys
import time
from datetime import datetime

import matplotlib.pyplot as plt

from lattice.market import Market
from lattice.option import OptionTrade
from lattice.pricer import Pricer
from lattice.tree import Tree

T0 = datetime(2026, 1, 1)
MAT = datetime(2027, 1, 1)
MARKET = Market(100.0, 0.05, 0.25)
CALL = OptionTrade(100.0, MAT)

PAS = [50, 100, 200, 300, 500, 700, 900]


def chronometre(methode, repetitions=3):
    """Le meilleur temps sur plusieurs passages, en millisecondes."""
    meilleur = float("inf")
    for _ in range(repetitions):
        depart = time.perf_counter()
        prix = methode()
        meilleur = min(meilleur, time.perf_counter() - depart)
    return prix, meilleur * 1000.0


def mesures():
    """Prix et temps des deux methodes, sur le meme arbre deja construit."""
    print("=== BACKWARD CONTRE RECURSIF (arbre deja construit) ===")
    print(f"{'N':>5} | {'backward':>11} {'recursif':>11} {'rapport':>8} | {'ecart de prix':>14}")

    temps = {"backward": [], "recursif": []}
    for n in PAS:
        tree = Tree(MARKET, T0, MAT, n)
        tree.build_tree()
        pricer = Pricer(tree, CALL)

        prix_a, t_a = chronometre(pricer.price_backward)
        prix_r, t_r = chronometre(pricer.price_recursive)

        temps["backward"].append(t_a)
        temps["recursif"].append(t_r)
        print(f"{n:5d} | {t_a:9.1f}ms {t_r:9.1f}ms {t_r / t_a:8.2f} | {prix_r - prix_a:+14.1e}")

    return temps


def la_limite():
    """La profondeur maximale que la recursion accepte."""
    print()
    print("=== LA LIMITE DE LA RECURSION ===")
    limite = sys.getrecursionlimit()
    print(f"  limite de recursion de Python : {limite}")
    print(f"  un arbre a {limite} pas est refuse par price_recursive :")
    tree = Tree(MARKET, T0, MAT, limite)
    tree.build_tree()
    try:
        Pricer(tree, CALL).price_recursive()
    except RecursionError as erreur:
        print(f"    RecursionError : {erreur}")
    print(f"  le meme arbre en backward : {Pricer(tree, CALL).price_backward():.8f}")


def figure(temps):
    """A gauche les temps, a droite le surcout de la recursion."""
    fig, (gauche, droite) = plt.subplots(1, 2, figsize=(11, 4))

    for nom in ("backward", "recursif"):
        gauche.plot(PAS, temps[nom], "o-", markersize=4, label=nom)
    gauche.set_xlabel("nombre de pas")
    gauche.set_ylabel("temps de valorisation (ms)")
    gauche.set_title("Les deux parcours, arbre deja construit")

    droite.axhline(1.0, color="black", linestyle="--", linewidth=1,
                   label="meme cout")
    droite.plot(PAS, [r / a for r, a in zip(temps["recursif"], temps["backward"])],
                "o-", markersize=4, color="tab:red", label="recursif / backward")
    droite.set_xlabel("nombre de pas")
    droite.set_ylabel("rapport des temps")
    droite.set_title("Ce que coute la recursion")

    for axe in (gauche, droite):
        axe.legend()
        axe.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("results/backward_vs_recursif.png", dpi=140)
    print()
    print("figure ecrite dans results/backward_vs_recursif.png")


if __name__ == "__main__":
    figure(mesures())
    la_limite()

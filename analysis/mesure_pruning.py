"""
Mesure du gain du pruning : nombre de noeuds, temps de construction et memoire.
Produit le tableau et les deux figures de la section "pruning" du rapport.

    python analysis/mesure_pruning.py
"""

import time
import tracemalloc
from datetime import datetime

import matplotlib.pyplot as plt

from lattice.market import Market
from lattice.option import OptionTrade
from lattice.pricer import Pricer, column
from lattice.tree import Tree

T0 = datetime(2026, 1, 1)
MAT = datetime(2027, 1, 1)
MARKET = Market(100.0, 0.05, 0.20)
CALL = OptionTrade(100.0, MAT)

PAS = [50, 100, 200, 400, 700, 1000]
SEUILS = [1e-10, 1e-8, 1e-7, 1e-5, 1e-3]


def nb_noeuds(tree):
    """Compte les noeuds en parcourant l'arbre par les pointeurs."""
    total = 0
    trunk = tree.root
    while trunk is not None:
        total += sum(1 for _ in column(trunk))
        trunk = trunk.next_mid
    return total


def construire(nb_steps, prune, seuil=1e-7):
    """Construit un arbre et renvoie noeuds, temps (s) et memoire (Mo)."""
    tracemalloc.start()
    depart = time.perf_counter()

    tree = Tree(MARKET, T0, MAT, nb_steps, prune_threshold=seuil, prune=prune)
    tree.build_tree()

    duree = time.perf_counter() - depart
    memoire = tracemalloc.get_traced_memory()[1] / (1024 * 1024)
    tracemalloc.stop()

    return tree, nb_noeuds(tree), duree, memoire


def tableau_du_gain():
    """Le tableau principal : sans pruning contre avec pruning."""
    print("=== GAIN DU PRUNING (seuil 1e-7) ===")
    print(f"{'N':>5} | {'noeuds OFF':>11} {'ON':>9} {'gain':>6} | "
          f"{'temps OFF':>10} {'ON':>8} | {'Mo OFF':>7} {'ON':>7} | {'biais':>10}")

    mesures = []
    for n in PAS:
        plein, n_plein, t_plein, m_plein = construire(n, prune=False)
        elague, n_elag, t_elag, m_elag = construire(n, prune=True)

        prix_plein = Pricer(plein, CALL).price_backward()
        prix_elag = Pricer(elague, CALL).price_backward()

        print(f"{n:5d} | {n_plein:11d} {n_elag:9d} "
              f"{100 * (1 - n_elag / n_plein):5.1f}% | "
              f"{t_plein * 1000:9.0f}ms {t_elag * 1000:6.0f}ms | "
              f"{m_plein:6.1f} {m_elag:6.1f}  | {prix_elag - prix_plein:+.2e}")

        mesures.append((n, n_plein, n_elag, m_plein, m_elag))
    return mesures


def tableau_des_seuils(nb_steps=500):
    """L'arbitrage seuil / biais, demande par l'enonce."""
    print()
    print(f"=== ARBITRAGE SEUIL / BIAIS (N = {nb_steps}) ===")
    reference, n_ref, _, m_ref = construire(nb_steps, prune=False)
    prix_ref = Pricer(reference, CALL).price_backward()
    print(f"{'seuil':>8} | {'noeuds':>8} {'gain':>6} | {'Mo':>6} | {'prix':>14} | {'biais':>10}")
    print(f"{'aucun':>8} | {n_ref:8d} {'-':>6} | {m_ref:6.1f} | {prix_ref:14.10f} | {'-':>10}")

    for seuil in SEUILS:
        tree, noeuds, _, memoire = construire(nb_steps, prune=True, seuil=seuil)
        prix = Pricer(tree, CALL).price_backward()
        print(f"{seuil:8.0e} | {noeuds:8d} {100 * (1 - noeuds / n_ref):5.1f}% | "
              f"{memoire:6.1f} | {prix:14.10f} | {prix - prix_ref:+.2e}")


def figures(mesures):
    """Deux graphes : les noeuds et la memoire, avec et sans pruning."""
    pas = [m[0] for m in mesures]
    fig, (gauche, droite) = plt.subplots(1, 2, figsize=(11, 4))

    gauche.plot(pas, [m[1] for m in mesures], "o-", label="sans pruning")
    gauche.plot(pas, [m[2] for m in mesures], "o-", label="avec pruning")
    gauche.set_xlabel("nombre de pas")
    gauche.set_ylabel("nombre de noeuds")
    gauche.set_title("Noeuds construits")

    droite.plot(pas, [m[3] for m in mesures], "o-", label="sans pruning")
    droite.plot(pas, [m[4] for m in mesures], "o-", label="avec pruning")
    droite.set_xlabel("nombre de pas")
    droite.set_ylabel("memoire (Mo)")
    droite.set_title("Memoire utilisee")

    for axe in (gauche, droite):
        axe.legend()
        axe.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("results/pruning.png", dpi=140)
    print()
    print("figure ecrite dans results/pruning.png")


if __name__ == "__main__":
    figures(tableau_du_gain())
    tableau_des_seuils()

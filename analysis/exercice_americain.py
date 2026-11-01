"""
Prime d'exercice anticipe : effet du taux d'interet et du dividende.
Montre les deux resultats de l'enonce : le call sans dividende ne s'exerce
jamais par anticipation quand le taux est positif (cas d'egalite), mais il
s'exerce des que le taux devient negatif ou qu'un dividende est detache.
Produit la figure de la section "americaines" du rapport.

    python analysis/exercice_americain.py
"""

from datetime import datetime

import matplotlib.pyplot as plt

from lattice.market import Market
from lattice.option import OptionTrade
from lattice.plot_tree import is_exercised
from lattice.pricer import Pricer, column
from lattice.tree import Tree

T0 = datetime(2026, 1, 1)
MAT = datetime(2027, 1, 1)
EX_DIV = datetime(2026, 7, 1)

SPOT = 100.0
VOL = 0.25
NB_STEPS = 100

TAUX = [-0.05 + 0.005 * i for i in range(27)]
DIVIDENDES = [0.5 * i for i in range(25)]


def primes(market):
    """
    Prime americaine du call et du put sur un meme arbre.

    Un seul arbre sert aux quatre valorisations : price_backward reecrit
    option_value a chaque passage, donc rien ne reste d'une option a l'autre.
    """
    tree = Tree(market, T0, MAT, NB_STEPS)
    tree.build_tree()

    resultats = {}
    for nom, is_call in (("call", True), ("put", False)):
        europeenne = OptionTrade(SPOT, MAT, is_call, False)
        americaine = OptionTrade(SPOT, MAT, is_call, True)
        prix_eu = Pricer(tree, europeenne).price_backward()
        prix_us = Pricer(tree, americaine).price_backward()
        resultats[nom] = prix_us - prix_eu
    return resultats


def noeuds_exerces(market, is_call):
    """Combien de noeuds preferent exercer par anticipation."""
    tree = Tree(market, T0, MAT, NB_STEPS)
    tree.build_tree()
    americaine = OptionTrade(SPOT, MAT, is_call, True)
    Pricer(tree, americaine).price_backward()

    total, trunk = 0, tree.root
    while trunk is not None:
        total += sum(1 for n in column(trunk) if is_exercised(n, americaine))
        trunk = trunk.next_mid
    return total


def par_taux():
    """La prime des deux sens quand le taux passe du negatif au positif."""
    print("=== PRIME D'EXERCICE ANTICIPE SELON LE TAUX (sans dividende) ===")
    print(f"{'taux':>7} | {'call':>12} {'put':>12}")
    mesures = {"call": [], "put": []}
    for taux in TAUX:
        resultats = primes(Market(SPOT, taux, VOL))
        mesures["call"].append(resultats["call"])
        mesures["put"].append(resultats["put"])
        if abs(taux * 1000) % 10 < 1e-9:
            print(f"{taux:7.1%} | {resultats['call']:12.6f} {resultats['put']:12.6f}")
    return mesures


def par_dividende():
    """La prime du call quand on grossit le dividende detache a 6 mois."""
    print()
    print("=== PRIME DU CALL AMERICAIN SELON LE DIVIDENDE (taux 5 %) ===")
    print(f"{'D':>6} | {'prime':>12}")
    mesures = []
    for dividende in DIVIDENDES:
        market = Market(SPOT, 0.05, VOL, dividende, EX_DIV)
        prime = primes(market)["call"]
        mesures.append(prime)
        if dividende % 2 == 0:
            print(f"{dividende:6.1f} | {prime:12.6f}")

    # le seuil : le dividende doit depasser les interets perdus sur le strike
    premier = next((d for d, p in zip(DIVIDENDES, mesures) if p > 1e-9), None)
    print(f"premier dividende qui declenche l'exercice anticipe : {premier} EUR")
    return mesures


def figure(par_t, par_d):
    """A gauche l'effet du taux, a droite l'effet du dividende."""
    fig, (gauche, droite) = plt.subplots(1, 2, figsize=(11, 4))

    gauche.axhline(0.0, color="black", linewidth=0.8)
    gauche.axvline(0.0, color="0.7", linestyle="--", linewidth=1)
    for nom in ("call", "put"):
        gauche.plot([t * 100 for t in TAUX], par_t[nom], "o-", markersize=3, label=nom)
    gauche.set_xlabel("taux d'interet (%)")
    gauche.set_ylabel("americaine - europeenne (EUR)")
    gauche.set_title("Sans dividende : le call ne vaut plus\nque le taux soit negatif")

    droite.axhline(0.0, color="black", linewidth=0.8)
    droite.plot(DIVIDENDES, par_d, "o-", markersize=3, color="tab:red", label="call")
    droite.set_xlabel("dividende detache a 6 mois (EUR)")
    droite.set_ylabel("americaine - europeenne (EUR)")
    droite.set_title("Call, taux 5 % : un dividende assez gros\nfait reapparaitre l'exercice")

    for axe in (gauche, droite):
        axe.legend()
        axe.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("results/americain.png", dpi=140)
    print()
    print("figure ecrite dans results/americain.png")


if __name__ == "__main__":
    mesures_taux = par_taux()
    mesures_div = par_dividende()

    print()
    print("=== NOEUDS D'EXERCICE ANTICIPE (taux 5 %, sans dividende) ===")
    reference = Market(SPOT, 0.05, VOL)
    print(f"call : {noeuds_exerces(reference, True)} noeuds")
    print(f"put  : {noeuds_exerces(reference, False)} noeuds")

    figure(mesures_taux, mesures_div)

"""
Convergence des deux arbres vers Black-Scholes, et le "tunnel".
Produit la figure de la section "convergence" du rapport.

    python analysis/convergence.py
"""

from datetime import datetime

import matplotlib.pyplot as plt

from lattice.api import price
from lattice.black_scholes import bs_price
from lattice.market import Market
from lattice.option import OptionTrade
from lattice.precision import error_constant

T0 = datetime(2026, 1, 1)
MAT = datetime(2027, 1, 1)
ANNEES = 1.0

# le cas de reference du projet : a la monnaie, un an, taux nul
MARKET = Market(100.0, 0.0, 0.30)
CALL = OptionTrade(100.0, MAT)

PAS = list(range(10, 201, 5))


def mesures():
    """Prix des deux arbres pour chaque nombre de pas."""
    exact = bs_price(MARKET.s0, CALL.strike, ANNEES, MARKET.rate, MARKET.vol, True)
    prix = {}
    for sorte in ("trinomial", "binomial"):
        prix[sorte] = [price(MARKET, CALL, T0, n, kind=sorte, prune=True) for n in PAS]
    return exact, prix


def tableau(exact, prix):
    """Le tableau que l'on recopie dans le rapport."""
    print(f"=== CONVERGENCE (Black-Scholes = {exact:.6f}) ===")
    print(f"{'N':>5} | {'trinomial':>12} {'ecart x N':>10} | "
          f"{'binomial':>12} {'ecart x N':>10}")
    for i, n in enumerate(PAS):
        tri, bino = prix["trinomial"][i], prix["binomial"][i]
        if n % 25 == 0 or n in (10, 15):
            print(f"{n:5d} | {tri:12.6f} {(tri - exact) * n:+10.3f} | "
                  f"{bino:12.6f} {(bino - exact) * n:+10.3f}")

    # la constante annoncee par le cours, a comparer au palier du tunnel
    for sorte in ("trinomial", "binomial"):
        print(f"constante du cours C ({sorte:>10}) = "
              f"{error_constant(MARKET, ANNEES, sorte):+.3f} EUR")


def figure(exact, prix):
    """A gauche le prix, a droite l'ecart multiplie par N : le tunnel."""
    fig, (gauche, droite) = plt.subplots(1, 2, figsize=(11, 4))

    gauche.axhline(exact, color="black", linestyle="--", linewidth=1,
                   label=f"Black-Scholes = {exact:.4f}")
    droite.axhline(0.0, color="black", linewidth=0.8)

    for sorte in ("trinomial", "binomial"):
        gauche.plot(PAS, prix[sorte], "o-", markersize=3, label=sorte)
        droite.plot(PAS, [(p - exact) * n for p, n in zip(prix[sorte], PAS)],
                    "o-", markersize=3, label=sorte)

    gauche.set_xlabel("nombre de pas")
    gauche.set_ylabel("prix du call (EUR)")
    gauche.set_title("Prix de l'arbre contre Black-Scholes")

    droite.set_xlabel("nombre de pas")
    droite.set_ylabel("(arbre - Black-Scholes) x N")
    droite.set_title("Le tunnel : l'erreur est en 1/N")

    for axe in (gauche, droite):
        axe.legend()
        axe.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("results/convergence.png", dpi=140)
    print()
    print("figure ecrite dans results/convergence.png")


if __name__ == "__main__":
    reference, prix_mesures = mesures()
    tableau(reference, prix_mesures)
    figure(reference, prix_mesures)

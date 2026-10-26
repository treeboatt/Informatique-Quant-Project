import math

# coefficient du triangle rabote au strike : 3/8 pour le trinomial, 1/2 pour le
# binomial. les casiers du trinomial sont plus serres, donc il se trompe moins
COEFFICIENT = {"trinomial": 3.0 / 8.0, "binomial": 0.5}


def error_constant(market, maturity, kind="trinomial"):
    """
    Le C de "erreur = C / nb_steps", d'apres le cours.
    maturity est en annees.
    """
    if kind not in COEFFICIENT:
        raise ValueError(f"unknown kind: {kind}")

    # le S0 e^(rT) de Sigma se simplifie avec celui du carre de l'ecartement,
    # il n'en reste donc qu'un seul au numerateur
    vol, rate = market.vol, market.rate
    spread = math.sqrt(math.exp(vol * vol * maturity) - 1.0)
    return COEFFICIENT[kind] * market.s0 * math.exp(rate * maturity) * vol * vol * maturity \
        / (math.sqrt(2.0 * math.pi) * spread)


def expected_gap(market, maturity, nb_steps, kind="trinomial"):
    """Ecart attendu entre l'arbre et Black-Scholes, en euros."""
    return error_constant(market, maturity, kind) / nb_steps


def steps_for_precision(market, maturity, gap, kind="trinomial"):
    """Nombre de pas a demander pour viser un ecart donne, en euros."""
    if gap <= 0.0:
        raise ValueError("la precision visee doit etre strictement positive")
    return math.ceil(error_constant(market, maturity, kind) / gap)

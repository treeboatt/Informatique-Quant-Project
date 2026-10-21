import datetime
import time

import matplotlib.pyplot as plt
import streamlit as st

from lattice.api import price
from lattice.black_scholes import bs_price
from lattice.greeks import OneDimDerivative
from lattice.market import Market, year_fraction
from lattice.option import OptionTrade
from lattice.plot_tree import plot_tree
from lattice.precision import expected_gap, steps_for_precision
from lattice.pricer import Pricer
from lattice.tree import BinomialTree, Tree

# les couleurs de l'application, au meme endroit pour ne pas les repeter partout
FOND = "#0F1318"
ENCRE = "#E8EDF5"
VERT = "#00E5A0"
GRIS = "#1E2530"
ROUGE = "#FF4D6A"

st.set_page_config(page_title="Pricer d'options", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono&display=swap');

html, body, .stApp, [class*="st-"] { font-family: 'DM Mono', monospace; }

/* sauf les icones de streamlit, qui ont besoin de leur propre police */
[data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }

/* on n'utilise pas la barre laterale, autant cacher son bouton */
[data-testid="stSidebarCollapsedControl"] { display: none; }

.block-container { padding-top: 2.5rem; padding-bottom: 5rem; max-width: 1500px; }

/* le bandeau du haut */
.hero {
    border: 1px solid #1E2530;
    border-radius: 14px;
    padding: 30px 34px;
    margin-bottom: 2.2rem;
    background: radial-gradient(900px 320px at 0% 0%, rgba(0,229,160,0.13), transparent 62%),
                linear-gradient(180deg, #11161C 0%, #0F1318 100%);
}
.hero .badge {
    color: #00E5A0;
    font-size: 0.66rem;
    letter-spacing: 3px;
    border: 1px solid rgba(0,229,160,0.35);
    border-radius: 999px;
    padding: 5px 14px;
}
.hero h1 { font-size: 2.7rem; line-height: 1.12; margin: 20px 0 8px 0; }
.hero h1 .vert { color: #00E5A0; }
.hero p { color: #8A93A8; font-size: 0.82rem; margin: 0; letter-spacing: 0.5px; }

/* les titres de section : la barre verte doit coller au texte, pas le deborder */
h2, h3 {
    border-left: 3px solid #00E5A0;
    padding: 0 0 0 14px !important;
    margin: 0 0 1.1rem 0 !important;
    line-height: 1.5;
    text-transform: uppercase;
    font-size: 0.95rem;
    letter-spacing: 1.5px;
}

[data-testid="stMetricValue"] { color: #00E5A0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <span class="badge">TRINOMIAL &nbsp;·&nbsp; BINOMIAL &nbsp;·&nbsp; BLACK-SCHOLES</span>
  <h1>Pricing d'options <span class="vert">par arbre</span></h1>
  <p>Projet Informatique financiere &mdash; M2 272 Dauphine</p>
</div>
""", unsafe_allow_html=True)


# ============================================================== les parametres

bloc_marche, bloc_option, bloc_modele = st.columns(3, gap="medium")

with bloc_marche, st.container(border=True):
    st.subheader("Marche")
    s0 = st.number_input("Prix de l'action", value=100.0, step=1.0)
    vol = st.number_input("Volatilite", value=0.30, step=0.01, format="%.4f")
    rate = st.number_input("Taux sans risque", value=0.03, step=0.01, format="%.4f")
    dividend = st.number_input("Dividende discret (EUR)", value=0.0, step=1.0)
    ex_day = st.date_input("Date de detachement", datetime.date(2027, 4, 21))

with bloc_option, st.container(border=True):
    st.subheader("Option")
    strike = st.number_input("Strike", value=100.0, step=1.0)
    is_call = st.radio("Type", ["Call", "Put"], horizontal=True) == "Call"
    is_american = st.radio("Exercice", ["Europeenne", "Americaine"],
                           horizontal=True) == "Americaine"
    pricing_day = st.date_input("Date de pricing", datetime.date(2026, 9, 1))
    maturity_day = st.date_input("Maturite", datetime.date(2027, 6, 28))

with bloc_modele, st.container(border=True):
    st.subheader("Modele")
    kind = st.selectbox("Type d'arbre", ["trinomial", "binomial"])
    nb_steps = st.slider("Nombre de pas", 10, 500, 100)
    nb_dessine = st.slider("Pas a dessiner", 3, 25, 8)
    pruning = st.checkbox("Pruning", value=True)
    greeks_wanted = st.checkbox("Calculer les grecques", value=True)


# ============================================================== mise en forme

# streamlit renvoie des dates, le projet travaille avec des datetime
pricing_date = datetime.datetime.combine(pricing_day, datetime.time())
maturity = datetime.datetime.combine(maturity_day, datetime.time())
ex_date = datetime.datetime.combine(ex_day, datetime.time()) if dividend > 0 else None

if maturity <= pricing_date:
    st.error("La maturite doit etre apres la date de pricing.")
    st.stop()

market = Market(s0, rate, vol, dividend, ex_date)
option = OptionTrade(strike, maturity, is_call, is_american)
years = year_fraction(pricing_date, maturity)
classe_arbre = BinomialTree if kind == "binomial" else Tree

# Black-Scholes n'est une reference valable que pour une europeenne sans dividende
comparable = (not is_american) and dividend == 0.0


# ============================================================== outils

def prix_arbre(nb=None, quand=None, marche=None, opt=None):
    """Un seul endroit ou on appelle le pricer, ca evite les oublis."""
    return price(marche or market, opt or option, quand or pricing_date,
                 nb or nb_steps, kind=kind, prune=pruning)


def graphe(x, courbes, ylabel):
    """Un petit graphe sombre. Matplotlib cale l'axe sur les valeurs, ce que
    st.line_chart ne fait pas : il part de zero et ecrase les deux courbes."""
    fig, ax = plt.subplots(figsize=(6, 3.4))
    fig.patch.set_facecolor(FOND)
    ax.set_facecolor(FOND)
    ax.tick_params(colors=ENCRE, labelsize=8)
    for cote in ax.spines.values():
        cote.set_color(GRIS)

    for nom, (valeurs, couleur) in courbes.items():
        ax.plot(x, valeurs, color=couleur, linewidth=1.6, label=nom)

    ax.set_xlabel("nombre de pas", color=ENCRE, fontsize=9)
    ax.set_ylabel(ylabel, color=ENCRE, fontsize=9)
    ax.grid(color=GRIS, linewidth=0.5)
    legende = ax.legend(fontsize=8, facecolor=FOND, edgecolor=GRIS)
    for texte in legende.get_texts():
        texte.set_color(ENCRE)
    fig.tight_layout()
    return fig


# ============================================================== le pricing

depart = time.perf_counter()
tree_price = prix_arbre()
temps_arbre = time.perf_counter() - depart

black_price = bs_price(s0, strike, years, rate, vol, is_call) if comparable else None


# ============================================================== les grecques

# les fonctions a deriver. elles ont toutes la signature f(param, x) attendue
# par OneDimDerivative : on gele tout sauf la variable qu'on fait bouger

def arbre_par_spot(param, s):
    return prix_arbre(marche=Market(s, rate, vol, dividend, ex_date))


def arbre_par_vol(param, v):
    return prix_arbre(marche=Market(s0, rate, v, dividend, ex_date))


def arbre_par_taux(param, r):
    return prix_arbre(marche=Market(s0, r, vol, dividend, ex_date))


def black_par_spot(param, s):
    return bs_price(s, strike, years, rate, vol, is_call)


def black_par_vol(param, v):
    return bs_price(s0, strike, years, rate, v, is_call)


def black_par_taux(param, r):
    return bs_price(s0, strike, years, r, vol, is_call)


def grecques(par_spot, par_vol, par_taux, theta, decalage):
    """Delta, gamma, vega et rho avec la meme machine a deriver."""
    return {
        "Delta": OneDimDerivative(par_spot, None, shift=decalage).first(s0),
        "Gamma": OneDimDerivative(par_spot, None, shift=decalage).second(s0),
        # on ramene le vega et le rho a une variation de 1 %
        "Vega (+1% vol)": OneDimDerivative(par_vol, None, shift=0.01).first(vol) / 100.0,
        "Rho (+1% taux)": OneDimDerivative(par_taux, None, shift=0.01).first(rate) / 100.0,
        "Theta (par jour)": theta,
    }


# le decalage doit depasser l'ecart entre deux noeuds voisins, sinon les trois
# prix tombent dans le meme casier et le gamma de l'arbre vaut exactement zero
ecart_noeuds = s0 * (classe_arbre(market, pricing_date, maturity, nb_steps).alpha - 1.0)
decalage = max(1.0, ecart_noeuds)

resultats = {}
if greeks_wanted:
    with st.spinner("Calcul des grecques..."):
        # theta : on avance la date de pricing d'un jour et on regarde ce qu'on perd
        demain = pricing_date + datetime.timedelta(days=1)
        theta_arbre = prix_arbre(quand=demain) - tree_price

        for nom, valeur in grecques(arbre_par_spot, arbre_par_vol, arbre_par_taux,
                                    theta_arbre, decalage).items():
            resultats.setdefault(nom, {})["Arbre"] = valeur

        if comparable:
            theta_black = bs_price(s0, strike, years - 1 / 365.0, rate, vol, is_call) - black_price
            # Black-Scholes est une courbe lisse : un petit decalage y est plus
            # precis, contrairement a l'arbre qui a besoin de sortir du casier
            for nom, valeur in grecques(black_par_spot, black_par_vol, black_par_taux,
                                        theta_black, 0.5).items():
                resultats.setdefault(nom, {})["Black-Scholes"] = valeur


# ============================================================== le prix

st.subheader("Prix")

cases = st.columns(4, gap="medium")
cases[0].metric("Arbre", f"{tree_price:.4f}")
cases[1].metric("Black-Scholes", f"{black_price:.4f}" if comparable else "-")
cases[2].metric("Ecart", f"{tree_price - black_price:+.4f}" if comparable else "-")
cases[3].metric("Temps de calcul", f"{temps_arbre * 1000:.0f} ms")

st.caption(
    f"{'Call' if is_call else 'Put'} {'americain' if is_american else 'europeen'} "
    f"@ {strike:.0f}, {nb_steps} pas, arbre {kind}, pruning "
    f"{'actif' if pruning else 'inactif'} "
    f"(r={rate:.2%}, vol={vol:.2%}, div={dividend:.2f} EUR, T={years:.4f} an)"
)

if not comparable:
    st.info("Pas de formule fermee pour une americaine ou avec dividende : l'arbre est seul.")

if is_american:
    europeenne = OptionTrade(strike, maturity, is_call, False)
    st.success(f"Prime d'exercice anticipe : {tree_price - prix_arbre(opt=europeenne):+.6f} EUR")

st.write("")


# ============================================================== grecques et erreur

gauche, droite = st.columns([3, 2], gap="large")

with gauche:
    st.subheader("Grecques")
    if greeks_wanted:
        lignes = ["Delta", "Gamma", "Vega (+1% vol)", "Rho (+1% taux)", "Theta (par jour)"]
        tableau = {"": lignes, "Arbre": [resultats[n]["Arbre"] for n in lignes]}
        if comparable:
            tableau["Black-Scholes"] = [resultats[n]["Black-Scholes"] for n in lignes]
            tableau["Ecart"] = [resultats[n]["Arbre"] - resultats[n]["Black-Scholes"]
                                for n in lignes]
        st.dataframe(tableau, use_container_width=True, hide_index=True)
        st.caption(f"Decalage de {decalage:.2f} EUR pour l'arbre, soit l'ecart entre deux "
                   f"noeuds voisins : en dessous, les trois prix tombent dans le meme "
                   f"casier et le gamma vaut exactement zero.")
    else:
        st.caption("Coche \"Calculer les grecques\" dans le bloc Modele.")

with droite:
    st.subheader("Precision")
    if comparable:
        annonce = expected_gap(market, years, nb_steps, kind)
        st.metric("Erreur annoncee par le cours", f"{annonce:.6f} EUR")
        st.caption(f"Pour viser 1 centime il faudrait "
                   f"{steps_for_precision(market, years, 0.01, kind)} pas.")
    else:
        st.caption("La formule du cours se compare a Black-Scholes : "
                   "europeenne et sans dividende.")

st.write("")


# ============================================================== le dessin

st.subheader("L'arbre")

petit = classe_arbre(market, pricing_date, maturity, nb_dessine, prune=pruning)
petit.build_tree()
# on price le petit arbre pour que chaque noeud connaisse sa valeur : c'est ce
# qui permet de savoir ou l'exercice anticipe a lieu
Pricer(petit, option).price_backward()

st.pyplot(plot_tree(petit, f"Arbre {kind} - {nb_dessine} pas", dark=True, option=option))

if is_american:
    st.caption("En rouge, les noeuds ou il vaut mieux exercer tout de suite ; en vert, "
               "ceux ou il vaut mieux garder l'option. La separation entre les deux, "
               "c'est la frontiere d'exercice.")
else:
    st.caption("La taille d'un noeud suit sa probabilite d'etre atteint. Dans le binomial, "
               "un noeud sur deux n'est jamais atteint car p_mid vaut 0. Avec le pruning, "
               "les noeuds trop improbables ne sont plus crees du tout.")

st.write("")


# ============================================================== la convergence

st.subheader("Convergence")

if comparable:
    pas = list(range(10, nb_steps + 1, max(1, nb_steps // 25)))
    prix = [prix_arbre(nb=n) for n in pas]

    courbe, ecart = st.columns(2, gap="large")
    with courbe:
        st.pyplot(graphe(pas, {"arbre": (prix, VERT),
                               "Black-Scholes": ([black_price] * len(pas), ROUGE)},
                         "prix de l'option"))
        st.caption("Le prix de l'arbre se rapproche de Black-Scholes quand on ajoute des pas.")
    with ecart:
        st.pyplot(graphe(pas, {"ecart x N": ([(p - black_price) * n
                                              for p, n in zip(prix, pas)], VERT)},
                         "ecart x nombre de pas"))
        st.caption("Cette courbe se stabilise : c'est la convergence en 1/N. "
                   "En binomial elle oscille selon la parite du nombre de pas.")
else:
    st.caption("La convergence se compare a Black-Scholes : europeenne et sans dividende.")

import datetime
import time

import pandas as pd
import streamlit as st

from lattice.api import price
from lattice.black_scholes import bs_price
from lattice.greeks import OneDimDerivative
from lattice.market import Market, year_fraction
from lattice.option import OptionTrade
from lattice.plot_tree import plot_tree
from lattice.precision import expected_gap, steps_for_precision
from lattice.tree import BinomialTree, Tree

st.set_page_config(page_title="Pricer d'options", layout="wide")

# police monospace partout (les chiffres s'alignent) et une barre verte
# devant chaque titre de section
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono&display=swap');

html, body, .stApp, [class*="st-"] { font-family: 'DM Mono', monospace; }

/* sauf les icones de streamlit, qui ont besoin de leur propre police */
[data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }

h2, h3 {
    border-left: 3px solid #00E5A0;
    padding-left: 12px;
    text-transform: uppercase;
    font-size: 1.1rem;
}
</style>
""", unsafe_allow_html=True)

st.title("Pricing d'options par arbre")
st.caption("Projet Informatique financiere - M2 272 Dauphine")


# ============================================================== la barre de gauche

st.sidebar.header("Marche")
s0 = st.sidebar.number_input("Prix de l'action", value=100.0, step=1.0)
vol = st.sidebar.number_input("Volatilite", value=0.30, step=0.01, format="%.4f")
rate = st.sidebar.number_input("Taux sans risque", value=0.03, step=0.01, format="%.4f")
dividend = st.sidebar.number_input("Dividende discret (EUR)", value=0.0, step=1.0)
ex_day = st.sidebar.date_input("Date de detachement", datetime.date(2027, 4, 21))

st.sidebar.header("Option")
strike = st.sidebar.number_input("Strike", value=100.0, step=1.0)
is_call = st.sidebar.radio("Type", ["Call", "Put"], horizontal=True) == "Call"
is_american = st.sidebar.radio("Exercice", ["Europeenne", "Americaine"]) == "Americaine"
pricing_day = st.sidebar.date_input("Date de pricing", datetime.date(2026, 9, 1))
maturity_day = st.sidebar.date_input("Maturite", datetime.date(2027, 6, 28))

st.sidebar.header("Modele")
kind = st.sidebar.selectbox("Type d'arbre", ["trinomial", "binomial"])
nb_steps = st.sidebar.slider("Nombre de pas", 10, 500, 100)
pruning = st.sidebar.checkbox("Pruning", value=True)
greeks_wanted = st.sidebar.checkbox("Calculer les grecques", value=True)


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

st.caption(
    f"{'Call' if is_call else 'Put'} {'americain' if is_american else 'europeen'} "
    f"@ {strike:.0f} avec {nb_steps} pas "
    f"(r={rate:.2%}, vol={vol:.2%}, div={dividend:.2f} EUR, T={years:.4f} an)"
)


# ============================================================== le pricing

def prix_arbre(nb=None, quand=None, marche=None, opt=None):
    """Un seul endroit ou on appelle le pricer, ca evite les oublis."""
    return price(marche or market, opt or option, quand or pricing_date,
                 nb or nb_steps, kind=kind, prune=pruning)


depart = time.perf_counter()
tree_price = prix_arbre()
temps_arbre = time.perf_counter() - depart

depart = time.perf_counter()
black_price = bs_price(s0, strike, years, rate, vol, is_call) if comparable else None
temps_black = time.perf_counter() - depart


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


resultats = {"Prix": {"Arbre": tree_price}}
if comparable:
    resultats["Prix"]["Black-Scholes"] = black_price

# le decalage doit depasser l'ecart entre deux noeuds voisins, sinon les trois
# prix tombent dans le meme casier et le gamma de l'arbre vaut exactement zero
ecart_noeuds = s0 * (classe_arbre(market, pricing_date, maturity, nb_steps).alpha - 1.0)
decalage = max(1.0, ecart_noeuds)

if greeks_wanted:
    with st.spinner("Calcul des grecques..."):
        # theta : on avance la date de pricing d'un jour et on regarde ce qu'on perd
        demain = pricing_date + datetime.timedelta(days=1)
        theta_arbre = prix_arbre(quand=demain) - tree_price

        valeurs_arbre = grecques(arbre_par_spot, arbre_par_vol, arbre_par_taux,
                                 theta_arbre, decalage)
        for nom, valeur in valeurs_arbre.items():
            resultats.setdefault(nom, {})["Arbre"] = valeur

        if comparable:
            theta_black = bs_price(s0, strike, years - 1 / 365.0, rate, vol, is_call) - black_price
            # Black-Scholes est une courbe lisse : un petit decalage y est plus
            # precis, contrairement a l'arbre qui a besoin de sortir du casier
            valeurs_black = grecques(black_par_spot, black_par_vol, black_par_taux,
                                     theta_black, 0.5)
            for nom, valeur in valeurs_black.items():
                resultats.setdefault(nom, {})["Black-Scholes"] = valeur


# ============================================================== affichage

st.subheader("Resultats")

colonnes = ["Black-Scholes", "Arbre"] if comparable else ["Arbre"]
tableau = pd.DataFrame(resultats).T.reindex(columns=colonnes)
if comparable:
    tableau["Ecart"] = tableau["Arbre"] - tableau["Black-Scholes"]

gauche, droite = st.columns([5, 3])
gauche.dataframe(tableau.style.format("{:.6f}"), use_container_width=True)

with droite:
    st.metric("Temps de l'arbre", f"{temps_arbre * 1000:.0f} ms")
    if comparable:
        st.metric("Temps de Black-Scholes", f"{temps_black * 1000:.3f} ms")
        annonce = expected_gap(market, years, nb_steps, kind)
        st.metric("Erreur annoncee par le cours", f"{annonce:.6f} EUR")
        st.caption(
            f"Pour viser 1 centime il faudrait "
            f"{steps_for_precision(market, years, 0.01, kind)} pas."
        )
    else:
        st.info("Pas de formule fermee pour une americaine ou avec dividende : "
                "l'arbre est seul.")

if is_american:
    europeenne = OptionTrade(strike, maturity, is_call, False)
    prime = tree_price - prix_arbre(opt=europeenne)
    st.success(f"Prime d'exercice anticipe : {prime:+.6f} EUR")

if greeks_wanted:
    st.caption(f"Grecques de l'arbre calculees par decalage de {decalage:.2f} EUR, soit "
               f"l'ecart entre deux noeuds voisins. En dessous, les trois prix tombent dans "
               f"le meme casier et le gamma vaut exactement zero. Black-Scholes etant lisse, "
               f"il utilise un decalage de 0,50 EUR.")


# ============================================================== le dessin

st.subheader("L'arbre")
st.caption("Un arbre a plusieurs centaines de pas est illisible, on en redessine un petit "
           "avec exactement le meme marche.")

nb_dessine = st.slider("Pas a dessiner", 3, 25, 8)
petit = classe_arbre(market, pricing_date, maturity, nb_dessine, prune=pruning)
petit.build_tree()
st.pyplot(plot_tree(petit, f"Arbre {kind} - {nb_dessine} pas", dark=True))
st.caption("La taille d'un noeud suit sa probabilite d'etre atteint. Dans le binomial, "
           "un noeud sur deux n'est jamais atteint car p_mid vaut 0. Avec le pruning, "
           "les noeuds trop improbables ne sont plus crees du tout.")


# ============================================================== la convergence

st.subheader("Convergence")

if comparable:
    pas = list(range(10, nb_steps + 1, max(1, nb_steps // 20)))
    prix = [prix_arbre(nb=n) for n in pas]

    st.line_chart(pd.DataFrame({"arbre": prix, "Black-Scholes": black_price}, index=pas))

    ecarts = [(p - black_price) * n for p, n in zip(prix, pas)]
    st.caption("Ecart x nombre de pas : il doit se stabiliser, c'est la convergence en 1/N. "
               "Avec le binomial il oscille selon la parite du nombre de pas.")
    st.line_chart(pd.DataFrame({"ecart x N": ecarts}, index=pas))
else:
    st.caption("La convergence se compare a Black-Scholes : europeenne et sans dividende.")

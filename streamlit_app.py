import datetime
import random
import time
import tracemalloc

import matplotlib.pyplot as plt
import streamlit as st

from lattice.api import price
from lattice.black_scholes import bs_price
from lattice.greeks import OneDimDerivative, TwoDimDerivative
from lattice.market import Market, year_fraction
from lattice.option import OptionTrade
from lattice.plot_tree import plot_tree
from lattice.precision import expected_gap, steps_for_precision
from lattice.pricer import Pricer, column
from lattice.tree import BinomialTree, Tree

# les couleurs de l'application, au meme endroit pour ne pas les repeter partout
FOND = "#0F1318"
ENCRE = "#E8EDF5"
VERT = "#00E5A0"
GRIS = "#1E2530"
ROUGE = "#FF4D6A"
BLEU = "#6C8FFF"

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
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    gap: 28px;
    border: 1px solid #1E2530;
    border-radius: 14px;
    padding: 30px 34px;
    margin-bottom: 2.2rem;
    background: #090C10;
}

/* le graphique en bougies, en fond */
.hero .bougies {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
}

/* un voile sombre de gauche a droite, pour que le texte reste lisible
   par dessus les bougies */
.hero::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, #090C10 0%, #090C10 40%,
                                rgba(9,12,16,0.82) 56%, rgba(9,12,16,0.30) 80%,
                                rgba(9,12,16,0.10) 100%);
    pointer-events: none;
}

/* un filet d'accent en haut, qui s'eteint vers la droite */
.hero::after {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #00E5A0 0%, rgba(0,229,160,0.25) 38%, transparent 72%);
    pointer-events: none;
}

.hero > div { position: relative; z-index: 2; }
.hero > svg:not(.bougies) { position: relative; z-index: 2; }
.hero .equipe {
    color: #00E5A0;
    font-size: 0.64rem;
    letter-spacing: 4px;
    display: block;
    margin-bottom: 6px;
}
.hero h1 {
    font-size: 2.3rem;
    line-height: 1.1;
    margin: 0 0 8px 0;
    letter-spacing: -1px;
}
.hero h1 .vert { color: #00E5A0; }
.hero .qui {
    display: block;
    color: #E8EDF5;
    font-size: 0.78rem;
    letter-spacing: 0.5px;
}
.hero .quoi {
    display: block;
    color: #8A93A8;
    font-size: 0.68rem;
    letter-spacing: 2px;
    margin-top: 5px;
}

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

def fond_bougies(largeur=1200, hauteur=250, nb=42):
    """
    Un petit graphique en bougies dessine en SVG, pour le fond du bandeau.
    La graine est fixee, donc le dessin est toujours le meme.
    """
    random.seed(5)
    pas = largeur / nb
    cours = hauteur * 0.92          # on part en bas pour avoir une vraie montee
    dessin = []

    # la grille de fond
    for i in range(1, 9):
        y = hauteur * i / 9
        dessin.append(f'<line x1="0" y1="{y:.0f}" x2="{largeur}" y2="{y:.0f}" '
                      f'stroke="#E8EDF5" stroke-width="0.5" opacity="0.05"/>')
    for i in range(1, 13):
        x = largeur * i / 13
        dessin.append(f'<line x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="{hauteur}" '
                      f'stroke="#E8EDF5" stroke-width="0.5" opacity="0.05"/>')

    for i in range(nb):
        ouverture = cours
        # en SVG l'axe y descend, donc monter veut dire retirer des pixels.
        # la hausse s'accelere vers la droite : a gauche les bougies restent
        # basses et ne genent pas le titre
        cours -= random.uniform(-2.0, 2.0 + 15.0 * (i / nb))
        x = i * pas + pas / 2
        monte = cours < ouverture
        couleur = "#00E5A0" if monte else "#FF4D6A"
        # les bougies s'eclaircissent vers la droite, la ou est le prix
        opacite = 0.14 + 0.70 * (i / nb)
        haut = min(ouverture, cours) - random.uniform(3, 11)
        bas = max(ouverture, cours) + random.uniform(3, 11)
        corps = max(abs(cours - ouverture), 3.5)

        dessin.append(f'<line x1="{x:.1f}" y1="{haut:.1f}" x2="{x:.1f}" y2="{bas:.1f}" '
                      f'stroke="{couleur}" stroke-width="1.1" opacity="{opacite:.2f}"/>')
        dessin.append(f'<rect x="{x - pas * 0.3:.1f}" y="{min(ouverture, cours):.1f}" '
                      f'width="{pas * 0.6:.1f}" height="{corps:.1f}" rx="1" '
                      f'fill="{couleur}" opacity="{opacite:.2f}"/>')

    # la derniere bougie brille, c'est le point d'arrivee
    dessin.append(f'<circle cx="{largeur - pas / 2:.1f}" cy="{cours:.1f}" r="16" '
                  f'fill="#00E5A0" opacity="0.18" filter="url(#flou)"/>')
    dessin.append(f'<circle cx="{largeur - pas / 2:.1f}" cy="{cours:.1f}" r="3.5" '
                  f'fill="#E8EDF5"/>')

    return (f'<svg class="bougies" viewBox="0 0 {largeur} {hauteur}" '
            f'preserveAspectRatio="none">'
            f'<defs><filter id="flou"><feGaussianBlur stdDeviation="7"/></filter></defs>'
            f'{"".join(dessin)}</svg>')


# le logo : un petit arbre trinomial dessine en SVG, trois branches par noeud
LOGO = """
<svg width="66" height="66" viewBox="0 0 48 48" fill="none">
  <path d="M7 24 L23 11 M7 24 L23 24 M7 24 L23 37" stroke="#00E5A0"
        stroke-width="1.4" opacity="0.55"/>
  <path d="M23 11 L41 6 M23 11 L41 15 M23 24 L41 15 M23 24 L41 24
           M23 24 L41 33 M23 37 L41 33 M23 37 L41 42" stroke="#00E5A0"
        stroke-width="1" opacity="0.28"/>
  <circle cx="7" cy="24" r="4.2" fill="#00E5A0"/>
  <circle cx="23" cy="11" r="2.4" fill="#00E5A0" opacity="0.85"/>
  <circle cx="23" cy="24" r="3.2" fill="#00E5A0"/>
  <circle cx="23" cy="37" r="2.4" fill="#00E5A0" opacity="0.85"/>
  <circle cx="41" cy="6" r="1.5" fill="#00E5A0" opacity="0.5"/>
  <circle cx="41" cy="15" r="2" fill="#00E5A0" opacity="0.65"/>
  <circle cx="41" cy="24" r="2.4" fill="#00E5A0" opacity="0.75"/>
  <circle cx="41" cy="33" r="2" fill="#00E5A0" opacity="0.65"/>
  <circle cx="41" cy="42" r="1.5" fill="#00E5A0" opacity="0.5"/>
</svg>
"""

st.markdown(f"""
<div class="hero">
  {fond_bougies()}
  {LOGO}
  <div>
    <span class="equipe">TRINOME</span>
    <h1>Lattice <span class="vert">Pricer</span></h1>
    <span class="qui">Maxime Gruez &nbsp;·&nbsp; Guillaume Turlan</span>
    <span class="quoi">M2 272 DAUPHINE &nbsp;·&nbsp; INFORMATIQUE FINANCIERE</span>
  </div>
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
    jusqu_a = st.slider("Convergence jusqu'a N", 40, 200, 120)
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


@st.cache_data(show_spinner="Calcul de la convergence...")
def etude_tunnel(s0, rate, vol, strike, is_call, pricing_date, maturity, jusqu_a):
    """
    Ecart x N pour les deux arbres, a chaque N entier. Il faut tous les N :
    avec un pas de 2 on raterait l'oscillation du binomial, qui depend de la
    parite. Ca fait quelques centaines de prix, d'ou la mise en cache.
    """
    marche = Market(s0, rate, vol)
    opt = OptionTrade(strike, maturity, is_call, False)
    reference = bs_price(s0, strike, year_fraction(pricing_date, maturity), rate, vol, is_call)

    n_pas = list(range(10, jusqu_a + 1))
    ecarts = {}
    for sorte in ("trinomial", "binomial"):
        ecarts[sorte] = [(price(marche, opt, pricing_date, n, kind=sorte, prune=True)
                          - reference) * n for n in n_pas]
    return n_pas, ecarts


def graphe(x, courbes, ylabel, zero=False):
    """Un petit graphe sombre. Matplotlib cale l'axe sur les valeurs, ce que
    st.line_chart ne fait pas : il part de zero et ecrase les deux courbes."""
    fig, ax = plt.subplots(figsize=(6, 3.4))
    fig.patch.set_facecolor(FOND)
    ax.set_facecolor(FOND)
    ax.tick_params(colors=ENCRE, labelsize=8)
    for cote in ax.spines.values():
        cote.set_color(GRIS)

    if zero:
        ax.axhline(0, color=ENCRE, linewidth=0.8, alpha=0.4)

    for nom, (valeurs, couleur) in courbes.items():
        ax.plot(x, valeurs, color=couleur, linewidth=1.3, label=nom)

    ax.set_xlabel("nombre de pas", color=ENCRE, fontsize=9)
    ax.set_ylabel(ylabel, color=ENCRE, fontsize=9)
    ax.grid(color=GRIS, linewidth=0.5)
    legende = ax.legend(fontsize=8, facecolor=FOND, edgecolor=GRIS)
    for texte in legende.get_texts():
        texte.set_color(ENCRE)
    fig.tight_layout()
    return fig


# ============================================================== le pricing

def mesure_arbre():
    """
    Construit et price l'arbre deux fois : une fois chronometre, une fois sous
    tracemalloc. On ne peut pas faire les deux d'un coup, tracemalloc multiplie
    le temps par 3 a 4 et le chrono ne voudrait plus rien dire.
    """
    depart = time.perf_counter()
    arbre = classe_arbre(market, pricing_date, maturity, nb_steps, prune=pruning)
    arbre.build_tree()
    prix = Pricer(arbre, option).price_backward()
    duree = time.perf_counter() - depart

    tracemalloc.start()
    bis = classe_arbre(market, pricing_date, maturity, nb_steps, prune=pruning)
    bis.build_tree()
    Pricer(bis, option).price_backward()
    memoire = tracemalloc.get_traced_memory()[1] / (1024 * 1024)
    tracemalloc.stop()

    # on compte les noeuds en marchant sur les pointeurs, sans liste
    noeuds = 0
    trunk = arbre.root
    while trunk is not None:
        noeuds += sum(1 for _ in column(trunk))
        trunk = trunk.next_mid

    return prix, duree, memoire, noeuds


tree_price, temps_arbre, memoire_arbre, nb_noeuds = mesure_arbre()

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


# le vanna croise deux variables, il lui faut une fonction a deux arguments
def arbre_par_spot_et_vol(param, s, v):
    return prix_arbre(marche=Market(s, rate, v, dividend, ex_date))


def black_par_spot_et_vol(param, s, v):
    return bs_price(s, strike, years, rate, v, is_call)


def grecques(par_spot, par_vol, par_taux, par_spot_vol, theta, decalage):
    """Toutes les grecques avec la meme machine a deriver."""
    return {
        "Delta": OneDimDerivative(par_spot, None, shift=decalage).first(s0),
        "Gamma": OneDimDerivative(par_spot, None, shift=decalage).second(s0),
        # on ramene le vega et le rho a une variation de 1 %
        "Vega (+1% vol)": OneDimDerivative(par_vol, None, shift=0.01).first(vol) / 100.0,
        "Rho (+1% taux)": OneDimDerivative(par_taux, None, shift=0.01).first(rate) / 100.0,
        "Theta (par jour)": theta,
        # vanna = d(delta)/d(vol) : meme decalage que le gamma sur le spot
        "Vanna (+1% vol)": TwoDimDerivative(par_spot_vol, None, shift_x=decalage,
                                            shift_y=0.01).cross(s0, vol) / 100.0,
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
                                    arbre_par_spot_et_vol,
                                    theta_arbre, decalage).items():
            resultats.setdefault(nom, {})["Arbre"] = valeur

        if comparable:
            theta_black = bs_price(s0, strike, years - 1 / 365.0, rate, vol, is_call) - black_price
            # Black-Scholes est une courbe lisse : un petit decalage y est plus
            # precis, contrairement a l'arbre qui a besoin de sortir du casier
            for nom, valeur in grecques(black_par_spot, black_par_vol, black_par_taux,
                                        black_par_spot_et_vol,
                                        theta_black, 0.5).items():
                resultats.setdefault(nom, {})["Black-Scholes"] = valeur


# ============================================================== le prix

st.subheader("Prix")

cases = st.columns(3, gap="medium")
cases[0].metric("Arbre", f"{tree_price:.4f}")
cases[1].metric("Black-Scholes", f"{black_price:.4f}" if comparable else "-")
cases[2].metric("Ecart", f"{tree_price - black_price:+.4f}" if comparable else "-")

couts = st.columns(3, gap="medium")
couts[0].metric("Temps de calcul", f"{temps_arbre * 1000:.0f} ms")
couts[1].metric("Memoire", f"{memoire_arbre:.1f} Mo")
couts[2].metric("Noeuds construits", f"{nb_noeuds:,}".replace(",", " "))

st.caption(
    f"{'Call' if is_call else 'Put'} {'americain' if is_american else 'europeen'} "
    f"@ {strike:.0f}, {nb_steps} pas, arbre {kind}, pruning "
    f"{'actif' if pruning else 'inactif'} "
    f"(r={rate:.2%}, vol={vol:.2%}, div={dividend:.2f} EUR, T={years:.4f} an). "
    f"Le temps et la memoire sont mesures sur deux constructions separees : "
    f"tracemalloc ralentit d'un facteur 3 a 4, le chrono serait fausse."
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
        lignes = ["Delta", "Gamma", "Vega (+1% vol)", "Rho (+1% taux)",
                  "Theta (par jour)", "Vanna (+1% vol)"]
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
    st.caption("En rouge, les noeuds ou il vaut mieux exercer par anticipation ; en vert, "
               "ceux ou il vaut mieux garder. La separation entre les deux, c'est la "
               "frontiere d'exercice. La derniere colonne n'est pas coloriee : a maturite "
               "on exerce forcement si on est dans la monnaie. Aucun noeud rouge veut dire "
               "qu'il ne faut jamais exercer avant l'echeance, ce qui est le cas d'un call "
               "sans dividende : la prime americaine vaut alors exactement zero.")
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

    courbe, tunnel = st.columns(2, gap="large")
    with courbe:
        st.pyplot(graphe(pas, {"arbre": (prix, VERT),
                               "Black-Scholes": ([black_price] * len(pas), ROUGE)},
                         "prix de l'option"))
        st.caption("Le prix de l'arbre se rapproche de Black-Scholes quand on ajoute des pas.")

    with tunnel:
        n_tunnel, ecarts = etude_tunnel(s0, rate, vol, strike, is_call,
                                        pricing_date, maturity, jusqu_a)
        st.pyplot(graphe(n_tunnel, {"trinomial": (ecarts["trinomial"], VERT),
                                    "binomial": (ecarts["binomial"], BLEU)},
                         "(arbre - Black) x N", zero=True))
        st.caption("Multiplier l'ecart par N le rend lisible : il reste borne, donc "
                   "l'erreur decroit bien en 1/N. Le trinomial se cale sur une valeur, "
                   "le binomial oscille entre deux selon la parite de N.")
else:
    st.caption("La convergence se compare a Black-Scholes : europeenne et sans dividende.")

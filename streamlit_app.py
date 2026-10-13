import datetime

import pandas as pd
import streamlit as st

from lattice.api import price
from lattice.black_scholes import bs_price
from lattice.market import Market, year_fraction
from lattice.option import OptionTrade

st.title("Pricing d'options par arbre")
st.caption("Projet Informatique financiere - M2 272 Dauphine")

# ---------------------------------------------------------------- parametres
st.sidebar.header("Marche")
s0 = st.sidebar.number_input("Prix de l'action", value=100.0, step=1.0)
rate = st.sidebar.number_input("Taux sans risque", value=0.05, step=0.01, format="%.3f")
vol = st.sidebar.number_input("Volatilite", value=0.20, step=0.01, format="%.3f")

st.sidebar.header("Option")
strike = st.sidebar.number_input("Strike", value=100.0, step=1.0)
is_call = st.sidebar.radio("Type", ["Call", "Put"]) == "Call"
is_american = st.sidebar.radio("Exercice", ["Europeenne", "Americaine"]) == "Americaine"

st.sidebar.header("Dates")
pricing_day = st.sidebar.date_input("Date de pricing", datetime.date(2026, 1, 1))
maturity_day = st.sidebar.date_input("Maturite", datetime.date(2027, 1, 1))

st.sidebar.header("Dividende")
dividend = st.sidebar.number_input("Montant", value=0.0, step=1.0)
ex_day = st.sidebar.date_input("Date de detachement", datetime.date(2026, 7, 1))

st.sidebar.header("Arbre")
kind = st.sidebar.selectbox("Type d'arbre", ["trinomial", "binomial"])
nb_steps = st.sidebar.slider("Nombre de pas", 5, 500, 100)

# streamlit renvoie des dates, le projet travaille avec des datetime
pricing_date = datetime.datetime.combine(pricing_day, datetime.time())
maturity = datetime.datetime.combine(maturity_day, datetime.time())
ex_date = datetime.datetime.combine(ex_day, datetime.time()) if dividend > 0 else None

if maturity <= pricing_date:
    st.error("La maturite doit etre apres la date de pricing.")
    st.stop()

market = Market(s0, rate, vol, dividend, ex_date)
option = OptionTrade(strike, maturity, is_call, is_american)

# ---------------------------------------------------------------- le prix
tree_price = price(market, option, pricing_date, nb_steps, kind=kind)
maturity_in_years = year_fraction(pricing_date, maturity)

# Black-Scholes n'est une reference valable que pour une europeenne sans dividende
comparable = (not is_american) and dividend == 0.0

left, middle, right = st.columns(3)
left.metric("Prix de l'arbre", f"{tree_price:.4f} EUR")
if comparable:
    reference = bs_price(s0, strike, maturity_in_years, rate, vol, is_call)
    middle.metric("Black-Scholes", f"{reference:.4f} EUR")
    right.metric("Ecart", f"{tree_price - reference:+.4f} EUR")
else:
    middle.metric("Black-Scholes", "-")
    right.caption("Pas de formule fermee pour une americaine ou avec dividende.")

# ---------------------------------------------------------------- americaine
if is_american:
    european = OptionTrade(strike, maturity, is_call, False)
    premium = tree_price - price(market, european, pricing_date, nb_steps, kind=kind)
    st.info(f"Prime d'exercice anticipe : {premium:.4f} EUR")

# ---------------------------------------------------------------- convergence
st.subheader("Convergence")

if comparable:
    reference = bs_price(s0, strike, maturity_in_years, rate, vol, is_call)
    steps = list(range(10, nb_steps + 1, max(1, nb_steps // 20)))
    prices = [price(market, option, pricing_date, n, kind=kind) for n in steps]

    st.line_chart(pd.DataFrame({"arbre": prices, "Black-Scholes": reference}, index=steps))

    gaps = [(p - reference) * n for p, n in zip(prices, steps)]
    st.caption("Ecart x nombre de pas : il doit se stabiliser, c'est la convergence en 1/N.")
    st.line_chart(pd.DataFrame({"ecart x N": gaps}, index=steps))
else:
    st.caption("La convergence se compare a Black-Scholes : europeenne et sans dividende.")

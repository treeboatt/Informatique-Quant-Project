# Contrat d'interface

Ce document fixe les noms des classes, des attributs et des méthodes que le projet
utilise. Il sert à ce que le moteur d'arbre (membre A) et le pricing (membre B)
s'emboîtent sans mauvaise surprise le jour de l'intégration.

Toute modification de ce document passe par une PR relue par l'autre membre.

## Règles générales

- **Aucun dict, aucune liste, aucun array pour accéder aux noeuds** (contrainte de
  l'énoncé). On circule uniquement par les pointeurs `up` / `down`, `next_up` /
  `next_mid` / `next_down` et `prec_mid`.
- Les dates sont des `datetime.datetime`, jamais des `datetime.date`.
- Une seule conversion dates -> années : `year_fraction(d1, d2)` dans `market.py`
  (jours / 365). `tree.py` l'importe, il ne la redéfinit pas.
- Taux et volatilité sont annualisés, en continu, en float.
- Point d'entrée unique du projet : `api.price(...)`.

## Classes et fonctions

| Qui | Classe / fonction | Attributs et méthodes | Fichier |
|---|---|---|---|
| B | `Market` (dataclass frozen) | `s0`, `rate`, `vol`, `dividend = 0.0`, `div_ex_date = None` | `market.py` |
| B | `year_fraction(d1, d2)`, `DAYS_PER_YEAR` | conversion dates -> années | `market.py` |
| B | `OptionTrade` (dataclass frozen) | `strike`, `maturity`, `is_call = True`, `is_american = False` ; `payoff(s)` | `option.py` |
| B | `bs_price`, `norm_cdf` | `bs_price(s0, strike, T, rate, vol, is_call = True)` | `black_scholes.py` |
| A | `Node` | `price`, `tree`, `up`, `down`, `next_up`, `next_mid`, `next_down`, `p_up`, `p_mid`, `p_down`, `proba_reach`, `option_value` ; `get_or_create_up()`, `get_or_create_down()`, `find_closest(target)`, `compute_probabilities(fwd, var)` | `node.py` |
| A | `TrunkNode(Node)` | en plus : `prec_mid`, `column_date`, `is_div_in_next_period` ; `next_date()`, `are_same_dates(d1, d2)` | `node.py` |
| A | `Tree` | `market`, `nb_steps`, `prune_threshold`, `dt`, `alpha`, `df`, `growth`, `var_factor`, `step_timedelta`, `root` ; `forward_and_variance(s, trunk)`, `build_tree()`, `build_next_column(trunk)` | `tree.py` |
| A | `BinomialTree(Tree)` | alpha et probabilités binomiales, deux successeurs | `tree.py` |
| B | `Pricer` | `tree`, `option` ; `price_backward()`, `price_recursive()` ; `column(trunk)` parcourt une colonne via `up` / `down` | `pricer.py` |
| B | `OneDimDerivative` | `(function, other_parameters, shift)` ; `first(x)`, `second(x)` | `greeks.py` |
| B | `price(...)` | `price(market, option, pricing_date, nb_steps, kind = "trinomial", method = "backward")` | `api.py` |
| A | `plot_tree` | dessin de l'arbre, valeurs de l'option, frontière d'exercice | `plot_tree.py` |
| B | application Streamlit | visuel final, aucune logique de pricing dedans | `streamlit_app.py` |

## Conventions qui ont un impact sur le code de l'autre

1. **`option_value` vaut `None` à la création du noeud, pas `0.0`.** Le pricer
   récursif mémorise les valeurs déjà calculées avec `if node.option_value is None`.
   Si le noeud naît à `0.0`, le pricer considère que tout est déjà calculé et
   renvoie 0 partout.
2. **`next_up` et `next_down` peuvent être `None`** (noeud élagué par le pruning).
   Le pricer teste avant d'additionner. Pour un noeud élagué, `p_mid = 1`.
3. `is_div_in_next_period` est calculé dans le constructeur de `TrunkNode`
   (phase 4, avec `are_same_dates`). Tant qu'il n'y a pas de dividende, il reste
   à `False`.
4. `find_closest(target)` commence par un garde-fou `assert target > 0` : avec un
   dividende, un forward négatif en bas de l'arbre ferait boucler la descente à
   l'infini.
5. `tree.df` est le facteur d'actualisation **d'un pas**, `exp(-r * dt)`. C'est
   celui qu'utilise le pricer.

## Qui écrit quoi

- **Membre A** : `node.py`, `tree.py`, `plot_tree.py`.
- **Membre B** : `market.py`, `option.py`, `black_scholes.py`, `pricer.py`,
  `greeks.py`, `api.py`, `streamlit_app.py`.
- Les tests d'un fichier sont écrits par celui qui écrit le fichier, sauf le test
  de l'arbre à 2 pas, fait à deux.

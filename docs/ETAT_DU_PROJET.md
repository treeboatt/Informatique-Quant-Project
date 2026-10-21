# État du projet — tableau de bord partagé

**Projet** : pricing d'options par arbre recombinant (binomial et trinomial), M2 272 Dauphine, cours d'informatique financière.
**Dépôt** : https://github.com/treeboatt/Informatique-Quant-Project
**Binôme** : Maxime Gruez (`treeboatt`) et Guillaume Turlan (`GuillaumeTurlan`).
**Dernière mise à jour** : 29/09/2026, à partir de `main = b461e4c`.

---

## 0. À quoi sert ce fichier

On travaille chacun de notre côté, chacun avec un assistant. Ce fichier est le **point de synchronisation unique** : il dit ce qui existe, ce qui est en cours, ce qui reste, et qui prend quoi. Il évite les deux accidents classiques du binôme : écrire deux fois la même chose, et casser le code de l'autre.

**Règle : on le met à jour dans la PR qui change l'état du projet**, pas après coup. Une ligne modifiée dans le tableau du §4 suffit.

Le contrat technique (noms de classes, d'attributs, de méthodes) reste dans [`interface.md`](interface.md). Ce fichier-ci dit *où on en est*, `interface.md` dit *comment ça s'emboîte*. Les deux sont à lire avant de commencer une tâche.

### Pour les deux assistants — à lire avant de proposer du code

1. Lire `docs/interface.md` **puis** ce fichier, avant d'écrire la moindre ligne.
2. Ne pas modifier un fichier attribué à l'autre membre (§4) sans que ce soit annoncé dans une PR dédiée.
3. La **contrainte forte de l'énoncé** : aucun `dict`, aucune `list`, aucun `array` pour accéder aux nœuds. On circule uniquement par pointeurs (`up`/`down`, `next_up`/`next_mid`/`next_down`, `prec_mid`). Collecter des `float` dans un test ne viole pas la contrainte.
4. Le code doit rester **crédible comme travail d'étudiant** : pas de génération en masse, chacun tape et commite son code avec ses propres messages.
5. Vérifier avant de proposer : `pytest -q` et `ruff check .` doivent passer, et les prix de référence du §5 ne doivent pas bouger.

---

## 1. Où en est le projet, en deux phrases

Le **moteur trinomial est complet, dividende discret inclus**, et validé : l'arbre se construit, le pricer remonte les valeurs, le prix converge vers Black-Scholes en 1/N, et les invariants exacts du dividende tiennent à 1e-13 pour tout N (§5). 53 tests verts, ruff propre.

Il manque **l'arbre binomial** (obligatoire dans l'énoncé, c'est la priorité n°1 restante), le pricing récursif, les Greeks, le pruning mémoire, les graphes, le Streamlit et le rapport.

---

## 2. Ce qui existe dans `main`

| Fichier | Contenu | Écrit par | Testé |
|---|---|---|---|
| `src/lattice/market.py` | `Market` (dataclass frozen : `s0`, `rate`, `vol`, `dividend`, `div_ex_date`), `year_fraction`, `DAYS_PER_YEAR` | Maxime | oui |
| `src/lattice/option.py` | `OptionTrade` (`strike`, `maturity`, `is_call`, `is_american`) + `payoff` | Maxime | oui |
| `src/lattice/black_scholes.py` | `bs_price`, `norm_cdf` | Maxime | oui |
| `src/lattice/node.py` | `Node`, `TrunkNode` : `get_or_create_up/down`, `find_closest`, `compute_probabilities`, `set_constant_probabilities`, `has_valid_probabilities`, `prune_invalid`, `next_date`, `are_same_dates`, `is_div_in_next_period` | Guillaume | oui |
| `src/lattice/pricer.py` | `column(trunk)` (générateur), `Pricer.price_backward`, `Pricer._node_value` | Maxime | oui |
| `src/lattice/tree.py` | `Tree` : `__init__` (+ probabilités constantes, `nb_invalid_nodes`), `forward_and_variance`, `link_successors`, `build_tree`, `build_next_column` | Maxime, dividende par Guillaume | **non — voir §3** |
| `docs/interface.md` | contrat d'interface | Maxime | — |

**53 tests verts**, ruff propre, CI verte.

### Trois détails qui font perdre du temps si on les ignore

- **`year_fraction` est dans `market.py`, pas dans `tree.py`** (contrairement au squelette du prof). C'est une **fonction du module**, pas une méthode de `Market` : on écrit `year_fraction(d1, d2)` après `from lattice.market import year_fraction`, jamais `market.year_fraction(...)`.
- **`tree.df` est le facteur d'actualisation d'UN pas**, `exp(-r * dt)`. C'est celui qu'utilise le pricer.
- **`link_successors` prend maintenant 4 arguments** : `link_successors(node, fwd, var, trunk)`. Le `trunk` sert à lire `is_div_in_next_period`, qui est porté par le nœud de tronc et vaut pour toute la colonne.

---

## 3. En cours, pas encore dans `main`

| Quoi | Qui | État |
|---|---|---|
| `tests/test_tree.py` — 11 tests de construction et de convergence de l'arbre | Maxime | écrit et vérifié en local, **pas encore poussé**. PR à venir |

> **Conséquence à connaître** : `tree.py` est aujourd'hui dans `main` **sans aucun test**. La CI est verte mais elle ne vérifie rien sur l'arbre — alors que `tree.py` vient justement d'être modifié. Tant que cette PR n'est pas fusionnée, une modification de `tree.py` passe la CI sans être contrôlée. **C'est la prochaine chose à pousser.**
>
> (Ces 11 tests ont été passés en local sur `b461e4c` : ils sont verts, le dividende ne les casse pas.)

**Branche `feature/node-base`** : son contenu est déjà dans `main`, elle est périmée. À supprimer dès que Guillaume confirme qu'il ne repart pas de là (sinon risque de divergence).

**Détail à corriger au passage** : `src/lattice/tree.py` n'a plus de saut de ligne final (`\ No newline at end of file`). Sans importance fonctionnelle, mais à remettre lors de la prochaine modification du fichier.

---

## 4. Ce qui reste à faire

Priorité : **P1 = obligatoire dans l'énoncé**, P2 = attendu pour le rapport, P3 = extension valorisée.

| # | Tâche | Fichier | Qui | Prio | État / notes de départ |
|---|---|---|---|---|---|
| 1 | `price(market, option, pricing_date, nb_steps, kind, method, prune)` | `api.py` | Maxime (B) | P1 | **FAIT (29/09)** — point d'entrée unique. L'arbre est bâti sur `option.maturity`, donc les deux ne peuvent pas diverger |
| 2 | `BinomialTree(Tree)` | `tree.py` | Guillaume (A) | P1 | **FAIT (29/09)** — 8 lignes : dans cette architecture un binomial est un trinomial avec `p_mid = 0`. Converge **en oscillant avec la parité de N** (−2,76 pair / +3,16 impair) |
| 3 | Dividende discret | `node.py`, `tree.py` | Guillaume (A) | P1 | **FAIT (29/09)** — `is_div_in_next_period` calculé dans `TrunkNode`, probabilités constantes hors période de dividende, gestion des forwards ≤ 0 en bas de l'arbre. Invariants exacts vérifiés à 1e-13 (§5) |
| 4 | `price_recursive` + comparaison de perf avec le backward | `pricer.py` | Maxime (B) | **P2** | **à faire.** `_node_value` est déjà factorisée pour être réutilisée sans duplication. Attention à la convention `option_value is None` (§6) |
| 5 | Pruning et mesure mémoire | `tree.py` | Guillaume (A) | P3 | **FAIT (20/10)** — un nœud sous `prune_threshold` ne branche plus : ses successeurs haut et bas ne sont jamais créés, et sa probabilité passe à `next_mid`. **Optionnel, désactivé par défaut** (`prune=False`) : activé en permanence il casse les invariants exacts du dividende, dont le biais est de l'ordre du seuil. Mesures au §5 bis |
| 6 | Greeks (`OneDimDerivative`) | `greeks.py` | Maxime (B) | P2 | **FAIT (29/09)** — delta, véga, rhô fiables ; **gamma instable** par bump, d'où la tâche 11 |
| 7 | `plot_tree.py` + frontière d'exercice | `plot_tree.py` | Guillaume (A) | P3 | **FAIT (13 et 21/10)** — taille des nœuds ∝ `proba_reach`, et coloriage exercer/garder pour les américaines |
| 8 | `streamlit_app.py` | `streamlit_app.py` | Maxime (B) | P3 | **FAIT (13 au 21/10)** — prix, grecques contre Black-Scholes, dessin de l'arbre, convergence |
| 9 | Estimation de l'erreur et N d'une précision cible | `precision.py` | Maxime (B) | P3 | **FAIT (20/10)** — `error_constant`, `expected_gap`, `steps_for_precision` |
| 10 | **Études de convergence et graphes du rapport** | `analysis/` | Maxime (B) | **P2** | **à faire** — le tunnel, l'écart vs strike, binomial vs trinomial. `analysis/mesure_pruning.py` existe déjà pour la partie mémoire |
| 11 | **Delta et gamma par nœuds autour de la racine** | `tree.py` | Guillaume (A) | **P2** | **à faire** — la 2ᵉ méthode du prof, qui corrige le gamma instable du bump |
| 12 | Rapport ≈ 10 pages | `report/` | les deux | **P1** | **à faire** — ce qui a été fait, résultats marquants, difficultés surmontées, beaux graphes |
| 13 | Mail au professeur | — | Maxime | **P1** | **à faire** — questions ouvertes au §8. Toujours pas envoyé, la date de rendu reste inconnue |

### Répartition des fichiers (rappel de `interface.md`)

- **Guillaume (membre A)** : `node.py`, `tree.py`, `plot_tree.py`.
- **Maxime (membre B)** : `market.py`, `option.py`, `black_scholes.py`, `pricer.py`, `greeks.py`, `api.py`, `streamlit_app.py`.
- Les tests d'un fichier sont écrits par celui qui écrit le fichier.

**Avant d'attaquer une tâche, on prévient l'autre** (un message court : « je prends le binomial »). C'est ce qui évite le travail en double.

---

## 5. Résultats numériques de référence

À utiliser pour vérifier qu'une modification n'a rien cassé. Tous re-vérifiés sur `b461e4c` le 29/09.

### Sans dividende — call, S0 = K = 100, T = 1 an, σ = 30 %, r = 0. Black-Scholes = 11,923538.

| N | prix de l'arbre | écart × N | temps de construction |
|---|---|---|---|
| 10 | 11,619170 | −3,04 | — |
| 20 | 11,773656 | −3,00 | 2 ms |
| 100 | 11,893879 | −2,966 | 36 ms |
| 200 | — | −2,962 | 142 ms |
| 1000 | 11,920579 | −2,96 | ≈ 3 s |

L'écart × N tend vers une constante : **la convergence est en 1/N**, régulière. C'est le résultat central du rapport pour le trinomial.

Autres invariants, tous vérifiés :

- r = 5 %, σ = 20 %, N = 1000 : call **10,4515** (BS 10,4506), put **5,5744** (BS 5,5735) ;
- parité call-put sur l'arbre : écart **9,8e-13** ;
- call américain − call européen (r > 0, sans dividende) : **exactement 0** ;
- somme des `proba_reach` sur **chaque** colonne : **1,000000000000** ;
- nombre de nœuds de la colonne i : **2i+1**, sur toutes les colonnes ;
- probabilités trinomiales à σ = 25 %, r = 2 %, Δt = 1/12 : p_up = 0,1629, p_mid = 0,6666, p_down = 0,1704 — moments reproduits à **1e-14** ;
- `nb_invalid_nodes = 0` sans dividende.

### Avec dividende — S0 = 100, σ = 25 %, r = 5 %, D = 3, ex-date à 6 mois, T = 1 an

Les deux invariants ci-dessous sont **exacts quel que soit N** : ce sont les meilleurs tests du dividende.

- **call de strike 0 = S0 − D·e^{−r·t_ex}** = 97,07346898
- **parité C − P = S0 − D·e^{−r·t_ex} − K·e^{−rT}**

| N | écart sur le call K = 0 | écart sur la parité | `nb_invalid_nodes` |
|---|---|---|---|
| 10 | −9,95e-14 | −9,24e-14 | 0 |
| 50 | +4,97e-13 | +2,06e-13 | 0 |
| 200 | +7,39e-13 | +5,67e-13 | 0 |

**Formules du dividende** : E = S·e^{rΔt} − D·e^{r(t+Δt−t_ex)} ; V = (S − (t+Δt−t_ex)/Δt · D)² · e^{2rΔt}(e^{σ²Δt} − 1). Tolérance sur les dates : 1 jour / N / 1000.

**Un arbre peut pricer plusieurs options sans être reconstruit** : à N = 1000, construction ≈ 3 s, puis ≈ 300 ms par prix européen et ≈ 630 ms par prix américain. C'est ce qui rend les études de convergence et le Streamlit utilisables.

### Binomial contre trinomial *(vérifié)*

Le binomial converge **en oscillant avec la parité de N**, là où le trinomial converge régulièrement :

| N | binomial (écart × N) | trinomial |
|---|---|---|
| 100 **pair** | **−2,756** | −2,966 |
| 101 **impair** | **+3,162** | −2,966 |
| 200 pair | −2,757 | −2,962 |
| 201 impair | +3,160 | −2,962 |

### Exercice anticipé *(vérifié)*

| Cas | Prime américaine | Nœuds d'exercice anticipé |
|---|---|---|
| Call, r > 0, **sans dividende** | **+0,000000** | **0** |
| Put, mêmes paramètres | +0,615213 | 257 |
| Call **avec dividende de 12 €** | +3,317681 | 20 |

Le call sans dividende ne s'exerce jamais par anticipation : c'est le cas d'égalité de l'énoncé. Un dividende assez gros fait réapparaître l'exercice juste avant le détachement — il faut qu'il dépasse les intérêts perdus sur le strike (seuil entre 1 et 2 € sur notre cas de référence).

---

## 5 bis. Pruning : le gain mesuré

Reproduire avec `python analysis/mesure_pruning.py` (écrit aussi `results/pruning.png`).

**S0 = 100, K = 100, vol 20 %, r = 5 %, T = 1 an, seuil 1e-7 :**

| N | nœuds sans | avec | gain | temps sans | avec | **Mo sans** | **avec** | biais |
|---|---|---|---|---|---|---|---|---|
| 100 | 10 201 | 4 235 | 58,5 % | 90 ms | 37 ms | 1,7 | 0,7 | −3,1e-09 |
| 400 | 160 801 | 32 997 | 79,5 % | 1662 ms | 447 ms | 27,0 | 5,6 | −1,1e-08 |
| 700 | 491 401 | 75 501 | 84,6 % | 5185 ms | 639 ms | 82,5 | 12,7 | −1,5e-08 |
| **1000** | **1 002 001** | **127 904** | **87,2 %** | **10 088 ms** | **1187 ms** | **168,2** | **21,5** | **−1,9e-08** |

**À N = 1000 : 8 fois moins de nœuds, 8 fois moins de mémoire, 8 fois plus rapide, pour un biais de 2 centièmes de milliardième d'euro.** Sans pruning la mémoire croît en N², avec pruning quasi linéairement.

### L'arbitrage du seuil (N = 500)

| seuil | nœuds | gain | Mo | biais |
|---|---|---|---|---|
| aucun | 251 001 | — | 42,2 | — |
| 1e-10 | 55 944 | 77,7 % | 9,4 | **−5,9e-12** |
| 1e-08 | 49 489 | 80,3 % | 8,3 | −9,1e-10 |
| 1e-07 | 45 906 | 81,7 % | 7,7 | −1,2e-08 |
| 1e-05 | 37 691 | 85,0 % | 6,4 | −2,7e-06 |
| 1e-03 | 27 059 | 89,2 % | 4,6 | **−9,5e-04** |

Même au seuil le plus prudent (1e-10) on supprime **77 % des nœuds** pour un biais invisible. Au-delà de 1e-5 le biais devient perceptible. Le point d'équilibre est vers **1e-7 / 1e-8**.

---

## 6. Conventions qui cassent le code de l'autre si on les oublie

1. **`option_value` vaut `None` à la création du nœud, pas `0.0`.** Le pricer récursif mémorise avec `if node.option_value is None`. Si le nœud naît à `0.0`, le pricer croit que tout est déjà calculé et renvoie 0 partout.
2. **`next_up` et `next_down` peuvent être `None`** (nœud élagué). Le pricer teste avant d'additionner. Pour un nœud élagué, `p_mid = 1`.
3. **`find_closest(target)` commence par `assert target > 0`.** Ce garde-fou n'est pas décoratif : sans lui, `find_closest(-5.0)` descend indéfiniment (un prix divisé par α reste positif, la condition d'arrêt n'est jamais atteinte). Le programme ne plante pas, il **tourne dans le vide** — ça a déjà coûté 12 Go de RAM et un processus à tuer. **Ne pas lancer `pytest` si ce garde-fou a disparu.** C'est pour cela que `build_next_column` teste `fwd > 0` avant d'appeler `find_closest` en descendant la colonne.
4. **`link_successors(node, fwd, var, trunk)`** prend le tronc en 4ᵉ argument : `is_div_in_next_period` est porté par le nœud de tronc et vaut pour toute la colonne.
5. **Probabilités constantes hors dividende** : quand `is_div_in_next_period` est faux, les nœuds copient `tree.p_up / p_mid / p_down` calculés une fois dans le constructeur, au lieu de résoudre le système. Plus rapide et plus précis. Une modification de `Tree.__init__` qui casse ces trois attributs casse tout l'arbre.
6. Les dates sont des `datetime.datetime`, **jamais** des `datetime.date`.
7. Toute modification de `interface.md` passe par une PR relue par l'autre.

---

## 7. Pièges déjà rencontrés (et matière pour la section « difficultés » du rapport)

- **Coupure de ligne sans parenthèses** : `moment = a + b` puis `+ c` à la ligne suivante → Python exécute deux instructions, calcule `+ c` et le jette. **Aucune erreur, résultat faux.** Toujours des parenthèses autour de l'expression entière.
- **`d1` de Black-Scholes sans parenthèses au dénominateur** : invisible à T = 1 (√1 = 1), détecté seulement par un test à T = 0,5.
- **`math.sqrt` au lieu de `math.exp`** pour `df` et `growth` : `ValueError: math domain error` dès que r > 0.
- **Oublier le `* dt`** dans `exp(rate * dt)` : capitalise une année entière à chaque pas. À N = 1000, l'action passe de 100 € à 5,2e+23 €.
- **Forward négatif avec un gros dividende** : en bas de l'arbre, le forward peut passer sous zéro. Il n'existe alors aucun nœud « le plus proche » — d'où le test `fwd > 0` et le traitement par `prune_invalid`. Avec dividende, l'élagage n'est plus une optimisation mais une **nécessité**.
- `pytest.approx(x, 10e-4)` : la tolérance est **relative**, et `10e-4` vaut 1e-3 (pas 1e-4).
- Deux fonctions de test du même nom dans un fichier : la seconde **écrase silencieusement** la première.
- Ruff 0.16 active trop de règles par défaut ; `pyproject.toml` restreint à `select = ["E", "F", "I"]`, `line-length = 100`.

---

## 8. Méthode de travail

### Lancer et vérifier

```powershell
cd C:\Users\nbgru\Dev\Informatique-Quant-Project
.venv\Scripts\Activate.ps1
pytest -q
ruff check .
```

(Chemin à adapter chez Guillaume.) Environnement : Python 3.12, venv dans `.venv`, `pip install -e .` fait, pytest + ruff. Le venv est à réactiver dans **chaque nouvelle fenêtre**.

### Cycle git

Une tâche = une branche = une PR. Le dépôt est privé sur un plan gratuit, donc **il n'y a pas de protection de branche** : techniquement, rien n'empêche de commiter directement sur `main`. C'est justement pour ça qu'on s'impose la branche — elle rend le travail relisible, et elle permet de revenir en arrière proprement si une modification casse les prix de référence.

```powershell
git switch main
git pull
git switch -c feature/ma-tache
```

puis, une fois que `pytest -q` et `ruff check .` passent :

```powershell
git add <fichiers>
git commit -m "message"
git push -u origin feature/ma-tache
gh pr create --fill
```

Et après la fusion : `git switch main`, `git pull`, `git branch -d feature/ma-tache`.

On demande la relecture à l'autre ; s'il n'est pas disponible sous 24 h, on fusionne et on le signale plutôt que de rester bloqué.

### Questions ouvertes au professeur (mail pas encore envoyé)

- Date et format du rendu (lien GitHub ? archive ? PDF du rapport ?)
- Quelles extensions sont notées ?
- Un visuel final en **Streamlit** plutôt qu'en Excel convient-il ? Une version VBA est-elle attendue ?
- Soutenance orale ou non ?
- L'usage d'outils d'IA est-il autorisé, et faut-il le déclarer dans le rapport ?

---

## 9. Ce que demande l'énoncé (mémo)

**Obligatoire** : arbre binomial **et** trinomial avec un pricer ; maximum de code dans des classes ; convergence vers Black-Scholes ; écart selon le nombre de pas et le strike ; exercice américain (Am − Eu, effet d'un taux > 0 ou < 0, cas d'égalité) ; dividende discret (impact sur call et put avec r = 0).

**Extensions valorisées** : graphe de l'arbre et frontière d'exercice ; nombre de pas maximal (temps, mémoire) ; pruning ; N déduit d'une précision cible ; dérivées via une fonction passée en paramètre ; delta et gamma par nœuds ajoutés autour de la racine.

**Rapport** : court, ce qui a été fait, résultats marquants, difficultés surmontées, beaux graphes.

---

## 10. Journal

| Date | `main` | Quoi |
|---|---|---|
| 22/09 → 25/09 | `0b18f3f` | PR #1 à #5 : `market`, `option`, `black_scholes`, `interface.md`, `node`, `pricer`, `tree` trinomial. Moteur trinomial complet et validé contre Black-Scholes |
| 29/09 | `b461e4c` | Guillaume : dividende discret opérationnel (`is_div_in_next_period`), probabilités constantes hors dividende, `prune_invalid` + `nb_invalid_nodes`, 10 tests. Vérifié : aucune régression sur les prix de référence, invariants du dividende exacts à 1e-13 |
| 29/09 | `58c7c38` | `greeks.py` (`OneDimDerivative`), `BinomialTree`, `api.py`. PR #7 à #9 |
| 06/10 → 13/10 | `d2d5b97` | tests du dividende (invariants exacts), application Streamlit. PR #10 et #11 |
| 20/10 → 21/10 | *en PR* | `plot_tree.py` + frontière d'exercice (#12), pruning mémoire + `precision.py` (#13), interface Streamlit complète (#14). **119 tests** |

> ⚠️ **Au 21/10, les PR #12, #13 et #14 sont ouvertes et non fusionnées.** Elles s'empilent : fusionner dans l'ordre **12 → 13 → 14**. Tant que ce n'est pas fait, `main` ne contient ni le pruning, ni le dessin de l'arbre, ni l'application.

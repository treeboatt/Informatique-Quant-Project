# Pricing d'options par arbre (lattice)

Projet d'informatique financière, M2 272 Paris-Dauphine, 2026-2027. Projet en binôme.

On price des calls et des puts, européens et américains, sur un arbre recombinant **binomial** et **trinomial**, avec **dividende discret**, en Python orienté objet. On valide contre Black-Scholes et on étudie la convergence, la vitesse, la mémoire et le pruning.

Contrainte du cours : **aucun dict, aucune liste ni array pour accéder aux noeuds**. Les noeuds sont reliés par pointeurs (`next_up`, `next_mid`, `next_down`, `up`, `down`, `prec_mid`).

## Installation

Il faut Python 3.12 ou plus et git. Commandes pour Windows (PowerShell) :

```powershell
git clone https://github.com/treeboatt/Informatique-Quant-Project.git
cd Informatique-Quant-Project
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
pytest
```

Si l'activation échoue avec « running scripts is disabled on this system », lancer une fois :
`Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

À chaque nouvelle session de travail : se placer dans le dossier du projet et réactiver le venv.

## Structure du dépôt

```
├── src/lattice/     # le package : market, option, node, tree, pricer, black_scholes, greeks, api, plot_tree
├── tests/           # tests pytest
├── docs/            # interface.md : contrat d'interface Node / Tree / Pricer
├── analysis/        # 1 script = 1 étude = 1 figure
├── results/         # figures (PNG) et CSV produits par analysis/
└── report/          # le rapport en PDF
```

Répartition : **A** (moteur d'arbre) possède `node.py`, `tree.py` et `plot_tree.py`. **B** (pricing, validation, analyses) possède `market.py`, `option.py`, `black_scholes.py`, `pricer.py`, `greeks.py`, `api.py` et `tests/`. Un fichier = un propriétaire principal.

## Résultats

Chaque script d'`analysis/` est autonome : il affiche ses tableaux dans la console et écrit sa figure dans `results/`.

| Script | Figure | Ce qu'il montre |
|---|---|---|
| `convergence.py` | `convergence.png` | L'erreur est en **1/N** : l'écart × N se stabilise à **−2,96** pour le trinomial. Le binomial, lui, **oscille avec la parité de N** (−2,76 pair, +3,16 impair) |
| `ecart_vs_strike.py` | `ecart_strike.png` | À nombre de pas fixe, l'erreur **oscille avec le strike** : elle est la plus mauvaise quand le strike tombe sur un nœud de la dernière colonne, la meilleure entre deux nœuds |
| `exercice_americain.py` | `americain.png` | Sans dividende, la prime d'exercice anticipé du call est **exactement nulle** tant que le taux est positif, et devient positive dès qu'il passe sous zéro — le put fait l'inverse. À 5 %, il faut un dividende d'au moins **3 €** pour que le call s'exerce par anticipation |
| `convergence_binaire.py` | `binaire.png` | Une binaire a un saut et non un angle : elle converge en **1/√N**, pas en 1/N (erreur × √N constante à 0,343). Le one-touch vaut environ **deux fois** la binaire européenne de même barrière |
| `mesure_pruning.py` | `pruning.png` | À N = 1000, le pruning retire **87 % des nœuds** et divise la mémoire et le temps par 8, pour un biais de 2 × 10⁻⁸ € |
| `backward_vs_recursif.py` | `backward_vs_recursif.png` | Les deux parcours rendent le **même prix au bit près**, mais le récursif est **2,5 à 4,3 × plus lent** et bute sur la limite de récursion de Python : au-delà de ~950 pas il est refusé, là où le backward n'a aucune limite |

```powershell
python analysis/convergence.py
```

L'application Streamlit reprend ces études de façon interactive, et ajoute les grecques, le dessin de l'arbre et le nombre de pas à viser pour une précision donnée :

```powershell
streamlit run streamlit_app.py
```

## Conventions de code

- Noms en anglais dans le code (comme les slides : `next_mid`, `prec_mid`), commentaires et rapport en français.
- `snake_case` pour les fonctions et attributs, `PascalCase` pour les classes, annotations de type partout.
- Aucune constante « magique » : 365, seuil de pruning, tolérance sur les dates sont des paramètres nommés.
- Une docstring d'une ligne par fonction publique ; chaque bug corrigé est accompagné d'un test qui le reproduit.
- `__slots__` sur `Node` et `TrunkNode`.
- Les scripts d'analyse ne contiennent aucune logique de pricing : ils appellent `api.price(...)`. Seule exception, quand une étude price des centaines d'options sur les mêmes paramètres de marché : elle construit alors l'arbre une fois et le réutilise via `Pricer`, car `api.price` le reconstruirait à chaque appel.
- `ruff format` et `pytest` avant chaque commit.

## Workflow Git

- Personne ne pousse directement sur `main`.
- Une branche par tâche (`feature/black-scholes`, `feature/dividend`...), une pull request par branche, relue et approuvée par l'autre membre avant la fusion.
- Messages de commit préfixés : `feat`, `fix`, `test`, `perf`, `refactor`, `docs`. Exemple : `feat(pricer): add american exercise`.
- La CI (GitHub Actions) lance `pytest` à chaque push et sur chaque pull request.

```powershell
git switch main
git pull
git switch -c feature/ma-tache
# ... travailler, puis :
ruff format .
pytest
git add <fichiers>
git commit -m "feat(...): ..."
git push -u origin feature/ma-tache
# puis ouvrir la pull request sur GitHub
```

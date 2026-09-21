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
├── excel/           # arbre à 2 pas calculé à la main
└── report/          # sources et PDF du rapport
```

Répartition : **A** (moteur d'arbre) possède `node.py`, `tree.py`, `plot_tree.py` et `excel/`. **B** (pricing, validation, analyses) possède `market.py`, `option.py`, `black_scholes.py`, `pricer.py`, `greeks.py`, `api.py` et `tests/`. Un fichier = un propriétaire principal.

## Conventions de code

- Noms en anglais dans le code (comme les slides : `next_mid`, `prec_mid`), commentaires et rapport en français.
- `snake_case` pour les fonctions et attributs, `PascalCase` pour les classes, annotations de type partout.
- Aucune constante « magique » : 365, seuil de pruning, tolérance sur les dates sont des paramètres nommés.
- Une docstring d'une ligne par fonction publique ; chaque bug corrigé est accompagné d'un test qui le reproduit.
- `__slots__` sur `Node` et `TrunkNode`.
- Les scripts d'analyse ne contiennent aucune logique de pricing : ils appellent `api.price(...)`.
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

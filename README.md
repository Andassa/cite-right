# cite-right

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/cite-right.svg)](https://pypi.org/project/cite-right/)

**cite-right** est un outil en ligne de commande qui génère des citations académiques à partir d’un **DOI**, d’une **URL** (arXiv ou `doi.org`), d’un **ISBN** ou d’un **titre**, en s’appuyant sur des **APIs publiques gratuites** (aucune clé payante requise).

## Fonctionnalités

- Résolution **CrossRef** (DOI), **OpenAlex** (titre), **arXiv** (préprint), **Open Library** (ISBN)
- Repli automatique vers **Semantic Scholar** si besoin
- Styles : **APA 7**, **MLA 9**, **IEEE**, **Chicago 17** (auteur-date), **Vancouver**, **Harvard**
- Exports : **texte**, **BibTeX**, **RIS**, **Markdown**, **HTML**
- **Cache SQLite** local (`.cite-right-cache.db`) pour limiter les appels réseau
- Option **`--use-suggested-style`** : suggestion de style selon des mots-clés du domaine
- Mode **batch** (fichier texte) et mode **interactif**

## Installation

### Avec `pip`

```bash
pip install cite-right
```

### Développement avec `uv`

```bash
uv venv
uv pip install -e ".[dev]"
cite-right --doi "10.1038/s41586-021-03819-2" --style APA
```

## Démarrage rapide

```bash
# DOI
cite-right --doi "10.1038/s41586-021-03819-2" --style APA

# URL arXiv
cite-right --url "https://arxiv.org/abs/1706.03762" --style IEEE

# Titre (OpenAlex)
cite-right --title "Attention is all you need" --style MLA

# ISBN (Open Library)
cite-right --isbn "9780134685991" --style Chicago

# Détection automatique du type (argument positionnel)
cite-right "10.1038/s41586-021-03819-2" --style APA

# Batch + fichier de sortie
cite-right --batch sources.txt --style APA --output bibliography.md

# Copie presse-papier
cite-right --doi "10.1038/s41586-021-03819-2" --style APA --copy

# Export BibTeX / RIS / HTML
cite-right --doi "10.1038/s41586-021-03819-2" --export bibtex
cite-right --title "climate change" --export ris -o refs.ris

# Style suggéré automatiquement
cite-right --doi "10.1056/NEJMoa..." --use-suggested-style

# Assistant
cite-right --interactive
```

## Styles supportés

| Style     | Usage typique                          |
|----------|-----------------------------------------|
| APA      | Sciences sociales, psychologie          |
| MLA      | Lettres, humanités                      |
| IEEE     | Ingénierie, informatique                |
| Chicago  | Histoire, édition (auteur-date)         |
| Vancouver| Médecine, sciences de la santé          |
| Harvard  | Auteur-date (variante courante UK/AU)   |

## Fichier batch

Une ligne = une source (DOI, URL, ISBN ou titre). Les lignes vides et les lignes commençant par `#` sont ignorées.

## Contribution

1. Forkez le dépôt et créez une branche (`feature/...`).
2. Installez les dépendances de développement : `uv pip install -e ".[dev]"`.
3. Lancez les tests : `pytest`.
4. Proposez une pull request claire (description + contexte).

Les rapports de bug et idées d’évolution sont les bienvenus via les issues du dépôt.

## Licence

MIT — voir le fichier `pyproject.toml` (métadonnées du projet).

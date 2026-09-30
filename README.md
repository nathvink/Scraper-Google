# Scraper-Google

Petit outil en ligne de commande pour scraper une page web précise.

## Installation
```
pip install -r requirements.txt
```

## Utilisation
```
# Résumé de la page (titre, description, titres, liens, images)
python scraper.py https://example.com

# Extraire des éléments précis : nom=sélecteur_css[@attribut]
python scraper.py URL -s "nom=.item .name" -s "prix=.item .price" -s "lien=.item a@href"

# Export CSV ou JSON dans un fichier
python scraper.py URL -s "titre=h1" -f csv -o resultat.csv
```
Options : `-f json|csv`, `-o fichier`, `--timeout N`, `--ignore-robots`.

Le script respecte `robots.txt` par défaut. Il ne gère pas les pages rendues en
JavaScript (il lit le HTML brut) ; pour celles-ci, il faudrait passer à Playwright.

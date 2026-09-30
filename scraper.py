#!/usr/bin/env python3
"""Scraper d'une page web précise.

Exemples :
  python scraper.py https://example.com
  python scraper.py https://example.com -s "titre=h1" -s "liens=a@href"
  python scraper.py URL -s "produit=.item" -s "prix=.item .price" -f csv -o out.csv

Syntaxe d'un sélecteur : nom=sélecteur_css[@attribut]
  - sans @attribut : on récupère le texte de l'élément
  - avec @attribut : on récupère la valeur de l'attribut (href, src, ...)
Sans -s, l'outil extrait un résumé de la page (titre, description, titres, liens, images).
"""
import argparse
import csv
import json
import sys
import time
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; ScraperGoogle/1.0)"


def fetch(url, timeout=15, retries=3, headers=None):
    """Télécharge la page avec quelques tentatives en cas d'erreur réseau/5xx."""
    hdrs = {"User-Agent": USER_AGENT, "Accept-Language": "fr,en;q=0.8"}
    hdrs.update(headers or {})
    last = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=hdrs, timeout=timeout)
            if resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding
            return resp.text
        except requests.RequestException as exc:
            last = exc
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"Impossible de récupérer {url} : {last}")


def allowed_by_robots(url):
    """True si robots.txt autorise (ou est absent/inaccessible)."""
    p = urlparse(url)
    rp = robotparser.RobotFileParser()
    try:
        r = requests.get(f"{p.scheme}://{p.netloc}/robots.txt",
                         headers={"User-Agent": USER_AGENT}, timeout=10)
        if r.status_code != 200:
            return True
        rp.parse(r.text.splitlines())
    except requests.RequestException:
        return True
    return rp.can_fetch(USER_AGENT, url)


def parse_selector(spec):
    if "=" not in spec:
        raise ValueError(f"Sélecteur invalide '{spec}' : attendu nom=css[@attr]")
    name, rest = spec.split("=", 1)
    css, attr = (rest.rsplit("@", 1) + [None])[:2] if "@" in rest else (rest, None)
    return name.strip(), css.strip(), attr


def extract_custom(soup, selectors, base_url):
    data = {}
    for spec in selectors:
        name, css, attr = parse_selector(spec)
        values = []
        for el in soup.select(css):
            if attr:
                v = el.get(attr)
                if isinstance(v, list):
                    v = " ".join(v)
                if v and attr in ("href", "src"):
                    v = urljoin(base_url, v)
            else:
                v = el.get_text(" ", strip=True)
            if v:
                values.append(v)
        data[name] = values
    return data


def extract_summary(soup, base_url):
    desc = soup.find("meta", attrs={"name": "description"})
    return {
        "titre": [soup.title.get_text(strip=True)] if soup.title else [],
        "description": [desc["content"]] if desc and desc.get("content") else [],
        "titres": [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])],
        "liens": [urljoin(base_url, a["href"]) for a in soup.find_all("a", href=True)],
        "images": [urljoin(base_url, i["src"]) for i in soup.find_all("img", src=True)],
    }


def save(data, fmt, output):
    if fmt == "json":
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(text + "\n")
        else:
            print(text)
        return
    # CSV : une colonne par sélecteur, lignes alignées
    keys = list(data)
    n = max((len(v) for v in data.values()), default=0)
    out = open(output, "w", newline="", encoding="utf-8-sig") if output else sys.stdout
    try:
        w = csv.writer(out)
        w.writerow(keys)
        for i in range(n):
            w.writerow([data[k][i] if i < len(data[k]) else "" for k in keys])
    finally:
        if output:
            out.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scraper d'une page web précise.")
    ap.add_argument("url", help="URL de la page à scraper")
    ap.add_argument("-s", "--select", action="append", default=[],
                    metavar="nom=css[@attr]", help="sélecteur à extraire (répétable)")
    ap.add_argument("-f", "--format", choices=["json", "csv"], default="json")
    ap.add_argument("-o", "--output", help="fichier de sortie (défaut : écran)")
    ap.add_argument("--ignore-robots", action="store_true",
                    help="ne pas vérifier robots.txt")
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args(argv)

    if not args.ignore_robots and not allowed_by_robots(args.url):
        print("robots.txt interdit le scraping de cette page "
              "(--ignore-robots pour passer outre, à vos risques).", file=sys.stderr)
        return 2
    try:
        html = fetch(args.url, timeout=args.timeout)
        soup = BeautifulSoup(html, "html.parser")
        data = (extract_custom(soup, args.select, args.url) if args.select
                else extract_summary(soup, args.url))
    except (RuntimeError, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    save(data, args.format, args.output)
    if args.output:
        print(f"Résultat écrit dans {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

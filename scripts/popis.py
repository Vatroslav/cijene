"""Koja trgovina ima stavke s OurGroceries popisa.

    python scripts/popis.py                 popis "Špeža"
    python scripts/popis.py "Žabac"         drugi popis
    python scripts/popis.py --detalji       uz svaku stavku i proizvode koji su je pogodili
    python scripts/popis.py --lokalno       cjenici iz site/data.json umjesto s objavljene stranice
    python scripts/popis.py --stavka "grčki jogurt" [--stavka ...]   bez OurGroceriesa, zadane stavke

Popis se čita kroz skriptu u health repou (ondje je prijava, lokalno) - jednom po
pokretanju, na zahtjev, nikad u petlji. Ništa se ne zapisuje ni ne objavljuje, a popis ne
izlazi s računala.

Ocjena riječi je ista kao u aplikaciji (site/app.js, termScore) - mijenjati oboje zajedno.
"""

import argparse
import json
import math
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OG_SCRIPTS = Path.home() / "github" / "health" / "scripts"
DATA_URL = "https://vatroslav.github.io/cijene/data.json"
DEFAULT_LIST = "Špeža"
# Veznici i prijedlozi iz prirodnog opisa stavke ("povrće za juhu") ne nose značenje za pretragu
STOPWORDS = {"za", "i", "s", "sa", "od", "u", "na", "bez", "ili", "po"}


# --- podudaranje (kopija logike iz site/app.js) --------------------------------------

def norm(s):
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def words(s):
    return [w for w in re.split(r"[^a-z0-9]+", norm(s)) if w]


def common_prefix(a, b):
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    return i


def one_edit(a, b):
    if abs(len(a) - len(b)) > 1:
        return False
    i = j = edits = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
            continue
        edits += 1
        if edits > 1:
            return False
        if len(a) > len(b):
            i += 1
        elif len(b) > len(a):
            j += 1
        else:
            i += 1
            j += 1
    return edits + (len(a) - i) + (len(b) - j) <= 1


def term_score(t, w):
    if w == t:
        return 3
    if w.startswith(t):
        return 2
    if len(w) >= 3 and t.startswith(w):
        return 1.5
    if len(t) >= 4 and len(w) >= 4 and abs(len(t) - len(w)) <= 1 and common_prefix(t, w) >= max(3, min(len(t), len(w)) - 1):
        return 1.2
    if len(t) >= 3 and t in w:
        return 1
    if len(t) >= 5 and one_edit(t, w):
        return 1
    return 0


# --- stavka s popisa -> proizvodi -----------------------------------------------------
# Stavke su pisane običnim jezikom ("mlijeko zobeno", "deterdžent za pranje suđa (čarli)"),
# a cjenik kraticama ("NAPITAK ALPRO ZOB", "DET.ČARLI CLASSIC"), pa se sve riječi rijetko
# poklope. Proizvod koji pogodi sve riječi = sigurno (✓). Inače se po trgovini uzima proizvod
# koji pogodi najviše riječi (barem pola) = djelomično (~), uz ispis kandidata - je li to
# stvarno ta stavka, procjenjuje čovjek (ili Claude) iz naziva.

QUANTITY = re.compile(r"^[0-9]+([.,][0-9]+)?(g|kg|ml|l|dl|kom|x)?$")
MIN_TERM = 1.2


def terms_of(text):
    ws = [w for w in words(text) if w not in STOPWORDS and not QUANTITY.match(w)]
    return ws or words(text)


def match_item(text, products, idx):
    """Po trgovini: ("full", broj, [nazivi]) | ("partial", broj, ["[pogođene riječi] naziv"]) | None.

    Kod djelomičnog pogotka kandidati se grupiraju po tome koje su riječi pogodili, a grupe
    idu od rjeđih riječi prema češćima: za "mlijeko zobeno" prvo "[zobeno] NAPITAK ALPRO ZOB",
    pa tek onda "[mlijeko] ...". Rijetkost nije uvijek i važnost ("smrznuti" je rjeđi od
    "batat"), zato se ispisuje više grupa, a ne jedan pobjednik.
    """
    terms = terms_of(text)
    need = max(1, math.ceil(len(terms) / 2))
    per_store = {i: [] for i in idx}
    df = dict.fromkeys(terms, 0)
    for p in products:
        hit, sc = [], 0.0
        for t in terms:
            b = max((term_score(t, w) for w in p["words"]), default=0)
            if b >= MIN_TERM:
                hit.append(t)
                sc += b
                df[t] += 1
        if len(hit) >= need:
            for i in idx:
                if i in p["by_store"]:
                    per_store[i].append((tuple(hit), sc, p["by_store"][i]))
    rarity = {t: -df[t] for t in terms}
    result = {}
    for i, cands in per_store.items():
        full = sorted((c for c in cands if len(c[0]) == len(terms)), key=lambda c: -c[1])
        if full:
            result[i] = ("full", len(full), [name for _, _, name in full])
            continue
        if not cands:
            result[i] = None
            continue
        best = {}
        for hit, sc, name in cands:
            if hit not in best or sc > best[hit][0]:
                best[hit] = (sc, name)
        groups = sorted(best, key=lambda h: (-len(h), -sum(rarity[t] for t in h)))
        result[i] = ("partial", len(cands), [f"[{' '.join(h)}] {best[h][1]}" for h in groups])
    return result


# --- podaci ----------------------------------------------------------------------------

def load_data(local):
    if local:
        return json.loads((REPO / "site" / "data.json").read_text(encoding="utf-8"))
    with urllib.request.urlopen(DATA_URL, timeout=60) as r:
        return json.load(r)


def products_of(data):
    """Grupiranje po barkodu, kao u aplikaciji."""
    F = {f: i for i, f in enumerate(data["fields"])}
    by_key = {}
    for r in data["items"]:
        key = r[F["barcode"]] or f"{r[F['store']]}:{r[F['name']]}"
        # by_store: naziv kako ga piše ta trgovina (isti barkod, različiti nazivi po lancu)
        p = by_key.setdefault(key, {"by_store": {}})
        p["by_store"][r[F["store"]]] = r[F["name"]]
    for p in by_key.values():
        p["words"] = set(words(" ".join(p["by_store"].values())))
    return list(by_key.values())


def read_list(name):
    sys.path.insert(0, str(OG_SCRIPTS))
    import ourgroceries as og  # noqa: E402 - skripta iz health repoa

    client = og.load_client()
    found = [sl for sl in client.lists() if sl.get("name", "").lower() == name.lower()]
    if not found:
        sys.exit(f"Nema popisa '{name}'. Popisi: " + ", ".join(sl.get("name", "") for sl in client.lists()))
    items = []
    for item in client.items(found[0]["id"]):
        if item.get("crossedOff") or item.get("crossedOffAt"):
            continue
        # količina je u nazivu ("grcki jogurt (4)"), napomena posebno - pretražuje se samo naziv
        items.append(re.sub(r"\s*\(\d+\)$", "", og.item_name(item)).strip())
    return found[0]["name"], items


# --- ispis -----------------------------------------------------------------------------

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Koja trgovina ima stavke s OurGroceries popisa.")
    parser.add_argument("popis", nargs="?", default=DEFAULT_LIST)
    parser.add_argument("--detalji", action="store_true", help="ispiši proizvode koji su pogodili stavku (do 3)")
    parser.add_argument("--sve", action="store_true", help="uz --detalji ispiši sve proizvode, ne samo 3")
    parser.add_argument("--lokalno", action="store_true", help="cjenici iz site/data.json")
    parser.add_argument("--stavka", action="append", help="stavka umjesto OurGroceries popisa (može više puta)")
    args = parser.parse_args()

    list_name, items = ("Stavke", args.stavka) if args.stavka else read_list(args.popis)
    if not items:
        print(f"{list_name}: nema aktivnih stavki.")
        return
    data = load_data(args.lokalno)
    stores = data["stores"]
    products = products_of(data)
    idx = [i for i, s in enumerate(stores) if not s.get("error")]

    rows = [(text, match_item(text, products, idx)) for text in items]

    dates = sorted({s["date"] for s in stores if s.get("date")})
    print(f"{list_name} - {len(items)} stavki, cjenici {', '.join(dates)}\n")
    summary = []
    for i in idx:
        sure = sum(1 for _, r in rows if r[i] and r[i][0] == "full")
        maybe = sum(1 for _, r in rows if r[i] and r[i][0] == "partial")
        summary.append(f"{stores[i]['name']} {sure}/{len(items)}" + (f" (+{maybe} ~)" if maybe else ""))
    print("   ".join(summary))
    for s in stores:
        if s.get("error"):
            print(f"{s['name']}: cjenik nedostupan ({s['error']})")
    print()

    width = max(len(t) for t, _ in rows) + 2
    print("".ljust(width) + "".join(stores[i]["name"].ljust(11) for i in idx))
    for text, r in rows:
        cells = "".join(("-" if not r[i] else f"{'✓' if r[i][0] == 'full' else '~'} {r[i][1]}").ljust(11) for i in idx)
        print(text.ljust(width) + cells)
        if args.detalji:
            for i in idx:
                if r[i]:
                    names = "; ".join(r[i][2] if args.sve else r[i][2][:3])
                    print(f"    {stores[i]['name']}: {'✓' if r[i][0] == 'full' else '~'} {names}")

    missing = [t for t, r in rows if not any(r.values())]
    if missing:
        print("\nNema ni u jednoj trgovini: " + ", ".join(missing))
    print("\n✓ = proizvod pogađa sve riječi stavke, ~ = samo dio (provjeri s --detalji).")
    print("Broj = koliko proizvoda odgovara. Cjenik je asortiman trgovine, ne stanje na polici.")


if __name__ == "__main__":
    main()

"""Preuzima dnevne cjenike odabranih trgovina u Velikoj Gorici i slaže ih u jedan JSON.

Pokretanje:  python scripts/fetch.py [izlazni_folder]     (default: site)
Rezultat:    <izlazni_folder>/data.json

Izvor je obveza objave cjenika (Odluka Vlade, NN 75/2025): svaka prodavaonica
svaki dan do 8:00 objavljuje CSV. Kad današnji cjenik još nije dostupan
(ili link vraća 404), uzima se zadnji dostupni unatrag DAYS_BACK dana.
Samo standardna biblioteka - nema ovisnosti.
"""

import csv
import datetime as dt
import html
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

UA = "Mozilla/5.0 (compatible; cijene/1.0; +https://github.com/Vatroslav/cijene)"
DAYS_BACK = 7

STORES = [
    {"id": "zabac", "chain": "zabac", "name": "Žabac", "address": "Trg grada Vukovara 8",
     "zabac_location": "Velika Gorica"},
    {"id": "spar", "chain": "spar", "name": "Spar", "address": "Matice hrvatske 22",
     "spar_code": "87076"},
    {"id": "interspar", "chain": "spar", "name": "Interspar", "address": "Rakarska ulica 13",
     "spar_code": "8728"},
    {"id": "konzum", "chain": "konzum", "name": "Konzum", "address": "Marina Getaldića 1",
     "konzum_code": "0208"},
    {"id": "lidl", "chain": "lidl", "name": "Lidl", "address": "Ul. kneza Ljudevita Posavskog 55",
     "lidl_code": "240"},
]

# Stupci po lancu (nazivi zaglavlja lowercase, tuple = prihvatljive varijante).
# None = lanac ne objavljuje taj podatak.
COLUMNS = {
    "spar": {
        "name": "naziv", "code": "šifra", "brand": "marka", "qty": "neto količina",
        "unit": "jedinica mjere", "price": "mpc (eur)",
        "unit_price": "cijena za jedinicu mjere (eur)",
        "special": "mpc za vrijeme posebnog oblika prodaje (eur)",
        "low30": "najniža cijena u posljednjih 30 dana (eur)",
        "barcode": "barkod", "category": "kategorija proizvoda",
    },
    "konzum": {
        "name": "naziv proizvoda", "code": "šifra proizvoda", "brand": "marka proizvoda",
        "qty": "neto količina", "unit": "jedinica mjere", "price": "maloprodajna cijena",
        "unit_price": "cijena za jedinicu mjere",
        "special": "mpc za vrijeme posebnog oblika prodaje",
        # Konzumovo zaglavlje ima tipfeler "posljednih" - prihvaćaju se oba oblika
        "low30": ("najniža cijena u posljednjih 30 dana", "najniža cijena u posljednih 30 dana"),
        "barcode": "barkod", "category": "kategorija proizvoda",
    },
    "lidl": {
        # neto_količina je samo broj; jedinica_mjere je opis pakiranja ("1,5l", "800g")
        "name": "naziv", "code": "šifra", "brand": "marka", "qty": "jedinica_mjere",
        "unit": None, "price": "maloprodajna_cijena",
        "unit_price": "cijena_za_jedinicu_mjere",
        "special": "mpc_za_vrijeme_posebnog_oblika_prodaje",
        "low30": "najniza_cijena_u_poslj._30_dana",
        "barcode": "barkod", "category": "kategorija_proizvoda",
    },
    "zabac": {
        "name": "naziv artikla", "code": "šifra artikla", "brand": "marka", "qty": "gramaža",
        "unit": None, "price": "mpc", "unit_price": None, "special": None,
        "low30": "najniža cijena u posljednjih 30 dana",
        "barcode": "barcode", "category": "naziv grupe artikala",
    },
}


class NotAvailable(Exception):
    pass


def get(url: str, retry_404: int = 0) -> bytes:
    """retry_404: koliko puta ponoviti na 404 (Konzum nasumično vraća 404 za postojeće datoteke)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    attempt, misses = 0, 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                misses += 1
                if misses > retry_404:
                    raise NotAvailable(f"HTTP {e.code}: {url}") from e
                time.sleep(1)
                continue
            err = e
        except (urllib.error.URLError, TimeoutError) as e:
            err = e
        attempt += 1
        if attempt >= 3:
            raise NotAvailable(f"{err}: {url}")
        time.sleep(3 * attempt)


def days():
    today = dt.date.today()
    return [today - dt.timedelta(days=i) for i in range(DAYS_BACK)]


# --- izvori -------------------------------------------------------------------

def fetch_spar(store):
    for d in days():
        try:
            index = json.loads(get(f"https://www.spar.hr/datoteke_cjenici/Cjenik{d:%Y%m%d}.json"))
        except (NotAvailable, ValueError):
            continue
        for f in index.get("files", []):
            if f"_{store['spar_code']}_" in f.get("name", ""):
                try:
                    return get(f["URL"]), d, f["URL"]
                except NotAvailable:
                    break
    raise NotAvailable("Spar: nema cjenika za zadnjih %d dana" % DAYS_BACK)


KONZUM = "https://www.konzum.hr"


def konzum_url(store, d):
    """Lista cjenika je paginirana; traži se link čiji naslov nosi šifru prodavaonice."""
    seen = set()
    for page in range(1, 60):
        try:
            page_html = get(f"{KONZUM}/cjenici?date={d:%Y-%m-%d}&page={page}", retry_404=5).decode("utf-8", "replace")
        except NotAvailable:
            return None
        hrefs = set(re.findall(r'href="(/cjenici/download\?title=[^"]+)"', page_html)) - seen
        if not hrefs:
            return None
        seen |= hrefs
        for href in hrefs:
            href = html.unescape(href)
            parts = urllib.parse.unquote_plus(href.split("title=", 1)[1]).split(",")
            if len(parts) > 2 and parts[2].strip() == store["konzum_code"]:
                # Konzum vraća 404 kad su razmaci kodirani kao "+" - mora biti %20
                return KONZUM + href.replace("+", "%20")
    return None


def fetch_konzum(store):
    for d in days():
        url = konzum_url(store, d)
        if url:
            try:
                return get(url, retry_404=15), d, url
            except NotAvailable:
                continue
    raise NotAvailable("Konzum: nema cjenika za zadnjih %d dana" % DAYS_BACK)


def fetch_zabac(store):
    loc = urllib.parse.quote(store["zabac_location"])
    page_html = get(f"https://zabacfoodoutlet.hr/cjenik/?store={loc}").decode("utf-8", "replace")
    rows = re.findall(r"<h3>([^<]*\d{2}\.\d{2}\.\d{4}[^<]*)</h3>.*?href=\"([^\"]+\.csv)\"", page_html, re.S)
    for title, url in rows[:DAYS_BACK]:
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", title)
        d = dt.date(int(m[3]), int(m[2]), int(m[1]))
        try:
            return get(url), d, url
        except NotAvailable:
            continue
    raise NotAvailable("Žabac: nema dostupnog cjenika")


LIDL = "https://tvrtka.lidl.hr"
LIDL_INDEX = [f"{LIDL}/cijene/cijene-u-trgovinama", f"{LIDL}/cijene"]


def lidl_zip_date(href):
    """Datum iz imena ZIP-a. Lidl ih imenuje ručno ("..._na_dan_18_09_2026", "Cijene_14.07."),
    pa se gleda samo ime datoteke, a godina može nedostajati."""
    name = urllib.parse.unquote(href).rsplit("/", 1)[-1].removesuffix(".zip")
    for m in re.finditer(r"(\d{1,2})[._\s-]+(\d{1,2})(?:[._\s-]+(\d{4}))?", name):
        day, month, year = int(m[1]), int(m[2]), int(m[3] or dt.date.today().year)
        try:
            return dt.date(year, month, day)
        except ValueError:
            continue
    return None


def csv_from_zip(raw: bytes, prefix: str):
    """CSV prodavaonice iz ZIP-a; ZIP zna biti ugniježđen u ZIP ili imati podfolder."""
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for name in z.namelist():
            if name.rsplit("/", 1)[-1].startswith(prefix) and name.lower().endswith(".csv"):
                return z.read(name), name
        for name in z.namelist():
            if name.lower().endswith(".zip"):
                found = csv_from_zip(z.read(name), prefix)
                if found:
                    return found
    return None


def fetch_lidl(store):
    links = {}
    for index in LIDL_INDEX:
        try:
            page_html = get(index).decode("utf-8", "replace")
        except NotAvailable:
            continue
        for href in re.findall(r'href="([^"]+\.zip)"', page_html):
            d = lidl_zip_date(href)
            if d:
                links[urllib.parse.urljoin(LIDL, html.unescape(href))] = d
    oldest = dt.date.today() - dt.timedelta(days=DAYS_BACK)
    for url, d in sorted(links.items(), key=lambda kv: kv[1], reverse=True):
        if d < oldest:
            break
        try:
            found = csv_from_zip(get(url), f"Supermarket {store['lidl_code']}_")
        except (NotAvailable, zipfile.BadZipFile):
            continue
        if found:
            # pravi datum je u imenu CSV-a ("..._18.09.2026_7.15h.csv"), ime ZIP-a je samo naznaka
            m = re.search(r"_(\d{1,2})\.(\d{1,2})\.(\d{4})_", found[1])
            return found[0], dt.date(int(m[3]), int(m[2]), int(m[1])) if m else d, url
    raise NotAvailable("Lidl: nema cjenika za zadnjih %d dana" % DAYS_BACK)


FETCHERS = {"spar": fetch_spar, "konzum": fetch_konzum, "zabac": fetch_zabac, "lidl": fetch_lidl}


# --- parsiranje ---------------------------------------------------------------

def decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1250")


def num(s):
    s = (s or "").strip().replace(",", ".")
    try:
        return round(float(s), 4)
    except ValueError:
        return None


UNITS = {"ko": "kom", "ea": "kom", "l": "L"}


def fmt_num(n: float) -> str:
    return f"{n:g}".replace(".", ",")


def clean_qty(qty: str, unit: str) -> str:
    """Spar: '0,1000' + 'kg' -> '0,1 kg'; Konzum: '0.50 kg' -> '0,5 kg'; Žabac: slobodan tekst."""
    qty = (qty or "").strip()
    if unit and re.fullmatch(r"[\d.,]+", qty) and num(qty) is not None:
        return f"{fmt_num(num(qty))} {UNITS.get(unit.strip().lower(), unit.strip())}"
    m = re.fullmatch(r"([\d.,]+)\s+(\S+)", qty)
    if m and num(m[1]) is not None:
        return f"{fmt_num(num(m[1]))} {UNITS.get(m[2].lower(), m[2])}"
    return qty


def unit_label(qty: str, unit: str, chain: str) -> str:
    """Jedinica na koju se odnosi cijena za jedinicu mjere."""
    if chain == "spar":
        u = (unit or "").strip()
    elif chain == "konzum":
        parts = (qty or "").split()
        u = parts[-1] if len(parts) > 1 else ""
    elif chain == "lidl":
        # cijena po jedinici je po kg ili L, ovisno o pakiranju ("800g", "1,5l")
        m = re.search(r"\d\s*(kg|g|ml|l)\b", (qty or "").lower())
        u = {"kg": "kg", "g": "kg", "ml": "L", "l": "L"}[m[1]] if m else ""
    else:
        u = ""
    return UNITS.get(u.lower(), u)


def parse(raw: bytes, chain: str):
    text = decode(raw)
    first = text.split("\n", 1)[0]
    reader = csv.reader(io.StringIO(text), delimiter=";" if first.count(";") > first.count(",") else ",")
    header = [h.strip().lower() for h in next(reader)]
    cols = COLUMNS[chain]
    idx = {}
    for field, name in cols.items():
        if name is None:
            continue
        found = [n for n in ((name,) if isinstance(name, str) else name) if n in header]
        if not found:
            raise ValueError(f"{chain}: nema stupca {name!r} (zaglavlje: {header})")
        idx[field] = header.index(found[0])

    def val(row, field):
        i = idx.get(field)
        return row[i].strip() if i is not None and i < len(row) else ""

    items, seen = [], {}
    for row in reader:
        if not row or not val(row, "name"):
            continue
        # Lidl ponavlja isti artikl (istu šifru) u više redaka, po jedan za svaki barkod.
        # Ostaje jedan redak, s EAN-13 barkodom ako ga ima (on se poklapa s drugim lancima).
        code = val(row, "code")
        if chain == "lidl" and code in seen:
            if len(val(row, "barcode")) == 13 and len(items[seen[code]]["barcode"]) != 13:
                items[seen[code]]["barcode"] = val(row, "barcode")
            continue
        seen[code] = len(items)
        qty_raw, unit = val(row, "qty"), val(row, "unit")
        items.append({
            "name": re.sub(r"\s+", " ", val(row, "name")),
            "brand": val(row, "brand"),
            "qty": clean_qty(qty_raw, unit),
            "price": num(val(row, "price")),
            "unit_price": num(val(row, "unit_price")),
            "unit": unit_label(qty_raw, unit, chain),
            "special": num(val(row, "special")),
            "low30": num(val(row, "low30")),
            "barcode": val(row, "barcode").lstrip("0") or "",
            "category": val(row, "category").strip().capitalize(),
        })
    return items


# --- main ---------------------------------------------------------------------

FIELDS = ["store", "name", "brand", "qty", "price", "unit_price", "unit", "special", "low30", "barcode", "category"]


def main():
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    out_dir.mkdir(parents=True, exist_ok=True)
    stores, rows = [], []
    for i, store in enumerate(STORES):
        info = {k: store[k] for k in ("id", "name", "address")}
        try:
            raw, date, url = FETCHERS[store["chain"]](store)
            items = parse(raw, store["chain"])
            info.update(date=date.isoformat(), source=url, count=len(items))
            rows += [[i] + [it[f] for f in FIELDS[1:]] for it in items]
            print(f"{store['name']}: {len(items)} proizvoda, cjenik {date}")
        except Exception as e:  # jedna trgovina ne smije srušiti ostale
            info.update(error=str(e))
            print(f"::warning::{store['name']}: {e}")
        stores.append(info)

    if not rows:
        print("::error::Nijedan cjenik nije preuzet")
        sys.exit(1)

    data = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
        "stores": stores,
        "fields": FIELDS,
        "items": rows,
    }
    (out_dir / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Ukupno {len(rows)} redaka -> {out_dir / 'data.json'}")


if __name__ == "__main__":
    main()

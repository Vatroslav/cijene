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

# Druga stranica (site/akcije): samo proizvodi na akciji, trgovine u Sisku i Velikoj Gorici.
STORES_SALE = [
    {"id": "ktc-si-tesle", "chain": "ktc", "name": "KTC Sisak", "city": "Sisak",
     "address": "Nikole Tesle 12B", "ktc_branch": "RC SISAK PJ-41"},
    {"id": "ktc-si-zagrebacka", "chain": "ktc", "name": "KTC Sisak", "city": "Sisak",
     "address": "Zagrebačka 49", "ktc_branch": "RC SISAK II PJ-73"},
    {"id": "ktc-vg", "chain": "ktc", "name": "KTC Velika Gorica", "city": "Velika Gorica",
     "address": "Trg kralja Petra Krešimira IV 1", "ktc_branch": "RC VELIKA GORICA PJ-8B"},
    {"id": "eurospin-si", "chain": "eurospin", "name": "Eurospin Sisak", "city": "Sisak",
     "address": "Zagrebačka 49G", "eurospin_code": "310012"},
    {"id": "eurospin-vg", "chain": "eurospin", "name": "Eurospin Velika Gorica",
     "city": "Velika Gorica", "address": "Ulica Juraja Dobrile 1C", "eurospin_code": "310006"},
    {"id": "lidl-si", "chain": "lidl", "name": "Lidl Sisak", "city": "Sisak",
     "address": "Zagrebačka 49f", "lidl_code": "114"},
    {"id": "lidl-vg", "chain": "lidl", "name": "Lidl Velika Gorica", "city": "Velika Gorica",
     "address": "Ul. kneza Ljudevita Posavskog 55", "lidl_code": "240"},
    {"id": "plodine-vg", "chain": "plodine", "name": "Plodine Velika Gorica",
     "city": "Velika Gorica", "address": "Ul. kneza Ljudevita Posavskog 47", "plodine_code": "140"},
    {"id": "zabac-vg", "chain": "zabac", "name": "Žabac Velika Gorica", "city": "Velika Gorica",
     "address": "Trg grada Vukovara 8", "zabac_location": "Velika Gorica"},
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
    "ktc": {
        "name": "naziv proizvoda", "code": "šifra proizvoda", "brand": "marka proizvoda",
        "qty": "neto količina", "unit": "jedinica mjere", "price": "maloprodajna cijena",
        "unit_price": "cijena za jedinicu mjere",
        "special": "mpc za vrijeme posebnog oblika prodaje",
        "low30": "najniža cijena u posljednjih 30 dana",
        "barcode": "barkod", "category": "kategorija",
    },
    "eurospin": {
        "name": "naziv_proizvoda", "code": "šifra_proizvoda", "brand": "marka_proizvoda",
        "qty": "neto_količina", "unit": "jedinica_mjere", "price": "maloprod.cijena(eur)",
        "unit_price": "cijena_za_jedinicu_mjere",
        "special": "mpc_poseb.oblik_prod",
        "low30": "najniža_mpc_u_30dana",
        "barcode": "barkod", "category": "kategorija_proizvoda",
    },
    "plodine": {
        # zaglavlje je bez dijakritike, a jedinica_mjere je vrsta pakiranja ("KOM"),
        # pa jedinica za cijenu po JM ide iz neto količine ("1 L")
        "name": "naziv proizvoda", "code": "sifra proizvoda", "brand": "marka proizvoda",
        "qty": "neto kolicina", "unit": None, "price": "maloprodajna cijena",
        "unit_price": "cijena po jm",
        "special": "mpc za vrijeme posebnog oblika prodaje",
        "low30": "najniza cijena u poslj. 30 dana",
        "barcode": "barkod", "category": "kategorija proizvoda",
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


_DOWNLOADS = {}


def get_cached(url: str) -> bytes:
    """Isti ZIP dijeli više prodavaonica (Lidl, Eurospin, Plodine) - skida se jednom po pokretanju."""
    if url not in _DOWNLOADS:
        _DOWNLOADS[url] = get(url)
    return _DOWNLOADS[url]


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


def csv_from_zip(raw: bytes, match):
    """CSV prodavaonice iz ZIP-a; ZIP zna biti ugniježđen u ZIP ili imati podfolder.
    match dobiva ime datoteke bez putanje i vraća je li to tražena prodavaonica."""
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for name in z.namelist():
            if name.lower().endswith(".csv") and match(name.rsplit("/", 1)[-1]):
                return z.read(name), name
        for name in z.namelist():
            if name.lower().endswith(".zip"):
                found = csv_from_zip(z.read(name), match)
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
        prefix = f"Supermarket {store['lidl_code']}_"
        try:
            found = csv_from_zip(get_cached(url), lambda n: n.startswith(prefix))
        except (NotAvailable, zipfile.BadZipFile):
            continue
        if found:
            # pravi datum je u imenu CSV-a ("..._18.09.2026_7.15h.csv"), ime ZIP-a je samo naznaka
            m = re.search(r"_(\d{1,2})\.(\d{1,2})\.(\d{4})_", found[1])
            return found[0], dt.date(int(m[3]), int(m[2]), int(m[1])) if m else d, url
    raise NotAvailable("Lidl: nema cjenika za zadnjih %d dana" % DAYS_BACK)


KTC = "https://www.ktc.hr"


def fetch_ktc(store):
    """Stranica po poslovnici nabraja CSV-ove zadnjih tjedana; datum je u imenu datoteke.
    Za isti dan zna biti više objava ("...-1-", "...-2-") - uzima se zadnja."""
    page_html = get(f"{KTC}/cjenici?poslovnica=" + urllib.parse.quote(store["ktc_branch"])).decode("utf-8", "replace")
    files = {}
    for href in set(re.findall(r'href="(/ktcftp/[^"]+\.csv)"', page_html)):
        m = re.search(r"-(\d{4})(\d{2})(\d{2})-\d+\.csv$", href)
        if m:
            files.setdefault(dt.date(int(m[1]), int(m[2]), int(m[3])), []).append(html.unescape(href))
    for d in days():
        for href in sorted(files.get(d, []), reverse=True):
            url = KTC + urllib.parse.quote(href)
            try:
                raw = get(url)
            except NotAvailable:
                continue
            # neke poslovnice objavljuju datoteku sa samim zaglavljem - to nije cjenik
            if decode(raw).strip().count("\n") >= 1:
                return raw, d, url
    raise NotAvailable("KTC: nema cjenika s artiklima za zadnjih %d dana" % DAYS_BACK)


EUROSPIN = "https://www.eurospin.hr/wp-content/themes/eurospin/documenti-prezzi"


def fetch_eurospin(store):
    """Jedan dnevni ZIP sa svim prodavaonicama, ime je predvidivo po datumu."""
    prefix = f"diskontna_prodavaonica-{store['eurospin_code']}-"
    for d in days():
        url = f"{EUROSPIN}/cjenik_{d:%d.%m.%Y}-7.30.zip"
        try:
            found = csv_from_zip(get_cached(url), lambda n: n.startswith(prefix))
        except (NotAvailable, zipfile.BadZipFile):
            continue
        if found:
            return found[0], d, url
    raise NotAvailable("Eurospin: nema cjenika za zadnjih %d dana" % DAYS_BACK)


PLODINE_INDEX = "https://www.plodine.hr/info-o-cijenama"


def plodine_store_code(name: str) -> str:
    """Ime je SUPERMARKET_<adresa>_<pbr>_<grad>_<šifra>_<broj>_<vrijeme>.csv"""
    parts = name.removesuffix(".csv").split("_")
    return parts[-3] if len(parts) > 3 else ""


def fetch_plodine(store):
    """Jedan dnevni ZIP sa svim prodavaonicama; stranica /cjenici je mrtva (403),
    popis je na /info-o-cijenama."""
    page_html = get(PLODINE_INDEX).decode("utf-8", "replace")
    links = {}
    for href in set(re.findall(r'href="([^"]+\.zip)"', page_html)):
        m = re.search(r"cjenici_(\d{2})_(\d{2})_(\d{4})_", href)
        if m:
            links[dt.date(int(m[3]), int(m[2]), int(m[1]))] = html.unescape(href)
    for d in days():
        url = links.get(d)
        if not url:
            continue
        try:
            found = csv_from_zip(get_cached(url), lambda n: plodine_store_code(n) == store["plodine_code"])
        except (NotAvailable, zipfile.BadZipFile):
            continue
        if found:
            return found[0], d, url
    raise NotAvailable("Plodine: nema cjenika za zadnjih %d dana" % DAYS_BACK)


FETCHERS = {"spar": fetch_spar, "konzum": fetch_konzum, "zabac": fetch_zabac, "lidl": fetch_lidl,
            "ktc": fetch_ktc, "eurospin": fetch_eurospin, "plodine": fetch_plodine}


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


UNITS = {"ko": "kom", "ea": "kom", "kom": "kom", "l": "L", "kg": "kg", "g": "g", "ml": "ml"}


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
    if chain in ("spar", "ktc", "eurospin"):
        u = (unit or "").strip()
    elif chain == "konzum":
        parts = (qty or "").split()
        u = parts[-1] if len(parts) > 1 else ""
    elif chain in ("lidl", "plodine"):
        # cijena po jedinici je po kg ili L, ovisno o pakiranju ("800g", "1,5l", "1 L")
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
        # Lidl i Eurospin ponavljaju isti artikl (istu šifru) u više redaka, po jedan za
        # svaki barkod. Ostaje jedan redak, s EAN-13 barkodom ako ga ima (on se poklapa
        # s drugim lancima).
        code = val(row, "code")
        if chain in ("lidl", "eurospin") and code in seen:
            if len(val(row, "barcode")) == 13 and len(items[seen[code]]["barcode"]) != 13:
                items[seen[code]]["barcode"] = val(row, "barcode")
            continue
        seen[code] = len(items)
        qty_raw, unit = val(row, "qty"), val(row, "unit")
        items.append({
            "code": code,
            "name": re.sub(r"\s+", " ", val(row, "name")),
            "brand": val(row, "brand"),
            "qty": clean_qty(qty_raw, unit),
            "price": num(val(row, "price")),
            "unit_price": num(val(row, "unit_price")),
            "unit": unit_label(qty_raw, unit, chain),
            # Eurospin upisuje 0 kad proizvod nije na akciji
            "special": num(val(row, "special")) or None,
            "low30": num(val(row, "low30")),
            "barcode": val(row, "barcode").lstrip("0") or "",
            "category": val(row, "category").strip().capitalize(),
        })
    return items


# --- main ---------------------------------------------------------------------

FIELDS = ["store", "name", "brand", "qty", "price", "unit_price", "unit", "special", "low30", "barcode", "category"]


# code služi za spajanje iste akcije u više prodavaonica istog lanca (Eurospin i Lidl
# imaju jednake cijene u Sisku i Velikoj Gorici, pa bi se inače sve prikazalo dvaput)
SALE_FIELDS = ["store", "code", "name", "brand", "qty", "price", "special", "low30", "unit_price", "unit", "category"]

# Žabac je outlet: prodaje robu s kratkim rokom po sniženoj cijeni, pa u cjeniku
# nema stupca s akcijskom cijenom - nema što označiti kad je cijeli asortiman sniženi.
ZABAC_NOTE = "Cijeli asortiman je sniženi, pa Žabac u cjeniku ne označava pojedinačne akcije. Ovdje su svi artikli."


def collect(store):
    """(info, items) za jednu prodavaonicu; greška se upisuje u info, ne diže se dalje."""
    info = {k: store[k] for k in ("id", "chain", "name", "address", "city") if k in store}
    try:
        raw, date, url = FETCHERS[store["chain"]](store)
        items = parse(raw, store["chain"])
        info.update(date=date.isoformat(), source=url, count=len(items))
        print(f"{store['name']}, {store['address']}: {len(items)} proizvoda, cjenik {date}")
        return info, items
    except Exception as e:  # jedna trgovina ne smije srušiti ostale
        info.update(error=str(e))
        print(f"::warning::{store['name']}, {store['address']}: {e}")
        return info, []


def write(path: Path, data: dict, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    data["generated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Ukupno {len(rows)} redaka -> {path}")


def build_prices(out_dir: Path):
    """Glavna stranica: cijeli cjenik pet trgovina u Velikoj Gorici."""
    stores, rows = [], []
    for i, store in enumerate(STORES):
        info, items = collect(store)
        rows += [[i] + [it[f] for f in FIELDS[1:]] for it in items]
        stores.append(info)
    if not rows:
        print("::error::Nijedan cjenik nije preuzet")
        sys.exit(1)
    write(out_dir / "data.json", {"stores": stores, "fields": FIELDS, "items": rows}, rows)


def build_sale(out_dir: Path):
    """Stranica s akcijama: samo sniženi proizvodi, trgovine u Sisku i Velikoj Gorici."""
    stores, rows = [], []
    for i, store in enumerate(STORES_SALE):
        info, items = collect(store)
        if store["chain"] == "zabac":
            info["note"] = ZABAC_NOTE
            sale = [it for it in items if it["price"]]
        else:
            # Lidl, Plodine i Spar ostave MPC prazan kad je proizvod na akciji, KTC upiše 0 -
            # akcija se prepoznaje po popunjenoj akcijskoj cijeni, ne po usporedbi s MPC-om
            sale = [{**it, "price": it["price"] or None} for it in items if it["special"]]
        info["sale"] = len(sale)
        rows += [[i] + [it[f] for f in SALE_FIELDS[1:]] for it in sale]
        stores.append(info)
    if not rows:
        print("::warning::Akcije: nijedan cjenik nije preuzet, stranica se ne mijenja")
        return
    write(out_dir / "akcije" / "data.json", {"stores": stores, "fields": SALE_FIELDS, "items": rows}, rows)


def main():
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    build_prices(out_dir)
    build_sale(out_dir)


if __name__ == "__main__":
    main()

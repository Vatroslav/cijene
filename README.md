# Cijene - Velika Gorica

Koja od pet trgovina u Velikoj Gorici ima ono što tražim - iz njihovih dnevnih cjenika.

- **Pretraga:** neizrazita ("grčki jogurt" nalazi i "JOG.GRČ.TIP"), relevantno prvo; svaki
  proizvod pokazuje u kojoj trgovini ga ima (i po kojoj cijeni).
- **Popis:** stavke za kupovinu -> koliko ih svaka trgovina ima (npr. Interspar 14/15).
  Popis se čuva u pregledniku (localStorage), ne ide nikamo.

**Aplikacija:** https://vatroslav.github.io/cijene/

| Trgovina | Adresa |
|---|---|
| Žabac | Trg grada Vukovara 8 |
| Spar | Matice hrvatske 22 |
| Interspar | Rakarska ulica 13 |
| Konzum (hipermarket) | Marina Getaldića 1 |
| Lidl | Ul. kneza Ljudevita Posavskog 55 |

## Kako radi

Trgovci su dužni svaki dan do 8:00 objaviti cjenik svake prodavaonice u CSV/XML formatu
(Odluka Vlade o objavi cjenika, NN 75/2025). GitHub Actions svako jutro pokreće
`scripts/fetch.py`, koji preuzme cjenike, složi ih u `site/data.json` i objavi statičnu
stranicu na GitHub Pages. Nema servera, baze ni API ključeva.

Ako današnji cjenik još nije dostupan, uzima se zadnji dostupni (do 7 dana unatrag) - datum
cjenika za svaku trgovinu piše na dnu stranice.

## Lokalno

```bash
python scripts/fetch.py site
python -m http.server 8766 --directory site
```

Samo standardna Python biblioteka, bez ovisnosti.

## Dodavanje trgovine

Nova prodavaonica postojećeg lanca (Spar/Interspar, Konzum, Žabac, Lidl, KTC, Eurospin, Plodine) =
novi unos u `STORES` (ili `STORES_SALE`) u `scripts/fetch.py` sa šifrom prodavaonice iz naziva
datoteke cjenika. Novi lanac traži svoju `fetch_*` funkciju i mapiranje stupaca u `COLUMNS`.

## Akcije - Sisak i Velika Gorica

Druga, zasebna stranica: **https://vatroslav.github.io/cijene/akcije/**

Popis proizvoda koji su danas na akciji, u devet prodavaonica. Prilagođena je starijim
korisnicima na mobitelu (krupan tekst, jak kontrast, veliki gumbi, jedan stupac) i radi kao
PWA - može se dodati na početni zaslon i otvara se kao aplikacija.

| Trgovina | Adresa | Grad |
|---|---|---|
| KTC | Nikole Tesle 12B | Sisak |
| KTC | Zagrebačka 49 | Sisak |
| KTC | Trg kralja Petra Krešimira IV 1 | Velika Gorica |
| Eurospin | Zagrebačka 49G | Sisak |
| Eurospin | Ulica Juraja Dobrile 1C | Velika Gorica |
| Lidl | Zagrebačka 49f | Sisak |
| Lidl | Ul. kneza Ljudevita Posavskog 55 | Velika Gorica |
| Plodine | Ul. kneza Ljudevita Posavskog 47 | Velika Gorica |
| Žabac | Trg grada Vukovara 8 | Velika Gorica |

Proizvod je na akciji kad trgovina u cjeniku popuni akcijsku cijenu; za usporedbu se pokazuje
redovna cijena ili, kad je nema, najniža cijena u zadnjih 30 dana. Žabac je outlet i nema stupac
akcijske cijene - ide sa svim artiklima i napomenom, ispod proizvoda s pravim popustom. KTC u
Velikoj Gorici objavljuje prazan cjenik, pa se prikazuje kao trgovina bez cjenika.

Izbor trgovina i upisana pretraga pamte se u pregledniku (localStorage) i ne idu nikamo.

Ikone se ne generiraju pri svakom objavljivanju - po potrebi ručno:

```bash
python scripts/ikone.py site/akcije
```

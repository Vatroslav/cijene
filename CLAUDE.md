# Cijene

Javni repo: pretraga dnevnih cjenika pet trgovina u Velikoj Gorici (Žabac, Spar Matice
hrvatske 22, Interspar Rakarska 13, Konzum hipermarket Marina Getaldića 1, Lidl Ul. kneza
Ljudevita Posavskog 55). Korisnici su Vatra i
Monika, uglavnom na mobitelu. Opis i pokretanje: `README.md`.

**Cilj je dostupnost, ne cijena** (Vatra, 18.9.2026.): u kojoj trgovini ima sve s popisa i gdje
ima određeni proizvod. Razlike u cijeni su minorne - cijena je sekundarna informacija, ne
isticati "najjeftinije". Pretraga je neizrazita, relevantno prvo.

## "Koja trgovina ima sve s popisa?"
Cijeli postupak je globalni skill `popis` (`~/.claude/skills/popis/SKILL.md`) - ovo je sažetak.
Pokrenuti `python scripts/popis.py --detalji` (default popis "Špeža"; drugi popis kao argument;
određeni proizvod bez OurGroceriesa: `--stavka "grčki jogurt" --detalji --sve`).
Popis čita kroz `~/github/health/scripts/ourgroceries.py` - samo na zahtjev, nikad u petlji.
✓ = proizvod pogađa sve riječi stavke. ~ = samo dio: kandidati su grupirani po pogođenim
riječima (`[zobeno] Alpro Oat Drink`), a pravi pogodak treba **semantički procijeniti** iz
naziva i Vatri odgovoriti po trgovini, a ne prepisati tablicu. Lažni pogoci su česti kod kratica
("baterije" -> "BAT.AIRWICK").

## Arhitektura
- `scripts/fetch.py` - preuzimanje i normalizacija, samo standardna biblioteka. Izlazi
  `site/data.json` i `site/akcije/data.json` (ne commitaju se).
- `scripts/popis.py` - OurGroceries popis -> pokrivenost po trgovini (lokalno, ne ide na stranicu).
- `scripts/ikone.py` - crta ikone stranice s akcijama; pokreće se ručno, PNG-ovi idu u git.
- `site/` - statična aplikacija (vanilla JS), bez build koraka.
- `site/akcije/` - druga stranica: proizvodi na akciji u Sisku i Velikoj Gorici, PWA,
  prilagođena starijim korisnicima na mobitelu (krupan tekst, jak kontrast, veliki gumbi).
  Zasebne datoteke, ne dijeli CSS ni JS s glavnom stranicom.
- `.github/workflows/update.yml` - dnevno preuzimanje + deploy na GitHub Pages (artifact, podaci nisu u gitu).

## Zamke izvora
Kako koji lanac objavljuje cjenike (Konzum 404, Spar 403, Lidl, KTC, Eurospin, Plodine...) je u
`knowledge/zamke-izvora.md`, s oznakom provjere. Pročitati prije izmjene `fetch.py` ili kad
trgovina ne prolazi; nakon žive provjere izvora obnoviti `verified` u tom fileu.

## Pravila
- Ne dodavati ovisnosti ni build korak bez jasnog razloga - jednostavnost je namjerna.
- Nakon izmjene `fetch.py` lokalno pokrenuti `python scripts/fetch.py site` i provjeriti da svih pet trgovina prolazi.

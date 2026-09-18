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
Popis čita kroz `~/github/fitness-coach/scripts/ourgroceries.py` - samo na zahtjev, nikad u petlji.
✓ = proizvod pogađa sve riječi stavke. ~ = samo dio: kandidati su grupirani po pogođenim
riječima (`[zobeno] Alpro Oat Drink`), a pravi pogodak treba **semantički procijeniti** iz
naziva i Vatri odgovoriti po trgovini, a ne prepisati tablicu. Lažni pogoci su česti kod kratica
("baterije" -> "BAT.AIRWICK").

## Arhitektura
- `scripts/fetch.py` - preuzimanje i normalizacija, samo standardna biblioteka. Izlaz `site/data.json` (ne commita se).
- `scripts/popis.py` - OurGroceries popis -> pokrivenost po trgovini (lokalno, ne ide na stranicu).
- `site/` - statična aplikacija (vanilla JS), bez build koraka.
- `.github/workflows/update.yml` - dnevno preuzimanje + deploy na GitHub Pages (artifact, podaci nisu u gitu).

## Poznate zamke izvora (provjereno 18.9.2026.)
- **Konzum:** u linku za preuzimanje razmaci moraju biti `%20` - s `+` server vraća 404.
  Isti link nasumično vraća 404 i kad datoteka postoji (otprilike pola pokušaja), zato `retry_404`.
  Zaglavlje ima tipfeler "posljednih" umjesto "posljednjih".
- **Spar:** stranica s cjenicima vraća 403 skriptama, ali JSON indeks
  `datoteke_cjenici/Cjenik{YYYYMMDD}.json` radi. CSV je u cp1250 i odvojen s `;`, a MPC je prazan kad je proizvod na akciji.
- **Žabac:** HTML stranica `?store=Velika%20Gorica`, datoteke imaju nasumična imena, a datum je u naslovu.
  Nema cijene za jedinicu mjere ni akcijske cijene.
- **Lidl:** jedan ZIP (~55 MB) sa svim trgovinama dnevno, ručno imenovan (datum u imenu ZIP-a
  bez stalnog formata, ponekad bez godine; ZIP zna biti ugniježđen). Prodavaonica VG = `Supermarket 240_`,
  pravi datum je u imenu CSV-a. Isti artikl je u više redaka (po barkodu) - ostaje jedan po šifri.
- Kategorije se razlikuju po lancu: Spar i Konzum imaju 6-8 grubih, Žabac tridesetak finih.

## Pravila
- Ne dodavati ovisnosti ni build korak bez jasnog razloga - jednostavnost je namjerna.
- Nakon izmjene `fetch.py` lokalno pokrenuti `python scripts/fetch.py site` i provjeriti da svih pet trgovina prolazi.

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
- `scripts/fetch.py` - preuzimanje i normalizacija, samo standardna biblioteka. Izlazi
  `site/data.json` i `site/akcije/data.json` (ne commitaju se).
- `scripts/popis.py` - OurGroceries popis -> pokrivenost po trgovini (lokalno, ne ide na stranicu).
- `scripts/ikone.py` - crta ikone stranice s akcijama; pokreće se ručno, PNG-ovi idu u git.
- `site/` - statična aplikacija (vanilla JS), bez build koraka.
- `site/akcije/` - druga stranica: proizvodi na akciji u Sisku i Velikoj Gorici, PWA,
  prilagođena starijim korisnicima na mobitelu (krupan tekst, jak kontrast, veliki gumbi).
  Zasebne datoteke, ne dijeli CSS ni JS s glavnom stranicom.
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

## Zamke izvora za stranicu s akcijama (provjereno 20.9.2026.)
- **Akcija se ne prepoznaje usporedbom cijena.** Lidl, Plodine i Spar ostave MPC prazan kad je
  proizvod na akciji, KTC upiše 0 - akcijska cijena je tad jedina cijena u retku. Proizvod je
  na akciji kad je popunjen stupac akcijske cijene, a za usporedbu služi najniža cijena u 30 dana.
- **KTC:** stranica po poslovnici (`/cjenici?poslovnica=RC SISAK PJ-41`), datum je u imenu CSV-a,
  za isti dan zna biti više objava. Poslovnica u Velikoj Gorici (PJ-8B) svaki dan objavi datoteku
  sa samim zaglavljem, a druga (PJ-83) nijednu - zato se preskaču datoteke bez redaka.
- **Eurospin:** jedan dnevni ZIP, ime je predvidivo (`cjenik_20.09.2026-7.30.zip`). Cijene i
  asortiman su istovjetni u svim prodavaonicama, pa se ista akcija spaja u jedan redak.
- **Plodine:** popis je na `/info-o-cijenama`; stara adresa `/cjenici` vraća 403 i pregledniku.
  Jedan dnevni ZIP sa svim prodavaonicama, šifra prodavaonice je treći element s kraja imena CSV-a.
  Cijene znaju biti pisane bez vodeće nule (`,75`).
- **Žabac** nema stupac akcijske cijene jer je outlet - cijeli asortiman je sniženi. Zato na
  stranici ide sa svim artiklima i napomenom; sortiranje po popustu ga gura ispod pravih akcija.

## Pravila
- Ne dodavati ovisnosti ni build korak bez jasnog razloga - jednostavnost je namjerna.
- Nakon izmjene `fetch.py` lokalno pokrenuti `python scripts/fetch.py site` i provjeriti da svih pet trgovina prolazi.

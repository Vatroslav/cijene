---
verified:
  - by: claude/opus-5.5
    at: 2026-11-25T19:12:00+01:00
    how: python scripts/fetch.py nakon popravka Spara i Plodina (5/5 glavna, 9/9 akcije); Spar CSV 87076 i Interspar 8728 od 25.11. (stupac akcije DA/NE, 2258 i 5511 DA, svi s popunjenim MPC-om); Plodine ZIP 25.11. prodavaonica 140 (bazna cijena = sidrena cijena iz ZIP-a 22.11. na svih 38780 zajedničkih šifri; ZIP 23.11. još sa sidrenom); run 45665214312 (provjera pala na Plodine). Konzum, Lidl, Žabac, KTC i Eurospin prolaze 25.11.
stale_after: 2026-12-02T00:00:00+01:00
---

# Zamke izvora cjenika

Kako lanci objavljuju dnevne cjenike i gdje to odstupa od očekivanog. Pročitati prije izmjene
`scripts/fetch.py` ili kad neka trgovina ne prolazi.

17.11.2026. stupile su na snagu nove odluke o objavi cjenika (NN 101/2026, odgođeno s 1.10. u
NN 110/2026). Konzum i Lidl su istog dana promijenili zaglavlja; rok provjere je kratak jer lanci
mogu još dorađivati format.

## Glavna stranica (pet trgovina u Velikoj Gorici)

- **Konzum:** u linku za preuzimanje razmaci smiju biti `+` ili `%20` - 6.10. oba oblika
  rade jednako (zapis od 18.9. da `+` vraća 404 bio je vjerojatno nasumični 404). Isti link
  nasumično vraća 404 i kad datoteka postoji (6.10.: 23 od 62 pokušaja), zato `retry_404`.
  **Od 17.11.2026. novo zaglavlje**, isti model kao Plodine od 1.10.: nema stupca akcijske
  cijene, najniže cijene u 30 dana ni kategorije. Akcija je `poseban oblik prodaje` = `DA` (uz
  `naziv posebnog oblika prodaje` = "Akcijska prodaja"; 18.11. 4272 od 34153 artikala), a
  `maloprodajna cijena` je tad akcijska cijena. Novi stupac `bazna cijena` jednak je MPC-u u
  22588 redaka - što točno znači nije provjereno, a glavna stranica ga ne koristi.
- **Spar:** Cloudflare vraća 403 zadanom Python User-Agentu; s User-Agentom iz `fetch.py`
  stranica s cjenicima 6.10. radi. Skripta ionako koristi JSON indeks
  `datoteke_cjenici/Cjenik{YYYYMMDD}.json`. CSV je u cp1250 i odvojen s `;`. Do 24.11. MPC je
  bio prazan kad je proizvod na akciji, a akcijska cijena u svom stupcu.
  **Od 25.11.2026. novo zaglavlje**, isti model kao Konzum i Plodine: stupac `mpc za vrijeme
  posebnog oblika prodaje (eur)` nosi oznaku `DA`/`NE`, a `mpc (eur)` je tad akcijska cijena
  (25.11. Spar 2258, Interspar 5511 artikala s `DA`, svi s popunjenim MPC-om). Nema najniže
  cijene u 30 dana ni kategorije; novi stupac je `sidrena cijena (eur)` (broj, ne tekst kao kod
  Lidla), glavna stranica ga ne koristi. Parser čita stupac akcije i kao cijenu i kao oznaku,
  pa radi i ako Spar vrati stari format.
- **Žabac:** HTML stranica `?store=Velika%20Gorica`, datoteke imaju nasumična imena, a datum je
  u naslovu. Nema cijene za jedinicu mjere ni akcijske cijene.
- **Lidl:** od 23.9.2026. cjenici više nisu ZIP na tvrtka.lidl.hr (`/cijene/cijene-u-trgovinama`
  vraća 404, `/cijene` nosi samo mrtve linkove iz kolovoza). Sad je svaki CSV zaseban link na
  `www.lidl.hr/c/cijene/s10073252` (`/explore/assets/webPriceData/hr/Supermarket 240_..._06.10.2026_7.15h.csv`),
  oko 30 dana unatrag za svih 116 prodavaonica, jedan CSV po prodavaonici i danu. Imena imaju
  razmake i dijakritiku, pa se link kodira. Prodavaonica VG = `Supermarket 240_` (Sisak
  `Supermarket 114_`), datum je u imenu CSV-a, CSV je u cp1250 i odvojen zarezom, a isti artikl
  je u više redaka (po barkodu) - ostaje jedan po šifri. CSV od 21.9. objavljen je bez stupca
  `NAZIV` i bez stupaca akcije - Lidlova greška, jednodnevna.
  **Od 17.11.2026. novo zaglavlje:** nema kategorije; `cijena_za_jedinicin_mjere` (Lidlov
  tipfeler) i `najniza_cijena_u_poslj_30_dana` (bez točke). `jedinica_mjere` više nije pakiranje
  ("800g") nego oznaka "g (1kg)", "ml (1 L)", "bez (1 kom.)", "g (100 g)" - u zagradi je jedinica
  cijene po jedinici mjere. `neto_kolicina` je u kg ili L, i kod komadnih artikala ("bez", "kom",
  "komad", oko 60 % redaka) je to težina, ne broj komada - tamo pakiranje ostaje prazno.
  `sidrena_cijena` je tekst ("MPC na 2.5.2025: 1,99€"), ne broj. Akcija i dalje ostavlja MPC
  prazan. 17.11. VG ima 5614 šifri (16.11. 7013) - manje artikala u cjeniku, ne greška parsera.
  **Od 20.11.2026. opet novo zaglavlje:** stupci imaju nastavak `_robe` (`naziv_robe`,
  `sifra_robe` bez dijakritike, `marka_robe`, `maloprodajna_cijena_robe`,
  `cijena_za_jedinicin_mjere_robe`, `barkod_robe`), novi su `ean_barkod_robe` (isti kao
  `barkod_robe` u svim recima 20.11.) i `bazna_cijena_robe` (tekst "MPC na 2.5.2025: 1,99€",
  bivša `sidrena_cijena`). CSV je sad odvojen točka-zarezom, decimale su sa zarezom. Parser
  prihvaća stare i nove nazive.
- Kategorije ima još samo Žabac (22 uže). Konzum i Lidl ih ne objavljuju od 17.11.2026., a
  Spar od 25.11. (do tada svi po 6 grubih).

## Stranica s akcijama (Sisak i Velika Gorica)

- **Akcija se ne prepoznaje usporedbom cijena.** Lidl i Spar ostave MPC prazan kad je proizvod
  na akciji, KTC upiše 0 - akcijska cijena je tad jedina cijena u retku. Proizvod je na akciji
  kad je popunjen stupac akcijske cijene, a za usporedbu služi najniža cijena u 30 dana.
- **KTC:** stranica po poslovnici (`/cjenici?poslovnica=RC SISAK PJ-41`), datum je u imenu CSV-a,
  za isti dan zna biti više objava. Poslovnica u Velikoj Gorici (PJ-8B) objavljuje samo datoteke
  sa samim zaglavljem (zadnja 2.10.), a druga (PJ-83) nijednu - zato se preskaču datoteke bez
  redaka, a KTC Velika Gorica u `fetch.py` ne diže uzbunu kad ne prođe (`"alarm": False`).
  18.11. PJ-8B prvi put ima artikle (1113); jedan dan još nije razlog za vraćanje uzbune. Kad nema
  akcije, KTC u stupac akcijske cijene upiše `0.00`; od 29.9. sisačke poslovnice nemaju nijednu akciju.
- **Eurospin:** jedan dnevni ZIP, ime je predvidivo (`cjenik_06.10.2026-7.30.zip`). Cijene i
  asortiman su istovjetni u svim prodavaonicama, pa se ista akcija spaja u jedan redak.
- **Plodine:** popis je na `/info-o-cijenama`; stara adresa `/cjenici` vraća 403 i s
  User-Agentom preglednika. Jedan dnevni ZIP sa svim prodavaonicama, šifra prodavaonice je treći
  element s kraja imena CSV-a. Cijene znaju biti pisane bez vodeće nule (`,75`).
  **Od 1.10.2026. novo zaglavlje:** nema stupaca akcijske cijene, neto količine, kategorije ni
  najniže cijene u 30 dana. Akcija je oznaka `poseban oblik prodaje` = `DA` (uz `naziv posebnog
  oblika prodaje` = "Akcija"), MPC je tad akcijska cijena, a za usporedbu je tu `sidrena cijena`
  (cijena na dan 2.5.2025.) - na stranici piše kao "cijena na dan 2. svibnja 2025.", ne precrtano.
  Provjereno 6.10. na 126 artikala koji su 30.9. bili bez akcije, a 6.10. na akciji: sidrena
  cijena je u medijanu jednaka redovnoj, za 108 od 126 unutar 5 %. Količina je u imenu
  ("VODA JAMNICA 1 L BOCA"), `jedinica mjere` je KOM ili KG (roba na vagu). CSV sad nabraja i
  artikle kojih u prodavaonici nema (`dostupno nedostupno` = `NEDOSTUPNO`, 6.10. 20157 od 37994
  redaka) - oni se preskaču. ZIP je narastao s ~64 MB na ~180 MB.
  **Od 24.11.2026.** `sidrena cijena` se zove `bazna cijena` - iste vrijednosti (25.11. jednaka
  sidrenoj iz ZIP-a od 22.11. na svih 38780 zajedničkih šifri; ZIP od 23.11. još ima staro
  ime). Parser prihvaća oba naziva. Cjenik od 25.11. ima i stupac `neto kolicina` ("1 L",
  "0,500 L"); parser ga ne koristi, pakiranje i dalje čita iz imena.
- **Žabac** nema stupac akcijske cijene jer je outlet - cijeli asortiman je sniženi. Zato na
  stranici ide sa svim artiklima i napomenom; sortiranje po popustu ga gura ispod pravih akcija.

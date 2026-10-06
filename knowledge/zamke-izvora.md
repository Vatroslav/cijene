---
verified:
  - by: claude/opus-5.5
    at: 2026-10-06T10:54:07+02:00
    how: python scripts/fetch.py (obje stranice); izravno preuzimanje i čitanje CSV-ova svakog lanca (zaglavlja, kodiranje, stupci akcije, broj kategorija); ponovljeni pokušaji Konzumovih linkova s + i %20; indeksne stranice Spar, Lidl, KTC, Plodine, Žabac; logovi GitHub Actions od 18.9.
stale_after: 2026-11-24T00:00:00+01:00
---

# Zamke izvora cjenika

Kako lanci objavljuju dnevne cjenike i gdje to odstupa od očekivanog. Pročitati prije izmjene
`scripts/fetch.py` ili kad neka trgovina ne prolazi.

Rok provjere je kratak namjerno: 17.11.2026. na snagu stupaju nove odluke o objavi cjenika
(NN 101/2026, odgođeno s 1.10. u NN 110/2026), pa lanci mogu ponovno mijenjati format.

## Glavna stranica (pet trgovina u Velikoj Gorici)

- **Konzum:** u linku za preuzimanje razmaci smiju biti `+` ili `%20` - 6.10. oba oblika
  rade jednako (zapis od 18.9. da `+` vraća 404 bio je vjerojatno nasumični 404). Isti link
  nasumično vraća 404 i kad datoteka postoji (6.10.: 23 od 62 pokušaja), zato `retry_404`.
  Zaglavlje ima tipfeler "posljednih" umjesto "posljednjih".
- **Spar:** Cloudflare vraća 403 zadanom Python User-Agentu; s User-Agentom iz `fetch.py`
  stranica s cjenicima 6.10. radi. Skripta ionako koristi JSON indeks
  `datoteke_cjenici/Cjenik{YYYYMMDD}.json`. CSV je u cp1250 i odvojen s `;`, a MPC je prazan kad
  je proizvod na akciji.
- **Žabac:** HTML stranica `?store=Velika%20Gorica`, datoteke imaju nasumična imena, a datum je
  u naslovu. Nema cijene za jedinicu mjere ni akcijske cijene.
- **Lidl:** od 23.9.2026. cjenici više nisu ZIP na tvrtka.lidl.hr (`/cijene/cijene-u-trgovinama`
  vraća 404, `/cijene` nosi samo mrtve linkove iz kolovoza). Sad je svaki CSV zaseban link na
  `www.lidl.hr/c/cijene/s10073252` (`/explore/assets/webPriceData/hr/Supermarket 240_..._06.10.2026_7.15h.csv`),
  oko 30 dana unatrag za svih 116 prodavaonica. **`fetch.py` to još ne zna - Lidl od 23.9. ne
  prolazi.** I dalje vrijedi: prodavaonica VG = `Supermarket 240_` (Sisak `Supermarket 114_`),
  datum je u imenu CSV-a, CSV je u cp1250, a isti artikl je u više redaka (po barkodu) - ostaje
  jedan po šifri.
- Kategorije se razlikuju po lancu: Spar, Konzum i Lidl imaju po 6 grubih, Žabac 22 uže.

## Stranica s akcijama (Sisak i Velika Gorica)

- **Akcija se ne prepoznaje usporedbom cijena.** Lidl i Spar ostave MPC prazan kad je proizvod
  na akciji, KTC upiše 0 - akcijska cijena je tad jedina cijena u retku. Proizvod je na akciji
  kad je popunjen stupac akcijske cijene, a za usporedbu služi najniža cijena u 30 dana.
- **KTC:** stranica po poslovnici (`/cjenici?poslovnica=RC SISAK PJ-41`), datum je u imenu CSV-a,
  za isti dan zna biti više objava. Poslovnica u Velikoj Gorici (PJ-8B) svaki dan objavi datoteku
  sa samim zaglavljem, a druga (PJ-83) nijednu - zato se preskaču datoteke bez redaka. Kad nema
  akcije, KTC u stupac akcijske cijene upiše `0.00`; od 29.9. sisačke poslovnice nemaju nijednu akciju.
- **Eurospin:** jedan dnevni ZIP, ime je predvidivo (`cjenik_06.10.2026-7.30.zip`). Cijene i
  asortiman su istovjetni u svim prodavaonicama, pa se ista akcija spaja u jedan redak.
- **Plodine:** popis je na `/info-o-cijenama`; stara adresa `/cjenici` vraća 403 i s
  User-Agentom preglednika. Jedan dnevni ZIP sa svim prodavaonicama, šifra prodavaonice je treći
  element s kraja imena CSV-a. Cijene znaju biti pisane bez vodeće nule (`,75`).
  **Od 1.10.2026. novo zaglavlje i `fetch.py` ne prolazi:** nema stupaca akcijske cijene, neto
  količine, kategorije ni najniže cijene u 30 dana. Akcija je oznaka `poseban oblik prodaje` = `DA`
  (uz `naziv posebnog oblika prodaje` = "Akcija"), MPC je tad akcijska cijena, a za usporedbu je
  tu `sidrena cijena`.
- **Žabac** nema stupac akcijske cijene jer je outlet - cijeli asortiman je sniženi. Zato na
  stranici ide sa svim artiklima i napomenom; sortiranje po popustu ga gura ispod pravih akcija.

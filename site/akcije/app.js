'use strict';

// Podaci dolaze iz scripts/fetch.py (build_sale). Polja su u data.fields, redci u data.items.
const MJESECI = ['siječnja', 'veljače', 'ožujka', 'travnja', 'svibnja', 'lipnja',
  'srpnja', 'kolovoza', 'rujna', 'listopada', 'studenoga', 'prosinca'];
const KORAK = 30;
const IZBOR = 'akcije-trgovine';

let stores = [];
let items = [];
let vidljivo = KORAK;

const el = (id) => document.getElementById(id);

const eur = (n) => n.toLocaleString('hr-HR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' EUR';

function datum(iso) {
  const d = new Date(iso + 'T00:00');
  return `${d.getDate()}. ${MJESECI[d.getMonth()]} ${d.getFullYear()}.`;
}

// "A", "A i B", "A, B i C"
function nabroji(dijelovi) {
  if (dijelovi.length < 2) return dijelovi.join('');
  return dijelovi.slice(0, -1).join(', ') + ' i ' + dijelovi[dijelovi.length - 1];
}

function bezKvacica(s) {
  return s.toLowerCase()
    .replace(/[čć]/g, 'c').replace(/đ/g, 'd').replace(/š/g, 's').replace(/ž/g, 'z');
}

function ucitajIzbor() {
  try {
    return JSON.parse(localStorage.getItem(IZBOR)) || null;
  } catch (e) {
    return null;
  }
}

function spremiIzbor() {
  const on = stores.filter((s) => s.on).map((s) => s.id);
  try {
    localStorage.setItem(IZBOR, JSON.stringify(on));
  } catch (e) { /* privatni način rada - izbor se jednostavno ne pamti */ }
}

/* --- podaci --- */

function slozi(data) {
  const f = {};
  data.fields.forEach((name, i) => { f[name] = i; });

  stores = data.stores.map((s) => ({ ...s, on: false }));
  const spremljeno = ucitajIzbor();
  stores.forEach((s) => {
    // Žabac je isključen dok ga korisnik ne uključi - nema označenih akcija,
    // pa bi njegovih pet tisuća artikala zatrpalo ostale trgovine.
    s.on = spremljeno ? spremljeno.includes(s.id) : (s.chain !== 'zabac' && !s.error);
  });

  // Ista akcija u dvije prodavaonice istog lanca (Eurospin, Lidl) ide u jedan redak.
  const po = new Map();
  for (const row of data.items) {
    const s = data.stores[row[f.store]];
    const kljuc = `${s.chain}|${row[f.code]}|${row[f.special]}|${row[f.price]}`;
    const postoji = po.get(kljuc);
    if (postoji) {
      postoji.stores.push(row[f.store]);
      continue;
    }
    const special = row[f.special];
    const price = row[f.price];
    const low30 = row[f.low30];
    let ref = null, refLabel = '';
    if (special && price && price > special) {
      ref = price;
      refLabel = 'redovna cijena';
    } else if (special && low30 && low30 > special) {
      ref = low30;
      refLabel = 'najniža cijena u zadnjih 30 dana';
    }
    po.set(kljuc, {
      stores: [row[f.store]],
      name: row[f.name],
      brand: row[f.brand] || '',
      qty: row[f.qty] || '',
      cijena: special || price,
      akcija: !!special,
      ref: ref,
      refLabel: refLabel,
      popust: ref ? Math.round(((ref - special) / ref) * 100) : 0,
      unitPrice: row[f.unit_price],
      unit: row[f.unit] || '',
      trazi: bezKvacica(`${row[f.name]} ${row[f.brand] || ''}`),
    });
  }

  items = [...po.values()].sort((a, b) => b.popust - a.popust || a.name.localeCompare(b.name, 'hr'));
}

// Dvije KTC prodavaonice u Sisku zovu se isto - tad u naziv ide i ulica.
function oznaka(i) {
  const s = stores[i];
  const istoime = stores.filter((x) => x.name === s.name).length > 1;
  return istoime ? `${s.name}, ${s.address}` : s.name;
}

function odabrane() {
  return new Set(stores.map((s, i) => (s.on ? i : -1)).filter((i) => i >= 0));
}

function filtrirani() {
  const on = odabrane();
  const rijeci = bezKvacica(el('q').value.trim()).split(/\s+/).filter(Boolean);
  return items.filter((it) => {
    if (!it.stores.some((i) => on.has(i))) return false;
    return rijeci.every((r) => it.trazi.includes(r));
  });
}

/* --- prikaz --- */

function kartica(it) {
  const li = document.createElement('li');
  li.className = 'item';

  const ime = document.createElement('p');
  ime.className = 'name';
  ime.textContent = it.name;
  li.append(ime);

  const detalj = [it.brand, it.qty].filter(Boolean).join(' - ');
  if (detalj) {
    const m = document.createElement('p');
    m.className = 'meta';
    m.textContent = detalj;
    li.append(m);
  }

  const gdje = document.createElement('p');
  gdje.className = 'store';
  gdje.textContent = nabroji([...new Set(it.stores.map((i) => oznaka(i)))]);
  li.append(gdje);

  const red = document.createElement('div');
  red.className = 'prices';
  const sad = document.createElement('span');
  sad.className = 'now';
  if (!it.akcija) sad.style.color = 'var(--text)';
  sad.textContent = it.cijena == null ? 'nema cijene' : eur(it.cijena);
  red.append(sad);
  if (it.popust >= 1) {
    const badge = document.createElement('span');
    badge.className = 'off';
    badge.textContent = `-${it.popust}%`;
    red.append(badge);
  }
  li.append(red);

  if (it.ref) {
    const prije = document.createElement('p');
    prije.className = 'was';
    // precrtano samo kad je to stvarno redovna cijena; najniža cijena u 30 dana
    // je zakonska referenca, ne cijena od jučer, pa se ne precrtava
    prije.append(`${it.refLabel}: `);
    const iznos = document.createElement(it.refLabel === 'redovna cijena' ? 's' : 'b');
    iznos.textContent = eur(it.ref);
    prije.append(iznos);
    li.append(prije);
  }

  if (it.unitPrice && it.unit) {
    const jm = document.createElement('p');
    jm.className = 'per';
    jm.textContent = `${eur(it.unitPrice)} po ${it.unit}`;
    li.append(jm);
  }
  return li;
}

function crtaj() {
  const lista = filtrirani();
  const ul = el('results');
  ul.textContent = '';
  lista.slice(0, vidljivo).forEach((it) => ul.append(kartica(it)));
  el('more').hidden = lista.length <= vidljivo;

  const naAkciji = lista.filter((it) => it.akcija).length;
  if (!stores.some((s) => s.on)) {
    el('status').textContent = 'Nijedna trgovina nije odabrana. Otvori "Odaberi trgovine".';
  } else if (!lista.length) {
    el('status').textContent = 'Nema proizvoda koji odgovaraju pretrazi.';
  } else {
    el('status').textContent = `${naAkciji} ${naAkciji === 1 ? 'proizvod' : 'proizvoda'} na akciji`
      + (lista.length > naAkciji ? ` i ${lista.length - naAkciji} iz Žapca` : '');
  }

  const zabac = stores.find((s) => s.chain === 'zabac' && s.on && s.note);
  el('note').hidden = !zabac;
  if (zabac) el('note').textContent = zabac.note;
}

function crtajTrgovine() {
  const box = el('stores');
  box.textContent = '';
  stores.forEach((s, i) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip' + (s.error ? ' err' : '');
    b.setAttribute('aria-pressed', String(s.on));
    const naziv = document.createElement('span');
    naziv.className = 'chipName';
    naziv.append(s.name);
    const ulica = document.createElement('small');
    ulica.textContent = s.address;
    naziv.append(ulica);
    const broj = document.createElement('small');
    broj.className = 'chipCount';
    broj.textContent = s.error ? 'nema cjenika' : `${s.sale}`;
    b.append(naziv, broj);
    b.addEventListener('click', () => {
      stores[i].on = !stores[i].on;
      b.setAttribute('aria-pressed', String(stores[i].on));
      spremiIzbor();
      vidljivo = KORAK;
      crtaj();
    });
    box.append(b);
  });
}

function podnozje(data) {
  const s = stores.filter((x) => x.date);
  const datumi = [...new Set(s.map((x) => x.date))].sort();
  el('updated').textContent = datumi.length
    ? `Cjenici od ${datum(datumi[datumi.length - 1])}`
    : 'Cjenici nisu dostupni';
  const greske = stores.filter((x) => x.error).map((x) => `${x.name} (${x.address})`);
  el('sources').textContent = greske.length
    ? `Bez cjenika: ${nabroji(greske)}.`
    : '';
}

/* --- pokretanje --- */

async function start() {
  el('filtersToggle').addEventListener('click', () => {
    const open = el('filters').hidden;
    el('filters').hidden = !open;
    el('filtersToggle').setAttribute('aria-expanded', String(open));
  });
  el('allStores').addEventListener('click', () => {
    stores.forEach((s) => { s.on = !s.error; });
    crtajTrgovine();
    spremiIzbor();
    vidljivo = KORAK;
    crtaj();
  });
  el('q').addEventListener('input', () => { vidljivo = KORAK; crtaj(); });
  el('more').addEventListener('click', () => { vidljivo += KORAK; crtaj(); });

  try {
    const r = await fetch('data.json', { cache: 'no-cache' });
    if (!r.ok) throw new Error(r.status);
    const data = await r.json();
    slozi(data);
    crtajTrgovine();
    podnozje(data);
    crtaj();
  } catch (e) {
    el('status').textContent = 'Cjenici se trenutno ne mogu učitati. Pokušaj kasnije.';
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => { /* bez offline načina, stranica i dalje radi */ });
  }
}

start();

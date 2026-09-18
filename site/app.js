// Pretraga dnevnih cjenika i provjera popisa. Podaci: data.json (generira scripts/fetch.py).
// Proizvodi se grupiraju po barkodu, pa jedna kartica pokazuje ima li proizvod u svakoj trgovini.

const PAGE = 60;
const $ = (id) => document.getElementById(id);
const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d");
const words = (s) => norm(s).split(/[^a-z0-9]+/).filter(Boolean);
const eur = (n) => n.toLocaleString("hr-HR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const store_ = (k, v) => localStorage.setItem(k, JSON.stringify(v));
const load_ = (k, d) => JSON.parse(localStorage.getItem(k) || "null") ?? d;

let stores = [], products = [], byBarcode = new Map(), shown = PAGE;
const active = new Set(load_("stores", []));
let list = load_("popis", []);   // [{q}] ili [{barcode, name}]

async function load() {
  const data = await (await fetch("data.json", { cache: "no-cache" })).json();
  stores = data.stores;
  if (!active.size) stores.forEach((_, i) => active.add(i));
  const F = Object.fromEntries(data.fields.map((f, i) => [f, i]));
  const byKey = new Map();
  const cats = new Set();
  for (const r of data.items) {
    const key = r[F.barcode] || `${r[F.store]}:${r[F.name]}`;
    let p = byKey.get(key);
    if (!p) {
      p = { name: r[F.name], brand: r[F.brand], qty: r[F.qty], barcode: r[F.barcode], cats: new Set(), offers: new Map() };
      byKey.set(key, p);
    }
    if (r[F.category]) { p.cats.add(r[F.category]); cats.add(r[F.category]); }
    const price = r[F.price], special = r[F.special];
    p.offers.set(r[F.store], {
      price, special,
      now: special != null && (price == null || special < price) ? special : price,
      unitPrice: r[F.unit_price], unit: r[F.unit], name: r[F.name],
    });
  }
  products = [...byKey.values()];
  for (const p of products) {
    p.words = [...new Set(words([p.name, p.brand, ...[...p.offers.values()].map((o) => o.name)].join(" ")))];
    p.first = words(p.name)[0] || "";
    if (p.barcode) byBarcode.set(p.barcode, p);
  }
  const sel = $("category");
  [...cats].sort((a, b) => a.localeCompare(b, "hr")).forEach((c) => sel.add(new Option(c, c)));
  renderStores();
  renderSources(data.generated);
  renderAll();
}

// --- zajedničko -----------------------------------------------------------------

const activeStores = () => stores.map((_, i) => i).filter((i) => active.has(i));
const termsOf = (q) => words(q);

// --- neizrazita pretraga ----------------------------------------------------------
// Cjenici pišu nazive skraćeno i velikim slovima ("JOG.GRČ.TIP"), pa se svaki upisani
// pojam uspoređuje sa svakom riječi naziva. Bodovi: 3 ista riječ, 2 riječ počinje pojmom,
// 1.5 kratica (pojam počinje riječju "jog" / "grč"), 1.2 isti korijen ("grčki" / "grčkog"),
// 1 pojam unutar riječi ili jedno slovo razlike. Proizvod mora pogoditi sve pojmove.

function commonPrefix(a, b) {
  let i = 0;
  while (i < a.length && i < b.length && a[i] === b[i]) i++;
  return i;
}

function oneEdit(a, b) {   // udaljenost uređivanja <= 1
  if (Math.abs(a.length - b.length) > 1) return false;
  let i = 0, j = 0, edits = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) { i++; j++; continue; }
    if (++edits > 1) return false;
    if (a.length > b.length) i++; else if (b.length > a.length) j++; else { i++; j++; }
  }
  return edits + (a.length - i) + (b.length - j) <= 1;
}

function termScore(t, w) {
  if (w === t) return 3;
  if (w.startsWith(t)) return 2;
  if (w.length >= 3 && t.startsWith(w)) return 1.5;
  if (t.length >= 4 && w.length >= 4 && commonPrefix(t, w) >= Math.max(4, Math.min(t.length, w.length) - 2)) return 1.2;
  if (t.length >= 3 && w.includes(t)) return 1;
  if (t.length >= 5 && oneEdit(t, w)) return 1;
  return 0;
}

// min: najmanji bodovi po pojmu (popis traži strože podudaranje od pretrage)
function score(p, terms, min = 1) {
  if (terms.length === 1 && /^\d{8,}$/.test(terms[0])) return p.barcode === terms[0].replace(/^0+/, "") ? 10 : 0;
  let total = 0;
  for (const t of terms) {
    let best = 0;
    for (const w of p.words) {
      const s = termScore(t, w);
      if (s > best) best = s;
      if (best === 3) break;
    }
    if (best < min) return 0;
    total += best;
  }
  // naziv koji počinje traženim pojmom ("JOGURT GRČKI") ide ispred "SLAD. GRČKI JOGURT"
  if (terms.some((t) => termScore(t, p.first) >= 1.5)) total += 1;
  return total;
}

function renderStores() {
  $("stores").innerHTML = "";
  stores.forEach((s, i) => {
    const b = document.createElement("button");
    b.className = "chip" + (active.has(i) ? " on" : "") + (s.error ? " err" : "");
    b.textContent = s.name;
    b.title = s.error ? `Cjenik nije preuzet: ${s.error}` : `${s.address}, cjenik ${fmtDate(s.date)}`;
    b.onclick = () => {
      active.has(i) ? active.delete(i) : active.add(i);
      store_("stores", [...active]);
      renderStores(); shown = PAGE; renderAll();
    };
    $("stores").append(b);
  });
}

function fmtDate(iso) {
  const [y, m, d] = iso.split("-");
  return `${+d}.${+m}.${y}.`;
}

function renderSources(generated) {
  const items = stores.map((s) => s.error
    ? `${s.name} (${s.address}): cjenik trenutno nedostupan`
    : `<a href="${s.source}">${s.name}</a> (${s.address}): cjenik ${fmtDate(s.date)}`);
  $("sources").innerHTML = `Izvor: javni cjenici trgovaca (NN 75/2025). ${items.join(" · ")} · ` +
    `Osvježeno ${new Date(generated).toLocaleString("hr-HR")}.`;
}

function renderAll() { renderSearch(); renderList(); }

// --- pretraga -------------------------------------------------------------------

function renderSearch() {
  const terms = termsOf($("q").value);
  const cat = $("category").value, sale = $("sale").checked, sort = $("sort").value;
  const ul = $("results");
  ul.innerHTML = "";
  $("more").hidden = true;
  if (!terms.length && !cat && !sale) {
    $("status").textContent = `${products.length.toLocaleString("hr-HR")} proizvoda u cjenicima. Upiši što tražiš.`;
    return;
  }
  const act = activeStores();
  const hits = [];
  const perStore = new Map(act.map((i) => [i, 0]));
  for (const p of products) {
    if (cat && !p.cats.has(cat)) continue;
    const sc = terms.length ? score(p, terms) : 1;
    if (!sc) continue;
    const offers = act.map((i) => p.offers.get(i)).filter((o) => o && o.now != null);
    if (!offers.length) continue;
    if (sale && !offers.some((o) => o.special != null)) continue;
    act.forEach((i) => { if (p.offers.has(i)) perStore.set(i, perStore.get(i) + 1); });
    hits.push({ p, sc, n: offers.length, min: Math.min(...offers.map((o) => o.now)), unit: Math.min(...offers.map((o) => o.unitPrice ?? Infinity)) });
  }
  if (sort === "rel") hits.sort((a, b) => b.sc - a.sc || b.n - a.n || a.p.name.length - b.p.name.length);
  if (sort === "price") hits.sort((a, b) => a.min - b.min);
  if (sort === "unit") hits.sort((a, b) => a.unit - b.unit);
  if (sort === "name") hits.sort((a, b) => a.p.name.localeCompare(b.p.name, "hr"));

  $("status").innerHTML = hits.length
    ? `${hits.length.toLocaleString("hr-HR")} proizvoda: ` + act.map((i) => `${esc(stores[i].name)} <b>${perStore.get(i)}</b>`).join(" · ")
    : "Ništa nije pronađeno.";
  for (const h of hits.slice(0, shown)) ul.append(card(h.p, act));
  $("more").hidden = hits.length <= shown;
}

function card(p, act) {
  const li = document.createElement("li");
  li.className = "product";
  const meta = [p.brand, p.qty, p.barcode].filter(Boolean).join(" · ");
  const rows = act.map((i) => {
    const o = p.offers.get(i);
    if (!o || o.now == null) return `<tr class="none"><td>${stores[i].name}</td><td class="price">nema</td><td class="unit"></td></tr>`;
    const onSale = o.special != null && o.price != null && o.special < o.price;
    const price = onSale ? `<span class="old">${eur(o.price)}</span><span class="salep">${eur(o.now)}</span>` : eur(o.now);
    const unit = o.unitPrice != null && o.unit ? `${eur(o.unitPrice)}/${o.unit}` : "";
    const tag = o.special != null ? `<span class="tag">akcija</span>` : "";
    return `<tr><td><span class="yes">✓</span> ${stores[i].name}${tag}</td><td class="price">${price}</td><td class="unit">${unit}</td></tr>`;
  }).join("");
  const onList = p.barcode && list.some((it) => it.barcode === p.barcode);
  li.innerHTML = `<div class="phead"><div><div class="pname"></div><div class="pmeta"></div></div>` +
    (p.barcode ? `<button class="addp${onList ? " done" : ""}">${onList ? "Na popisu" : "+ Popis"}</button>` : "") +
    `</div><table>${rows}</table>`;
  li.querySelector(".pname").textContent = p.name;
  li.querySelector(".pmeta").textContent = meta;
  const btn = li.querySelector(".addp");
  if (btn && !onList) btn.onclick = () => {
    addItems([{ barcode: p.barcode, name: p.name }]);
    btn.textContent = "Na popisu"; btn.classList.add("done"); btn.onclick = null;
  };
  return li;
}

// --- popis ----------------------------------------------------------------------

function addItems(items) {
  for (const it of items) {
    const dup = it.barcode ? list.some((x) => x.barcode === it.barcode) : list.some((x) => x.q && norm(x.q) === norm(it.q));
    if (!dup) list.push(it);
  }
  store_("popis", list);
  renderList();
}

// Za svaku stavku: u kojim trgovinama postoji (i koliko proizvoda odgovara upitu).
function coverageOf(it, act) {
  const counts = new Map(act.map((i) => [i, 0]));
  if (it.barcode) {
    const p = byBarcode.get(it.barcode);
    if (p) act.forEach((i) => { if (p.offers.has(i)) counts.set(i, 1); });
  } else {
    const terms = termsOf(it.q);
    if (terms.length) for (const p of products) {
      if (!score(p, terms, 1.5)) continue;
      for (const i of act) if (p.offers.has(i)) counts.set(i, counts.get(i) + 1);
    }
  }
  return counts;
}

function renderList() {
  $("listCount").textContent = list.length ? `(${list.length})` : "";
  if (!products.length) return;
  const act = activeStores();
  const table = $("listTable");
  $("clearList").hidden = !list.length;
  if (!list.length) {
    $("coverage").innerHTML = `<p class="hint">Popis je prazan. Dodaj stavke gore ili gumbom "+ Popis" u pretrazi.</p>`;
    table.innerHTML = "";
    return;
  }
  const cov = list.map((it) => coverageOf(it, act));
  const have = act.map((i) => cov.filter((c) => c.get(i) > 0).length);
  const best = Math.max(...have);
  $("coverage").innerHTML = act.map((i, k) =>
    `<div class="cov${have[k] === list.length ? " full" : have[k] === best ? " best" : ""}">` +
    `<b>${stores[i].name}</b><span>${have[k]}/${list.length}</span></div>`).join("");

  table.innerHTML = `<tr><th></th>${act.map((i) => `<th>${esc(stores[i].name)}</th>`).join("")}<th></th></tr>` +
    list.map((it, n) => {
      const label = it.barcode ? `${esc(it.name)} <span class="pmeta">barkod</span>` : esc(it.q);
      const cells = act.map((i) => {
        const c = cov[n].get(i);
        return c ? `<td class="yes" title="${it.barcode ? "" : c + " proizvoda"}">✓</td>` : `<td class="no">-</td>`;
      }).join("");
      return `<tr><td class="item" data-n="${n}">${label}</td>${cells}<td><button class="del" data-n="${n}" title="Makni">×</button></td></tr>`;
    }).join("");
}

$("listTable").addEventListener("click", (e) => {
  const n = +e.target.closest("[data-n]")?.dataset.n;
  if (Number.isNaN(n)) return;
  if (e.target.classList.contains("del")) {
    list.splice(n, 1); store_("popis", list); renderList();
  } else {
    const it = list[n];   // klik na stavku = pretraga s tim upitom
    $("q").value = it.barcode || it.q;
    show("search"); shown = PAGE; renderSearch();
  }
});

function addFromInput() {
  const lines = $("newItem").value.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
  if (!lines.length) return;
  addItems(lines.map((q) => ({ q })));
  $("newItem").value = "";
  $("newItem").rows = 1;
}
$("addItem").onclick = addFromInput;
$("newItem").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); addFromInput(); } });
$("newItem").addEventListener("input", (e) => { e.target.rows = Math.min(8, e.target.value.split("\n").length); });
$("clearList").onclick = () => { if (confirm("Obrisati cijeli popis?")) { list = []; store_("popis", list); renderList(); } };

// --- navigacija -----------------------------------------------------------------

function show(view) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("on", t.dataset.view === view));
  $("searchBar").hidden = $("searchView").hidden = view !== "search";
  $("listBar").hidden = $("listView").hidden = view !== "list";
  location.hash = view === "list" ? "popis" : "";
}
document.querySelectorAll(".tab").forEach((t) => t.onclick = () => show(t.dataset.view));
if (location.hash === "#popis") show("list");

let timer;
$("q").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { shown = PAGE; renderSearch(); }, 150); });
["category", "sort", "sale"].forEach((id) => $(id).addEventListener("change", () => { shown = PAGE; renderSearch(); }));
$("more").onclick = () => { shown += PAGE; renderSearch(); };

load().catch((e) => { $("status").textContent = "Cjenici se nisu učitali: " + e.message; });

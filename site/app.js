// Pretraga dnevnih cjenika. Podaci: data.json (generira scripts/fetch.py).
// Proizvodi se grupiraju po barkodu, pa jedan redak pokazuje cijenu u svim trgovinama.

const PAGE = 60;
const $ = (id) => document.getElementById(id);
const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d");
const eur = (n) => n.toLocaleString("hr-HR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";

let stores = [], products = [], shown = PAGE;
const active = new Set(JSON.parse(localStorage.getItem("stores") || "null") || []);

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
      p = { name: r[F.name], brand: r[F.brand], qty: r[F.qty], barcode: r[F.barcode], cats: new Set(), offers: [] };
      byKey.set(key, p);
    }
    if (r[F.category]) { p.cats.add(r[F.category]); cats.add(r[F.category]); }
    const price = r[F.price], special = r[F.special];
    p.offers.push({
      store: r[F.store], price, special,
      now: special != null && (price == null || special < price) ? special : price,
      unitPrice: r[F.unit_price], unit: r[F.unit], low30: r[F.low30],
      name: r[F.name],
    });
  }
  products = [...byKey.values()];
  for (const p of products) {
    p.text = norm([p.name, p.brand, p.barcode, ...p.offers.map((o) => o.name)].join(" "));
  }
  const sel = $("category");
  [...cats].sort((a, b) => a.localeCompare(b, "hr")).forEach((c) => sel.add(new Option(c, c)));
  renderStores();
  renderSources(data.generated);
  render();
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
      localStorage.setItem("stores", JSON.stringify([...active]));
      renderStores(); shown = PAGE; render();
    };
    $("stores").append(b);
  });
}

function fmtDate(iso) {
  const [y, m, d] = iso.split("-");
  return `${+d}.${+m}.${y}.`;
}

function renderSources(generated) {
  const list = stores.map((s) => s.error
    ? `${s.name} (${s.address}): cjenik trenutno nedostupan`
    : `<a href="${s.source}">${s.name}</a> (${s.address}): cjenik ${fmtDate(s.date)}`);
  $("sources").innerHTML = `Izvor: javni cjenici trgovaca (NN 75/2025). ${list.join(" · ")}. ` +
    `Osvježeno ${new Date(generated).toLocaleString("hr-HR")}.`;
}

function render() {
  const q = norm($("q").value.trim());
  const terms = q.split(/\s+/).filter(Boolean);
  const cat = $("category").value, sale = $("sale").checked, sort = $("sort").value;
  const ul = $("results");
  ul.innerHTML = "";
  $("more").hidden = true;
  if (!terms.length && !cat && !sale) {
    $("status").textContent = `${products.length.toLocaleString("hr-HR")} proizvoda u cjenicima. Upiši što tražiš.`;
    return;
  }
  const hits = [];
  for (const p of products) {
    if (cat && !p.cats.has(cat)) continue;
    if (!terms.every((t) => p.text.includes(t))) continue;
    const offers = p.offers.filter((o) => active.has(o.store) && o.now != null);
    if (!offers.length) continue;
    if (sale && !offers.some((o) => o.special != null)) continue;
    offers.sort((a, b) => a.now - b.now);
    hits.push({ p, offers });
  }
  const unitOf = (h) => Math.min(...h.offers.map((o) => o.unitPrice ?? Infinity));
  if (sort === "price") hits.sort((a, b) => a.offers[0].now - b.offers[0].now);
  if (sort === "unit") hits.sort((a, b) => unitOf(a) - unitOf(b));
  if (sort === "name") hits.sort((a, b) => a.p.name.localeCompare(b.p.name, "hr"));

  $("status").textContent = hits.length ? `${hits.length.toLocaleString("hr-HR")} proizvoda` : "Ništa nije pronađeno.";
  for (const h of hits.slice(0, shown)) ul.append(card(h));
  $("more").hidden = hits.length <= shown;
}

function card({ p, offers }) {
  const li = document.createElement("li");
  li.className = "product";
  const meta = [p.brand, p.qty, p.barcode].filter(Boolean).join(" · ");
  const multi = offers.length > 1;
  const rows = offers.map((o, i) => {
    const onSale = o.special != null && o.price != null && o.special < o.price;
    const price = onSale ? `<span class="old">${eur(o.price)}</span><span class="salep">${eur(o.now)}</span>` : eur(o.now);
    const unit = o.unitPrice != null && o.unit ? `${eur(o.unitPrice)}/${o.unit}` : "";
    const tag = o.special != null ? `<span class="tag">akcija</span>` : "";
    const best = multi && i === 0 && o.now < offers[offers.length - 1].now ? "best" : "";
    return `<tr class="${best}"><td class="store">${stores[o.store].name}${tag}</td><td class="price">${price}</td><td class="unit">${unit}</td></tr>`;
  }).join("");
  li.innerHTML = `<div class="pname"></div><div class="pmeta"></div><table>${rows}</table>`;
  li.querySelector(".pname").textContent = p.name;
  li.querySelector(".pmeta").textContent = meta;
  return li;
}

let timer;
$("q").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { shown = PAGE; render(); }, 150); });
["category", "sort", "sale"].forEach((id) => $(id).addEventListener("change", () => { shown = PAGE; render(); }));
$("more").onclick = () => { shown += PAGE; render(); };

load().catch((e) => { $("status").textContent = "Cjenici se nisu učitali: " + e.message; });

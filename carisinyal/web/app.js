const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const pct = (v, d = 1) => (v == null ? "-" : (v * 100).toFixed(d) + "%");
const num = (v, d = 2) => (v == null ? "-" : Number(v).toLocaleString("id-ID", { maximumFractionDigits: d }));
const warna = (v) => (v > 0 ? "naik" : v < 0 ? "turun" : "");
const C = { aksen: "#f0a43a", naik: "#2ec27e", turun: "#e5534b", biru: "#4c9aff", redup: "#7d8a97", garis: "#222a33" };

const simpan = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
const ambil = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };

function status(teks, error = false) {
  $("#status").textContent = teks;
  $("#status").className = error ? "error" : "";
}

async function api(path, body) {
  status("memuat " + path.split("?")[0].replace("/api/", "") + "...");
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  const j = await r.json();
  if (!r.ok) { status(j.error, true); throw new Error(j.error); }
  status("");
  return j;
}

const q = (o) => "?" + new URLSearchParams(o).toString();
const sym = () => $("#simbol").value.trim().toUpperCase();
const rentang = () => $("#rentang").value;

Chart.defaults.color = C.redup;
Chart.defaults.borderColor = C.garis;
Chart.defaults.font.size = 11;
Chart.defaults.animation = false;
const charts = {};

function grafik(id, config) {
  charts[id]?.destroy();
  const dasar = {
    responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
    elements: { point: { radius: 0 }, line: { borderWidth: 1.5 } },
    plugins: { legend: { labels: { boxWidth: 10 } } },
    scales: { x: { ticks: { maxTicksLimit: 8, maxRotation: 0 } } },
  };
  charts[id] = new Chart($("#" + id), { ...config, options: { ...dasar, ...config.options } });
}

const garis = (label, data, color, extra = {}) => ({ label, data, borderColor: color, backgroundColor: color, ...extra });

function kartu(el, isi) {
  $(el).innerHTML = isi.map(([k, v, cls = "", sub = ""]) =>
    `<div><small>${esc(k)}</small><b class="${cls}">${v}</b> <i>${sub}</i></div>`).join("");
}

function tabel(el, kepala, baris) {
  $(el).innerHTML = `<tr>${kepala.map((h) => `<th class="${h.n ? "n" : ""}">${esc(h.t ?? h)}</th>`).join("")}</tr>` +
    baris.map((b) => `<tr>${b.map((c, i) => `<td class="${kepala[i].n ? "n" : ""}">${c}</td>`).join("")}</tr>`).join("");
}

// ---------- Pasar ----------
async function muatPasar() {
  const d = await api("/api/pasar" + q({ simbol: sym(), rentang: rentang() }));
  const r = d.ringkasan;
  kartu("#kartu-pasar", [
    [sym(), num(r.terakhir), "", r.tanggal],
    ["1 hari", pct(r.ret_1h, 2), warna(r.ret_1h)],
    ["1 bulan", pct(r.ret_1bln), warna(r.ret_1bln)],
    ["Volatilitas tahunan", pct(r.vol_tahunan)],
    ["RSI", num(d.rsi.at(-1), 1), d.rsi.at(-1) > 70 ? "turun" : d.rsi.at(-1) < 30 ? "naik" : ""],
  ]);
  grafik("c-harga", { type: "line", data: { labels: d.tanggal, datasets: [
    garis("Harga", d.close, "#d7dde4"),
    garis("SMA 20", d.sma20, C.aksen, { borderWidth: 1 }),
    garis("SMA 50", d.sma50, C.biru, { borderWidth: 1 }),
    garis("BB atas", d.bb_atas, "rgba(125,138,151,.5)", { borderWidth: 1, borderDash: [3, 3] }),
    garis("BB bawah", d.bb_bawah, "rgba(125,138,151,.5)", { borderWidth: 1, borderDash: [3, 3] }),
  ] } });
  grafik("c-rsi", { type: "line", data: { labels: d.tanggal, datasets: [garis("RSI", d.rsi, C.aksen)] },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { maxTicksLimit: 6, maxRotation: 0 } }, y: { min: 0, max: 100, ticks: { stepSize: 30 } } } } });
  grafik("c-macd", { data: { labels: d.tanggal, datasets: [
    { type: "bar", label: "Histogram", data: d.macd_hist, backgroundColor: d.macd_hist.map((v) => (v >= 0 ? C.naik : C.turun)) },
    { type: "line", ...garis("MACD", d.macd, C.biru) }, { type: "line", ...garis("Sinyal", d.macd_sinyal, C.aksen) },
  ] } });
}

function spark(data) {
  const v = data.filter((x) => x != null), lo = Math.min(...v), hi = Math.max(...v);
  const p = v.map((x, i) => `${(i / (v.length - 1)) * 70},${22 - ((x - lo) / (hi - lo || 1)) * 20 - 1}`).join(" ");
  return `<svg class="spark" viewBox="0 0 70 22"><polyline fill="none" stroke="${v.at(-1) >= v[0] ? C.naik : C.turun}" stroke-width="1.2" points="${p}"/></svg>`;
}

let watch = ambil("watchlist", ["BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK", "^JKSE", "AAPL", "BTC-USD"]);
async function muatWatchlist() {
  if (!watch.length) return ($("#wl").innerHTML = "");
  const d = await api("/api/watchlist" + q({ simbol: watch.join(",") }));
  $("#wl").innerHTML = d.map((w) => w.error
    ? `<tr data-s="${esc(w.simbol)}"><td>${esc(w.simbol)}</td><td colspan="3" class="turun">gagal</td><td class="x" data-hapus>×</td></tr>`
    : `<tr data-s="${esc(w.simbol)}"><td>${esc(w.simbol)}</td><td>${spark(w.spark)}</td><td class="n">${num(w.terakhir)}</td>
       <td class="n ${warna(w.ret_1h)}">${pct(w.ret_1h, 2)}</td><td class="x" data-hapus title="hapus">×</td></tr>`).join("");
}
$("#wl").onclick = (e) => {
  const tr = e.target.closest("tr");
  if (!tr) return;
  if (e.target.hasAttribute("data-hapus")) {
    watch = watch.filter((s) => s !== tr.dataset.s); simpan("watchlist", watch); tr.remove(); return;
  }
  $("#simbol").value = tr.dataset.s; muatTab();
};
$("#wl-form").onsubmit = (e) => {
  e.preventDefault();
  const s = $("#wl-input").value.trim().toUpperCase();
  if (s && !watch.includes(s)) { watch.push(s); simpan("watchlist", watch); muatWatchlist(); }
  $("#wl-input").value = "";
};

// ---------- Makro ----------
const PRESET = [
  ["Yield US 10th", "fred", "DGS10"], ["Fed funds", "fred", "FEDFUNDS"], ["Inflasi US (CPI)", "fred", "CPIAUCSL"],
  ["Pengangguran US", "fred", "UNRATE"], ["USD/IDR", "yahoo", "IDR=X"], ["Emas", "yahoo", "GC=F"], ["Harga minyak WTI", "fred", "DCOILWTICO"],
  ["PDB Indonesia %", "wb", "NY.GDP.MKTP.KD.ZG"], ["Inflasi Indonesia %", "wb", "FP.CPI.TOTL.ZG"],
  ["Ekspor % PDB Indonesia", "wb", "NE.EXP.GNFS.ZS"],
];
$("#preset-makro").innerHTML = PRESET.map(([n, s, k]) => `<button data-s="${s}" data-k="${k}">${n}</button>`).join("");
$("#preset-makro").onclick = (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  $("#makro-sumber").value = b.dataset.s; $("#makro-seri").value = b.dataset.k; muatMakro(b.textContent);
};
$("#makro-form").onsubmit = (e) => { e.preventDefault(); muatMakro(); };
async function muatMakro(judul) {
  const sumber = $("#makro-sumber").value, wb = sumber === "wb";
  const p = { sumber, seri: $("#makro-seri").value.trim(), negara: $("#makro-negara").value.trim() };
  const d = await api("/api/makro" + q(p));
  grafik("c-makro", { type: "line", data: { labels: d.tanggal, datasets: [garis(judul || p.seri, d.nilai, C.aksen, wb ? { pointRadius: 2 } : {})] } });
}

// ---------- Backtest ----------
const NAMA_STAT = { total_return: "Total return", cagr: "CAGR", max_drawdown: "Max drawdown", sharpe: "Sharpe" };
async function muatBacktest() {
  const strategi = $("#bt-strategi").value;
  const d = await api("/api/backtest" + q({ simbol: sym(), rentang: rentang(),
    strategi, biaya: $("#bt-biaya").value, ridge: $("#bt-ridge").value }));
  const s = d.statistik;
  kartu("#bt-stat", Object.keys(NAMA_STAT).map((k) => {
    const f = k === "sharpe" ? (v) => num(v) : (v) => pct(v);
    return [NAMA_STAT[k], f(s.strategi[k]), warna(s.strategi[k] - s.beli_tahan[k]), "beli-tahan " + f(s.beli_tahan[k])];
  }));
  grafik("c-ekuitas", { type: "line", data: { labels: d.tanggal, datasets: [
    garis("Strategi", d.strategi, C.aksen), garis("Beli-tahan", d.beli_tahan, C.redup)] } });
  grafik("c-dd", { type: "line", data: { labels: d.tanggal, datasets: [
    garis("Drawdown", d.drawdown, C.turun, { fill: true, backgroundColor: "rgba(229,83,75,.15)" })] },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { maxTicksLimit: 6, maxRotation: 0 } }, y: { ticks: { callback: (v) => pct(v, 0) } } } } });
  $("#bt-ml").style.display = d.evaluasi ? "" : "none";
  if (d.evaluasi) {
    const ic = d.evaluasi.ic;
    grafik("c-ic", { type: "bar", data: { labels: Object.keys(ic), datasets: [{ label: "IC", data: Object.values(ic),
      backgroundColor: Object.values(ic).map((v) => (v >= 0 ? C.naik : C.turun)) }] },
      options: { plugins: { legend: { display: false } }, scales: { x: {} } } });
    $("#bt-hit").textContent = `Arah prediksi benar ${pct(d.evaluasi.hit_rate)} dari ${d.evaluasi.n} hari. IC di bawah 0,05 biasanya terlalu lemah untuk dipakai sendirian.`;
  }
  $("#bt-n").textContent = d.transaksi.length;
  tabel("#bt-trx", ["Tanggal", "Aksi", { t: "Harga", n: 1 }],
    d.transaksi.slice().reverse().map((t) => [t.tanggal, `<span class="${t.aksi === "beli" ? "naik" : "turun"}">${t.aksi}</span>`, num(t.harga)]));
}
$("#bt-form").onsubmit = (e) => { e.preventDefault(); muatBacktest(); };
$("#bt-strategi").onchange = () => { document.querySelector(".ml-saja").style.display = $("#bt-strategi").value === "ml" ? "" : "none"; };
$("#bt-strategi").onchange();

// ---------- Risiko ----------
async function muatRisiko() {
  const d = await api("/api/risiko" + q({ simbol: sym(), rentang: rentang(), benchmark: $("#rk-bm").value.trim() }));
  const r = d.ringkasan;
  kartu("#rk-stat", [
    ["Volatilitas tahunan", pct(r.vol_tahunan)], ["VaR 95% (1 hari)", pct(r.var_historis, 2), "turun", "historis"],
    ["CVaR 95%", pct(r.cvar_historis, 2), "turun", "rata-rata hari terburuk 5%"], ["VaR parametrik", pct(r.var_parametrik, 2), "", "asumsi normal"],
    ["Max drawdown", pct(r.max_drawdown), "turun"], ["Beta", num(r.beta), "", "vs " + esc($("#rk-bm").value)],
    ["Korelasi", num(r.korelasi_benchmark)], ["Skew / kurtosis", `${num(r.skew)} / ${num(r.kurtosis)}`],
  ]);
  grafik("c-hist", { type: "bar", data: { labels: d.histogram.tepi.map((v) => pct(v, 1)), datasets: [{ label: "Hari",
    data: d.histogram.jumlah, backgroundColor: d.histogram.tepi.map((v) => (v < -r.var_historis ? C.turun : C.biru)) }] },
    options: { plugins: { legend: { display: false } } } });
  grafik("c-rk-dd", { type: "line", data: { labels: d.tanggal, datasets: [
    garis("Drawdown", d.drawdown, C.turun, { fill: true, backgroundColor: "rgba(229,83,75,.15)" })] },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { maxTicksLimit: 6, maxRotation: 0 } }, y: { ticks: { callback: (v) => pct(v, 0) } } } } });
}
$("#rk-form").onsubmit = (e) => { e.preventDefault(); muatRisiko(); };

// ---------- Portofolio ----------
async function muatPortofolio() {
  const d = await api("/api/portofolio" + q({ simbol: $("#pf-simbol").value }));
  const t = d.terbaik, titik = d.titik.vol.map((v, i) => ({ x: v, y: d.titik.ret[i] }));
  const tanda = (label, k, c) => ({ label, data: [{ x: t[k].vol, y: t[k].ret }], backgroundColor: c, pointRadius: 7 });
  grafik("c-frontier", { type: "scatter", data: { datasets: [
    tanda("Sharpe maks", "sharpe_maks", C.aksen), tanda("Varians min", "varians_min", C.biru), tanda("Bobot sama", "bobot_sama", "#ccc"),
    { label: "Kombinasi acak", data: titik, backgroundColor: "rgba(125,138,151,.25)", pointRadius: 1.5 },
  ] }, options: { interaction: { mode: "nearest" }, scales: {
    x: { title: { display: true, text: "volatilitas" }, ticks: { callback: (v) => pct(v, 0) } },
    y: { title: { display: true, text: "return" }, ticks: { callback: (v) => pct(v, 0) } } } } });
  const simbol = d.korelasi.simbol;
  tabel("#pf-bobot", ["Simbol", { t: "Sharpe maks", n: 1 }, { t: "Varians min", n: 1 }, { t: "Sama", n: 1 }],
    [...simbol.map((s) => [esc(s), pct(t.sharpe_maks.bobot[s]), pct(t.varians_min.bobot[s]), pct(t.bobot_sama.bobot[s])]),
     ["<b>Return / vol</b>", ...["sharpe_maks", "varians_min", "bobot_sama"].map((k) => `${pct(t[k].ret)} / ${pct(t[k].vol)}`)]]);
  $("#pf-kor").innerHTML = `<tr><th></th>${simbol.map((s) => `<th>${esc(s.replace(".JK", ""))}</th>`).join("")}</tr>` +
    d.korelasi.nilai.map((b, i) => `<tr><th>${esc(simbol[i].replace(".JK", ""))}</th>${b.map((v) =>
      `<td style="background:rgba(${v >= 0 ? "240,164,58" : "76,154,255"},${Math.abs(v) * 0.8})">${v.toFixed(2)}</td>`).join("")}</tr>`).join("");
}
$("#pf-form").onsubmit = (e) => { e.preventDefault(); muatPortofolio(); };

// ---------- Paper trading ----------
function tampilAkun(a) {
  const pl = a.nilai - a.modal_awal;
  kartu("#po-kartu", [["Total nilai", num(a.nilai, 0)], ["Kas", num(a.kas, 0)], ["Untung/rugi", num(pl, 0), warna(pl), pct(pl / a.modal_awal, 2)]]);
  // harga rata-rata dari riwayat beli, dikurangi proporsional saat jual
  const modal = {};
  for (const r of a.riwayat) {
    const m = (modal[r.simbol] ??= { n: 0, biaya: 0 });
    if (r.jumlah > 0) { m.biaya += r.jumlah * r.harga; m.n += r.jumlah; }
    else { m.biaya *= (m.n + r.jumlah) / m.n; m.n += r.jumlah; }
  }
  tabel("#po-posisi", ["Simbol", { t: "Lembar", n: 1 }, { t: "Harga rata", n: 1 }, { t: "Harga kini", n: 1 }, { t: "Nilai", n: 1 }, { t: "U/R", n: 1 }],
    Object.entries(a.posisi).map(([s, n]) => {
      const rata = modal[s].biaya / modal[s].n, ur = (a.harga[s] - rata) * n;
      return [esc(s), num(n, 0), num(rata), num(a.harga[s]), num(n * a.harga[s], 0), `<span class="${warna(ur)}">${num(ur, 0)}</span>`];
    }));
  tabel("#po-riwayat", ["Tanggal", "Simbol", { t: "Jumlah", n: 1 }, { t: "Harga", n: 1 }],
    a.riwayat.slice().reverse().map((r) => [r.tanggal, esc(r.simbol), `<span class="${warna(r.jumlah)}">${num(r.jumlah, 0)}</span>`, num(r.harga)]));
}
$("#po-form").onsubmit = (e) => e.preventDefault();
$("#po-form").querySelectorAll("button").forEach((b) => (b.onclick = async () => {
  b.disabled = true;
  try { tampilAkun(await api("/api/paper", { aksi: b.dataset.aksi, simbol: $("#po-simbol").value, jumlah: $("#po-jumlah").value })); }
  catch {} finally { b.disabled = false; }
}));

// ---------- Agen AI ----------
$("#ag-key").value = ambil("anthropic_key", "");
$("#ag-key").onchange = () => simpan("anthropic_key", $("#ag-key").value);
async function muatAgen() {
  if ($("#ag-daftar").children.length) return;
  const d = await api("/api/agen");
  const pilih = ambil("agen", ["teknikal", "risiko", "skeptis"]);
  $("#ag-daftar").innerHTML = Object.entries(d).map(([k, n]) =>
    `<label><input type="checkbox" value="${k}" ${pilih.includes(k) ? "checked" : ""}> ${esc(n)}</label>`).join("");
}
$("#ag-form").onsubmit = async (e) => {
  e.preventDefault();
  const agen = [...document.querySelectorAll("#ag-daftar input:checked")].map((i) => i.value);
  simpan("agen", agen);
  const tombol = $("#ag-form button");
  tombol.disabled = true;
  $("#ag-hasil").innerHTML = `<div class="panel redup">${agen.length} agen sedang membaca data ${esc(sym())}...</div>`;
  try {
    const d = await api("/api/agen", { simbol: sym(), pertanyaan: $("#ag-tanya").value, agen, api_key: $("#ag-key").value });
    $("#ag-hasil").innerHTML = d.jawaban.map((j) => `<div class="panel jawaban"><h3>${esc(j.nama)}</h3>${esc(j.teks)}</div>`).join("") +
      `<details class="panel"><summary>Data yang dikirim ke agen</summary><pre>${esc(d.konteks)}</pre></details>`;
  } catch (err) {
    $("#ag-hasil").innerHTML = `<div class="panel turun">${esc(err.message)}</div>`;
  } finally { tombol.disabled = false; }
};

// ---------- Navigasi ----------
const MUAT = { pasar: () => Promise.all([muatPasar(), muatWatchlist()]), makro: () => muatMakro("Yield US 10th"),
  backtest: muatBacktest, risiko: muatRisiko, portofolio: muatPortofolio, paper: async () => tampilAkun(await api("/api/paper")), agen: muatAgen };
let tab = ambil("tab", "pasar");
function muatTab() { MUAT[tab]().catch((e) => status(e.message, true)); }
function buka(t) {
  tab = t; simpan("tab", t);
  document.querySelectorAll("nav button, section").forEach((el) => el.classList.toggle("on", (el.dataset.tab || el.id) === t));
  muatTab();
}
$("nav").onclick = (e) => e.target.dataset.tab && buka(e.target.dataset.tab);
$("#global").onsubmit = (e) => { e.preventDefault(); muatTab(); };
buka(tab);

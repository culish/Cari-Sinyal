"""Server web lokal: API JSON + halaman UI. Hanya mendengar di 127.0.0.1."""
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd
import requests

from . import agen, backtest, data, indikator, ml, paper, portofolio, risiko

WEB = Path(__file__).parent / "web"
BUKU = os.environ.get("CARISINYAL_AKUN", "akun_paper.json")
_cache = {}


def harga(simbol, rentang="5y"):
    """Harga dengan cache 10 menit supaya pindah tab tidak mengulang unduhan."""
    kunci = (simbol.upper(), rentang)
    if kunci not in _cache or time.time() - _cache[kunci][0] > 600:
        _cache[kunci] = (time.time(), data.harga(simbol.upper(), rentang))
    return _cache[kunci][1]


def _list(s):
    return [None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), 6) for v in s]


def _tgl(s):
    return [str(t.date()) for t in s.index]


def _bersih(x):
    if isinstance(x, dict):
        return {k: _bersih(v) for k, v in x.items()}
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def pasar(q):
    close = harga(q["simbol"], q.get("rentang", "2y"))
    bb, m = indikator.bollinger(close), indikator.macd(close)
    r = close.pct_change()
    return {
        "tanggal": _tgl(close), "close": _list(close),
        "sma20": _list(close.rolling(20).mean()), "sma50": _list(close.rolling(50).mean()),
        "bb_atas": _list(bb["atas"]), "bb_bawah": _list(bb["bawah"]),
        "rsi": _list(indikator.rsi(close)), "macd": _list(m["macd"]), "macd_sinyal": _list(m["sinyal"]),
        "macd_hist": _list(m["histogram"]),
        "ringkasan": {"terakhir": float(close.iloc[-1]), "tanggal": str(close.index[-1].date()),
                      "ret_1h": float(r.iloc[-1]), "ret_1bln": float(close.iloc[-1] / close.iloc[-22] - 1),
                      "vol_tahunan": float(r.tail(252).std() * 252 ** 0.5)},
    }


def watchlist(q):
    hasil = []
    for s in [x.strip() for x in q["simbol"].split(",") if x.strip()]:
        try:
            c = harga(s, "1y")
            hasil.append({"simbol": s.upper(), "terakhir": float(c.iloc[-1]), "ret_1h": float(c.iloc[-1] / c.iloc[-2] - 1),
                          "ret_1bln": float(c.iloc[-1] / c.iloc[-22] - 1), "spark": _list(c.tail(60))})
        except (requests.RequestException, KeyError, IndexError, TypeError) as e:
            hasil.append({"simbol": s.upper(), "error": str(e)})
    return hasil


def makro(q):
    sumber = q.get("sumber", "fred")
    if sumber == "wb":
        s = data.worldbank(q["negara"], q["seri"])
    elif sumber == "yahoo":
        s = harga(q["seri"], "5y")
    else:
        s = data.fred(q["seri"])
    return {"tanggal": [str(t)[:10] for t in s.index], "nilai": _list(s)}


def _posisi(close, q):
    if q.get("strategi") == "ml":
        return ml.sinyal(close, ridge=float(q.get("ridge", 0)))
    return backtest.STRATEGI[q.get("strategi", "sma")](close)


def uji(q):
    close = harga(q["simbol"], q.get("rentang", "5y"))
    pos = _posisi(close, q)
    if q.get("strategi") == "ml" and pos.notna().sum() < 60:
        raise ValueError("data terlalu pendek untuk ML (model butuh 500 hari latih). Pilih rentang 5 thn atau lebih.")
    eq = backtest.jalankan(close, pos, float(q.get("biaya", 15)))
    bh = close / close.iloc[0]
    hasil = {
        "tanggal": _tgl(close), "strategi": _list(eq), "beli_tahan": _list(bh),
        "drawdown": _list(eq / eq.cummax() - 1),
        "statistik": {k: _bersih(v) for k, v in backtest.bandingkan(close, pos, float(q.get("biaya", 15))).to_dict().items()},
        "transaksi": backtest.transaksi(close, pos)[-50:],
    }
    if q.get("strategi") == "ml":
        hasil["evaluasi"] = _bersih(ml.evaluasi(close, ml.prediksi(close, ridge=float(q.get("ridge", 0)))))
    return hasil


def ukur_risiko(q):
    close = harga(q["simbol"], q.get("rentang", "5y"))
    bm = q.get("benchmark")
    r = close.pct_change().dropna()
    hist, tepi = np.histogram(r, bins=50)
    return {"ringkasan": _bersih(risiko.ringkasan(close, harga(bm, q.get("rentang", "5y")) if bm else None)),
            "histogram": {"tepi": _list(tepi[:-1]), "jumlah": hist.tolist()},
            "tanggal": _tgl(close), "drawdown": _list(close / close.cummax() - 1)}


def optimasi(q):
    simbol = [s.strip().upper() for s in q["simbol"].split(",") if s.strip()]
    if len(simbol) < 2:
        raise ValueError("isi minimal 2 simbol")
    df = pd.concat({s: harga(s, q.get("rentang", "3y")) for s in simbol}, axis=1).dropna()
    f = portofolio.frontier(df)
    titik = f["titik"].iloc[::4]  # cukup 1250 titik untuk grafik
    return {"titik": {k: _list(v) for k, v in titik.items()}, "terbaik": _bersih(f["terbaik"]),
            "korelasi": {"simbol": simbol, "nilai": f["korelasi"].round(3).values.tolist()}}


def akun_paper(_q=None):
    akun = paper.muat(BUKU)
    kini = {s: float(harga(s, "1mo").iloc[-1]) for s in akun["posisi"]}
    return {**akun, "harga": kini, "nilai": paper.nilai(akun, kini), "modal_awal": paper.MODAL_AWAL}


def order(body):
    akun = paper.muat(BUKU)
    simbol, jumlah = body["simbol"].upper(), int(body["jumlah"])
    if jumlah <= 0:
        raise ValueError("jumlah harus positif")
    c = harga(simbol, "1mo")
    paper.transaksi(akun, simbol, jumlah if body["aksi"] == "beli" else -jumlah, float(c.iloc[-1]), str(c.index[-1].date()))
    paper.simpan(akun, BUKU)
    return akun_paper()


def konteks(simbol):
    """Satu paket data yang sama untuk semua agen."""
    close = harga(simbol, "5y")
    p = pasar({"simbol": simbol, "rentang": "5y"})
    bagian = [
        f"Simbol {simbol}, data sampai {p['ringkasan']['tanggal']}: {json.dumps(p['ringkasan'])}",
        f"Indikator terakhir: RSI {p['rsi'][-1]}, MACD {p['macd'][-1]} (sinyal {p['macd_sinyal'][-1]}), "
        f"SMA20 {p['sma20'][-1]}, SMA50 {p['sma50'][-1]}, Bollinger {p['bb_bawah'][-1]} - {p['bb_atas'][-1]}",
        f"Risiko 5 tahun: {json.dumps(_bersih(risiko.ringkasan(close)))}",
    ]
    for nama in ("sma", "momentum"):
        bagian.append(f"Backtest {nama} vs beli-tahan:\n{backtest.bandingkan(close, backtest.STRATEGI[nama](close)).round(4).to_string()}")
    bagian.append(f"Evaluasi model ML walk-forward: {json.dumps(_bersih(ml.evaluasi(close, ml.prediksi(close))))}")
    for seri in ("DGS10", "FEDFUNDS"):
        try:
            bagian.append(f"FRED {seri} 6 data terakhir: {data.fred(seri).tail(6).round(2).to_dict()}")
        except requests.RequestException:
            pass
    return "\n\n".join(bagian)


def tanya_agen(body):
    pilih = [a for a in body.get("agen", []) if a in agen.AGEN] or ["kuant"]
    ktx = konteks(body["simbol"].upper())
    key = body.get("api_key") or None
    with ThreadPoolExecutor(len(pilih)) as ex:
        jawab = ex.map(lambda a: agen.tanya(a, body["pertanyaan"], ktx, key), pilih)
        return {"konteks": ktx, "jawaban": [{"agen": a, "nama": agen.AGEN[a][0], "teks": t} for a, t in zip(pilih, jawab)]}


GET = {"/api/pasar": pasar, "/api/watchlist": watchlist, "/api/makro": makro, "/api/backtest": uji,
       "/api/risiko": ukur_risiko, "/api/portofolio": optimasi, "/api/paper": akun_paper,
       "/api/agen": lambda q: {k: v[0] for k, v in agen.AGEN.items()}}
POST = {"/api/paper": order, "/api/agen": tanya_agen}
TIPE = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}


class Handler(BaseHTTPRequestHandler):
    def _kirim(self, kode, isi, tipe="application/json"):
        badan = isi if isinstance(isi, bytes) else json.dumps(isi, allow_nan=False).encode()
        self.send_response(kode)
        self.send_header("Content-Type", f"{tipe}; charset=utf-8")
        self.send_header("Content-Length", str(len(badan)))
        self.end_headers()
        self.wfile.write(badan)

    def _api(self, fn, arg):
        try:
            self._kirim(200, fn(arg))
        except Exception as e:  # semua error API dikembalikan ke UI sebagai pesan, bukan traceback
            self._kirim(400, {"error": f"{type(e).__name__}: {e}"})

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in GET:
            return self._api(GET[u.path], {k: v[0] for k, v in parse_qs(u.query).items()})
        f = (WEB / (u.path.lstrip("/") or "index.html")).resolve()
        if f.parent != WEB.resolve() or not f.is_file():
            return self._kirim(404, {"error": "tidak ada"})
        self._kirim(200, f.read_bytes(), TIPE.get(f.suffix, "application/octet-stream"))

    def do_POST(self):
        u = urlparse(self.path)
        if u.path not in POST:
            return self._kirim(404, {"error": "tidak ada"})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        self._api(POST[u.path], body)

    def log_message(self, *_):
        pass


def jalankan(port=8765, buka=True):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Cari-Sinyal jalan di {url} (Ctrl+C untuk berhenti)")
    if buka:
        import webbrowser
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

import argparse
import os

import pandas as pd
import requests

from . import backtest, data, ml, paper

BUKU = os.environ.get("CARISINYAL_AKUN", "akun_paper.json")


def _ringkas(close):
    r = close.pct_change()
    return pd.Series({
        "terakhir": close.iloc[-1],
        "tanggal": close.index[-1].date(),
        "ret_1bln": close.iloc[-1] / close.iloc[-22] - 1,
        "ret_1thn": close.iloc[-1] / close.iloc[-252] - 1 if len(close) > 252 else None,
        "vol_tahunan": r.tail(252).std() * 252 ** 0.5,
    })


def _posisi(close, strategi):
    return ml.sinyal(close) if strategi == "ml" else backtest.sma_cross(close)


def cmd_harga(a):
    print(_ringkas(data.harga(a.simbol, a.rentang)).to_string())


def cmd_makro(a):
    s = data.worldbank(a.negara, a.seri) if a.negara else data.fred(a.seri)
    print(s.tail(a.n).to_string())


def cmd_backtest(a):
    close = data.harga(a.simbol, a.rentang)
    hasil = backtest.bandingkan(close, _posisi(close, a.strategi), a.biaya)
    teks = pd.concat([hasil.drop("sharpe").map("{:.1%}".format), hasil.loc[["sharpe"]].map("{:.2f}".format)])
    print(teks.to_string())


def cmd_sinyal(a):
    close = data.harga(a.simbol, a.rentang)
    pos = _posisi(close, a.strategi).dropna()
    print(f"{a.simbol} {pos.index[-1].date()}: {'LONG' if pos.iloc[-1] else 'KELUAR'} ({a.strategi})")


def cmd_paper(a):
    akun = paper.muat(BUKU)
    if a.aksi in ("beli", "jual"):
        close = data.harga(a.simbol, "5d")
        harga = a.harga or close.iloc[-1]
        jumlah = a.jumlah if a.aksi == "beli" else -a.jumlah
        paper.transaksi(akun, a.simbol, jumlah, harga, str(close.index[-1].date()))
        paper.simpan(akun, BUKU)
        print(f"{a.aksi} {a.jumlah} {a.simbol} @ {harga:,.2f}")
    kini = {s: data.harga(s, "5d").iloc[-1] for s in akun["posisi"]}
    for s, n in akun["posisi"].items():
        print(f"{s:10} {n:>10} @ {kini[s]:>12,.2f}")
    print(f"kas {akun['kas']:,.0f} | total {paper.nilai(akun, kini):,.0f} (modal awal {paper.MODAL_AWAL:,})")


def cmd_riset(a):
    from . import riset

    close = data.harga(a.simbol, a.rentang)
    konteks = [f"Ringkasan {a.simbol}:\n{_ringkas(close).to_string()}",
               f"Backtest SMA 20/50 vs beli-tahan:\n{backtest.bandingkan(close, backtest.sma_cross(close)).to_string()}"]
    for seri in a.fred:
        konteks.append(f"FRED {seri} 12 data terakhir:\n{data.fred(seri).tail(12).to_string()}")
    print(riset.tanya(a.pertanyaan, "\n\n".join(konteks)))


def main(argv=None):
    p = argparse.ArgumentParser(prog="cari-sinyal", description="Riset trading dari terminal.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def baru(nama, fn, bantuan, simbol=True):
        sp = sub.add_parser(nama, help=bantuan)
        sp.set_defaults(fn=fn)
        if simbol:
            sp.add_argument("simbol", help="mis. BBCA.JK, AAPL, BTC-USD")
            sp.add_argument("--rentang", default="5y", help="1y, 5y, 10y, max")
        return sp

    baru("harga", cmd_harga, "ringkasan harga terakhir")

    sp = baru("makro", cmd_makro, "seri FRED atau Bank Dunia", simbol=False)
    sp.add_argument("seri", help="kode FRED (DGS10) atau indikator Bank Dunia (NY.GDP.MKTP.KD.ZG)")
    sp.add_argument("--negara", help="kode negara Bank Dunia, mis. IDN. Tanpa ini = FRED")
    sp.add_argument("-n", type=int, default=12)

    for nama, fn, bantuan in [("backtest", cmd_backtest, "uji strategi vs beli-tahan"),
                              ("sinyal", cmd_sinyal, "posisi strategi hari ini")]:
        sp = baru(nama, fn, bantuan)
        sp.add_argument("--strategi", choices=["sma", "ml"], default="sma")
        if nama == "backtest":
            sp.add_argument("--biaya", type=float, default=15, help="biaya per transaksi, basis poin")

    sp = sub.add_parser("paper", help="paper trading")
    sp.set_defaults(fn=cmd_paper)
    sp.add_argument("aksi", choices=["beli", "jual", "posisi"])
    sp.add_argument("simbol", nargs="?")
    sp.add_argument("jumlah", nargs="?", type=int)
    sp.add_argument("--harga", type=float, help="harga manual; default harga penutupan terakhir")

    sp = baru("riset", cmd_riset, "catatan riset dari Claude (butuh ANTHROPIC_API_KEY)")
    sp.add_argument("pertanyaan")
    sp.add_argument("--fred", nargs="*", default=[], help="seri FRED tambahan untuk konteks")

    a = p.parse_args(argv)
    if a.cmd == "paper" and a.aksi != "posisi" and not (a.simbol and a.jumlah and a.jumlah > 0):
        p.error("paper beli/jual butuh SIMBOL dan JUMLAH positif")
    try:
        a.fn(a)
    except (ValueError, KeyError, IndexError, requests.RequestException) as e:
        p.exit(1, f"gagal: {e}\n")

"""Backtest vektor: posisi hari ini dipakai untuk return besok, jadi tidak ada lookahead."""
import numpy as np
import pandas as pd

from . import indikator

HARI_BURSA = 252


def sma_cross(close, cepat=20, lambat=50):
    """1 saat SMA cepat di atas SMA lambat, 0 selain itu (long-only)."""
    return (close.rolling(cepat).mean() > close.rolling(lambat).mean()).astype(float)


def momentum(close, lookback=126):
    """Pegang saat return `lookback` hari terakhir positif."""
    return (close.pct_change(lookback) > 0).astype(float)


def _tahan(masuk, keluar, index):
    """Ubah sinyal masuk/keluar jadi posisi 0/1 yang bertahan sampai sinyal keluar."""
    pos = pd.Series(np.nan, index=index)
    pos[masuk] = 1.0
    pos[keluar] = 0.0
    return pos.ffill().fillna(0)


def rsi_reversion(close, bawah=30, atas=70):
    """Beli saat RSI di bawah `bawah`, keluar saat di atas `atas`."""
    r = indikator.rsi(close)
    return _tahan(r < bawah, r > atas, close.index)


def bollinger_reversion(close, n=20, k=2):
    """Beli saat harga tembus pita bawah, keluar saat kembali ke garis tengah."""
    b = indikator.bollinger(close, n, k)
    return _tahan(close < b["bawah"], close > b["tengah"], close.index)


STRATEGI = {"sma": sma_cross, "momentum": momentum, "rsi": rsi_reversion, "bollinger": bollinger_reversion}


def jalankan(close, posisi, biaya_bps=15):
    """Kurva ekuitas mulai dari 1.0. biaya_bps dipotong tiap kali posisi berubah."""
    pos = posisi.reindex(close.index).fillna(0).shift(1).fillna(0)
    ret = close.pct_change().fillna(0)
    biaya = pos.diff().abs().fillna(pos.abs()) * biaya_bps / 1e4
    return (1 + pos * ret - biaya).cumprod()


def statistik(ekuitas):
    ret = ekuitas.pct_change().dropna()
    tahun = len(ret) / HARI_BURSA
    sd = ret.std()
    return {
        "total_return": ekuitas.iloc[-1] / ekuitas.iloc[0] - 1,
        "cagr": (ekuitas.iloc[-1] / ekuitas.iloc[0]) ** (1 / tahun) - 1 if tahun else 0.0,
        "sharpe": ret.mean() / sd * np.sqrt(HARI_BURSA) if sd else 0.0,
        "max_drawdown": (ekuitas / ekuitas.cummax() - 1).min(),
    }


def transaksi(close, posisi):
    """Daftar perubahan posisi: tanggal, aksi, harga."""
    p = posisi.reindex(close.index).fillna(0)
    ubah = p.diff().fillna(p)
    ubah = ubah[ubah != 0]
    return [{"tanggal": str(t.date()), "aksi": "beli" if d > 0 else "jual", "harga": float(close[t])}
            for t, d in ubah.items()]


def bandingkan(close, posisi, biaya_bps=15):
    """Statistik strategi vs beli-dan-tahan pada periode yang sama."""
    return pd.DataFrame({
        "strategi": statistik(jalankan(close, posisi, biaya_bps)),
        "beli_tahan": statistik(close / close.iloc[0]),
    })

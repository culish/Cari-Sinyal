"""Backtest vektor: posisi hari ini dipakai untuk return besok, jadi tidak ada lookahead."""
import numpy as np
import pandas as pd

HARI_BURSA = 252


def sma_cross(close, cepat=20, lambat=50):
    """1 saat SMA cepat di atas SMA lambat, 0 selain itu (long-only)."""
    return (close.rolling(cepat).mean() > close.rolling(lambat).mean()).astype(float)


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


def bandingkan(close, posisi, biaya_bps=15):
    """Statistik strategi vs beli-dan-tahan pada periode yang sama."""
    return pd.DataFrame({
        "strategi": statistik(jalankan(close, posisi, biaya_bps)),
        "beli_tahan": statistik(close / close.iloc[0]),
    })

"""Indikator teknikal dari harga penutupan."""
import pandas as pd


def rsi(close, n=14):
    d = close.diff()
    naik = d.clip(lower=0).ewm(alpha=1 / n, min_periods=n).mean()
    turun = (-d.clip(upper=0)).ewm(alpha=1 / n, min_periods=n).mean()
    return 100 - 100 / (1 + naik / turun)


def macd(close, cepat=12, lambat=26, sinyal=9):
    garis = close.ewm(span=cepat, adjust=False).mean() - close.ewm(span=lambat, adjust=False).mean()
    sig = garis.ewm(span=sinyal, adjust=False).mean()
    return pd.DataFrame({"macd": garis, "sinyal": sig, "histogram": garis - sig})


def bollinger(close, n=20, k=2):
    tengah = close.rolling(n).mean()
    sd = close.rolling(n).std()
    return pd.DataFrame({"atas": tengah + k * sd, "tengah": tengah, "bawah": tengah - k * sd})

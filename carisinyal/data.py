"""Data pasar dan makro dari sumber gratis tanpa API key."""
import io

import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (cari-sinyal)"}


def _get(url, **params):
    r = requests.get(url, params=params, headers=UA, timeout=20)
    r.raise_for_status()
    return r


def parse_yahoo(payload):
    res = payload["chart"]["result"][0]
    idx = pd.to_datetime(res["timestamp"], unit="s").normalize()
    adj = res["indicators"].get("adjclose")
    close = adj[0]["adjclose"] if adj else res["indicators"]["quote"][0]["close"]
    return pd.Series(close, index=idx, name=res["meta"]["symbol"], dtype=float).dropna()


def harga(simbol, rentang="5y"):
    """Harga penutupan harian dari Yahoo Finance. Saham IDX pakai akhiran .JK, mis. BBCA.JK."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{simbol}"
    return parse_yahoo(_get(url, range=rentang, interval="1d").json())


def parse_fred(text):
    df = pd.read_csv(io.StringIO(text), na_values=".")
    s = df.set_index(pd.to_datetime(df.iloc[:, 0])).iloc[:, 1]
    return s.astype(float).dropna()


def fred(seri):
    """Seri FRED, mis. DGS10 (yield US 10 tahun), CPIAUCSL, FEDFUNDS."""
    return parse_fred(_get("https://fred.stlouisfed.org/graph/fredgraph.csv", id=seri).text)


def parse_worldbank(payload):
    rows = payload[1] or []
    s = pd.Series({int(r["date"]): r["value"] for r in rows}, dtype=float)
    return s.dropna().sort_index()


def worldbank(negara, indikator):
    """Indikator Bank Dunia tahunan, mis. negara=IDN, indikator=NY.GDP.MKTP.KD.ZG."""
    url = f"https://api.worldbank.org/v2/country/{negara}/indicator/{indikator}"
    return parse_worldbank(_get(url, format="json", per_page=100).json())

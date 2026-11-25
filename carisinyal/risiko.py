"""Ukuran risiko dari return harian."""
import numpy as np
from statistics import NormalDist


def ringkasan(close, benchmark=None, tingkat=0.95):
    r = close.pct_change().dropna()
    q = r.quantile(1 - tingkat)
    z = NormalDist().inv_cdf(1 - tingkat)
    hasil = {
        "vol_tahunan": r.std() * np.sqrt(252),
        "var_historis": -q,
        "cvar_historis": -r[r <= q].mean(),
        "var_parametrik": -(r.mean() + z * r.std()),
        "max_drawdown": (close / close.cummax() - 1).min(),
        "skew": r.skew(),
        "kurtosis": r.kurt(),
    }
    if benchmark is not None:
        rb = benchmark.pct_change().dropna()
        gab = r.to_frame("a").join(rb.rename("b"), how="inner")
        hasil["beta"] = gab["a"].cov(gab["b"]) / gab["b"].var()
        hasil["korelasi_benchmark"] = gab["a"].corr(gab["b"])
    return {k: float(v) for k, v in hasil.items()}

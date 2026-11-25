"""Optimasi portofolio long-only dengan sampel bobot acak (frontier Monte Carlo)."""
import numpy as np
import pandas as pd


def frontier(harga, n=5000, seed=0):
    """harga: DataFrame kolom = simbol. Kembalikan sampel (return, vol, sharpe) dan bobot terbaik."""
    r = harga.pct_change().dropna()
    mu, cov = r.mean().to_numpy() * 252, r.cov().to_numpy() * 252
    w = np.random.default_rng(seed).dirichlet(np.ones(len(mu)), n)
    w = np.vstack([w, np.full(len(mu), 1 / len(mu))])  # baris terakhir = bobot sama
    ret = w @ mu
    vol = np.sqrt(np.einsum("ij,jk,ik->i", w, cov, w))
    sharpe = ret / vol
    pilih = {"sharpe_maks": sharpe.argmax(), "varians_min": vol.argmin(), "bobot_sama": n}
    return {
        "titik": pd.DataFrame({"ret": ret, "vol": vol, "sharpe": sharpe}),
        "korelasi": r.corr(),
        "terbaik": {k: {"bobot": dict(zip(harga.columns, w[i].round(4))), "ret": float(ret[i]),
                        "vol": float(vol[i]), "sharpe": float(sharpe[i])} for k, i in pilih.items()},
    }

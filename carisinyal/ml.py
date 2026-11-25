"""Sinyal regresi linear walk-forward: model hanya dilatih dengan data sebelum hari prediksi."""
import numpy as np
import pandas as pd


def fitur(close):
    r = close.pct_change()
    return pd.DataFrame({
        "ret_1": r,
        "ret_5": close.pct_change(5),
        "ret_20": close.pct_change(20),
        "vol_20": r.rolling(20).std(),
        "jarak_sma50": close / close.rolling(50).mean() - 1,
    })


def sinyal(close, jendela=500, latih_ulang=20):
    """Posisi 1 jika prediksi return besok > 0. Model dilatih ulang tiap `latih_ulang` hari."""
    X = fitur(close)
    y = close.pct_change().shift(-1)
    ok = X.notna().all(axis=1)
    X, y = X[ok], y[ok]
    A = np.column_stack([np.ones(len(X)), X.to_numpy()])
    pred = pd.Series(np.nan, index=X.index)
    w = None
    for i in range(jendela, len(X)):
        if w is None or (i - jendela) % latih_ulang == 0:
            # target baris i-1 adalah return hari i, sudah diketahui saat penutupan hari i
            w, *_ = np.linalg.lstsq(A[i - jendela:i], y.iloc[i - jendela:i], rcond=None)
        pred.iloc[i] = A[i] @ w
    return (pred > 0).astype(float).where(pred.notna())

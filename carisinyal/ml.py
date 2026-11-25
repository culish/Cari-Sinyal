"""Sinyal regresi walk-forward: model hanya dilatih dengan data sebelum hari prediksi."""
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


def prediksi(close, jendela=500, latih_ulang=20, ridge=0.0):
    """Prediksi return besok. ridge > 0 menambah penalti L2 pada bobot fitur (fitur distandarkan)."""
    X = fitur(close)
    y = close.pct_change().shift(-1)
    ok = X.notna().all(axis=1)
    X, y = X[ok], y[ok]
    Xn = X.to_numpy()
    pred = pd.Series(np.nan, index=X.index)
    for i in range(jendela, len(X)):
        if (i - jendela) % latih_ulang == 0:
            # target baris i-1 adalah return hari i, sudah diketahui saat penutupan hari i
            latih = Xn[i - jendela:i]
            mu, sd = latih.mean(0), latih.std(0) + 1e-12
            A = np.column_stack([np.ones(jendela), (latih - mu) / sd])
            reg = ridge * np.eye(A.shape[1])
            reg[0, 0] = 0
            w = np.linalg.solve(A.T @ A + reg + 1e-9 * np.eye(A.shape[1]), A.T @ y.iloc[i - jendela:i].to_numpy())
        pred.iloc[i] = np.r_[1, (Xn[i] - mu) / sd] @ w
    return pred


def sinyal(close, jendela=500, latih_ulang=20, ridge=0.0):
    """Posisi 1 jika prediksi return besok > 0."""
    pred = prediksi(close, jendela, latih_ulang, ridge)
    return (pred > 0).astype(float).where(pred.notna())


def evaluasi(close, pred):
    """Information coefficient (korelasi peringkat) tiap fitur dan prediksi terhadap return besok."""
    besok = close.pct_change().shift(-1)
    df = fitur(close).assign(prediksi=pred, besok=besok).dropna()
    rank = df.rank()  # Spearman = Pearson dari peringkat, tanpa scipy
    ic = rank.drop(columns="besok").corrwith(rank["besok"])
    kena = (np.sign(df["prediksi"]) == np.sign(df["besok"])).mean()
    return {"ic": ic.round(4).to_dict(), "hit_rate": float(kena), "n": len(df)}

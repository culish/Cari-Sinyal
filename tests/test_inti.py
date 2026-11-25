import numpy as np
import pandas as pd
import pytest

from carisinyal import backtest, data, ml, paper


def harga_acak(n=900, seed=0):
    r = np.random.default_rng(seed).normal(0.0004, 0.01, n)
    return pd.Series(100 * np.cumprod(1 + r), index=pd.bdate_range("2020-01-01", periods=n))


def test_parse_yahoo_pakai_adjclose():
    payload = {"chart": {"result": [{
        "meta": {"symbol": "BBCA.JK"},
        "timestamp": [1700000000, 1700086400],
        "indicators": {"quote": [{"close": [10, 11]}], "adjclose": [{"adjclose": [9.5, None]}]},
    }]}}
    s = data.parse_yahoo(payload)
    assert s.name == "BBCA.JK" and s.tolist() == [9.5]


def test_parse_fred_buang_titik():
    s = data.parse_fred("observation_date,DGS10\n2024-01-01,.\n2024-01-02,3.95\n")
    assert s.tolist() == [3.95]


def test_parse_worldbank_urut_tahun():
    s = data.parse_worldbank([{}, [{"date": "2023", "value": 5.0}, {"date": "2022", "value": 5.3},
                                   {"date": "2021", "value": None}]])
    assert s.index.tolist() == [2022, 2023]


def test_beli_tahan_sama_dengan_harga():
    close = harga_acak()
    eq = backtest.jalankan(close, pd.Series(1.0, index=close.index), biaya_bps=0)
    # hari pertama belum punya posisi, jadi ekuitas mengikuti harga mulai hari kedua
    assert eq.iloc[-1] == pytest.approx(close.iloc[-1] / close.iloc[0])


def test_posisi_dipakai_besok_tanpa_lookahead():
    close = pd.Series([100, 110, 99, 120.0], index=pd.bdate_range("2024-01-01", periods=4))
    pos = pd.Series([0, 1, 0, 0.0], index=close.index)  # masuk di hari ke-2, kena turun 10% hari ke-3
    eq = backtest.jalankan(close, pos, biaya_bps=0)
    assert eq.iloc[-1] == pytest.approx(0.9)


def test_biaya_dipotong_tiap_ganti_posisi():
    close = pd.Series(100.0, index=pd.bdate_range("2024-01-01", periods=5))
    pos = pd.Series([1, 0, 1, 0, 0.0], index=close.index)
    eq = backtest.jalankan(close, pos, biaya_bps=100)
    assert eq.iloc[-1] == pytest.approx(0.99 ** 4)


def test_statistik_drawdown():
    eq = pd.Series([1, 1.2, 0.9, 1.0], index=pd.bdate_range("2024-01-01", periods=4))
    assert backtest.statistik(eq)["max_drawdown"] == pytest.approx(-0.25)


def test_sinyal_ml_tidak_mengintip_masa_depan():
    close = harga_acak(800)
    penuh = ml.sinyal(close, jendela=300)
    # sinyal yang dihitung dengan data sampai hari k harus sama dengan sinyal dari data penuh
    for k in (450, 600, 799):
        potong = ml.sinyal(close.iloc[:k], jendela=300)
        pd.testing.assert_series_equal(potong, penuh.loc[potong.index])
    assert set(penuh.dropna().unique()) <= {0.0, 1.0}


def test_paper_trading(tmp_path):
    akun = paper.muat(tmp_path / "akun.json")
    paper.transaksi(akun, "BBCA.JK", 1000, 9000, "2024-01-02")
    paper.transaksi(akun, "BBCA.JK", -400, 9500, "2024-01-03")
    assert akun["posisi"] == {"BBCA.JK": 600}
    assert paper.nilai(akun, {"BBCA.JK": 10000}) == paper.MODAL_AWAL - 9_000_000 + 3_800_000 + 6_000_000
    with pytest.raises(ValueError):
        paper.transaksi(akun, "BBCA.JK", -601, 9500, "2024-01-04")
    with pytest.raises(ValueError):
        paper.transaksi(akun, "BBCA.JK", 10**9, 9500, "2024-01-04")
    paper.simpan(akun, tmp_path / "akun.json")
    assert paper.muat(tmp_path / "akun.json") == akun


def test_cli_tanpa_jaringan(monkeypatch, tmp_path, capsys):
    from carisinyal import cli

    close = harga_acak()
    monkeypatch.setattr(data, "harga", lambda simbol, rentang="5y": close)
    monkeypatch.setattr(cli, "BUKU", str(tmp_path / "akun.json"))
    cli.main(["backtest", "BBCA.JK", "--strategi", "ml"])
    cli.main(["sinyal", "BBCA.JK"])
    cli.main(["paper", "beli", "BBCA.JK", "100"])
    out = capsys.readouterr().out
    assert "beli_tahan" in out and "sharpe" in out and "BBCA.JK" in out
    with pytest.raises(SystemExit):
        cli.main(["paper", "jual", "BBCA.JK", "101"])

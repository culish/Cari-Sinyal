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


def test_indikator_dan_strategi():
    from carisinyal import indikator

    close = harga_acak()
    r = indikator.rsi(close).dropna()
    assert r.between(0, 100).all()
    naik = pd.Series(np.arange(1, 60.0))
    assert indikator.rsi(naik).iloc[-1] == pytest.approx(100)
    for nama, fn in backtest.STRATEGI.items():
        pos = fn(close)
        assert set(pos.dropna().unique()) <= {0.0, 1.0}, nama
    trx = backtest.transaksi(close, backtest.sma_cross(close))
    assert [t["aksi"] for t in trx[:2]] == ["beli", "jual"]


def test_risiko_dan_portofolio():
    from carisinyal import portofolio, risiko

    a, b = harga_acak(seed=1), harga_acak(seed=2)
    r = risiko.ringkasan(a, benchmark=a)
    assert r["beta"] == pytest.approx(1) and r["cvar_historis"] >= r["var_historis"] > 0
    f = portofolio.frontier(pd.DataFrame({"A": a, "B": b}), n=500)
    for pilihan in f["terbaik"].values():
        assert sum(pilihan["bobot"].values()) == pytest.approx(1, abs=1e-3)
    assert f["terbaik"]["varians_min"]["vol"] <= f["terbaik"]["bobot_sama"]["vol"]


def test_server_api(monkeypatch, tmp_path):
    import json
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer

    from carisinyal import agen, server

    monkeypatch.setattr(data, "harga", lambda s, r="5y": harga_acak(seed=len(s)))
    monkeypatch.setattr(data, "fred", lambda s: pd.Series([4.0, 4.1], index=pd.date_range("2026-01-01", periods=2)))
    monkeypatch.setattr(agen, "tanya", lambda a, p, k, key=None: f"{a}:{key}")
    monkeypatch.setattr(server, "BUKU", str(tmp_path / "akun.json"))
    server._cache.clear()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}"

    def panggil(path, body=None):
        req = urllib.request.Request(url + path, data=body and json.dumps(body).encode(), method="POST" if body else "GET")
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    try:
        for path in ["/api/pasar?simbol=X", "/api/watchlist?simbol=A,B", "/api/makro?seri=DGS10",
                     "/api/backtest?simbol=X&strategi=rsi", "/api/backtest?simbol=X&strategi=ml",
                     "/api/risiko?simbol=X&benchmark=Y", "/api/portofolio?simbol=A,BB,CCC", "/api/paper"]:
            assert panggil(path)[0] == 200, path
        kode, akun = panggil("/api/paper", {"aksi": "beli", "simbol": "x", "jumlah": 10})
        assert kode == 200 and akun["posisi"] == {"X": 10}
        assert panggil("/api/paper", {"aksi": "jual", "simbol": "X", "jumlah": 11})[0] == 400
        kode, hasil = panggil("/api/agen", {"simbol": "X", "pertanyaan": "?", "agen": ["risiko", "makro"], "api_key": "k"})
        assert [j["teks"] for j in hasil["jawaban"]] == ["risiko:k", "makro:k"] and "DGS10" in hasil["konteks"]
        assert panggil("/../pyproject.toml")[0] == 404
    finally:
        srv.shutdown()

"""Paper trading: buku besar JSON lokal, tanpa uang sungguhan."""
import json
from pathlib import Path

MODAL_AWAL = 100_000_000


def muat(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {"kas": MODAL_AWAL, "posisi": {}, "riwayat": []}


def simpan(akun, path):
    Path(path).write_text(json.dumps(akun, indent=2))


def transaksi(akun, simbol, jumlah, harga, tanggal):
    """jumlah positif = beli, negatif = jual. Tolak jika kas atau saham tidak cukup."""
    if jumlah == 0 or harga <= 0:
        raise ValueError("jumlah tidak boleh 0 dan harga harus positif")
    punya = akun["posisi"].get(simbol, 0)
    nilai = jumlah * harga
    if nilai > akun["kas"]:
        raise ValueError(f"kas kurang: perlu {nilai:,.0f}, ada {akun['kas']:,.0f}")
    if punya + jumlah < 0:
        raise ValueError(f"hanya punya {punya} lembar {simbol}")
    akun["kas"] -= nilai
    akun["posisi"][simbol] = punya + jumlah
    if akun["posisi"][simbol] == 0:
        del akun["posisi"][simbol]
    akun["riwayat"].append({"tanggal": tanggal, "simbol": simbol, "jumlah": jumlah, "harga": harga})
    return akun


def nilai(akun, harga_kini):
    return akun["kas"] + sum(n * harga_kini[s] for s, n in akun["posisi"].items())

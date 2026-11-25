# Cari-Sinyal

Riset trading dari terminal. Ambil data gratis, uji strategi, lihat sinyal hari ini, latihan transaksi dengan uang bohongan, lalu minta Claude menulis catatan riset dari angka yang sama.

## Pasang

```bash
pip install -e .            # inti: pandas, numpy, requests
pip install -e ".[riset]"   # tambah perintah riset (Claude)
```

## Perintah

```bash
cari-sinyal harga BBCA.JK                         # harga terakhir, return 1 bulan/1 tahun, volatilitas
cari-sinyal makro DGS10                           # yield obligasi AS 10 tahun dari FRED
cari-sinyal makro NY.GDP.MKTP.KD.ZG --negara IDN  # pertumbuhan PDB Indonesia dari Bank Dunia
cari-sinyal backtest BBCA.JK --strategi sma       # SMA 20/50 vs beli-tahan, biaya 15 bps per transaksi
cari-sinyal backtest BBCA.JK --strategi ml        # regresi linear walk-forward
cari-sinyal sinyal TLKM.JK                        # LONG atau KELUAR untuk hari ini
cari-sinyal paper beli BBRI.JK 500                # beli 500 lembar di harga penutupan terakhir
cari-sinyal paper jual BBRI.JK 200
cari-sinyal paper posisi
ANTHROPIC_API_KEY=... cari-sinyal riset BBCA.JK "Bagaimana risiko 6 bulan ke depan?" --fred DGS10 FEDFUNDS
```

Simbol mengikuti Yahoo Finance: saham IDX pakai akhiran `.JK`, kripto seperti `BTC-USD`.

## Sumber data

| Sumber | Isi | Key |
|---|---|---|
| Yahoo Finance | harga harian (adjusted close) | tidak perlu |
| FRED | suku bunga, inflasi, dan seri makro AS lain | tidak perlu |
| Bank Dunia | indikator tahunan per negara | tidak perlu |
| Claude | catatan riset dari data di atas | `ANTHROPIC_API_KEY` milik sendiri |

## Cara kerja

- **Backtest**: posisi hari ini dipakai untuk return besok, jadi strategi tidak bisa melihat harga yang belum terjadi. Biaya dipotong setiap posisi berubah. Hasil selalu dibandingkan dengan beli-tahan di periode yang sama.
- **Sinyal ML**: lima fitur (return 1/5/20 hari, volatilitas 20 hari, jarak ke SMA 50). Model dilatih dengan 500 hari terakhir dan dilatih ulang tiap 20 hari. Ada tes yang memotong data di beberapa tanggal dan memastikan sinyal di tanggal itu tidak berubah saat data masa depan ditambah.
- **Paper trading**: kas awal Rp100.000.000 di `akun_paper.json` (ubah lokasi lewat `CARISINYAL_AKUN`). Transaksi ditolak kalau kas atau lembar tidak cukup.
- **Riset**: ringkasan harga, hasil backtest, dan seri FRED pilihan dikirim ke Claude. Model diminta membahas tren dan risiko tanpa memberi perintah beli atau jual.

Pada data acak, strategi ML yang sering berganti posisi kalah dari beli-tahan karena biaya. Cek angka `--biaya` sesuai broker sebelum percaya hasil backtest.

## Tes

```bash
pip install -e ".[dev]" && pytest
```

Tes tidak butuh internet.

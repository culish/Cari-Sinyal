# Cari-Sinyal

Aplikasi riset trading yang jalan di laptop sendiri. Ambil data gratis, uji strategi, ukur risiko, susun portofolio, latihan transaksi dengan uang bohongan, lalu minta beberapa agen Claude membaca angka yang sama.

## Pasang dan buka UI

```bash
git clone https://github.com/culish/Cari-Sinyal.git && cd Cari-Sinyal
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[riset]"
cari-sinyal web                    # buka http://127.0.0.1:8765 di browser
```

Server hanya mendengar di 127.0.0.1, jadi tidak bisa diakses dari komputer lain.

## Halaman di UI

| Halaman | Isi |
|---|---|
| Pasar | watchlist dengan sparkline, grafik harga + SMA 20/50 + pita Bollinger, RSI 14, MACD 12/26/9 |
| Makro | FRED (yield US, Fed funds, CPI, pengangguran, minyak), Bank Dunia (PDB dan inflasi Indonesia), kurs dan emas dari Yahoo |
| Backtest | SMA cross, momentum 6 bulan, RSI reversion, Bollinger reversion, ML walk-forward (dengan ridge). Kurva ekuitas vs beli-tahan, drawdown, daftar transaksi, information coefficient tiap fitur |
| Risiko | volatilitas, VaR dan CVaR 95% (historis dan parametrik), beta dan korelasi ke benchmark (default ^JKSE), skew, kurtosis, histogram return |
| Portofolio | 5.000 kombinasi bobot long-only, titik Sharpe maksimum dan varians minimum, matriks korelasi |
| Paper Trading | beli/jual di harga penutupan terakhir, posisi dengan harga rata-rata dan untung/rugi, riwayat |
| Agen AI | 6 agen (teknikal, fundamental, makro, risiko, kuant, skeptis) menjawab pertanyaan yang sama dari satu paket data. API key bisa diisi di UI atau lewat `ANTHROPIC_API_KEY` |

## Perintah terminal

Semua fitur utama juga bisa dipanggil tanpa UI.

```bash
cari-sinyal harga BBCA.JK                         # harga terakhir, return 1 bulan/1 tahun, volatilitas
cari-sinyal makro DGS10                           # yield obligasi AS 10 tahun dari FRED
cari-sinyal makro NY.GDP.MKTP.KD.ZG --negara IDN  # pertumbuhan PDB Indonesia dari Bank Dunia
cari-sinyal backtest BBCA.JK --strategi momentum  # sma, momentum, rsi, bollinger, ml; biaya default 15 bps
cari-sinyal backtest BBCA.JK --strategi ml        # regresi linear walk-forward
cari-sinyal sinyal TLKM.JK                        # LONG atau KELUAR untuk hari ini
cari-sinyal paper beli BBRI.JK 500                # beli 500 lembar di harga penutupan terakhir
cari-sinyal paper jual BBRI.JK 200
cari-sinyal paper posisi
ANTHROPIC_API_KEY=... cari-sinyal riset BBCA.JK "Bagaimana risiko 6 bulan ke depan?" --agen risiko skeptis
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
- **Agen**: semua agen menerima paket yang sama: ringkasan harga, indikator terakhir, risiko, backtest SMA dan momentum, evaluasi model ML, serta yield US 10 tahun dan Fed funds. Paket itu bisa dilihat di bawah jawaban. Agen diminta membahas data tanpa memberi perintah beli atau jual.
- **Portofolio**: bobot dicari dengan sampel acak. Untuk 2 sampai 10 saham hasilnya cukup dekat; untuk puluhan saham sampel acak mulai meleset.

Pada data acak, strategi ML yang sering berganti posisi kalah dari beli-tahan karena biaya. Cek angka `--biaya` sesuai broker sebelum percaya hasil backtest.

## Yang tidak ikut

Inspirasinya FinceptTerminal, awesome-quant, dan Machine Learning for Trading. Bagian ini sengaja tidak dibuat: data laporan keuangan (tidak ada sumber gratis yang stabil untuk IDX), data intraday, broker sungguhan, model deep learning, dan analisis sentimen berita.

## Tes

```bash
pip install -e ".[dev]" && pytest
```

Tes tidak butuh internet.

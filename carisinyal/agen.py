"""Agen riset berbasis Claude. Pakai API key sendiri (ANTHROPIC_API_KEY atau isian di UI)."""
MODEL = "claude-opus-5-5"

UMUM = ("Tulis dalam bahasa Indonesia, ringkas, pakai angka dari data yang diberikan. "
        "Sebut apa yang perlu dicek lagi. Jangan memberi perintah beli atau jual.")

AGEN = {
    "teknikal": ("Analis Teknikal", "Baca tren, momentum, RSI, MACD, dan pita Bollinger."),
    "fundamental": ("Analis Fundamental", "Nilai bisnis di balik saham: sektor, posisi pasar, dan risiko bisnis. "
                    "Akui kalau data laporan keuangan tidak tersedia di konteks."),
    "makro": ("Analis Makro", "Hubungkan suku bunga, inflasi, dan pertumbuhan ekonomi dengan aset ini."),
    "risiko": ("Manajer Risiko", "Fokus ke volatilitas, VaR, drawdown, beta, dan skenario terburuk."),
    "kuant": ("Analis Kuant", "Nilai hasil backtest dan model ML: overfitting, biaya, dan ukuran sampel."),
    "skeptis": ("Si Skeptis", "Cari kelemahan di argumen yang paling optimis dan tunjukkan data yang bertentangan."),
}


def tanya(agen, pertanyaan, konteks, api_key=None):
    import anthropic  # opsional: pip install ".[riset]"

    nama, peran = AGEN[agen]
    resp = anthropic.Anthropic(api_key=api_key or None).beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=f"Kamu {nama}. {peran} {UMUM}",
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": f"Data:\n{konteks}\n\nPertanyaan: {pertanyaan}"}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("model menolak permintaan ini")
    return "".join(b.text for b in resp.content if b.type == "text")

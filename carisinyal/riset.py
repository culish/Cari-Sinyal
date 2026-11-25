"""Catatan riset dari Claude. Pakai API key sendiri (ANTHROPIC_API_KEY)."""
MODEL = "claude-opus-5-5"

SISTEM = (
    "Kamu analis riset pasar. Tulis dalam bahasa Indonesia, ringkas, pakai angka dari data. "
    "Bahas tren, risiko, dan apa yang perlu dicek lagi. Jangan memberi perintah beli atau jual."
)


def tanya(pertanyaan, konteks):
    import anthropic  # opsional: pip install ".[riset]"

    client = anthropic.Anthropic()
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SISTEM,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": f"Data:\n{konteks}\n\nPertanyaan: {pertanyaan}"}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("model menolak permintaan ini")
    return "".join(b.text for b in resp.content if b.type == "text")

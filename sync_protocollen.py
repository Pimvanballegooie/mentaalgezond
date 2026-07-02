#!/usr/bin/env python3
"""
Sync protocollen vanuit Google Docs naar statische HTML-pagina's.
Zelfde systeem als kansrijkopgroeien.net, met Mentaal Gezond (teal) styling.

Gebruik:
1. Voeg protocollen toe aan protocollen-config.json:
   {
     "protocollen": [
       {
         "slug": "hyperventilatie",
         "titel": "Hyperventilatie",
         "categorie": "Ademhaling",
         "omschrijving": "Behandelprotocol voor hyperventilatie en disfunctioneel ademen",
         "doc_id_ouders": "GOOGLE_DOC_ID_LEESBARE_VERSIE",
         "doc_id_therapeuten": "GOOGLE_DOC_ID_KLINISCHE_VERSIE"
       }
     ]
   }
2. Draai: python3 sync_protocollen.py
3. GitHub Action draait dit nachtelijks automatisch.

Shortcodes in Google Docs:
[CALLOUT] tekst [/CALLOUT]  -> gekleurd infoblok
[TABEL] ... [/TABEL]        -> tabel styling
[VIDEO] youtube-url [/VIDEO] -> embedded video
"""

import json
import re
import urllib.request
import html as html_lib
from pathlib import Path

CONFIG_FILE = "protocollen-config.json"
OUTPUT_DIR = Path("protocollen")

# Mentaal Gezond kleuren
KLEUREN = {
    "primair": "#2A9D8F",
    "primair_light": "#E8F5F4",
    "primair_dark": "#1f7a6e",
    "navy": "#264653",
    "navy_dark": "#1a2f38",
}

PAGINA_TEMPLATE = """<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{titel} – Mentaal Gezond</title>
  <meta name="description" content="{omschrijving}" />
  <style>
    @font-face {{ font-family: 'Inter'; src: url('../fonts/inter-v20-latin-regular.woff2') format('woff2'); font-weight: 400; font-display: swap; }}
    @font-face {{ font-family: 'Inter'; src: url('../fonts/inter-v20-latin-700.woff2') format('woff2'); font-weight: 700; font-display: swap; }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{ --teal: {primair}; --teal-light: {primair_light}; --navy: {navy}; --navy-dark: {navy_dark}; --grey-bg: #F8F9FA; --grey-border: #E8ECF0; --text: {navy}; --text-muted: #6B7A7E; }}
    body {{ font-family: 'Inter', sans-serif; font-size: 16px; color: var(--text); background: white; line-height: 1.75; }}
    header {{ background: white; border-bottom: 1px solid var(--grey-border); padding: 0 24px; position: sticky; top: 0; z-index: 100; }}
    .header-inner {{ max-width: 800px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; height: 64px; }}
    .logo {{ font-weight: 700; color: var(--navy); text-decoration: none; }}
    .logo span {{ color: var(--teal); }}
    .terug {{ color: var(--teal); text-decoration: none; font-size: 0.85rem; font-weight: 600; }}
    .versie-tabs {{ max-width: 800px; margin: 24px auto 0; padding: 0 24px; display: flex; gap: 8px; }}
    .versie-tab {{ padding: 10px 20px; border-radius: 10px 10px 0 0; font-size: 0.88rem; font-weight: 600; cursor: pointer; border: 1px solid var(--grey-border); border-bottom: none; background: var(--grey-bg); color: var(--text-muted); }}
    .versie-tab.actief {{ background: white; color: var(--teal); border-color: var(--teal); }}
    .content {{ max-width: 800px; margin: 0 auto; padding: 32px 24px 80px; }}
    .versie {{ display: none; }}
    .versie.actief {{ display: block; }}
    h1 {{ font-size: 1.7rem; font-weight: 700; color: var(--navy); margin-bottom: 20px; }}
    h2 {{ font-size: 1.2rem; font-weight: 700; color: var(--navy); margin: 28px 0 12px; }}
    h3 {{ font-size: 1.02rem; font-weight: 700; color: var(--navy); margin: 20px 0 8px; }}
    p {{ margin-bottom: 12px; }}
    ul, ol {{ margin: 8px 0 16px 24px; }}
    li {{ margin-bottom: 6px; }}
    .callout {{ background: var(--teal-light); border-left: 4px solid var(--teal); border-radius: 0 10px 10px 0; padding: 16px 20px; margin: 16px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.9rem; }}
    th, td {{ border: 1px solid var(--grey-border); padding: 10px 14px; text-align: left; }}
    th {{ background: var(--teal-light); color: var(--navy); font-weight: 700; }}
    .video-wrap {{ position: relative; padding-bottom: 56.25%; margin: 16px 0; border-radius: 12px; overflow: hidden; }}
    .video-wrap iframe {{ position: absolute; inset: 0; width: 100%; height: 100%; border: none; }}
    footer {{ background: var(--navy-dark); color: rgba(255,255,255,0.4); text-align: center; padding: 24px; font-size: 0.78rem; }}
  </style>
</head>
<body>
<header>
  <div class="header-inner">
    <a href="../index.html" class="logo"><span>Mentaal</span> Gezond</a>
    <a href="../protocollen.html" class="terug">← Alle protocollen</a>
  </div>
</header>
<div class="versie-tabs">
  <div class="versie-tab actief" onclick="toonVersie('ouders', this)">📗 Voor patiënten</div>
  <div class="versie-tab" onclick="toonVersie('therapeuten', this)">📕 Voor therapeuten</div>
</div>
<div class="content">
  <div class="versie actief" id="versie-ouders">{inhoud_ouders}</div>
  <div class="versie" id="versie-therapeuten">{inhoud_therapeuten}</div>
</div>
<footer><p>© 2026 Mentaal Gezond · Automatisch gesynchroniseerd vanuit Google Docs</p></footer>
<script>
function toonVersie(naam, el) {{
  document.querySelectorAll('.versie-tab').forEach(t => t.classList.remove('actief'));
  document.querySelectorAll('.versie').forEach(v => v.classList.remove('actief'));
  el.classList.add('actief');
  document.getElementById('versie-' + naam).classList.add('actief');
}}
</script>
</body>
</html>"""


def haal_google_doc_html(doc_id):
    """Download Google Doc als HTML via export URL."""
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        print(f"  ⚠ Kon doc {doc_id} niet ophalen: {e}")
        return None


def schoon_google_html(raw_html):
    """Extraheer body-inhoud en verwijder Google styling."""
    if not raw_html:
        return "<p><em>Inhoud kon niet worden geladen.</em></p>"
    body_match = re.search(r'<body[^>]*>(.*)</body>', raw_html, re.DOTALL)
    inhoud = body_match.group(1) if body_match else raw_html
    # Verwijder Google inline styles en classes
    inhoud = re.sub(r'\sstyle="[^"]*"', '', inhoud)
    inhoud = re.sub(r'\sclass="[^"]*"', '', inhoud)
    inhoud = re.sub(r'<span>', '', inhoud)
    inhoud = re.sub(r'</span>', '', inhoud)
    # Verwerk shortcodes
    inhoud = re.sub(r'\[CALLOUT\](.*?)\[/CALLOUT\]', r'<div class="callout">\1</div>', inhoud, flags=re.DOTALL)
    inhoud = re.sub(r'\[TABEL\](.*?)\[/TABEL\]', r'\1', inhoud, flags=re.DOTALL)
    def video_embed(m):
        url = m.group(1).strip()
        vid_match = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]+)', url)
        if vid_match:
            return f'<div class="video-wrap"><iframe src="https://www.youtube.com/embed/{vid_match.group(1)}" allowfullscreen></iframe></div>'
        return ''
    inhoud = re.sub(r'\[VIDEO\](.*?)\[/VIDEO\]', video_embed, inhoud, flags=re.DOTALL)
    return inhoud


def main():
    config = json.loads(Path(CONFIG_FILE).read_text(encoding='utf-8'))
    protocollen = config.get('protocollen', [])
    if not protocollen:
        print("Geen protocollen in config — niets te doen.")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)

    for p in protocollen:
        print(f"→ {p['titel']}")
        inhoud_ouders = schoon_google_html(haal_google_doc_html(p.get('doc_id_ouders', ''))) if p.get('doc_id_ouders') else '<p><em>Nog geen patiëntversie beschikbaar.</em></p>'
        inhoud_therapeuten = schoon_google_html(haal_google_doc_html(p.get('doc_id_therapeuten', ''))) if p.get('doc_id_therapeuten') else '<p><em>Nog geen klinische versie beschikbaar.</em></p>'

        pagina = PAGINA_TEMPLATE.format(
            titel=html_lib.escape(p['titel']),
            omschrijving=html_lib.escape(p.get('omschrijving', '')),
            inhoud_ouders=inhoud_ouders,
            inhoud_therapeuten=inhoud_therapeuten,
            **KLEUREN
        )
        out = OUTPUT_DIR / f"{p['slug']}.html"
        out.write_text(pagina, encoding='utf-8')
        print(f"  ✓ {out}")

    print(f"\n✓ {len(protocollen)} protocollen gesynchroniseerd.")


if __name__ == '__main__':
    main()

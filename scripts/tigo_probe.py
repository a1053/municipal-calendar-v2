"""Explora tigosports.gt con un navegador (solo lectura): texto visible, enlaces y llamadas JSON."""
import json, re
from playwright.sync_api import sync_playwright

PAGES = ["https://www.tigosports.gt/", "https://tigosports.gt/liga-nacional", "https://tigosports.gt/liga-nacional/en-la-jugada-fracaso-de-municipal",
         "https://www.tigosports.gt/en-vivo"]
with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(locale="es-GT", user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36")
    for url in PAGES:
        page = ctx.new_page()
        calls = []
        page.on("response", lambda r, calls=calls: calls.append((r.status, r.request.resource_type, r.url)) if r.request.resource_type in ("xhr", "fetch") else None)
        print("\n#####", url)
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(2500)
        except Exception as e:  # noqa: BLE001
            print(" error:", type(e).__name__, str(e)[:120])
        print(" título:", page.title(), "| url final:", page.url)
        txt = re.sub(r"\n\s*\n+", "\n", page.inner_text("body"))
        print(" texto (1200):", txt[:1200].replace("\n", " | "))
        links = page.eval_on_selector_all("a[href]", "els => els.map(e => [e.innerText.trim().slice(0,50), e.href])")
        seen, n = set(), 0
        for t, h in links:
            if "tigosports.gt" in h and h not in seen and n < 40:
                seen.add(h); n += 1; print("  ->", t, h)
        print(" llamadas xhr/fetch:")
        for st, rt, u in calls[:25]:
            print("  ", st, u[:170])
        page.close()
    br.close()

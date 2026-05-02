import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(ignore_https_errors=True)
        
        print("Navegando a CENACE...")
        await page.goto(
            "https://www.cenace.gob.ec/info-operativa/InformacionOperativa.htm",
            wait_until="networkidle",
            timeout=30000
        )
        await page.wait_for_timeout(4000)

        # --- 1. Conteo de elementos clave ---
        elementos = {
            "table":  await page.query_selector_all("table"),
            "iframe": await page.query_selector_all("iframe"),
            "img":    await page.query_selector_all("img"),
            "canvas": await page.query_selector_all("canvas"),
            "div":    await page.query_selector_all("div"),
        }
        print("\n=== ELEMENTOS EN EL DOM ===")
        for tag, lista in elementos.items():
            print(f"  <{tag}>: {len(lista)}")

        # --- 2. Mostrar iframes (muy común en dashboards de energía) ---
        iframes = await page.query_selector_all("iframe")
        print("\n=== IFRAMES ENCONTRADOS ===")
        if not iframes:
            print("  Ninguno")
        for i, fr in enumerate(iframes):
            src = await fr.get_attribute("src") or "(sin src)"
            print(f"  [{i}] src={src}")

        # --- 3. Mostrar imágenes (pueden contener los datos como PNG) ---
        imgs = await page.query_selector_all("img")
        print("\n=== IMÁGENES ENCONTRADAS ===")
        if not imgs:
            print("  Ninguna")
        for i, img in enumerate(imgs[:20]):  # máximo 20
            src = await img.get_attribute("src") or "(sin src)"
            print(f"  [{i}] {src}")

        # --- 4. Texto visible en la página ---
        texto = await page.inner_text("body")
        print("\n=== TEXTO VISIBLE (primeros 1000 chars) ===")
        print(texto[:1000])

        # --- 5. Requests de red capturados ---
        print("\n=== URLs DE RED CAPTURADAS ===")
        urls_red = []
        page.on("request", lambda req: urls_red.append(req.url))
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(4000)
        for url in urls_red:
            if any(x in url for x in ["json", "api", "data", "cenace", ".png", ".jpg", "ajax"]):
                print(f"  {url}")

        # --- 6. Guardar HTML completo ---
        html = await page.content()
        with open("cenace_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\nHTML guardado ({len(html):,} bytes) → cenace_debug.html")

        await browser.close()

asyncio.run(main())
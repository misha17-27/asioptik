import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for lang, w in (('en', 320), ('en', 300), ('ru', 840), ('az', 300), ('ru', 300)):
            ctx = await b.new_context(viewport={'width': w, 'height': 800})
            pg = await ctx.new_page(); await setup(pg)
            await pg.goto(f'{BASE}/dist/optika-4-lupa.html?lang={lang}'); await pg.wait_for_timeout(800)
            r = await pg.evaluate("""() => { const vw = document.documentElement.clientWidth; return [...document.querySelectorAll('body *')].filter(e => { if (e.closest('#loupe, .layer, .hs-slide:not(.is-active), .tabs')) return false; const cs = getComputedStyle(e); if (cs.position === 'fixed' || cs.visibility === 'hidden') return false; const r = e.getBoundingClientRect(); return r.width && r.right > vw + 0.5; }).slice(0, 8).map(e => e.tagName + '.' + String(e.className.baseVal != null ? e.className.baseVal : e.className).split(' ').slice(0, 2).join('.') + ' «' + e.textContent.trim().slice(0, 24) + '» right=' + Math.round(e.getBoundingClientRect().right)); }""")
            print(lang, w, 'overflow', await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), r)
            await ctx.close()
        await b.close()
asyncio.run(main())

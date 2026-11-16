import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, mob in ((414, True), (414, False), (412, True), (428, True), (375, True)):
            ctx = await b.new_context(viewport={'width': w, 'height': 896}, is_mobile=mob, has_touch=mob)
            pg = await ctx.new_page(); await setup(pg)
            await pg.goto(f'{BASE}/dist/optika-4-lupa.html'); await pg.wait_for_timeout(900)
            r = await pg.evaluate("""() => { const d = document.documentElement, vw = d.clientWidth; const wide = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.right > vw + 0.2 && !e.closest('.layer') && getComputedStyle(e).position !== 'fixed'; }).slice(0, 6).map(e => e.tagName + '.' + String(e.className.baseVal != null ? e.className.baseVal : e.className).split(' ')[0] + ' right=' + e.getBoundingClientRect().right.toFixed(2)); return { inner: innerWidth, client: vw, scroll: d.scrollWidth, body: document.body.scrollWidth, wide }; }""")
            print(w, 'mobile' if mob else 'desktop', r)
            await ctx.close()
        await b.close()
asyncio.run(main())

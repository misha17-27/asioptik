import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        bad = []
        for lang in ('az', 'ru', 'en'):
            ctx = await b.new_context(viewport={'width': 400, 'height': 800})
            pg = await ctx.new_page(); await setup(pg)
            await pg.goto(f'{BASE}/dist/optika-4-lupa.html?lang={lang}'); await pg.wait_for_timeout(700)
            for w in list(range(300, 520, 4)) + list(range(520, 1500, 20)):
                await pg.set_viewport_size({'width': w, 'height': 800}); await pg.wait_for_timeout(190)
                o = await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                h = await pg.evaluate("(() => { const r = document.querySelector('.hdr-right').getBoundingClientRect(), l = document.querySelector('.logo').getBoundingClientRect(), n = document.getElementById('siteNav'); const nr = n.offsetParent && getComputedStyle(n).position !== 'absolute' ? n.getBoundingClientRect().right : l.right; return Math.round(r.left - nr); })()")
                if o > 0 or h < 4: bad.append((lang, w, o, h))
            await ctx.close()
        await b.close()
        print('widths with overflow or a cramped header:', bad or 'none')
asyncio.run(main())

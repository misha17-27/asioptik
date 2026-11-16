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
            for prod in ('c-toric', 'f-florence', 'l-prog'):
                await pg.goto(f'{BASE}/dist/optika-4-lupa.html?lang={lang}&product={prod}'); await pg.wait_for_timeout(500)
                if prod == 'f-florence':
                    await pg.locator('label:has(#pp-lens-yes)').click(); await pg.wait_for_timeout(150)
                    await pg.locator('label:has(#pp-lt-l-photo)').click(); await pg.wait_for_timeout(150)
                for w in list(range(300, 620, 8)) + list(range(620, 1500, 40)):
                    await pg.set_viewport_size({'width': w, 'height': 800}); await pg.wait_for_timeout(30)
                    o = await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                    clip = await pg.evaluate("[...document.querySelectorAll('#ppForm select, #ppForm .choice b, #ppForm .rxb-eye, #ppForm .btn, .pp-total b')].filter(e => e.scrollWidth > e.clientWidth + 3 && e.tagName !== 'SELECT').map(e => e.className || e.tagName).slice(0, 3)")
                    if o > 0 or clip: bad.append((lang, prod, w, o, clip))
            await ctx.close()
        await b.close()
        print('product pages, problem widths:', bad[:12] or 'none', '| total', len(bad))
asyncio.run(main())

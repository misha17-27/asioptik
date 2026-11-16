import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for vp, tag in (({'width': 1440, 'height': 900}, 'd'), ({'width': 390, 'height': 844}, 'm'), ({'width': 1024, 'height': 768}, 't')):
            ctx = await b.new_context(viewport=vp, device_scale_factor=1)
            pg = await ctx.new_page(); await setup(pg)
            await pg.goto(f'{BASE}/dist/optika-4-lupa.html?lang=en'); await pg.wait_for_timeout(1200)
            for lang in ('en', 'az', 'ru'):
                if lang != 'en':
                    await pg.locator(f'.hdr-right [data-set-lang="{lang}"]').click(); await pg.wait_for_timeout(400)
                await pg.locator('#eye').scroll_into_view_if_needed(); await pg.wait_for_timeout(2600)
                r = await pg.evaluate("""[...document.querySelectorAll('.chart-row:not(.r6) b')].map(b => b.textContent + ' ' + getComputedStyle(b).fontSize + ' ls=' + (parseFloat(getComputedStyle(b).letterSpacing)/parseFloat(getComputedStyle(b).fontSize)).toFixed(2) + ' over=' + (b.scrollWidth - b.clientWidth))""")
                print(tag, lang, r)
                await pg.locator('.chart').screenshot(path=f'{ROOT}/shots/v4-chart-{tag}-{lang}.png')
            await ctx.close()
        await b.close()
asyncio.run(main())

import asyncio
from playwright.async_api import async_playwright
from run import setup, BASE, ROOT
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, h, tag in ((1440, 900, 'd'), (1000, 900, 't'), (700, 900, 's'), (390, 844, 'm')):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1 if w > 800 else 2)
            pg = await ctx.new_page(); await setup(pg)
            await pg.goto(f'{BASE}/dist/optika-4-lupa.html'); await pg.wait_for_timeout(1500)
            el = pg.locator('#kids .sb'); await el.scroll_into_view_if_needed(); await pg.wait_for_timeout(300)
            await el.screenshot(path=f'{ROOT}/shots/kids-{tag}.png')
            box = await el.bounding_box(); o = await pg.evaluate('document.documentElement.scrollWidth - innerWidth')
            print(tag, w, 'banner', round(box['width']), 'x', round(box['height']), '| overflow x:', o)
            await ctx.close()
        await b.close()
asyncio.run(main())

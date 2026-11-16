"""Снимки после смены логотипа и палитры: шапка, первый экран, секции, товар, корзина."""
import asyncio
import sys
from playwright.async_api import async_playwright
from run import setup, BASE, ROOT

URL = f'{BASE}/dist/optika-4-lupa.html'
SH = f'{ROOT}/shots'


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors = []
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
        pg = await ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        await setup(pg)
        await pg.goto(URL + '?lang=ru')
        await pg.wait_for_timeout(2600)
        await pg.screenshot(path=f'{SH}/br-d-hero.png')
        await pg.screenshot(path=f'{SH}/br-d-full.png', full_page=True)
        # шапка крупно
        await pg.screenshot(path=f'{SH}/br-d-header.png', clip={'x': 0, 'y': 0, 'width': 1440, 'height': 90})
        # лупа над текстом
        box = await pg.locator('.hero h1').first.bounding_box()
        if box:
            await pg.mouse.move(box['x'] + box['width'] * .45, box['y'] + box['height'] * .5)
            await pg.wait_for_timeout(500)
            await pg.screenshot(path=f'{SH}/br-d-loupe.png')
        # страница товара
        await pg.goto(URL + '?lang=ru&product=c-daily')
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path=f'{SH}/br-d-pp.png')
        await pg.goto(URL + '?lang=ru&product=f-milan')
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path=f'{SH}/br-d-pp-frame.png', full_page=True)
        await ctx.close()

        for w, tag in ((390, 'm390'), (360, 'm360'), (820, 't820')):
            ctx = await b.new_context(viewport={'width': w, 'height': 844 if w < 600 else 1100}, device_scale_factor=2, is_mobile=w < 600, has_touch=True)
            pg = await ctx.new_page()
            pg.on('pageerror', lambda e: errors.append(f'pageerror({w}): {e}'))
            await setup(pg)
            await pg.goto(URL)
            await pg.wait_for_timeout(2600)
            await pg.screenshot(path=f'{SH}/br-{tag}-hero.png')
            if w == 390:
                await pg.screenshot(path=f'{SH}/br-{tag}-full.png', full_page=True)
            await ctx.close()
        await b.close()
        print('console:', errors or 'clean')

asyncio.run(main())

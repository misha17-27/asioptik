"""Слайды первого экрана с фотографиями: кадрирование, читаемость текста, запасной рисунок.
Настоящие фото лежат на фотостоке; здесь их заменяют уменьшенные образцы из test/fake/ph (нет образца — запрос обрывается)."""
import asyncio, os, re, sys
from playwright.async_api import async_playwright
from run import setup, ROOT
SH = f'{ROOT}/shots'; PHP = 'http://127.0.0.1:8771'
async def stock(route):
    m = re.search(r'/photos/(\d+)/', route.request.url); f = f'{ROOT}/test/fake/ph/{m.group(1)}.jpg' if m else ''
    if f and os.path.exists(f): await route.fulfill(path=f, content_type='image/jpeg')
    else: await route.abort()
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for tag, w, h in (('d', 1440, 900), ('m', 390, 844)):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if tag == 'm' else 1); pg = await ctx.new_page(); await setup(pg)
            errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('https://images.pexels.com/**', stock)
            await pg.goto(PHP + '/ru'); await pg.wait_for_timeout(1500)
            await pg.evaluate("document.querySelector('.hero-inner:not(.is-clone) [data-hs=toggle]').click()")   # остановить смену слайдов
            n = await pg.locator('.hero-inner:not(.is-clone) .hs-dot').count()
            for k in range(0, n - 1):
                await pg.locator('.hero-inner:not(.is-clone) .hs-dot').nth(k).click(); await pg.wait_for_timeout(900)
                info = await pg.evaluate("""() => { const s = document.querySelector('.hero-inner:not(.is-clone) .hs-slide.is-active'), ph = s.querySelector('.ph'), box = s.querySelector('.bn-in'); return { cls: s.className.replace('hs-slide ', '').replace(' is-active', ''), photo: !!ph && box.classList.contains('has-photo'), nat: ph ? [ph.naturalWidth, ph.naturalHeight] : null, pos: ph ? ph.style.objectPosition : '', flip: ph ? ph.classList.contains('is-flip') : false, arts: getComputedStyle(s.querySelector('.bn-arts')).visibility, title: s.querySelector('.bn-title').textContent }; }""")
                print(tag, k, info)
                await pg.locator('.hero-inner:not(.is-clone) .hs-track').screenshot(path=f'{SH}/hero-{tag}-{k + 1}.png')
            if tag == 'd': await pg.screenshot(path=f'{SH}/hero-d-full.png')
            print(tag, 'errors:', errs or 'none'); await ctx.close()
        await b.close()
asyncio.run(main())

"""Страницы «Взрослым» и «Детям»: ссылки меню ведут на страницу каталога с товарами и разделами только для них."""
import asyncio, sys, urllib.request
from playwright.async_api import async_playwright
from run import setup, ROOT
SH = f'{ROOT}/shots'
PHP = 'http://127.0.0.1:8771'; ONE = 'http://127.0.0.1:8765/dist/optika-4-lupa.html'
INFO = """() => { const q = s => document.querySelector(s); const vis = el => !!el && el.getClientRects().length > 0;
  return { url: location.pathname.split('/').pop() + location.search + location.hash, title: document.title, h1: q('#pgTitle') ? q('#pgTitle').textContent : '—', lead: (q('.pg-lead') || {}).textContent || '',
    crumbs: [...document.querySelectorAll('#pageView .pp-crumbs a')].map(a => a.textContent), parts: [...document.querySelectorAll('.pg-parts a')].map(a => a.textContent),
    tiles: [...document.querySelectorAll('#pageView .ctile')].map(a => a.querySelector('b').textContent + ' | ' + a.querySelector('.ctile-body span').textContent + ' | ' + a.getAttribute('href')),
    cards: document.querySelectorAll('#productsGrid > *').length, current: [...document.querySelectorAll('#siteNav a[aria-current=page]')].map(a => a.textContent),
    switchOn: [...document.querySelectorAll('[data-aud-switch] .is-active')].map(b => b.textContent), canon: q('link[rel=canonical]').getAttribute('href'), ox: document.documentElement.scrollWidth - innerWidth }; }"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for name, base, home in (('php', PHP, PHP + '/?lang=ru'), ('one file', ONE, ONE + '?lang=ru')):
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); pg = await ctx.new_page(); await setup(pg)
            errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'ERR_' not in m.text and 'font' not in m.text.lower() and '404' not in m.text else None)
            await pg.route('https://images.pexels.com/**', lambda r: r.abort())
            await pg.goto(home); await pg.wait_for_timeout(1200)
            print(f'--- {name}'); print('menu links:', await pg.evaluate("[...document.querySelectorAll('#siteNav a[data-aud]')].map(a => a.textContent + ' → ' + a.getAttribute('href'))"))
            await pg.locator('#siteNav a[data-aud=kids]').click(); await pg.wait_for_timeout(700); print('kids:', await pg.evaluate(INFO))
            if name == 'php': await pg.screenshot(path=f'{SH}/aud-kids-d.png')
            await pg.locator('#siteNav a[data-aud=adults]').click(); await pg.wait_for_timeout(700); print('adults:', await pg.evaluate(INFO))
            if name == 'php': await pg.screenshot(path=f'{SH}/aud-adults-d.png')
            await pg.locator('.pg-parts a').first.click(); await pg.wait_for_timeout(700); print('men:', await pg.evaluate(INFO))
            await pg.locator('#pageView .ctile').first.click(); await pg.wait_for_timeout(700); print('men → first tile:', await pg.evaluate(INFO))
            # отбор «для кого» в самом каталоге меняет и шапку страницы
            await pg.locator('[data-aud-switch] [data-key=kids]').click(); await pg.wait_for_timeout(500); print('switch to kids:', await pg.evaluate(INFO))
            await pg.locator('[data-aud-switch] [data-key=""]').click(); await pg.wait_for_timeout(500); print('switch to all:', await pg.evaluate(INFO))
            await pg.go_back(); await pg.wait_for_timeout(700); print('back:', (await pg.evaluate(INFO))['url'], '|', (await pg.evaluate(INFO))['h1'])
            # прямой заход по адресу и смена языка
            await pg.goto((base + '/catalog?aud=kids&lang=az') if name == 'php' else (base + '?page=catalog&aud=kids&lang=az')); await pg.wait_for_timeout(1200); i = await pg.evaluate(INFO); print('direct az:', i['title'], '|', i['h1'], '|', i['tiles'], '|', i['current'])
            await pg.locator('.hdr-right [data-set-lang=en]').click(); await pg.wait_for_timeout(600); i = await pg.evaluate(INFO); print('→ en:', i['title'], '|', i['h1'], '|', i['crumbs'], '|', i['current'])
            # со страницы товара ссылка меню тоже открывает страницу раздела
            await pg.goto((base + '/product/f-milan?lang=ru') if name == 'php' else (base + '?product=f-milan&lang=ru')); await pg.wait_for_timeout(1000)
            await pg.locator('#siteNav a[data-aud=adults]').click(); await pg.wait_for_timeout(700); i = await pg.evaluate(INFO); print('from product:', i['url'], '|', i['h1'], '| cards', i['cards'])
            print('errors:', errs or 'none'); await ctx.close()
            # телефон
            ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True); pg = await ctx.new_page(); await setup(pg)
            await pg.route('https://images.pexels.com/**', lambda r: r.abort())
            await pg.goto(home); await pg.wait_for_timeout(1000); await pg.locator('.hdr-right .js-menu-toggle').click(); await pg.wait_for_timeout(400)
            await pg.locator('#siteNav a[data-aud=kids]').click(); await pg.wait_for_timeout(700); i = await pg.evaluate(INFO); print('m kids:', i['url'], '|', i['h1'], '| tiles', len(i['tiles']), '| cards', i['cards'], '| overflow', i['ox'], '| menu open:', await pg.evaluate("document.body.classList.contains('menu-open')"))
            if name == 'php': await pg.screenshot(path=f'{SH}/aud-kids-m.png')
            await ctx.close()
        await b.close()
asyncio.run(main())

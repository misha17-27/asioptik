"""Снимки экранов админ-панели для просмотра глазами: обзор, заказы, клиенты, страницы, товары, формы."""
import asyncio, os, sys
from playwright.async_api import async_playwright
from run import ROOT
B = 'http://127.0.0.1:8771'; SH = f'{ROOT}/shots'; PW = 'Test-Admin-2026'   # пароль только для локальной тестовой базы
PAGES = [('home', '/admin/'), ('orders', '/admin/?p=orders'), ('clients', '/admin/?p=clients'), ('pages', '/admin/?p=pages'), ('page-home', '/admin/?p=page&id=home'),
         ('products', '/admin/?p=list&type=product'), ('product-new', '/admin/?p=edit&type=product&cat=frames'), ('brands', '/admin/?p=list&type=brand'), ('posts', '/admin/?p=list&type=post'), ('banners', '/admin/?p=banners')]
FULL = os.environ.get('FULL') == '1'   # FULL=1 — снимать страницу целиком, а не только видимую часть
async def main():
    only = sys.argv[1:]
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors = []
        for tag, w, h in (('d', 1440, 900), ('m', 390, 844)):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if tag == 'm' else 1); pg = await ctx.new_page()
            pg.on('pageerror', lambda e: errors.append(str(e))); pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
            pg.on('response', lambda r: errors.append(f'{r.status} {r.url}') if r.status >= 400 else None)
            await pg.goto(B + '/admin/'); await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click(); await pg.wait_for_load_state()
            for name, url in PAGES:
                if only and name not in only: continue
                await pg.goto(B + url); await pg.wait_for_timeout(350)
                ox = await pg.evaluate('document.documentElement.scrollWidth - innerWidth')
                print(tag, name, '| h1:', await pg.inner_text('h1'), '| overflow x:', ox)
                await pg.screenshot(path=f'{SH}/adm2-{tag}-{name}.png', full_page=FULL or (tag == 'm' and name in ('home', 'products')))
            await ctx.close()
        print('errors:', errors or 'none')
        await b.close()
asyncio.run(main())

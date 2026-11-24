"""Мобильное меню: на весь экран, сверху логотип и «закрыть», внизу язык и контакты."""
import asyncio
from playwright.async_api import async_playwright
from run import setup, ROOT
SH = f'{ROOT}/shots'
PHP = 'http://127.0.0.1:8771'
INFO = """() => { const nav = document.querySelector('#siteNav'), r = nav.getBoundingClientRect(), cs = getComputedStyle(nav); const vis = el => !!el && el.getClientRects().length > 0;
  const foot = nav.querySelector('.nav-foot').getBoundingClientRect();
  return { open: document.body.classList.contains('menu-open'), shown: cs.display !== 'none', box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], view: [innerWidth, innerHeight],
    logo: vis(nav.querySelector('.nav-logo .logo-full')), close: vis(nav.querySelector('.nav-close')), links: [...nav.querySelectorAll('.nav-links a')].filter(vis).map(a => a.textContent),
    lang: [...nav.querySelectorAll('.nav-foot [data-set-lang]')].map(b => b.textContent + (b.classList.contains('is-active') ? '*' : '')), tel: nav.querySelector('.nav-tel').textContent + ' → ' + nav.querySelector('.nav-tel').getAttribute('href'),
    wa: (nav.querySelector('.nav-wa').getAttribute('href') || '').slice(0, 28), info: [...nav.querySelectorAll('.nav-info')].map(p => p.textContent.trim()),
    footBottom: Math.round(foot.bottom), scroll: nav.scrollHeight - nav.clientHeight, expanded: [...document.querySelectorAll('.js-menu-toggle')].map(b => b.getAttribute('aria-expanded')),
    inert: ['main', '.site-footer', '.hdr-right'].map(s => document.querySelector(s).inert), focus: document.activeElement.className, top: document.elementFromPoint(innerWidth - 40, innerHeight - 40).closest('#siteNav') ? 'menu' : 'page',
    bodyScroll: getComputedStyle(document.body).overflow, ox: document.documentElement.scrollWidth - innerWidth }; }"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for tag, w, h in (('m', 390, 844), ('s', 360, 640), ('t', 820, 1180)):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True); pg = await ctx.new_page(); await setup(pg)
            errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.route('https://images.pexels.com/**', lambda r: r.abort())
            await pg.goto(PHP + '/'); await pg.wait_for_timeout(1200)
            await pg.evaluate('window.scrollTo(0, 900)'); await pg.wait_for_timeout(300)   # шапка с размытием: меню всё равно должно занять весь экран
            await pg.locator('.hdr-right .js-menu-toggle').click(); await pg.wait_for_timeout(500)
            i = await pg.evaluate(INFO); print(f'--- {tag} {w}x{h}'); print('open:', i)
            await pg.screenshot(path=f'{SH}/menu-{tag}.png')
            await pg.locator('.nav-foot [data-set-lang=ru]').click(); await pg.wait_for_timeout(500); j = await pg.evaluate(INFO); print('→ ru, still open:', j['open'], '|', j['links'][:3], '|', j['lang'], '|', j['info'])
            if tag == 'm': await pg.screenshot(path=f'{SH}/menu-m-ru.png')
            await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300); j = await pg.evaluate(INFO); print('Escape:', j['open'], j['shown'], j['expanded'], j['inert'], '| focus:', j['focus'][:40], '| body:', j['bodyScroll'])
            await pg.locator('.hdr-right .js-menu-toggle').click(); await pg.wait_for_timeout(400); await pg.locator('.nav-close').click(); await pg.wait_for_timeout(300); print('close button:', (await pg.evaluate(INFO))['open'])
            await pg.locator('.hdr-right .js-menu-toggle').click(); await pg.wait_for_timeout(400); await pg.locator('#siteNav a[data-aud=kids]').click(); await pg.wait_for_timeout(700)
            j = await pg.evaluate(INFO); print('link closes menu:', j['open'], '|', await pg.evaluate("location.pathname + location.search"), '| h1:', await pg.inner_text('#pgTitle'), '| overflow', j['ox'])
            print('errors:', errs or 'none'); await ctx.close()
        # на широком экране меню обычное, логотип и низ меню скрыты
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); pg = await ctx.new_page(); await setup(pg); await pg.route('https://images.pexels.com/**', lambda r: r.abort())
        await pg.goto(PHP + '/ru'); await pg.wait_for_timeout(1000)
        print('--- desktop:', await pg.evaluate("""() => { const vis = el => !!el && el.getClientRects().length > 0, n = document.querySelector('#siteNav'); return { head: vis(n.querySelector('.nav-head')), foot: vis(n.querySelector('.nav-foot')), links: [...n.querySelectorAll('.nav-links a')].filter(vis).length, navH: Math.round(n.getBoundingClientRect().height), headerH: Math.round(document.querySelector('.site-header').getBoundingClientRect().height) }; }"""))
        await ctx.close(); await b.close()
asyncio.run(main())

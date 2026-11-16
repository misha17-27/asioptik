"""Баннеры секций «Для взрослых» и «Для детей»: вид на компьютере, планшете и телефоне, смена фото, кнопки коллекций."""
import asyncio, pathlib, sys
from playwright.async_api import async_playwright
from run import setup, BASE, ROOT
SH = ROOT / 'shots'
FAKE = ROOT / 'test' / 'fake'
async def fake_photos(pg, on=True):
    async def h(route):
        pid = route.request.url.split('/photos/')[1].split('/')[0]
        f = FAKE / f'{pid}.jpg'
        if on and f.exists(): await route.fulfill(status=200, content_type='image/jpeg', body=f.read_bytes())
        else: await route.abort()
    await pg.route('https://images.pexels.com/**', h)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors = []
        for tag, w, h, lang in (('d', 1440, 900, 'ru'), ('t', 900, 1100, 'az'), ('m', 390, 844, 'ru'), ('w', 1920, 1000, 'en')):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if tag == 'm' else 1)
            pg = await ctx.new_page(); await setup(pg); await fake_photos(pg)
            pg.on('pageerror', lambda e: errors.append(str(e))); pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'ERR_' not in m.text and 'font' not in m.text.lower() and '404' not in m.text else None)
            await pg.goto(f'{BASE}/dist/optika-4-lupa.html?lang={lang}'); await pg.wait_for_timeout(1500)
            for sec in ('adults', 'kids'):
                el = pg.locator(f'#{sec} .sb'); await el.scroll_into_view_if_needed(); await pg.wait_for_timeout(1300)
                info = await pg.evaluate("""(sec) => { const sb = document.querySelector('#' + sec + ' .sb'), r = sb.getBoundingClientRect(), h2 = sb.querySelector('h2').getBoundingClientRect(), cta = sb.querySelector('.sb-cta, .btn').getBoundingClientRect();
                    const feats = sb.querySelector('.sb-feats'); const fr = feats ? feats.getBoundingClientRect() : h2;
                    return { w: Math.round(r.width), h: Math.round(r.height), full: Math.round(r.left) === 0 && Math.round(r.width) === document.documentElement.clientWidth, photo: sb.classList.contains('has-photo'),
                      photos: [...sb.querySelectorAll(':scope > .ph')].map(i => (i.classList.contains('is-on') ? 'on ' : '') + (i.classList.contains('is-wide') ? 'wide' : i.classList.contains('is-tall') ? 'tall' : 'right')), h2: sb.querySelector('h2').innerText.replace(/\\n/g, ' / '),
                      textAboveButtons: Math.round(cta.top - Math.max(h2.bottom, fr.bottom)), overflowX: document.documentElement.scrollWidth - innerWidth }; }""", sec)
                print(tag, lang, sec, info)
                await el.screenshot(path=f'{SH}/bn-{tag}-{sec}.png')
            if tag == 'd':
                sb = pg.locator('#adults .sb')
                print('buttons:', await sb.locator('.sb-cta a').all_inner_texts(), '| feats:', await sb.locator('.sb-feats li').all_inner_texts(), '| dots:', await sb.locator('.sb-dot').count())
                await sb.locator('.sb-dot').nth(1).click(); await pg.wait_for_timeout(1100)
                print('dot 2 →', await pg.evaluate("[...document.querySelectorAll('#adults .sb > .ph')].map(i => i.classList.contains('is-on'))"), '| pressed:', await sb.locator('.sb-dot').evaluate_all("els => els.map(e => e.getAttribute('aria-pressed'))"), '| stopped:', await sb.get_attribute('data-stop'))
                await sb.screenshot(path=f'{SH}/bn-d-adults-2.png')
                await sb.locator('.sb-cta a').nth(1).click(); await pg.wait_for_timeout(900)
                print('women button →', pg.url.split('/')[-1], '| aud', await pg.evaluate('Shop.state.aud'), '| cards', await pg.locator('#productsGrid .card').count())
                await pg.go_back(); await pg.wait_for_timeout(700)
                await pg.locator('#kids .sb a.btn').click(); await pg.wait_for_timeout(900); print('kids button →', pg.url.split('/')[-1], '| cards', await pg.locator('#productsGrid .card').count())
                # смена фото сама по себе: ждём один шаг
                pg2 = await ctx.new_page(); await setup(pg2); await fake_photos(pg2); await pg2.goto(f'{BASE}/dist/optika-4-lupa.html?lang=ru'); await pg2.wait_for_timeout(800)
                await pg2.locator('#adults .sb').scroll_into_view_if_needed(); await pg2.mouse.move(5, 5); await pg2.wait_for_timeout(6600)
                print('auto change after 6 s:', await pg2.evaluate("[...document.querySelectorAll('#adults .sb > .ph')].map(i => i.classList.contains('is-on'))"))
                # без фото: остаётся рисунок
                pg3 = await ctx.new_page(); await setup(pg3); await fake_photos(pg3, False); await pg3.goto(f'{BASE}/dist/optika-4-lupa.html?lang=ru'); await pg3.wait_for_timeout(900)
                for sec in ('adults', 'kids'):
                    el = pg3.locator(f'#{sec} .sb'); await el.scroll_into_view_if_needed(); await pg3.wait_for_timeout(900); await el.screenshot(path=f'{SH}/bn-d-{sec}-nophoto.png')
                    print('no photos', sec, await pg3.evaluate("(s) => { const sb = document.querySelector('#' + s + ' .sb'); return { photo: sb.classList.contains('has-photo'), imgs: sb.querySelectorAll(':scope > .ph').length, art: getComputedStyle(sb.querySelector('.sb-art')).visibility }; }", sec))
            await ctx.close()
        print('errors:', errors or 'none')
        await b.close()
asyncio.run(main())

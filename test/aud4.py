import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright
from PIL import Image
F = f'{BASE}/dist/optika-4-lupa.html'
SH = f'{ROOT}/shots'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errs = []
        for lang in ('az', 'ru', 'en'):
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
            pg = await ctx.new_page()
            pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
            pg.on('console', lambda m: errs.append(m.type + ': ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
            await setup(pg)
            await pg.goto(F + '?lang=' + lang); await pg.wait_for_timeout(1300)
            print(lang, 'nav:', await pg.evaluate("[...document.querySelectorAll('#siteNav a')].filter(a => a.offsetParent).map(a => a.textContent)"), '| hdr overflow:', await pg.evaluate("document.querySelector('.hdr').scrollWidth - document.querySelector('.hdr').clientWidth"))
            print(lang, 'sections:', await pg.evaluate("[...document.querySelectorAll('.aud')].map(s => s.id + ' «' + s.querySelector('h2').textContent + '» rows=' + [...s.querySelectorAll('.aud-grid')].map(r => (r.id || '-') + ':' + r.querySelectorAll('.card').length).join(','))"))
            top = await pg.evaluate("document.getElementById('adults').offsetTop"); bottom = await pg.evaluate("document.getElementById('cats').offsetTop")
            await pg.screenshot(path=f'{SH}/a-{lang}-full.png', full_page=True)
            im = Image.open(f'{SH}/a-{lang}-full.png').crop((0, top - 60, 1440, bottom + 420)); im = im.resize((960, int(im.size[1] * 960 / 1440))); im.save(f'{SH}/a-{lang}-auds.png'); print(lang, 'crop', im.size)
            if lang == 'ru':
                # nav -> adults section; filter two levels
                await pg.locator('#siteNav a[href="#adults"]').click(); await pg.wait_for_timeout(700)
                print('adults top:', await pg.evaluate("Math.round(document.getElementById('adults').getBoundingClientRect().top)"))
                await pg.locator('#women .aud-panel a.btn').click(); await pg.wait_for_timeout(800)
                print('women CTA -> aud', await pg.evaluate('Shop.state.aud'), 'cards', await pg.locator('#productsGrid .card').count(), '| switch:', await pg.evaluate("[...document.querySelectorAll('[data-aud-switch] button')].map(b => b.textContent + (b.classList.contains('is-active') ? '*' : ''))"))
                await pg.screenshot(path=f'{SH}/a-ru-filter.png')
                await pg.locator('[data-aud-switch] [data-key="women"]').click(); await pg.wait_for_timeout(200)
                print('toggle women off -> aud', await pg.evaluate('Shop.state.aud'), 'cards', await pg.locator('#productsGrid .card').count(), '| focus:', await pg.evaluate('document.activeElement.dataset.key'))
                await pg.locator('[data-aud-switch] [data-key="men"]').click(); await pg.wait_for_timeout(200)
                print('men -> cards', await pg.locator('#productsGrid .card').count())
                await pg.locator('[data-aud-switch] [data-key="kids"]').click(); await pg.wait_for_timeout(200)
                print('kids -> cards', await pg.locator('#productsGrid .card').count(), '| sub row:', await pg.locator('[data-aud-switch] .aud-sub').count())
                await pg.locator('[data-aud-switch] [data-key=""]').click(); await pg.wait_for_timeout(200)
                print('all -> cards', await pg.locator('#productsGrid .card').count())
            await ctx.close()
        # tablet + mobile
        for w, h, tag, mob in ((1000, 900, 't', False), (390, 844, 'm', True)):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob)
            pg = await ctx.new_page(); await setup(pg)
            await pg.goto(F + '?lang=ru'); await pg.wait_for_timeout(1300)
            print(tag, 'overflow x:', await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"))
            for sec in ('adults', 'kids', 'catalog'):
                await pg.evaluate(f"window.scrollTo(0, document.getElementById('{sec}').offsetTop - 70)"); await pg.wait_for_timeout(500)
                if sec == 'catalog':   # каталог теперь на своей странице
                    await pg.goto(F + '?lang=ru&page=catalog#catalog'); await pg.wait_for_timeout(1200)
                    await pg.locator('[data-aud-switch] [data-key="adults"]').click(); await pg.wait_for_timeout(300)
                await pg.screenshot(path=f'{SH}/a-{tag}-{sec}.png')
            await ctx.close()
        await b.close()
        print('errors:', errs or 'none')
    ims = [Image.open(f'{SH}/a-m-{s}.png') for s in ('adults', 'kids', 'catalog')]
    out = Image.new('RGB', (sum(i.size[0] // 2 for i in ims) + 20, 844), 'white'); x = 0
    for i in ims:
        i = i.resize((i.size[0] // 2, i.size[1] // 2)); out.paste(i, (x, 0)); x += i.size[0] + 10
    out.save(f'{SH}/a-m-combo.png')
asyncio.run(main())

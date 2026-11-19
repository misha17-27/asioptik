import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT, decode, pick_branch
from playwright.async_api import async_playwright
F = f'{BASE}/dist/optika-4-lupa.html'
SH = f'{ROOT}/shots'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errs = []
        ctx = await b.new_context(viewport={'width': 1000, 'height': 900})
        pg = await ctx.new_page()
        pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errs.append(m.type + ': ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        await setup(pg)
        await pg.goto(F + '?lang=ru'); await pg.wait_for_timeout(1300)
        await pg.evaluate("window.scrollTo(0, document.getElementById('men').offsetTop - 80)"); await pg.wait_for_timeout(600)
        await pg.screenshot(path=f'{SH}/r-tablet-aud.png')
        print('tablet overflow x:', await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"))
        await pg.set_viewport_size({'width': 1440, 'height': 900}); await pg.wait_for_timeout(400)
        await pg.evaluate("window.scrollTo(0, document.getElementById('men').offsetTop - 80)"); await pg.wait_for_timeout(600)
        await pg.screenshot(path=f'{SH}/r-ru-aud.png')
        # contacts page: "book an eye test" link -> home, repair form, exam ticked
        await pg.goto(F + '?lang=ru&product=c-month'); await pg.wait_for_timeout(900)
        await pg.locator('#ppForm a[data-pick-svc="exam"]').click(); await pg.wait_for_timeout(1500)
        print('exam link:', pg.url.split('/')[-1], '| page:', repr(await pg.evaluate('Shop.state.page')), '| exam checked:', await pg.is_checked('#rpServices input[data-svc-id="exam"]'), '| form top:', await pg.evaluate("Math.round(document.getElementById('repairForm').getBoundingClientRect().top)"), '| title:', await pg.title())
        # repair request still works
        await pg.fill('#rpName', 'Камран'); await pick_branch(pg, '#repairForm'); await pg.fill('#rpPhone', '0551112233'); await pg.locator('#rpDesc').click()
        await pg.locator('#repairForm [type=submit]').click(); await pg.wait_for_timeout(500)
        print(decode((await pg.evaluate('window.__opened'))[-1])[1].replace('\n', ' | '))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        # eye section CTA, hero CTA
        await pg.locator('.hdr > .logo').click(); await pg.wait_for_timeout(600)
        await pg.locator('#heroInner .hero-cta a[data-goto="frames"]').click(); await pg.wait_for_timeout(900)
        print('hero CTA: cat', await pg.evaluate('Shop.state.cat'), 'aud', repr(await pg.evaluate('Shop.state.aud')), 'cards', await pg.locator('#productsGrid .card').count())
        # quick add a frame from an audience section, colour chosen on the card syncs everywhere
        await pg.locator('.hdr > .logo').click(); await pg.wait_for_timeout(500)   # каталог теперь на своей странице, секции — на главной
        await pg.locator('#women [data-pid="f-florence"] [data-swatch="1"]').click(); await pg.wait_for_timeout(200)
        print('synced in catalog:', await pg.evaluate("document.querySelector('#productsGrid [data-pid=\"f-florence\"] [data-swatch=\"1\"]').classList.contains('is-active')"))
        await pg.locator('#women [data-pid="f-florence"] [data-add]').click(); await pg.wait_for_timeout(300)
        print('cart:', await pg.evaluate('JSON.stringify(Shop.state.cart)'))
        await pg.locator('#women [data-pid="f-florence"] .card-title a').click(); await pg.wait_for_timeout(500)
        print('page colour from card:', await pg.evaluate("Shop.state.pps['f-florence'].sel.color"), '| checked radio:', await pg.evaluate("document.querySelector('#ppForm input[name=pp-p-color]:checked').value"))
        # cart "to catalog" link from an empty cart on a product page
        await pg.evaluate("localStorage.removeItem('optika4-cart')"); await pg.reload(); await pg.wait_for_timeout(700)
        await pg.locator('.site-header [data-open-cart]').click(); await pg.wait_for_timeout(400)
        await pg.locator('#cartEmpty a').click(); await pg.wait_for_timeout(700)
        print('empty cart link:', pg.url.split('/')[-1], '| page:', repr(await pg.evaluate('Shop.state.page')), '| catalog top:', await pg.evaluate("Math.round(document.getElementById('catalog').getBoundingClientRect().top)"), '| drawer open:', await pg.evaluate("document.getElementById('cartDrawer').classList.contains('is-open')"))
        # search + audience filter empty state and reset
        await pg.locator('[data-aud-switch] [data-key="kids"]').click(); await pg.fill('#searchInput', 'авиатор'); await pg.wait_for_timeout(400)
        print('empty shown:', await pg.evaluate("!document.getElementById('catalogEmpty').hidden"))
        await pg.locator('[data-reset-filter]').click(); await pg.wait_for_timeout(300)
        print('after reset: aud', repr(await pg.evaluate('Shop.state.aud')), 'cards', await pg.locator('#productsGrid .card').count())
        print('errors:', errs or 'none')
        await ctx.close()
        # mobile menu
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); await setup(pg)
        await pg.goto(F + '?product=s-kids'); await pg.wait_for_timeout(900)
        await pg.locator('.hdr-right .js-menu-toggle').click(); await pg.wait_for_timeout(300)
        await pg.screenshot(path=f'{SH}/r-m-menu.png')
        await pg.locator('#siteNav a[data-aud="kids"]').click(); await pg.wait_for_timeout(700)
        print('mobile nav from product:', pg.url.split('/')[-1], '| page:', await pg.inner_text('#pgTitle'), '| cards:', await pg.locator('#productsGrid .card').count(), '| menu open:', await pg.evaluate("document.body.classList.contains('menu-open')"))
        await pg.screenshot(path=f'{SH}/r-m-kids.png')
        await b.close()
asyncio.run(main())

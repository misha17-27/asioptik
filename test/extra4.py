import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright
F = f'{BASE}/dist/optika-4-lupa.html'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
        await setup(pg)
        await pg.goto(F + '?lang=en'); await pg.wait_for_timeout(1200)
        print('lang attr:', await pg.evaluate('document.documentElement.lang'), '| desc:', await pg.evaluate("document.querySelector('meta[name=description]').content")[:60] if False else await pg.evaluate("document.querySelector('meta[name=description]').content"))
        print('switch buttons:', await pg.evaluate("[...document.querySelectorAll('.hdr-right [data-set-lang]')].map(b => b.outerHTML)"))
        # reload without param: language should persist
        await pg.goto(F); await pg.wait_for_timeout(800)
        print('persisted lang:', await pg.evaluate('document.documentElement.lang'), '| h1:', await pg.inner_text('h1'))
        # loupe follows the mouse and shows magnified copy
        before = await pg.evaluate("document.getElementById('loupe').style.transform")
        box = await pg.locator('#heroStage').bounding_box()
        await pg.mouse.move(box['x'] + 300, box['y'] + 260); await pg.wait_for_timeout(700)
        after = await pg.evaluate("document.getElementById('loupe').style.transform")
        print('loupe moved:', before, '->', after)
        print('clone inert:', await pg.evaluate("document.querySelector('#loupeInner .hero-inner').hasAttribute('inert')"), '| ids in clone:', await pg.evaluate("document.querySelectorAll('#loupeInner [id]').length"))
        await pg.locator('.hdr-right [data-set-lang="ru"]').click(); await pg.wait_for_timeout(500)
        print('clone h1 after RU:', await pg.evaluate("document.querySelector('#loupeInner h1').textContent"), '| url:', pg.url.split('/')[-1])
        print('kit text:', await pg.evaluate("[...document.querySelectorAll('#heroKit text')].slice(0,2).map(t => t.textContent)"))
        print('clone kit text:', await pg.evaluate("[...document.querySelectorAll('#loupeInner .hero-kit text')].slice(0,2).map(t => t.textContent)"))
        print('fine print:', await pg.inner_text('#finePrint'))
        print('facts:', await pg.evaluate("[...document.querySelectorAll('.facts li')].map(l => l.textContent.trim())"))
        # invalid state border colour
        await pg.locator('#repairForm [type=submit]').click(); await pg.wait_for_timeout(300)
        print('invalid border:', await pg.evaluate("getComputedStyle(document.querySelector('#repairForm input[name=name]')).borderColor"), '| msg:', await pg.evaluate("document.querySelector('#repairForm .field-error')?.textContent"))
        await pg.locator('.hdr-right [data-set-lang="az"]').click(); await pg.wait_for_timeout(400)
        print('error msg after AZ:', await pg.evaluate("document.querySelector('#repairForm .field-error')?.textContent"))
        # checkout summary quantity in EN
        await pg.locator('.hdr-right [data-set-lang="en"]').click(); await pg.wait_for_timeout(300)
        await pg.locator('#productsGrid [data-pid="f-milan"] [data-add]').click(); await pg.wait_for_timeout(300)
        await pg.locator('.site-header [data-open-cart]').click(); await pg.wait_for_timeout(400)
        await pg.locator('#cartDrawer [data-checkout]').click(); await pg.wait_for_timeout(400)
        print('EN qty:', await pg.evaluate("[...document.querySelectorAll('.co-i-qty')].map(e => e.textContent)"))
        # keyboard: Tab stays inside checkout
        inside = []
        for _ in range(40):
            await pg.keyboard.press('Tab')
            inside.append(await pg.evaluate("!!document.activeElement.closest('#checkoutModal')"))
        print('focus trapped:', all(inside))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        print('focus restored to:', await pg.evaluate("document.activeElement.className"))
        for lang in ('az', 'ru'):
            await pg.locator(f'.hdr-right [data-set-lang="{lang}"]').click(); await pg.wait_for_timeout(300)
            print(lang, 'qty:', await pg.evaluate("[...document.querySelectorAll('.co-i-qty')].map(e => e.textContent)"), '| ok title key ok:', await pg.evaluate("document.title"))
        print('console:', errs or 'none')
        await b.close()
asyncio.run(main())

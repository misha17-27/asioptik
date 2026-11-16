import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright
F = f'{BASE}/dist/optika-4-lupa.html'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
        pg = await ctx.new_page(); await setup(pg)
        await pg.goto(F + '?lang=ru'); await pg.wait_for_timeout(1200)
        print('kit empty slot:', await pg.evaluate("[...document.querySelectorAll('#heroKit text')].map(t => t.textContent).filter(x => !/^[+−]/.test(x))"))
        print('clone empty slot:', await pg.evaluate("[...document.querySelectorAll('#loupeInner .hero-kit text')].map(t => t.textContent).filter(x => !/^[+−]/.test(x))"))
        await pg.locator('.hdr-right [data-set-lang="az"]').click(); await pg.wait_for_timeout(400)
        print('kit empty slot AZ:', await pg.evaluate("[...document.querySelectorAll('#heroKit text')].map(t => t.textContent).filter(x => !/^[+−]/.test(x))"), await pg.evaluate("[...document.querySelectorAll('#loupeInner .hero-kit text')].map(t => t.textContent).filter(x => !/^[+−]/.test(x))"))
        # order via keyboard-ish path, then close success and check focus
        await pg.locator('#productsGrid [data-pid="f-verona"] [data-add]').click(); await pg.wait_for_timeout(300)
        await pg.locator('.site-header [data-open-cart]').focus(); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(400)
        await pg.locator('#cartDrawer [data-checkout]').click(); await pg.wait_for_timeout(400)
        await pg.fill('#coName', 'Aysel'); await pg.fill('#coPhone', '501234567')
        await pg.locator('#coPhone').blur(); print('phone formatted:', await pg.input_value('#coPhone'))
        await pg.locator('#checkoutForm [type=submit]').click(); await pg.wait_for_timeout(500)
        print('success open:', await pg.evaluate("document.getElementById('successModal').classList.contains('is-open')"), '| cart count:', await pg.inner_text('.hdr-right .js-cart-count'))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        print('focus after success:', await pg.evaluate("document.activeElement.className"))
        # services leader: hidden when the name wraps
        print('dots widths:', await pg.evaluate("[...document.querySelectorAll('.svc')].map(s => s.querySelector('.svc-name').getClientRects().length > 0 && (s.querySelector('.svc-name').offsetHeight > 40 ? 'wrap:' : 'line:') + Math.round(s.querySelector('.svc-dots').getBoundingClientRect().width))"))
        await b.close()
asyncio.run(main())

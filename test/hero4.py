import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errs = []
        pg = await (await b.new_context(viewport={'width': 1440, 'height': 900})).new_page()
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await setup(pg)
        await pg.goto(f'{BASE}/dist/optika-4-lupa.html?lang=ru'); await pg.wait_for_timeout(1400)
        await pg.locator('#heroKit [data-hs-go="1"]').click(); await pg.mouse.move(5, 5); await pg.wait_for_timeout(900)
        await pg.screenshot(path=f'{ROOT}/shots/hero-slide.png')
        # keyboard: Tab reaches the active banner and the controls; hidden slides are skipped
        await pg.locator('#heroInner .hero-cta a').nth(1).focus()
        seq = []
        for _ in range(11):
            await pg.keyboard.press('Tab')
            seq.append(await pg.evaluate("(() => { const a = document.activeElement; return a.className.split(' ').slice(0,2).join('.') + (a.dataset.hs ? ':' + a.dataset.hs : '') + (a.dataset.hsGo != null ? ':' + a.dataset.hsGo : ''); })()"))
        print('tab order:', seq)
        # file:// with no images folder: banners fall back to drawings, no script errors
        pg2 = await (await b.new_context(viewport={'width': 1280, 'height': 800})).new_page(); e2 = []
        pg2.on('pageerror', lambda e: e2.append(str(e)))
        await pg2.route('https://**', lambda r: r.abort())
        await pg2.goto('file://' + __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))) + '/dist/optika-4-lupa.html'); await pg2.wait_for_timeout(1200)
        print('file://: photos kept:', await pg2.evaluate("document.querySelectorAll('img.ph').length"), '| has-photo:', await pg2.evaluate("document.querySelectorAll('.has-photo').length"), '| slides:', await pg2.evaluate("document.querySelectorAll('#heroKit .hs-slide').length"), '| errors:', e2 or 'none')
        print('errors:', errs or 'none')
        await b.close()
asyncio.run(main())

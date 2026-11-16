import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for f in ['optika-1-svetlaya.html', 'optika-2-yarkaya.html', 'optika-3-temnaya.html']:
            pg = await b.new_page(viewport={'width': 1366, 'height': 820})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            await setup(pg)
            await pg.goto(f'{BASE}/dist/{f}'); await pg.wait_for_timeout(1500)
            # keyboard: focus title button of first card, Enter opens product modal
            await pg.locator('#productsGrid [data-pid="f-oslo"] .card-title button').focus()
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
            open1 = await pg.evaluate("document.getElementById('productModal').classList.contains('is-open')")
            inside = []
            for _ in range(14):
                await pg.keyboard.press('Tab')
                inside.append(await pg.evaluate("document.getElementById('productModal').contains(document.activeElement)"))
            await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
            back = await pg.evaluate("document.activeElement && document.activeElement.textContent.trim()")
            # cart via keyboard
            await pg.locator('.site-header [data-open-cart]').focus(); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(350)
            trap = []
            for _ in range(8):
                await pg.keyboard.press('Tab')
                trap.append(await pg.evaluate("document.getElementById('cartDrawer').contains(document.activeElement)"))
            await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
            locked = await pg.evaluate("document.documentElement.classList.contains('is-locked')")
            # search by colour with ё-less spelling
            await pg.fill('#searchInput', 'черепаховый'); await pg.wait_for_timeout(300)
            n = await pg.locator('#productsGrid [data-pid]').count()
            sel = await pg.evaluate("Shop.state.sel['f-milan'] + ',' + Shop.state.sel['s-miami']")
            print(f, '| modal opened by Enter:', open1, '| focus stayed in modal:', all(inside), '| focus returned to:', back[:30],
                  '| cart trap:', all(trap), '| scroll unlocked:', not locked, '| "черепаховый" results:', n, 'sel', sel, '| errors:', errs or 'none')
            if 'yarkaya' in f:
                await pg.fill('#searchInput', ''); await pg.wait_for_timeout(200)
                await pg.evaluate("window.scrollTo(0,0)")
                await pg.locator('#heroPicker .ac[data-i="3"]').click(); await pg.wait_for_timeout(600)
                name = await pg.inner_text('#heroColorName')
                await pg.screenshot(path=f'{ROOT}/shots/v2-picker.png')
                await pg.locator('#heroColorCta').click(); await pg.wait_for_timeout(900)
                q = await pg.input_value('#searchInput'); cnt = await pg.locator('#productsGrid [data-pid]').count()
                print('   v2 picker ->', name, '| filter:', q, '| results:', cnt)
                await pg.screenshot(path=f'{ROOT}/shots/v2-picker-filter.png')
            if 'temnaya' in f:
                await pg.fill('#searchInput', ''); await pg.wait_for_timeout(200)
                await pg.evaluate("window.scrollTo(0,0)"); await pg.wait_for_timeout(200)
                await pg.mouse.move(1050, 420); await pg.wait_for_timeout(120)
                await pg.mouse.move(1060, 430); await pg.wait_for_timeout(900)
                tr = await pg.evaluate("document.getElementById('loupe').style.transform")
                await pg.screenshot(path=f'{ROOT}/shots/v3-loupe-kit.png')
                print('   v3 loupe transform after move:', tr)
            await pg.close()
        await b.close()
asyncio.run(main())

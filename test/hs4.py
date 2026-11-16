import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright
from PIL import Image
F = f'{BASE}/dist/optika-4-lupa.html'
SH = f'{ROOT}/shots'
TAG = sys.argv[1] if len(sys.argv) > 1 else 'np'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errs = []
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
        pg = await ctx.new_page()
        pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errs.append(m.type + ': ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        await setup(pg)
        await pg.goto(F); await pg.wait_for_timeout(1500)
        print('slides:', await pg.evaluate("[...document.querySelectorAll('#heroKit .hs-slide')].map(s => s.className.replace('hs-slide ','') + (s.querySelector('.has-photo') ? '+photo' : ''))"))
        print('dots:', await pg.evaluate("[...document.querySelectorAll('#heroKit .hs-dot')].map(d => d.getAttribute('aria-label'))"))
        await pg.mouse.move(5, 5)
        tiles = []
        for k in range(6):
            await pg.locator(f'#heroKit [data-hs-go="{k}"]').click(); await pg.mouse.move(5, 5); await pg.wait_for_timeout(800)
            await pg.screenshot(path=f'{SH}/hs-{TAG}-{k}.png', clip={'x': 760, 'y': 150, 'width': 600, 'height': 600})
            tiles.append(Image.open(f'{SH}/hs-{TAG}-{k}.png'))
            if k == 1:
                print('clone synced:', await pg.evaluate("[...document.querySelectorAll('#loupeInner .hs-slide')].findIndex(s => s.classList.contains('is-active'))"), '| active banner focusable:', await pg.evaluate("document.querySelector('#heroKit .hs-slide.is-active').tabIndex"), '| hidden banner visibility:', await pg.evaluate("getComputedStyle(document.querySelectorAll('#heroKit .hs-slide')[3]).visibility"))
        out = Image.new('RGB', (1800, 1200), 'white')
        for k, t in enumerate(tiles): out.paste(t, ((k % 3) * 600, (k // 3) * 600))
        out = out.resize((1200, 800)); out.save(f'{SH}/hs-{TAG}-grid.png')
        # autoplay: 6 s per slide, pauses on hover and with the pause button
        await pg.locator('#heroKit [data-hs-go="0"]').click(); await pg.mouse.move(5, 5)
        await pg.wait_for_timeout(6600); i1 = await pg.evaluate("[...document.querySelectorAll('#heroKit .hs-slide')].findIndex(s => s.classList.contains('is-active'))")
        box = await pg.locator('#heroKit .hs-track').bounding_box()
        await pg.mouse.move(box['x'] + 200, box['y'] + 200); await pg.wait_for_timeout(6600)
        i2 = await pg.evaluate("[...document.querySelectorAll('#heroKit .hs-slide')].findIndex(s => s.classList.contains('is-active'))")
        await pg.mouse.move(5, 5); await pg.locator('#heroKit [data-hs="toggle"]').click(); await pg.mouse.move(5, 5); await pg.wait_for_timeout(6600)
        i3 = await pg.evaluate("[...document.querySelectorAll('#heroKit .hs-slide')].findIndex(s => s.classList.contains('is-active'))")
        print('autoplay 0 ->', i1, '| on hover stays', i2, '| paused stays', i3, '| toggle label:', await pg.get_attribute('#heroKit .hs-toggle', 'aria-label'))
        await pg.locator('#heroKit [data-hs="next"]').click(); await pg.locator('#heroKit [data-hs="prev"]').click(); await pg.locator('#heroKit [data-hs="prev"]').click()
        print('prev wraps to:', await pg.evaluate("[...document.querySelectorAll('#heroKit .hs-slide')].findIndex(s => s.classList.contains('is-active'))"))
        # banner click -> catalog filtered
        await pg.locator('#heroKit [data-hs-go="3"]').click(); await pg.wait_for_timeout(700)
        await pg.locator('#heroKit .hs-slide.is-active').click(); await pg.wait_for_timeout(900)
        print('banner click: cat', await pg.evaluate('Shop.state.cat'), '| url', pg.url.split('/')[-1], '| catalog top', await pg.evaluate("Math.round(document.getElementById('catalog').getBoundingClientRect().top)"))
        # language switch keeps the slide, loupe still follows the mouse
        await pg.evaluate('window.scrollTo(0,0)'); await pg.wait_for_timeout(300)
        await pg.locator('.hdr-right [data-set-lang="ru"]').click(); await pg.wait_for_timeout(600)
        print('after RU: active', await pg.evaluate("[...document.querySelectorAll('#heroKit .hs-slide')].findIndex(s => s.classList.contains('is-active'))"), '| title', await pg.inner_text('#heroKit .hs-slide.is-active .bn-title'), '| meta', await pg.inner_text('#heroKit .hs-slide.is-active .bn-meta'), '| clone title', await pg.evaluate("document.querySelector('#loupeInner .hs-slide.is-active .bn-title').textContent"))
        await pg.mouse.move(400, 300); await pg.wait_for_timeout(600)
        print('loupe:', await pg.evaluate("document.getElementById('loupe').style.transform"))
        # sections
        top = await pg.evaluate("document.getElementById('adults').offsetTop"); bottom = await pg.evaluate("document.getElementById('catalog').offsetTop")
        print('section banners:', await pg.evaluate("[...document.querySelectorAll('.sb')].map(s => s.querySelector('h2').textContent + (s.classList.contains('has-photo') ? ' +photo' : ' (рисунок)'))"), '| panels with photo:', await pg.evaluate("document.querySelectorAll('.aud-panel.has-photo').length"))
        await pg.screenshot(path=f'{SH}/hs-{TAG}-full.png', full_page=True)
        im = Image.open(f'{SH}/hs-{TAG}-full.png').crop((0, top - 20, 1440, bottom + 40)); im = im.resize((960, int(im.size[1] * 960 / 1440))); im.save(f'{SH}/hs-{TAG}-sections.png'); print('sections crop', im.size)
        print('errors:', errs or 'none')
        await ctx.close()
        # mobile
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); await setup(pg)
        await pg.goto(F); await pg.wait_for_timeout(1400)
        print('m overflow x:', await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"))
        shots = []
        await pg.evaluate("window.scrollTo(0, document.getElementById('heroKit').offsetTop + document.getElementById('heroInner').offsetTop - 380)"); await pg.wait_for_timeout(400)
        await pg.evaluate("document.querySelector('#heroKit [data-hs-go=\"2\"]').click()"); await pg.wait_for_timeout(800)
        await pg.screenshot(path=f'{SH}/hs-{TAG}-m0.png'); shots.append(f'{SH}/hs-{TAG}-m0.png')
        for sec in ('adults', 'kids'):
            await pg.evaluate(f"window.scrollTo(0, document.getElementById('{sec}').offsetTop - 60)"); await pg.wait_for_timeout(600)
            await pg.screenshot(path=f'{SH}/hs-{TAG}-m-{sec}.png'); shots.append(f'{SH}/hs-{TAG}-m-{sec}.png')
        ims = [Image.open(s) for s in shots]
        out = Image.new('RGB', (sum(i.size[0] // 2 for i in ims) + 20, 844), 'white'); x = 0
        for i in ims:
            i = i.resize((i.size[0] // 2, i.size[1] // 2)); out.paste(i, (x, 0)); x += i.size[0] + 10
        out.save(f'{SH}/hs-{TAG}-m.png')
        await b.close()
asyncio.run(main())

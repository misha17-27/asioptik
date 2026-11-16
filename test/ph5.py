import asyncio, sys, re
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright
from PIL import Image
F = f'{BASE}/dist/optika-4-lupa.html'
SH = f'{ROOT}/shots'
async def fake(route):
    m = re.search(r'/photos/(\d+)/', route.request.url)
    await route.fulfill(path=f'{ROOT}/test/fake/{m.group(1)}.jpg', content_type='image/jpeg')
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errs = []; outs = []
        for w, h, tag, mob in ((1440, 900, 'd', False), (1000, 900, 't', False), (390, 844, 'm', True)):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob)
            pg = await ctx.new_page()
            pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
            await setup(pg)
            await pg.route('https://images.pexels.com/**', fake)
            await pg.goto(F + '?lang=ru'); await pg.wait_for_timeout(1300)
            top = await pg.evaluate("document.getElementById('adults').offsetTop")
            await pg.evaluate(f"window.scrollTo(0, {top} + 300)"); await pg.wait_for_timeout(600)
            await pg.evaluate(f"window.scrollTo(0, {top} + 900)"); await pg.wait_for_timeout(600)
            print(tag, 'photos:', await pg.evaluate("[...document.querySelectorAll('.aud .has-photo')].map(e => e.className.split(' ')[0] + ':' + e.querySelector('.ph').src.split('/photos/')[1].slice(0,7))"), '| kids banner photo:', await pg.evaluate("!!document.querySelector('#kids .sb.has-photo')"), '| overflow x:', await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"))
            bottom = await pg.evaluate("document.getElementById('kids').offsetTop")
            await pg.screenshot(path=f'{SH}/ph5-{tag}-full.png', full_page=True)
            sc = 2 if mob else 1
            im = Image.open(f'{SH}/ph5-{tag}-full.png').crop((0, (top - 10) * sc, w * sc, (bottom + 10) * sc))
            tw = {'d': 900, 't': 640, 'm': 390}[tag]
            im = im.resize((tw, int(im.size[1] * tw / im.size[0]))); im.save(f'{SH}/ph5-{tag}.png'); outs.append(im); print(tag, im.size)
            await ctx.close()
        await b.close()
        print('errors:', errs or 'none')
asyncio.run(main())

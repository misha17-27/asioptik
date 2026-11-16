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
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await setup(pg)
        lang = sys.argv[1] if len(sys.argv) > 1 else 'az'
        await pg.goto(F + '?lang=' + lang); await pg.wait_for_timeout(1500)
        await pg.locator('#men').scroll_into_view_if_needed(); await pg.wait_for_timeout(300)
        await pg.evaluate("window.scrollTo(0, document.getElementById('men').offsetTop - 70)"); await pg.wait_for_timeout(700)
        await pg.screenshot(path=f'{SH}/m-aud1.png')
        await pg.evaluate("window.scrollTo(0, document.getElementById('catalog').offsetTop - 70)"); await pg.wait_for_timeout(700)
        await pg.screenshot(path=f'{SH}/m-cat.png')
        print('doc overflow x:', await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"))
        await pg.goto(F + f'?lang={lang}&product=f-florence'); await pg.wait_for_timeout(1000)
        await pg.locator('label:has(#pp-lens-yes)').click(); await pg.wait_for_timeout(300)
        await pg.locator('label:has(#pp-lt-l-prog)').click(); await pg.wait_for_timeout(300)
        await pg.select_option('#pp-od-sph', '+1.50'); await pg.select_option('#pp-od-cyl', '-0.75'); await pg.fill('#pp-od-ax', '95')
        await pg.screenshot(path=f'{SH}/m-frame.png', full_page=True)
        print('frame page overflow x:', await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"))
        await pg.goto(F + f'?lang={lang}&product=c-toric'); await pg.wait_for_timeout(1000)
        await pg.screenshot(path=f'{SH}/m-toric.png', full_page=True)
        print('toric overflow x:', await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"))
        await pg.goto(F + f'?lang={lang}&product=l-photo'); await pg.wait_for_timeout(1000)
        await pg.locator('label:has(#pp-mode-photo)').click(); await pg.wait_for_timeout(200)
        await pg.set_input_files('#pp-photo', f'{SH}/kit-a.png'); await pg.wait_for_timeout(300)
        await pg.screenshot(path=f'{SH}/m-photo.png', full_page=True)
        await ctx.close(); await b.close()
        print('errors:', errs or 'none')
    ims = [Image.open(f'{SH}/{n}.png') for n in ('m-aud1', 'm-cat')]
    out = Image.new('RGB', (sum(i.size[0] // 2 for i in ims) + 10, 844), 'white'); x = 0
    for i in ims:
        i = i.resize((i.size[0] // 2, i.size[1] // 2)); out.paste(i, (x, 0)); x += i.size[0] + 10
    out.save(f'{SH}/m-home-combo.png')
    for n in ('m-frame', 'm-toric', 'm-photo'):
        i = Image.open(f'{SH}/{n}.png'); print(n, i.size)
    ims = [Image.open(f'{SH}/{n}.png') for n in ('m-frame', 'm-toric', 'm-photo')]
    h = min(max(i.size[1] for i in ims), 4400)
    out = Image.new('RGB', (sum(i.size[0] // 2 for i in ims) + 20, h // 2), 'white'); x = 0
    for i in ims:
        i = i.crop((0, 0, i.size[0], min(i.size[1], h))); i = i.resize((i.size[0] // 2, i.size[1] // 2)); out.paste(i, (x, 0)); x += i.size[0] + 10
    out.save(f'{SH}/m-pp-combo.png')
asyncio.run(main())

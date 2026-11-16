import asyncio
from playwright.async_api import async_playwright
from PIL import Image, ImageChops
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await (await b.new_context(viewport={'width': 800, 'height': 420})).new_page()
        await pg.goto('http://127.0.0.1:8765/test/logo.html'); await pg.wait_for_timeout(400)
        await pg.screenshot(path=__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))) + '/shots/logo-mine.png')
        await b.close()
    mine = Image.open(__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))) + '/shots/logo-mine.png').convert('RGB').crop((0, 0, 716, 218))
    ref = Image.open(__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))) + '/shots/logo-crop.png').convert('RGB')
    print('sizes', mine.size, ref.size)
    d = ImageChops.difference(mine, ref).convert('L')
    px = d.load(); w, h = d.size
    strong = sum(1 for y in range(h) for x in range(w) if px[x, y] > 90)
    ink = sum(1 for y in range(h) for x in range(w) if max(abs(a - b) for a, b in zip(ref.getpixel((x, y)), (242, 246, 253))) > 60)
    print('strongly different pixels:', strong, 'of', w * h, '| logo ink pixels:', ink, '| share of ink:', round(100 * strong / ink, 2), '%')
    out = Image.new('RGB', (716, 218 * 3 + 20), 'white'); out.paste(ref, (0, 0)); out.paste(mine, (0, 228)); out.paste(d.point(lambda v: 255 - min(255, v * 3)).convert('RGB'), (0, 456)); out.save(__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))) + '/shots/logo-cmp.png')
    Image.open(__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))) + '/shots/logo-mine.png').crop((0, 218, 800, 420)).save(__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))) + '/shots/logo-dark.png')
asyncio.run(main())

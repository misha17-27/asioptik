"""Баннер «Для детей» с фото-кандидатом: kidsphoto.py <id фото> <pos> <flip 0/1> <метка>"""
import asyncio, re, sys, pathlib, subprocess
from playwright.async_api import async_playwright
from run import setup, BASE, ROOT
pid, pos, flip, tag = sys.argv[1], sys.argv[2], sys.argv[3] == '1', sys.argv[4]
d = ROOT / 'src/data4.js'; src = d.read_text(encoding='utf-8')
new = re.sub(r"img: 'images/banner-kids.jpg',(?: demo: '[^']*',)?(?: pos: '[^']*',)?(?: flip: true,)? show:",
             "img: 'images/banner-kids.jpg', demo: 'https://images.pexels.com/photos/%s/pexels-photo-%s.jpeg?auto=compress&cs=tinysrgb&w=1920', pos: '%s',%s show:" % (pid, pid, pos, ' flip: true,' if flip else ''), src)
assert new != src or pid in src
d.write_text(new, encoding='utf-8')
subprocess.run(['python3', str(ROOT / 'build.py')], capture_output=True)
async def fake(route):
    m = re.search(r'/photos/(\d+)/', route.request.url)
    await route.fulfill(path=f'{ROOT}/test/fake/{m.group(1)}.jpg', content_type='image/jpeg')
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, h, t in ((1440, 900, 'd'), (820, 900, 't'), (390, 844, 'm')):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1 if w > 800 else 2)
            pg = await ctx.new_page(); await setup(pg); await pg.route('https://images.pexels.com/**', fake)
            await pg.goto(f'{BASE}/dist/optika-4-lupa.html?lang=ru'); await pg.wait_for_timeout(1200)
            el = pg.locator('#kids .sb'); await el.scroll_into_view_if_needed(); await pg.wait_for_timeout(1200)
            await el.screenshot(path=f'{ROOT}/shots/kp-{tag}-{t}.png')
            print(tag, t, 'has photo:', await pg.evaluate("document.querySelector('#kids .sb').classList.contains('has-photo')"))
            await ctx.close()
        await b.close()
asyncio.run(main())

import asyncio, sys, re
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright
async def fake(route):
    m = re.search(r'/photos/(\d+)/', route.request.url)
    await route.fulfill(path=f'{ROOT}/test/fake/{m.group(1)}.jpg', content_type='image/jpeg')
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await (await b.new_context(viewport={'width': 1440, 'height': 900})).new_page(); await setup(pg)
        await pg.route('https://images.pexels.com/**', fake)
        F = f'{BASE}/dist/optika-4-lupa.html'
        await pg.goto(F); await pg.wait_for_timeout(900)
        meta = "({ canonical: document.querySelector('link[rel=canonical]').href, og: document.querySelector('meta[property=\"og:url\"]').content, title: document.querySelector('meta[property=\"og:title\"]').content })"
        print('home az:', await pg.evaluate(meta))
        await pg.locator('.hdr-right [data-set-lang="ru"]').click(); await pg.wait_for_timeout(300)
        print('home ru:', await pg.evaluate(meta))
        await pg.locator('#kids [data-pid="f-kids"] .card-title a').click(); await pg.wait_for_timeout(400)   # карточка из секции на главной: каталог теперь на своей странице
        print('product ru:', await pg.evaluate(meta))
        await pg.go_back(); await pg.wait_for_timeout(400)
        await pg.evaluate("window.scrollTo(0, document.getElementById('adults').offsetTop + 200)"); await pg.wait_for_timeout(800)
        await pg.evaluate("window.scrollTo(0, document.getElementById('women').offsetTop)"); await pg.wait_for_timeout(800)
        print('photo sources:', await pg.evaluate("[...document.querySelectorAll('.aud .has-photo > .ph')].map(i => i.parentNode.className.split(' ')[0] + ' <- ' + (i.src.includes('pexels') ? 'временное фото по ссылке' : 'свой файл ' + i.src.split('/').pop()) + ' | pos ' + i.style.objectPosition)"))
        await b.close()
asyncio.run(main())

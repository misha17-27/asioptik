import asyncio
from playwright.async_api import async_playwright
from run import setup, BASE
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await (await b.new_context(viewport={'width': 1440, 'height': 900})).new_page(); await setup(pg)
        await pg.goto(f'{BASE}/dist/optika-4-lupa.html?lang=ru&page=catalog'); await pg.wait_for_timeout(1500)
        await pg.evaluate('window.scrollTo(0, 2400)'); await pg.wait_for_timeout(300)
        y0 = await pg.evaluate('scrollY')
        await pg.locator('#productsGrid [data-pid="c-daily"] .card-title a').click(); await pg.wait_for_timeout(500)
        await pg.go_back(); await pg.wait_for_timeout(600)
        print('catalog → product → back: scroll', y0, '->', await pg.evaluate('scrollY'), '|', pg.url.split('/')[-1])
        await pg.goto(f'{BASE}/dist/optika-4-lupa.html?lang=ru&page=blog&post=care'); await pg.wait_for_timeout(1200)
        await pg.evaluate('window.scrollTo(0, 900)'); await pg.wait_for_timeout(300)
        await pg.locator('.post-cta a').first.click(); await pg.wait_for_timeout(600)
        print('post CTA →', pg.url.split('/')[-1], '| repair top:', await pg.evaluate("Math.round(document.getElementById('repair').getBoundingClientRect().top)"))
        await pg.go_back(); await pg.wait_for_timeout(600)
        print('back to post: scroll', await pg.evaluate('scrollY'), '|', await pg.evaluate("document.querySelector('#pgTitle').textContent"))
        await pg.go_forward(); await pg.wait_for_timeout(600)
        print('forward:', pg.url.split('/')[-1], '| view', repr(await pg.evaluate('Shop.state.view')))
        await b.close()
asyncio.run(main())

import asyncio, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright
F = f'{BASE}/dist/optika-4-lupa.html'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for lang in ('az', 'ru', 'en'):
            for w in (1010, 1100, 1250, 1300, 1440):
                ctx = await b.new_context(viewport={'width': w, 'height': 800})
                pg = await ctx.new_page(); await setup(pg)
                await pg.goto(F + '?lang=' + lang); await pg.wait_for_timeout(700)
                r = await pg.evaluate("""() => { const h = document.querySelector('.hdr'), nav = document.getElementById('siteNav'), right = document.querySelector('.hdr-right');
                  const free = right.getBoundingClientRect().left - nav.getBoundingClientRect().right;
                  const more = nav.querySelector('.nav-more'); more.style.display = 'block'; const need = more.getBoundingClientRect().width + 26; more.style.display = '';
                  return [h.scrollWidth - h.clientWidth, Math.round(free), Math.round(need)]; }""")
                print(lang, w, 'overflow', r[0], '| free gap', r[1], '| eye-test link needs', r[2])
                await ctx.close()
        await b.close()
asyncio.run(main())

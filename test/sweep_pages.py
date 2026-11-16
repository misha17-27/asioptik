"""Новые страницы на разных ширинах и языках: нет ли горизонтальной прокрутки и вылезающих элементов."""
import asyncio
from playwright.async_api import async_playwright
from run import setup, BASE
VIEWS = ['', 'page=catalog', 'page=catalog&cat=contacts', 'page=about', 'page=blog', 'page=blog&post=prescription', 'page=blog&post=kids-glasses', 'page=contacts']
WIDTHS = [320, 344, 360, 375, 390, 414, 480, 600, 700, 768, 820, 900, 1000, 1024, 1100, 1101, 1180, 1280, 1301, 1440, 1920, 2560]
CHECK = """() => {
  const vw = document.documentElement.clientWidth, bad = [];
  document.querySelectorAll('main *, .site-footer *, .site-header *').forEach(el => {
    if (!el.getClientRects().length || el.closest('.hs, .loupe, #heroKit, .tabs, svg, .vh, .skip, iframe')) return;
    const r = el.getBoundingClientRect();
    if (r.width && (r.right > vw + 1 || r.left < -1)) bad.push(el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0] + ':' + Math.round(r.left) + '-' + Math.round(r.right));
  });
  return { ox: document.documentElement.scrollWidth - vw, bad: bad.slice(0, 4) };
}"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        bad = []; n = 0
        for lang in ('az', 'ru', 'en'):
            ctx = await b.new_context(viewport={'width': 1200, 'height': 900})
            pg = await ctx.new_page(); await setup(pg)
            for v in VIEWS:
                await pg.goto(f'{BASE}/dist/optika-4-lupa.html?lang={lang}' + ('&' + v if v else '')); await pg.wait_for_timeout(700)
                for w in WIDTHS:
                    await pg.set_viewport_size({'width': w, 'height': 900}); await pg.wait_for_timeout(260)
                    r = await pg.evaluate(CHECK); n += 1
                    if r['ox'] > 0 or r['bad']: bad.append((lang, v or 'home', w, r['ox'], r['bad']))
            await ctx.close()
        await b.close()
        print('checked', n, 'page/width/language combinations')
        print('problems:', bad or 'none')
asyncio.run(main())

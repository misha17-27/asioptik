import asyncio, sys, re, json
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from run import setup, BASE, ROOT
from playwright.async_api import async_playwright
F = f'{BASE}/dist/optika-4-lupa.html'
SH = f'{ROOT}/shots'
WIDTHS = [(320, 640), (360, 740), (390, 844), (414, 896), (600, 900), (768, 1024), (820, 1180), (1024, 768), (1180, 820), (1280, 800), (1440, 900), (1920, 1080), (2560, 1300)]
PROBE = """() => {
  const vw = document.documentElement.clientWidth, out = [];
  const seen = new Set();
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('#loupe, .hs-slide:not(.is-active), .layer:not(.is-open), .vh, svg, .tabs, [hidden]')) continue;
    const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    // выходит за правый или левый край окна
    if (r.right > vw + 1.5 || r.left < -1.5) { const k = 'out ' + el.tagName + '.' + String(el.className).split(' ')[0]; if (!seen.has(k)) { seen.add(k); out.push(k + ' ' + Math.round(r.left) + '..' + Math.round(r.right)); } }
    // текст не помещается в свой блок по ширине
    if (el.children.length === 0 && el.scrollWidth > el.clientWidth + 2 && cs.overflow !== 'visible' && cs.textOverflow !== 'ellipsis' && !/INPUT|SELECT|TEXTAREA/.test(el.tagName)) { const k = 'clip ' + el.tagName + '.' + String(el.className).split(' ')[0]; if (!seen.has(k)) { seen.add(k); out.push(k + ' «' + el.textContent.trim().slice(0, 30) + '»'); } }
  }
  return { overflowX: document.documentElement.scrollWidth - vw, issues: out.slice(0, 12) };
}"""
async def fake(route):
    m = re.search(r'/photos/(\d+)/', route.request.url)
    for f in (f'{ROOT}/test/fake/{m.group(1)}.jpg', f'{ROOT}/test/fake/ph/{m.group(1)}.jpg'):
        if __import__('os').path.exists(f): return await route.fulfill(path=f, content_type='image/jpeg')
    await route.abort()   # образца нет — на сайте остаётся рисунок
async def main():
    langs = sys.argv[1:] or ['ru']
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errs = []
        for lang in langs:
            for w, h in WIDTHS:
                mob = w < 700
                ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=mob, has_touch=mob)
                pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(f'{w}: ' + str(e)))
                await setup(pg); await pg.route('https://images.pexels.com/**', fake)
                res = {}
                await pg.goto(F + '?lang=' + lang); await pg.wait_for_timeout(900)
                await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); await pg.wait_for_timeout(500); await pg.evaluate("window.scrollTo(0, 0)")
                res['home'] = await pg.evaluate(PROBE)
                if w in (320, 768, 1024, 1920): await pg.screenshot(path=f'{SH}/resp-{lang}-{w}-home.png', full_page=True)
                await pg.goto(F + f'?lang={lang}&product=f-milan'); await pg.wait_for_timeout(600)
                await pg.locator('label:has(#pp-lens-yes)').click(); await pg.wait_for_timeout(200)
                await pg.locator('label:has(#pp-lt-l-prog)').click(); await pg.wait_for_timeout(200)
                res['frame+lens'] = await pg.evaluate(PROBE)
                if w in (320, 768, 1920): await pg.screenshot(path=f'{SH}/resp-{lang}-{w}-pp.png', full_page=True)
                await pg.goto(F + f'?lang={lang}&product=c-toric'); await pg.wait_for_timeout(600)
                res['toric'] = await pg.evaluate(PROBE)
                await pg.select_option('#pp-od-sph', '-2.00'); await pg.select_option('#pp-od-cyl', '-1.25'); await pg.select_option('#pp-od-ax', '90'); await pg.locator('#pp-q-os-dec').click()
                await pg.locator('#ppAdd').click(); await pg.wait_for_timeout(300)
                await pg.locator('.site-header [data-open-cart]').click(); await pg.wait_for_timeout(400)
                res['cart'] = await pg.evaluate(PROBE)
                await pg.locator('#cartDrawer [data-checkout]').click(); await pg.wait_for_timeout(400)
                res['checkout'] = await pg.evaluate(PROBE)
                if w in (320, 768): await pg.screenshot(path=f'{SH}/resp-{lang}-{w}-co.png')
                bad = {k: v for k, v in res.items() if v['overflowX'] > 0 or v['issues']}
                print(lang, w, 'OK' if not bad else json.dumps(bad, ensure_ascii=False))
                await ctx.close()
        await b.close()
        print('errors:', errs or 'none')
asyncio.run(main())

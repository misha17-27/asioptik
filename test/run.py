import asyncio, re, sys, os, urllib.parse, json, subprocess, time, pathlib
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8765
BASE = f'http://127.0.0.1:{PORT}'
FS = ROOT / 'test/node_modules/@fontsource'

def font_css(url):
    q = urllib.parse.urlparse(url).query
    fams = [v for k, v in urllib.parse.parse_qsl(q) if k == 'family']
    out = []
    for f in fams:
        name = f.split(':')[0]
        pkg = name.lower().replace(' ', '-')
        d = FS / pkg
        if not d.exists():
            continue
        for w in (300, 400, 500, 600, 700, 800, 900):
            for suf in ('', '-italic'):
                css = d / f'{w}{suf}.css'
                if css.exists():
                    out.append(css.read_text().replace('url(./files/', f'url({BASE}/test/node_modules/@fontsource/{pkg}/files/'))
    return '\n'.join(out)

# прозрачная картинка 1×1 вместо плитки карты
TILE = __import__('base64').b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')

async def setup(page):
    async def gf(route):
        await route.fulfill(status=200, content_type='text/css', body=font_css(route.request.url))
    await page.route('https://fonts.googleapis.com/**', gf)
    await page.route('https://fonts.gstatic.com/**', lambda r: r.abort())
    await page.route('https://maps.google.com/**', lambda r: r.fulfill(status=200, content_type='text/html', body='<html><body style="margin:0;background:#dfe3dc;font:14px sans-serif;display:grid;place-items:center;height:100vh;color:#667">карта</body></html>'))
    # карта филиалов: картинки OpenStreetMap в тесте заменены пустой плиткой (в интернет стенд не ходит),
    # а библиотеку карты версия сайта одним файлом берёт с unpkg.com — здесь её отдаём из папки сайта
    await page.route('https://tile.openstreetmap.org/**', lambda r: r.fulfill(status=200, content_type='image/png', body=TILE))
    async def leaflet(route):
        f = ROOT / 'site/assets/vendor/leaflet' / route.request.url.split('/dist/')[-1].split('?')[0]
        ok = f.is_file() and ROOT / 'site/assets/vendor/leaflet' in f.resolve().parents
        await route.fulfill(status=200 if ok else 404, content_type={'.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png'}.get(f.suffix, 'text/plain'), body=f.read_bytes() if ok else b'')
    await page.route('https://unpkg.com/leaflet@1.9.4/dist/**', leaflet)
    await page.add_init_script("window.__opened=[]; window.open=function(u){window.__opened.push(u); return {opener:null};};")

def lp(path, lang):
    """Адрес страницы PHP-сайта на языке: lp('/catalog?cat=sun', 'ru') → '/ru/catalog?cat=sun', lp('/', 'en') → '/en'.
    У азербайджанского (основного) языка приставки нет."""
    if lang == 'az': return path
    return '/' + lang + ('' if path == '/' else path[1:] if path[:2] in ('/?', '/#') else path)
# Сайт забывает выбранный язык: адрес без языка снова открывается на азербайджанском, а не на запомненном
FORGET = "try { localStorage.removeItem('optika-lang') } catch (e) {}"
async def pick_branch(page, form='#checkoutForm'):
    """Филиалов больше одного — при самовывозе и «принесу в салон» форма просит выбрать салон: берём первый."""
    r = page.locator(f'{form} input[name="branch"]')
    if await r.count() and await r.first.is_visible(): await r.first.check()

def decode(u):
    q = urllib.parse.urlparse(u)
    t = urllib.parse.parse_qs(q.query).get('text', [''])[0]
    return q.path, t

async def run(file, tag, flow=True):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors = []
        # desktop
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
        page = await ctx.new_page()
        page.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        await setup(page)
        await page.goto(f'{BASE}/dist/{file}')
        await page.wait_for_timeout(2900)
        await page.screenshot(path=f'{ROOT}/shots/{tag}-d-hero.png')
        await page.screenshot(path=f'{ROOT}/shots/{tag}-d-full.png', full_page=True)
        if flow:
            # 1) add a frame directly
            await page.locator('#productsGrid [data-pid="f-milan"] [data-add]').click()
            await page.wait_for_timeout(400)
            cnt = await page.locator('.js-cart-count').first.inner_text()
            print('count after quick add:', cnt)
            # swatch change on a card
            await page.locator('#productsGrid [data-pid="f-verona"] [data-swatch="1"]').click()
            # 2) contact lenses with options
            await page.locator('#catTabs [data-cat="contacts"]').click()
            await page.wait_for_timeout(200)
            await page.locator('#productsGrid [data-pid="c-daily"] [data-add]').click()
            await page.wait_for_timeout(450)
            await page.locator('#pmAdd').click()
            await page.wait_for_timeout(200)
            print('pm error:', await page.locator('#pmError').inner_text())
            await page.select_option('#opt-sph', '-2.50')
            await page.select_option('#opt-bc', '8.5')
            await page.locator('[data-pm-qty="1"]').click()
            await page.wait_for_timeout(200)
            await page.screenshot(path=f'{ROOT}/shots/{tag}-d-product.png')
            await page.locator('#pmAdd').click()
            await page.wait_for_timeout(500)
            # 3) spectacle lenses with index delta
            await page.locator('#catTabs [data-cat="lenses"]').click()
            await page.locator('#productsGrid [data-pid="l-blue"] [data-add]').click()
            await page.wait_for_timeout(400)
            await page.select_option('#opt-index', '1.60 (тонкие)')
            await page.locator('#pmAdd').click()
            await page.wait_for_timeout(400)
            # 4) cart
            await page.locator('.site-header [data-open-cart]').first.click()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f'{ROOT}/shots/{tag}-d-cart.png')
            await page.locator('#cartDrawer [data-checkout]').click()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f'{ROOT}/shots/{tag}-d-checkout.png')
            await page.locator('#checkoutForm [type=submit]').click()
            await page.wait_for_timeout(300)
            await page.screenshot(path=f'{ROOT}/shots/{tag}-d-checkout-errors.png')
            await page.fill('#coName', 'Анна'); await pick_branch(page)
            await page.fill('#coPhone', '+994 50 123 45 67')
            await page.locator('#checkoutForm input[name=delivery][value=courier]').check()
            await page.fill('#coAddress', 'ул. Низами 10, кв. 5')
            await page.locator('#checkoutForm input[name=payment][value=card]').check()
            await page.fill('[name=od_sph]', '-2.00'); await page.fill('[name=od_cyl]', '-0.50'); await page.fill('[name=od_ax]', '180')
            await page.fill('[name=os_sph]', '-2.25'); await page.fill('[name=pd]', '62')
            await page.fill('#coComment', 'Позвоните после 18:00')
            await page.screenshot(path=f'{ROOT}/shots/{tag}-d-checkout-filled.png', full_page=False)
            await page.locator('#checkoutForm [type=submit]').click()
            await page.wait_for_timeout(500)
            opened = await page.evaluate('window.__opened')
            for u in opened:
                path, t = decode(u)
                print('WA ORDER ->', path); print(t); print('-----')
            await page.screenshot(path=f'{ROOT}/shots/{tag}-d-success.png')
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(300)
            print('count after order:', await page.locator('.js-cart-count').first.inner_text())
            # 5) repair
            await page.locator('#servicesList [data-svc="pads"]').click()
            await page.locator('#servicesList [data-svc="clean"]').click()
            await page.wait_for_timeout(300)
            await page.locator('#repairForm').scroll_into_view_if_needed()
            await page.fill('#rpDesc', 'Сломался носоупор слева')
            await page.locator('#repairForm input[name=handover][value=courier]').check()
            await page.fill('#rpAddress', 'пр. Бюльбюля 20')
            await page.screenshot(path=f'{ROOT}/shots/{tag}-d-repair.png')
            await page.locator('#repairForm [type=submit]').click()
            await page.wait_for_timeout(500)
            opened = await page.evaluate('window.__opened')
            if len(opened) > 1:
                path, t = decode(opened[-1]); print('WA REPAIR ->', path); print(t); print('-----')
        await ctx.close()
        # mobile
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = await ctx.new_page()
        page.on('pageerror', lambda e: errors.append(f'pageerror(m): {e}'))
        await setup(page)
        await page.goto(f'{BASE}/dist/{file}')
        await page.wait_for_timeout(2900)
        await page.screenshot(path=f'{ROOT}/shots/{tag}-m-hero.png')
        await page.screenshot(path=f'{ROOT}/shots/{tag}-m-full.png', full_page=True)
        if flow:
            await page.locator('#productsGrid [data-pid="c-month"] [data-add]').click()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f'{ROOT}/shots/{tag}-m-product.png')
            await page.select_option('#opt-sph', '-3.00')
            await page.locator('#pmAdd').click()
            await page.wait_for_timeout(400)
            await page.locator('.site-header [data-open-cart]').first.click()
            await page.wait_for_timeout(500)
            await page.locator('#cartDrawer [data-checkout]').click()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f'{ROOT}/shots/{tag}-m-checkout.png')
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(300)
            await page.locator('.hdr-right .js-menu-toggle').click()
            await page.wait_for_timeout(300)
            await page.screenshot(path=f'{ROOT}/shots/{tag}-m-menu.png')
        await ctx.close()
        await b.close()
        print('console:', errors or 'clean')

if __name__ == '__main__':
    file, tag = sys.argv[1], sys.argv[2]
    flow = len(sys.argv) < 4
    asyncio.run(run(file, tag, flow))

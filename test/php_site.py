"""Версия на PHP: адреса страниц, заказ с сохранением в базе, заголовки для поисковиков."""
import asyncio, json, re, subprocess, urllib.request
from playwright.async_api import async_playwright
from run import setup, ROOT, decode
B = 'http://127.0.0.1:8771'
SH = f'{ROOT}/shots'
def sql(q):
    return subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', 'asioptik_test', '-N', '-e', q], capture_output=True, text=True).stdout.strip()
def head(path):
    t = urllib.request.urlopen(B + path).read().decode('utf-8')
    g = lambda p: (re.search(p, t) or [None, ''])[1]
    return {'title': g(r'<title>([^<]*)</title>'), 'canon': g(r'rel="canonical" href="([^"]*)"'), 'lang': g(r'<html lang="([a-z]+)"'), 'desc': g(r'name="description" content="([^"]*)"')[:60], 'noindex': 'noindex' in t[:3000]}
async def main():
    for p in ('/', '/product/c-daily?lang=ru', '/blog/care?lang=en', '/catalog?cat=sun&lang=ru', '/about', '/checkout'):
        print('server head', p, '→', head(p))
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors = []
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
        pg = await ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        failed = []
        pg.on('response', lambda r: failed.append(f'{r.status} {r.url}') if r.status >= 400 and '127.0.0.1' in r.url else None)
        await setup(pg)
        await pg.route('https://images.pexels.com/**', lambda r: r.abort())
        tail = lambda: pg.url.replace(B, '')
        await pg.goto(B + '/?lang=ru'); await pg.wait_for_timeout(1800)
        print('home:', tail(), '|', await pg.title(), '| tiles:', await pg.locator('#cats .ctile').count(), '| nav hrefs:', await pg.evaluate("[...document.querySelectorAll('#siteNav a[data-view]')].map(a => a.getAttribute('href'))"))
        await pg.locator('#cats .ctile-contacts').click(); await pg.wait_for_timeout(500)
        print('tile:', tail(), '| cards', await pg.locator('#productsGrid .card').count(), '|', await pg.title())
        await pg.locator('#productsGrid .card-title a').first.click(); await pg.wait_for_timeout(500)
        print('product:', tail(), '| h1:', await pg.inner_text('#ppName'), '| canon:', await pg.evaluate("document.querySelector('link[rel=canonical]').href"))
        await pg.reload(); await pg.wait_for_timeout(1300)
        print('reload product:', tail(), '| page', await pg.evaluate('Shop.state.page'), '| h1:', await pg.inner_text('#ppName'))
        await pg.go_back(); await pg.wait_for_timeout(500); print('back:', tail(), '| view', await pg.evaluate('Shop.state.view'))
        await pg.locator('#siteNav a[data-view="blog"]').click(); await pg.wait_for_timeout(400)
        await pg.locator('.bl-card h2 a').first.click(); await pg.wait_for_timeout(400)
        print('post:', tail(), '|', await pg.inner_text('#pgTitle'))
        await pg.goto(B + '/blog/kids-glasses?lang=en'); await pg.wait_for_timeout(1200)
        print('direct post EN:', await pg.inner_text('#pgTitle'), '| lang', await pg.evaluate('Shop.lang'))
        await pg.locator('.hdr > .logo').click(); await pg.wait_for_timeout(400); print('logo → home:', tail())
        await pg.locator('.hdr-right [data-set-lang=\"ru\"]').click(); await pg.wait_for_timeout(300)
        # заказ
        await pg.goto(B + '/product/f-milan?lang=ru'); await pg.wait_for_timeout(1200)
        await pg.locator('#ppAdd').click(); await pg.wait_for_timeout(300)
        await pg.locator('.site-header [data-open-cart]').first.click(); await pg.wait_for_timeout(300)
        await pg.locator('#cartDrawer [data-checkout]').click(); await pg.wait_for_timeout(500)
        print('checkout:', tail())
        await pg.fill('#coName', 'Лейла Тест'); await pg.fill('#coPhone', '0501234567'); await pg.fill('#coComment', 'Позвоните после 18:00 <b>x</b>')
        await pg.locator('#checkoutForm [type=submit]').click(); await pg.wait_for_timeout(900)
        print('after order:', tail(), '| orders in DB:', sql("SELECT CONCAT(number, ' | ', kind, ' | ', name, ' | ', phone, ' | ', total, ' | ', status, ' | ', lang) FROM ao_orders ORDER BY id DESC LIMIT 1"))
        await pg.keyboard.press('Escape')
        # заявка на ремонт
        await pg.goto(B + '/?lang=ru#repair'); await pg.wait_for_timeout(1300)
        await pg.locator('#servicesList [data-svc="pads"]').click()
        await pg.fill('#rpName', 'Камран'); await pg.fill('#rpPhone', '0551112233')
        await pg.locator('#repairForm [type=submit]').click(); await pg.wait_for_timeout(800); await pg.keyboard.press('Escape')
        # сообщение
        await pg.goto(B + '/contacts?lang=ru'); await pg.wait_for_timeout(1200)
        await pg.fill('#ctName', 'Айдан'); await pg.locator('#ctPhone').click(); await pg.keyboard.type('0557778899')
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(300); print('phone with extra digits:', await pg.locator('#contactForm .field-error').first.inner_text(), '| value', await pg.input_value('#ctPhone'))
        await pg.fill('#ctPhone', '0557778899'); await pg.select_option('#ctTopic', 'exam'); await pg.fill('#ctMsg', 'Можно прийти в субботу?')
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(800)
        print('saved:', sql("SELECT GROUP_CONCAT(CONCAT(kind, ':', name) ORDER BY id SEPARATOR ', ') FROM ao_orders"))
        print('order details:', sql("SELECT LEFT(data, 260) FROM ao_orders WHERE kind = 'order' ORDER BY id DESC LIMIT 1"))
        print('failed requests:', failed or 'none')
        await pg.goto(B + '/?lang=ru'); await pg.wait_for_timeout(1500); await pg.screenshot(path=f'{SH}/php-home.png')
        await ctx.close(); await b.close()
        errors = [x for x in errors if 'font' not in x.lower() and 'CORS' not in x and 'ERR_FAILED' not in x]
        print('errors:', errors or 'none')
asyncio.run(main())

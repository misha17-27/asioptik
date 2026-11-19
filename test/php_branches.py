"""Филиалы: раздел в админ-панели, список салонов и карта на сайте, выбор салона в заказе и в заявке на ремонт.

Главное, что здесь проверяется: у метки на карте подпись — название филиала из админ-панели, а по нажатию
на метку или на филиал в списке открывается карточка с этим названием.

Запуск: sh test/serve.sh, затем python3 test/php_branches.py (базу тест ставит заново сам).
"""
import asyncio, html, http.client, json, re, subprocess, sys, urllib.parse
from playwright.async_api import async_playwright
from run import setup, decode
from php_reset import reset, PW

B = 'http://127.0.0.1:8771'
fails = []
total = 0
def check(name, ok, detail=''):
    global total
    total += 1
    print(('ok   ' if ok else 'FAIL ') + name + ('' if ok or detail == '' else ' | ' + str(detail)[:500]))
    if not ok: fails.append(name)
def sql(q):
    return subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', 'asioptik_test', '-N', '--raw', '-e', q], capture_output=True, text=True).stdout.strip()
def get(path):
    c = http.client.HTTPConnection('127.0.0.1', 8771, timeout=60); c.request('GET', path)
    r = c.getresponse(); t = r.read().decode('utf-8', 'replace'); c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, t
def const(t, name):
    return json.loads(re.search(r'const ' + name + r' = (\{.*?\}|\[.*?\]);\n', t, re.S).group(1))
def desc(t):
    return html.unescape(re.search(r'<meta name="description" content="([^"]*)"', t).group(1))
N1, N2 = 'Asioptik — Центр', 'Asioptik — Гянджлик'
A1, A2 = 'г. Баку, ул. Примерная, 1', 'г. Баку, пр. Примерный, 25'


async def main():
    print('clean install:', reset())
    s, h, t = get('/contacts?lang=ru')
    BR, CFG = const(t, 'BRANCHES'), const(t, 'CONFIG')
    print('--- данные')
    check('two branches from the first data', [b['id'] for b in BR] == ['merkez', 'genclik'] and BR[0]['name']['ru'] == N1, BR)
    check('pins are numbers', all(isinstance(b.get('lat'), float) and isinstance(b.get('lng'), float) for b in BR) and (BR[0]['lat'], BR[0]['lng']) == (40.3725, 49.8371), [(b.get('lat'), b.get('lng')) for b in BR])
    check('address and hours are no longer in the shop settings', not any(k in CFG for k in ('address', 'hours', 'mapQuery')), list(CFG))
    check('contacts description names both addresses', desc(t) == f'Напишите в WhatsApp, позвоните или приходите в салон. Адреса: {A1}; {A2}.', desc(t))
    s, h, css = get('/assets/vendor/leaflet/leaflet.css'); s2, h2, js = get('/assets/vendor/leaflet/leaflet.js')
    check('map library is served by the site itself', s == 200 and s2 == 200 and 'Leaflet 1.9.4' in js and 'sourceMappingURL' not in js, (s, s2))

    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors, reqs, tiles = [], [], []
        async def new_page(w=1440, hgt=900, touch=False):
            ctx = await b.new_context(viewport={'width': w, 'height': hgt}, has_touch=touch, is_mobile=touch)
            page = await ctx.new_page()
            page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and '/node_modules/@fontsource/' not in m.text and 'Failed to load resource' not in m.text else None)
            page.on('request', lambda r: reqs.append(r.url))
            page.on('request', lambda r: tiles.append((r.url, r.headers.get('referer', ''))) if 'tile.openstreetmap.org' in r.url else None)
            page.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
            await setup(page)
            await page.route('https://images.pexels.com/**', lambda r: r.abort())
            return page
        async def ready(page, scope='#pageView'):
            await page.wait_for_selector(f'{scope} [data-branch-map][data-map-ready]', timeout=15000); await page.wait_for_timeout(350)
        async def login(page):
            await page.goto(B + '/admin/'); await page.fill('#login', 'admin'); await page.fill('#password', PW); await page.locator('button[type=submit]').click(); await page.wait_for_load_state()
        async def save(page):
            await page.locator('.actions .btn').first.click(); await page.wait_for_load_state()
        async def right(page, lang):
            """Поле второго языка в форме видно, когда он выбран справа."""
            btn = page.locator(f'[data-lg-set={lang}]').first
            if await btn.count(): await btn.click()

        print('--- контакты: список и карта')
        pg = await new_page()
        await pg.goto(B + '/contacts?lang=ru'); await ready(pg)
        cards = pg.locator('#pageView [data-branches] .loc')
        check('a card for every branch: name, address, hours', await cards.locator('.loc-name').all_inner_texts() == [N1, N2] and await cards.locator('.loc-addr').all_inner_texts() == [A1, A2]
              and 'Пн–Сб: 10:00–20:00' in await cards.nth(0).inner_text() and 'Ежедневно: 10:00–21:00' in await cards.nth(1).inner_text(), await cards.all_inner_texts())
        check('nothing is highlighted before a click', await pg.locator('#pageView .loc.is-on').count() == 0 and await pg.locator('#pageView .mp-pin.is-on').count() == 0)
        check('route link: Google Maps directions to the pin', await cards.nth(1).locator('.loc-links a').get_attribute('href') == 'https://www.google.com/maps/dir/?api=1&destination=40.4005%2C49.852', await cards.nth(1).locator('.loc-links a').get_attribute('href'))
        check('common phone is not repeated in every card', await cards.nth(0).locator('.loc-links a').count() == 1 and await pg.locator('#pageView .c-list a[data-cfg="phone"]').count() == 1)
        pins = pg.locator('#pageView .mp-pin')
        check('a pin for every branch', await pins.count() == 2)
        check('every pin is labelled with the name written in the admin panel', sorted(await pg.locator('#pageView .mp-label').all_inner_texts()) == sorted([N1, N2]), await pg.locator('#pageView .mp-label').all_inner_texts())
        check('pins carry the name for screen readers', sorted([await pins.nth(i).get_attribute('aria-label') for i in range(2)]) == sorted([N1, N2]))
        check('both pins are in view at once', await pg.evaluate("(() => { const m = Shop.maps[0].map, b = m.getBounds(); return Shop.branches.every(x => b.contains([x.lat, x.lng])); })()"))
        check('map pictures come from OpenStreetMap by its address', len(tiles) > 0 and all(re.match(r'^https://tile\.openstreetmap\.org/\d+/\d+/\d+\.png$', u) for u, r in tiles), tiles[:2])
        check('… and the request names the site, as OpenStreetMap requires', all(r.rstrip('/') == B for u, r in tiles), [r for u, r in tiles][:3])
        credit = pg.locator('#pageView .leaflet-control-attribution a')
        check('OpenStreetMap is credited on the map', await credit.inner_text() == 'OpenStreetMap' and await credit.get_attribute('href') == 'https://www.openstreetmap.org/copyright' and await credit.is_visible())
        check('map library comes from the site, nothing from other hosts', any('/assets/vendor/leaflet/leaflet.js?v=1.9.4' in u and u.startswith(B) for u in reqs) and not any('unpkg.com' in u for u in reqs))

        # нажатие на метку: карточка с названием
        pin2 = pg.locator(f'#pageView .mp-pin[aria-label="{N2}"]')
        await pin2.click(); await pg.wait_for_timeout(500)
        pop = pg.locator('#pageView .mp-pop')
        check('click on a pin: card with the name, address, hours and route', await pop.count() == 1 and await pop.locator('.mp-name').inner_text() == N2 and await pop.locator('.mp-addr').inner_text() == A2
              and 'Ежедневно: 10:00–21:00' in await pop.inner_text() and await pop.locator('.mp-route').get_attribute('href') == 'https://www.google.com/maps/dir/?api=1&destination=40.4005%2C49.852', await pop.inner_text() if await pop.count() else None)
        check('… and the branch is highlighted in the list', await pg.locator('#pageView .loc.is-on').get_attribute('data-branch') == 'genclik' and await pin2.evaluate('e => e.classList.contains("is-on")'))
        # нажатие на филиал в списке: карта переезжает к нему и открывает его карточку
        await cards.nth(0).locator('.loc-name').click(); await pg.wait_for_timeout(900)
        c = await pg.evaluate('(() => { const c = Shop.maps[0].map.getCenter(); return [c.lat, c.lng, Shop.maps[0].map.getZoom()]; })()')
        check('click on a branch in the list: its card on the map', await pop.count() == 1 and await pop.locator('.mp-name').inner_text() == N1 and await pg.locator('#pageView .loc.is-on').get_attribute('data-branch') == 'merkez', await pop.all_inner_texts())
        check('… the map moves to it', abs(c[0] - 40.3725) < 0.01 and abs(c[1] - 49.8371) < 0.01 and c[2] >= 16, c)
        # язык меняется на месте: подписи и карточка — на новом языке
        await pg.evaluate("Shop.setLang('en')"); await pg.wait_for_timeout(500)
        check('language switch: list, labels and the open card', await cards.locator('.loc-name').all_inner_texts() == ['Asioptik — Centre', 'Asioptik — Ganjlik'] and sorted(await pg.locator('#pageView .mp-label').all_inner_texts()) == ['Asioptik — Centre', 'Asioptik — Ganjlik']
              and await pop.locator('.mp-name').inner_text() == 'Asioptik — Centre' and await pop.locator('.mp-route').inner_text() == 'Directions', await pop.all_inner_texts())
        check('one map on the page, old ones are closed', await pg.evaluate('Shop.maps.length') == 1)
        await pg.evaluate("Shop.go({view: 'about'})"); await pg.wait_for_timeout(300)
        await pg.evaluate("Shop.go({view: 'contacts'})"); await ready(pg)
        check('coming back to the page: one map again, the chosen branch is open', await pg.evaluate('Shop.maps.filter(m => document.documentElement.contains(m.box)).length') == 1 and await pg.evaluate('Shop.maps.length') == 1 and await pop.locator('.mp-name').inner_text() == 'Asioptik — Centre')
        await pg.context.close()

        print('--- главная: карта загружается, когда до неё долистали')
        reqs.clear(); tiles.clear()
        pg = await new_page()
        await pg.goto(B + '/?lang=ru'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(800)
        check('home: the list is there, the map is not loaded yet', await pg.locator('#contacts [data-branches] .loc').count() == 2 and not any('leaflet' in u for u in reqs) and not tiles, [u for u in reqs if 'leaflet' in u][:2])
        await pg.locator('#contacts').scroll_into_view_if_needed(); await ready(pg, '#contacts')
        check('home: the map opens when it comes into view', await pg.locator('#contacts .mp-pin').count() == 2 and sorted(await pg.locator('#contacts .mp-label').all_inner_texts()) == sorted([N1, N2]))
        await pg.locator('#contacts [data-branch-show="genclik"]').click(); await pg.wait_for_timeout(600)
        check('home: click on a branch shows its name on the map', await pg.locator('#contacts .mp-pop .mp-name').inner_text() == N2)
        await pg.context.close()

        print('--- телефон')
        pg = await new_page(390, 844, True)
        await pg.goto(B + '/contacts?lang=ru'); await ready(pg)
        check('phone: no sideways scroll', await pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
        box = await pg.locator('#pageView [data-branch-map]').bounding_box()
        check('phone: the map is under the list and has a height', box['height'] >= 300 and box['y'] > (await pg.locator('#pageView .loc').last.bounding_box())['y'], box)
        await pg.locator('#pageView [data-branch-show="genclik"]').tap(); await pg.wait_for_timeout(1200)
        box = await pg.locator('#pageView [data-branch-map]').bounding_box()
        check('phone: tap on a branch brings the map into view with its name', 0 <= box['y'] and box['y'] + box['height'] <= 844 + 2 and await pg.locator('#pageView .mp-pop .mp-name').inner_text() == N2, box)
        await pg.goto(B + '/?lang=ru'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(500)
        await pg.locator('.menu-btn').tap(); await pg.wait_for_timeout(400)
        links = pg.locator('#siteNav .nav-locs a')
        check('phone menu: both branches with names and addresses', await links.all_inner_texts() == [f'{N1} {A1}', f'{N2} {A2}'], await links.all_inner_texts())
        check('phone menu still fits the screen', await pg.evaluate("(() => { const n = document.querySelector('#siteNav'); return n.scrollHeight <= n.clientHeight + 1; })()"), await pg.evaluate("(() => { const n = document.querySelector('#siteNav'); return [n.scrollHeight, n.clientHeight]; })()"))
        await links.nth(1).tap(); await ready(pg)
        check('phone menu: a branch opens «Контакты» with the map on it', pg.url == B + '/contacts?lang=ru' and await pg.locator('#pageView .mp-pop .mp-name').inner_text() == N2 and await pg.locator('#pageView .loc.is-on').get_attribute('data-branch') == 'genclik', pg.url)
        await pg.context.close()

        print('--- заказ и ремонт: выбор салона')
        pg = await new_page()
        async def to_checkout():
            await pg.goto(B + '/product/f-milan?lang=ru'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(400)
            await pg.locator('#ppAdd').click(); await pg.wait_for_timeout(300)
            await pg.goto(B + '/checkout?lang=ru'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(500)
            await pg.evaluate('window.__opened.length = 0')
        await to_checkout()
        fld = pg.locator('#coBranchField')
        check('checkout: with pickup the shop is asked', await fld.is_visible() and await fld.locator('legend').inner_text() == 'В каком салоне заберёте заказ' and await fld.locator('.choice b').all_inner_texts() == [N1, N2] and await fld.locator('.choice small').all_inner_texts() == [A1, A2])
        check('checkout: no shop is chosen for the customer', await fld.locator('input:checked').count() == 0)
        await pg.fill('#coName', 'Филиал Тест'); await pg.fill('#coPhone', '0501112233')
        await pg.locator('#checkoutForm [type=submit]').click(); await pg.wait_for_timeout(400)
        check('checkout: without a shop the order is not sent', await pg.evaluate('window.__opened.length') == 0 and await fld.locator('.field-error').inner_text() == 'Выберите салон', await fld.locator('.field-error').inner_text())
        await fld.locator('input[value=genclik]').check(); await pg.wait_for_timeout(200)
        check('checkout: the error goes away after a choice', await fld.locator('.field-error').inner_text() == '')
        await pg.locator('#checkoutForm [type=submit]').click(); await pg.wait_for_timeout(1500)
        wa = await pg.evaluate('window.__opened')
        text = decode(wa[0])[1] if wa else ''
        check('checkout: the message names the shop', f'Салон: {N2}, {A2}' in text and 'Получение: Самовывоз из салона' in text, text[-420:])
        d = json.loads(sql("SELECT data FROM ao_orders WHERE name='Филиал Тест' AND kind='order' ORDER BY id DESC LIMIT 1") or '{}')
        check('checkout: the saved order keeps the shop', d.get('details', {}).get('branch') == N2 and d.get('details', {}).get('delivery') == 'pickup', d.get('details'))
        await pg.keyboard.press('Escape')
        await to_checkout()
        check('checkout: the chosen shop is remembered for the next order', await pg.locator('#coBranchField input:checked').get_attribute('value') == 'genclik')
        await pg.locator('#checkoutForm input[name=delivery][value=courier]').check(); await pg.wait_for_timeout(200)
        check('checkout: courier delivery does not ask for a shop', not await fld.is_visible() and await pg.locator('#coAddressField').is_visible())
        await pg.fill('#coName', 'Курьер Тест'); await pg.fill('#coPhone', '0501112233'); await pg.fill('#coAddress', 'Баку, ул. Тестовая, 7')
        await pg.locator('#checkoutForm [type=submit]').click(); await pg.wait_for_timeout(1500)
        wa = await pg.evaluate('window.__opened'); text = decode(wa[0])[1] if wa else ''
        d = json.loads(sql("SELECT data FROM ao_orders WHERE name='Курьер Тест' ORDER BY id DESC LIMIT 1") or '{}')
        check('checkout: courier order has no shop line', bool(text) and 'Салон:' not in text and 'branch' not in d.get('details', {}), (text[-200:], d.get('details')))
        await pg.keyboard.press('Escape')
        # заявка на ремонт
        await pg.goto(B + '/?lang=ru#repair'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(900)
        await pg.evaluate('window.__opened.length = 0; localStorage.removeItem(Object.keys(localStorage).find(k => /cust/i.test(k)) || "")')
        await pg.reload(); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(900)
        rf = pg.locator('#rpBranchField')
        check('repair: «принесу в салон» asks which shop', await rf.is_visible() and await rf.locator('legend').inner_text() == 'В какой салон принесёте очки' and await rf.locator('.choice b').all_inner_texts() == [N1, N2])
        await pg.locator('#servicesList [data-svc="pads"]').click(); await pg.fill('#rpName', 'Ремонт Филиал'); await pg.fill('#rpPhone', '0551112233')
        await pg.locator('#repairForm [type=submit]').click(); await pg.wait_for_timeout(400)
        check('repair: without a shop the request is not sent', await pg.evaluate('window.__opened.length') == 0 and await rf.locator('.field-error').inner_text() == 'Выберите салон')
        await rf.locator('input[value=merkez]').check()
        await pg.locator('#repairForm [type=submit]').click(); await pg.wait_for_timeout(1500)
        wa = await pg.evaluate('window.__opened'); text = decode(wa[0])[1] if wa else ''
        d = json.loads(sql("SELECT data FROM ao_orders WHERE name='Ремонт Филиал' ORDER BY id DESC LIMIT 1") or '{}')
        check('repair: the message and the saved request name the shop', f'Салон: {N1}, {A1}' in text and d.get('details', {}).get('branch') == N1, (text[-260:], d.get('details')))
        await pg.keyboard.press('Escape')
        await pg.locator('#repairForm input[name=handover][value=courier]').check(); await pg.wait_for_timeout(200)
        check('repair: courier pickup does not ask for a shop', not await rf.is_visible() and await pg.locator('#rpAddressField').is_visible())

        print('--- админ-панель')
        await login(pg)
        item = pg.locator('.side a', has_text=re.compile('^Филиалы'))
        check('admin menu: «Филиалы» with the number of branches', await item.count() == 1 and '2' in await item.inner_text(), await item.inner_text() if await item.count() else None)
        await pg.goto(B + '/admin/?p=orders')
        check('admin, orders: pickup shows the shop', f'самовывоз · {N2}' in await pg.inner_text('tbody') and f'принесёт в салон · {N1}' in await pg.inner_text('tbody'), (await pg.inner_text('tbody'))[:300])
        await pg.goto(B + '/admin/?p=list&type=branch')
        check('admin, branches: note, addresses and pins in the list', 'название филиала' in await pg.inner_text('.card-tools .note') and A1 in await pg.inner_text('tbody') and await pg.locator('tbody .pill', has_text='метка стоит').count() == 2)
        await pg.goto(B + '/admin/?p=doc&name=config')
        check('admin, settings: address and hours moved to the branches', await pg.locator('#f-shopName').count() == 1 and await pg.locator('#f-address-az, #f-hours-az, #f-mapQuery').count() == 0 and '«Филиалы»' in await pg.inner_text('p.note'))
        await pg.goto(B + '/admin/?p=page&id=contacts')
        check('admin, page «Контакты»: texts of the branches block and a link to the branches', await pg.locator('code.key', has_text=re.compile(r'^loc\.route$')).count() == 1 and await pg.locator('a', has_text='Филиалы: адреса, часы работы, карта').count() == 1)
        ph = await pg.get_attribute('#f-seo-desc--ru', 'placeholder')
        check('admin, page «Контакты»: grey description = what the site shows', ph == f'Напишите в WhatsApp, позвоните или приходите в салон. Адреса: {A1}; {A2}.', ph)

        # форма филиала: метка на карте
        await pg.goto(B + '/admin/?p=list&type=branch'); await pg.locator('tbody a.strong').first.click(); await pg.wait_for_load_state()
        await pg.wait_for_selector('[data-map-pick][data-map-ready]', timeout=15000); await pg.wait_for_timeout(300)
        check('admin, branch: fields', all([await pg.locator(x).count() == 1 for x in ('#f-name-az', '#f-name-ru', '#f-address-az', '#f-hours-az', '#f-phone', '#f-coords', '#f-mapLink', '[data-map-pick]')]))
        check('admin, branch: the pin stands where the coordinates say', await pg.input_value('#f-coords') == '40.3725, 49.8371' and await pg.locator('.map-pick .map-pin').count() == 1
              and await pg.evaluate('(() => { const c = window.__mapPick.getCenter(); return Math.abs(c.lat - 40.3725) < 0.001 && Math.abs(c.lng - 49.8371) < 0.001; })()'))
        mp = pg.locator('[data-map-pick]')
        await mp.scroll_into_view_if_needed(); bb = await mp.bounding_box()
        await pg.mouse.click(bb['x'] + bb['width'] * 0.25, bb['y'] + bb['height'] * 0.3); await pg.wait_for_timeout(300)
        v = await pg.input_value('#f-coords')
        check('admin, branch: a click on the map writes the coordinates', bool(re.match(r'^40\.\d{6}, 49\.\d{6}$', v)) and v != '40.372500, 49.837100', v)
        await pg.fill('#f-coords', '40.4093, 49.8671'); await pg.wait_for_timeout(400)
        check('admin, branch: pasted coordinates move the pin', await pg.evaluate('(() => { const c = window.__mapPick.getCenter(); return Math.abs(c.lat - 40.4093) < 0.001 && Math.abs(c.lng - 49.8671) < 0.001; })()') and await pg.locator('.map-pick .map-pin').count() == 1)
        await pg.fill('#f-coords', ''); await pg.wait_for_timeout(300)
        check('admin, branch: an empty field removes the pin', await pg.locator('.map-pick .map-pin').count() == 0)
        await pg.fill('#f-coords', 'улица, дом'); await pg.fill('#f-mapLink', 'javascript:alert(1)'); await save(pg)
        errs = await pg.locator('.field.is-invalid .err').all_inner_texts()
        check('admin, branch: wrong coordinates and a wrong link are not saved', len(errs) == 2 and 'Координаты' in errs[0] and 'https://' in errs[1] and await pg.input_value('#f-coords') == 'улица, дом', errs)
        check('… the site keeps the previous pin', const(get('/contacts')[2], 'BRANCHES')[0].get('lat') == 40.3725)
        await pg.fill('#f-coords', '  40.37250000 ; 49.83710000 '); await pg.fill('#f-mapLink', ''); await save(pg)
        check('admin, branch: coordinates are tidied on save', const(get('/contacts')[2], 'BRANCHES')[0].get('lng') == 49.8371 and sql("SELECT JSON_VALUE(data, '$.coords') FROM ao_items WHERE type='branch' AND slug='merkez'") == '40.3725, 49.8371', sql("SELECT JSON_VALUE(data, '$.coords') FROM ao_items WHERE type='branch' AND slug='merkez'"))

        # новый филиал: свой телефон и своя ссылка на карту
        await pg.goto(B + '/admin/?p=edit&type=branch'); await pg.wait_for_selector('[data-map-pick][data-map-ready]', timeout=15000)
        check('admin, new branch: the map opens over Baku with no pin', await pg.locator('.map-pick .map-pin').count() == 0 and await pg.evaluate('(() => { const c = window.__mapPick.getCenter(); return Math.abs(c.lat - 40.3777) < 0.01 && Math.abs(c.lng - 49.892) < 0.01; })()'))
        await save(pg)
        check('admin, new branch: name and address are required', len(await pg.locator('.field.is-invalid').all()) == 2)
        await pg.fill('#f-name-az', 'Asioptik — 28 May'); await right(pg, 'ru'); await pg.fill('#f-name-ru', 'Asioptik — 28 Мая <b>'); await pg.fill('#f-address-az', 'Bakı, 28 May küç., 3'); await pg.fill('#f-address-ru', 'Баку, ул. 28 Мая, 3')
        await pg.fill('#f-hours-ru', 'Пн–Пт: 9:00–19:00'); await pg.fill('#f-phone', '+994 12 345 67 89'); await pg.fill('#f-coords', '40.3795, 49.8468'); await pg.fill('#f-mapLink', 'https://maps.app.goo.gl/AbCdEf123')
        await save(pg)
        BR = const(get('/contacts?lang=ru')[2], 'BRANCHES')
        new = BR[-1]
        check('new branch is on the site', len(BR) == 3 and new['name']['ru'] == 'Asioptik — 28 Мая <b>' and new['phone'] == '+994 12 345 67 89' and new['mapLink'] == 'https://maps.app.goo.gl/AbCdEf123' and (new['lat'], new['lng']) == (40.3795, 49.8468), new)
        # филиал без метки
        await pg.goto(B + '/admin/?p=edit&type=branch'); await pg.fill('#f-name-az', 'Asioptik — Nişansız'); await pg.fill('#f-address-az', 'Bakı, Yeni küç., 9'); await save(pg)
        await pg.goto(B + '/admin/?p=list&type=branch')
        check('admin, branches: the one without a pin is marked', await pg.locator('tbody .st', has_text='нет метки').count() == 1 and await pg.locator('tbody .pill', has_text='метка стоит').count() == 3)

        site = await new_page()
        await site.goto(B + '/contacts?lang=ru'); await ready(site)
        cards = site.locator('#pageView [data-branches] .loc')
        check('site: four cards, three pins', await cards.count() == 4 and await site.locator('#pageView .mp-pin').count() == 3)
        check('site: a name with markup is shown as text', await cards.nth(2).locator('.loc-name').inner_text() == 'Asioptik — 28 Мая <b>' and await site.locator('#pageView .loc-name b, #pageView .mp-label b').count() == 0 and 'Asioptik — 28 Мая <b>' in await site.locator('#pageView .mp-label').all_inner_texts())
        la = cards.nth(2).locator('.loc-links a')
        check('site: own phone and own map link of a branch', await la.all_inner_texts() == ['+994 12 345 67 89', 'Маршрут'] and await la.nth(0).get_attribute('href') == 'tel:+994123456789' and await la.nth(1).get_attribute('href') == 'https://maps.app.goo.gl/AbCdEf123'
              and await la.nth(1).get_attribute('rel') == 'noopener' and await la.nth(1).get_attribute('target') == '_blank', await la.all_inner_texts())
        check('site: a branch without a pin leads to a search by its address', await cards.nth(3).locator('.loc-links a').get_attribute('href') == 'https://www.google.com/maps/search/?api=1&query=' + urllib.parse.quote('Bakı, Yeni küç., 9', safe=''), await cards.nth(3).locator('.loc-links a').get_attribute('href'))
        await cards.nth(2).locator('.loc-name').click(); await site.wait_for_timeout(700)
        pop = site.locator('#pageView .mp-pop')
        check('site: the card of the new branch — its name as text, its own link', await pop.locator('.mp-name').inner_text() == 'Asioptik — 28 Мая <b>' and await pop.locator('.mp-name b').count() == 0 and await pop.locator('.mp-route').get_attribute('href') == 'https://maps.app.goo.gl/AbCdEf123')
        await site.context.close()

        print('--- один филиал')
        ids = dict(line.split('\t') for line in sql("SELECT slug, id FROM ao_items WHERE type='branch'").splitlines())
        async def show(slugs):
            """Оставить видимыми только эти филиалы (остальные скрыть в админ-панели)."""
            for slug, i in ids.items():
                await pg.goto(B + f'/admin/?p=edit&type=branch&id={i}')
                box = pg.locator('input[name=active]')
                if await box.is_checked() != (slug in slugs):
                    await box.set_checked(slug in slugs); await save(pg)
        await show(['genclik'])
        s, h, t = get('/contacts?lang=ru')
        check('one branch: description says «Адрес», not «Адреса»', desc(t) == f'Напишите в WhatsApp, позвоните или приходите в салон. Адрес: {A2}.', desc(t))
        site = await new_page()
        await site.goto(B + '/contacts?lang=ru'); await ready(site)
        check('one branch: one card, its name card on the map is open at once', await site.locator('#pageView .loc').count() == 1 and await site.locator('#pageView .mp-pop .mp-name').inner_text() == N2)
        check('one branch: the page agrees with the server about the description', await site.evaluate("document.querySelector('meta[name=description]').content") == desc(t))
        await site.goto(B + '/product/f-milan?lang=ru'); await site.wait_for_function('window.Shop'); await site.wait_for_timeout(400)
        await site.locator('#ppAdd').click(); await site.wait_for_timeout(300)
        await site.goto(B + '/checkout?lang=ru'); await site.wait_for_function('window.Shop'); await site.wait_for_timeout(500)
        check('one branch: checkout does not ask, pickup shows the address', await site.locator('#coBranchField').count() == 0 and await site.locator('#checkoutForm .choice small[data-cfg="address"]').inner_text() == A2)
        await site.fill('#coName', 'Один Филиал'); await site.fill('#coPhone', '0501112233'); await site.evaluate('window.__opened.length = 0')
        await site.locator('#checkoutForm [type=submit]').click(); await site.wait_for_timeout(1500)
        wa = await site.evaluate('window.__opened'); text = decode(wa[0])[1] if wa else ''
        d = json.loads(sql("SELECT data FROM ao_orders WHERE name='Один Филиал' ORDER BY id DESC LIMIT 1") or '{}')
        check('one branch: the order is sent, the shop is known without a question', bool(text) and 'Салон:' not in text and d.get('details', {}).get('branch') == N2, (text[-160:], d.get('details')))
        await site.context.close()
        site = await new_page(390, 844, True)
        await site.goto(B + '/?lang=ru'); await site.wait_for_function('window.Shop'); await site.wait_for_timeout(400)
        await site.locator('.menu-btn').tap(); await site.wait_for_timeout(400)
        check('one branch: phone menu shows the address and the hours', await site.locator('#siteNav .nav-locs .nav-info').all_inner_texts() == [A2, 'Ежедневно: 10:00–21:00'], await site.locator('#siteNav .nav-locs .nav-info').all_inner_texts())
        await site.context.close()

        print('--- филиал без метки: карта Google по адресу')
        await show([sql("SELECT slug FROM ao_items WHERE type='branch' AND JSON_VALUE(data, '$.coords') IS NULL")])
        only = const(get('/contacts?lang=ru')[2], 'BRANCHES')
        reqs.clear()
        site = await new_page()
        await site.goto(B + '/contacts?lang=ru'); await site.wait_for_selector('#pageView [data-branch-map] iframe', timeout=15000); await site.wait_for_timeout(400)
        src = await site.locator('#pageView [data-branch-map] iframe').get_attribute('src')
        check('no pins: the map of Google by the address, as before', len(only) == 1 and 'lat' not in only[0] and src == 'https://maps.google.com/maps?q=' + urllib.parse.quote('Bakı, Yeni küç., 9', safe='') + '&z=15&hl=ru&output=embed', src)
        check('no pins: the map library is not loaded', not any('leaflet' in u for u in reqs))
        await site.context.close()

        print('--- без филиалов')
        await show([])
        s, h, t = get('/contacts?lang=ru')
        check('no branches: description is the text of the page', desc(t) == 'Напишите в WhatsApp, позвоните или приходите в салон.', desc(t))
        site = await new_page()
        await site.goto(B + '/contacts?lang=ru'); await site.wait_for_function('window.Shop'); await site.wait_for_timeout(600)
        check('no branches: no list, no map, other contacts stay', not await site.locator('#pageView [data-branches]').is_visible() and not await site.locator('#pageView [data-branch-map]').is_visible() and await site.locator('#pageView .c-list a[data-cfg="phone"]').is_visible())
        check('no branches: the page agrees with the server about the description', await site.evaluate("document.querySelector('meta[name=description]').content") == desc(t))
        await site.context.close()

        print('--- обновление сайта, где адрес был в настройках')
        sql("DELETE FROM ao_items WHERE type='branch'")
        sql("UPDATE ao_settings SET value = JSON_SET(value, '$.address', JSON_OBJECT('az', 'Bakı, Köhnə küç., 5', 'ru', 'Баку, ул. Старая, 5'), '$.hours', JSON_OBJECT('az', JSON_ARRAY('Hər gün 10–19'), 'ru', JSON_ARRAY('Ежедневно 10–19')), '$.mapQuery', 'Asioptik Baku') WHERE name='config'")
        sql("UPDATE ao_settings SET value='3' WHERE name='data_version'")
        async def refresh():
            # любое сохранение в админ-панели сбрасывает готовые данные сайта; здесь — страница «Общие надписи» без правок
            await pg.goto(B + '/admin/?p=page&id=common'); await save(pg)
        await refresh()
        s, h, t = get('/contacts?lang=ru'); BR = const(t, 'BRANCHES')
        check('upgrade: the first branch is made from the old settings', len(BR) == 1 and BR[0]['id'] == 'main' and BR[0]['name'] == {'az': 'Asioptik', 'ru': 'Asioptik', 'en': 'Asioptik'} and BR[0]['address']['ru'] == 'Баку, ул. Старая, 5'
              and BR[0]['hours']['ru'] == ['Ежедневно 10–19'] and BR[0].get('mapQuery') == 'Asioptik Baku' and 'lat' not in BR[0], BR)
        check('upgrade: old values no longer go to the page with the settings', not any(k in const(t, 'CONFIG') for k in ('address', 'hours', 'mapQuery')))
        check('upgrade is recorded', sql("SELECT value FROM ao_settings WHERE name='data_version'") == '4')
        check('upgrade: description of «Контакты» keeps the address', desc(t) == 'Напишите в WhatsApp, позвоните или приходите в салон. Адрес: Баку, ул. Старая, 5.', desc(t))
        site = await new_page()
        await site.goto(B + '/contacts?lang=ru'); await site.wait_for_selector('#pageView [data-branch-map] iframe', timeout=15000); await site.wait_for_timeout(300)
        src = await site.locator('#pageView [data-branch-map] iframe').get_attribute('src')
        check('upgrade: the map looks for the same place as before', src == 'https://maps.google.com/maps?q=Asioptik%20Baku&z=15&hl=ru&output=embed' and await site.locator('#pageView .loc-name').inner_text() == 'Asioptik' and await site.locator('#pageView .loc-addr').inner_text() == 'Баку, ул. Старая, 5', src)
        await site.context.close()
        await pg.goto(B + '/admin/?p=list&type=branch')
        check('upgrade: the branch is in the admin panel and asks for a pin', await pg.locator('tbody tr').count() == 1 and await pg.locator('tbody .st', has_text='нет метки').count() == 1)
        sql("UPDATE ao_settings SET value='3' WHERE name='data_version'"); await refresh(); get('/')
        check('upgrade does not add a second branch when one is there', sql("SELECT COUNT(*) FROM ao_items WHERE type='branch'") == '1')
        sql("DELETE FROM ao_items WHERE type='branch'"); sql("UPDATE ao_settings SET value='4' WHERE name='data_version'"); await refresh(); get('/')
        check('branches removed by the owner do not come back', sql("SELECT COUNT(*) FROM ao_items WHERE type='branch'") == '0')

        check('no script errors', not errors, errors[:5])
        await b.close()
    print(f'\n{total - len(fails)} of {total} checks passed')
    if fails:
        print('FAILED:', fails); sys.exit(1)

asyncio.run(main())

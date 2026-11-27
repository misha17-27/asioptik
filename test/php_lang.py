"""Язык в адресе страницы: /ru/catalog, /en/contacts; у азербайджанского (основного) языка приставки нет.

Проверяется:
- каждая страница открывается на трёх языках по своему адресу, сервер и страница называют один и тот же адрес;
- прежние адреса с ?lang= ведут на новые одним переходом, чужой сайт в переадресацию подставить нельзя;
- кнопки языка меняют адрес без перезагрузки страницы, строка запроса и якорь остаются;
- сайт помнит выбранный язык: адрес без языка открывается на нём, и адрес это показывает;
- ссылки меню и карточек, canonical и hreflang — с языком в адресе; карта сайта и robots.txt знают все языки;
- версия сайта одним файлом по-прежнему держит язык в параметре ?lang=.

Запуск: sh test/serve.sh, затем python3 test/php_lang.py (базу тест ставит заново сам).
"""
import asyncio, html, http.client, json, re, sys
from playwright.async_api import async_playwright
from run import setup, lp
from php_reset import reset

B = 'http://127.0.0.1:8771'
ONE = 'http://127.0.0.1:8765/dist/optika-4-lupa.html'
SITE = 'https://asioptik.az'
LANGS = ('az', 'ru', 'en')
fails = []
total = 0
def check(name, ok, detail=''):
    global total
    total += 1
    if not ok:
        fails.append(name)
        print('  FAIL', name, '|', str(detail)[:400])
def get(path, method='GET', body=None, headers=None):
    c = http.client.HTTPConnection('127.0.0.1', 8771, timeout=60)
    c.request(method, path, body=body, headers=headers or {})
    r = c.getresponse(); text = r.read().decode('utf-8', 'replace'); c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, text
def meta(t):
    g = lambda pat: html.unescape((re.search(pat, t, re.S) or [None, ''])[1])
    return {'lang': g(r'<html lang="([a-z]+)"'), 'title': g(r'<title>(.*?)</title>'), 'canon': g(r'<link rel="canonical" href="([^"]*)"'), 'og': g(r'<meta property="og:url" content="([^"]*)"'),
            'alt': {l: html.unescape(u) for l, u in re.findall(r'<link rel="alternate" hreflang="([a-z-]+)" href="([^"]*)"', t)}}
def const(t, name):
    return json.loads(re.search(r'const ' + name + r' = (\{.*?\}|\[.*?\]);\n', t, re.S).group(1))
def site_url(path, lang):
    """Адрес для поисковиков: https://asioptik.az/, …/ru, …/en/catalog?cat=sun"""
    return SITE + lp(path, lang)


def server():
    s, h, t = get('/')
    pid = const(t, 'PRODUCTS')[0]['id']; post = const(t, 'POSTS')[0]['id']; brand = [b for b in const(t, 'BRANDS')][0]['id']
    pages = ['/', '/catalog', '/catalog?cat=frames', '/catalog?aud=kids', '/brands', f'/brands/{brand}', '/about', '/blog', f'/blog/{post}', '/contacts', '/checkout', f'/product/{pid}']

    # 1. каждая страница — на трёх языках, по своему адресу
    titles = {}
    for path in pages:
        for l in LANGS:
            u = lp(path, l); s, h, t = get(u); m = meta(t); titles[(path, l)] = m['title']
            check(f'{u}: opens in its language', s == 200 and m['lang'] == l, (s, m['lang']))
            check(f'{u}: address for search engines', m['canon'] == site_url(path, l) and m['og'] == m['canon'], m['canon'])
            # три языка и страница по умолчанию (x-default) — азербайджанская
            check(f'{u}: the three languages point at each other', m['alt'] == dict({x: site_url(path, x) for x in LANGS}, **{'x-default': site_url(path, 'az')}), m['alt'])
            links = re.findall(r'<a [^>]*href="([^"]*)"[^>]*data-view=', t)
            pre = '/' if l == 'az' else f'/{l}/'
            check(f'{u}: menu links keep the language', len(links) >= 8 and all(x.startswith(pre) for x in links) and (l != 'az' or not any(re.match(r'/(ru|en)/', x) for x in links)), links[:3])
            check(f'{u}: no ?lang= left in links', not re.findall(r'(?:href|content)="[^"]*[?&](?:amp;)?lang=', t), re.findall(r'(?:href|content)="[^"]*[?&](?:amp;)?lang=[^"]*', t)[:2])
        if not path.startswith('/brands/'):   # страница бренда называется его именем — оно на всех языках одно
            check(f'{path}: the title differs by language', len({titles[(path, l)] for l in LANGS}) == 3, [titles[(path, l)] for l in LANGS])
    s, h, t = get('/en/'); m = meta(t)
    check('/en/ with a slash at the end is the same page', s == 200 and m['lang'] == 'en' and m['canon'] == SITE + '/en', (s, m['canon']))

    # 2. прежние адреса ведут на новые одним переходом
    moved = [
        ('/?lang=en', '/en'), ('/?lang=ru', '/ru'), ('/?lang=az', '/'), ('/catalog?lang=ru', '/ru/catalog'), ('/catalog?cat=frames&lang=ru', '/ru/catalog?cat=frames'),
        ('/catalog?lang=en&aud=kids', '/en/catalog?aud=kids'), ('/catalog?lang=ru&cat=sun&utm_source=insta', '/ru/catalog?cat=sun&utm_source=insta'),
        (f'/product/{pid}?lang=en', f'/en/product/{pid}'), (f'/blog/{post}?lang=ru', f'/ru/blog/{post}'), (f'/brands/{brand}?lang=en', f'/en/brands/{brand}'),
        ('/contacts?lang=ru', '/ru/contacts'), ('/checkout?lang=en', '/en/checkout'), ('/index.php?lang=ru', '/ru'),
        # основной язык в адресе не пишется
        ('/az', '/'), ('/az/', '/'), ('/az/catalog?cat=sun', '/catalog?cat=sun'), (f'/az/product/{pid}', f'/product/{pid}'),
        # язык и в адресе, и в параметре: решает параметр — так выглядела бы ссылка, собранная по-старому
        ('/ru/catalog?lang=en', '/en/catalog'), ('/en/about?lang=az', '/about'), ('/az/blog?lang=ru', '/ru/blog'),
        # непонятный язык в параметре просто убирается
        ('/contacts?lang=xx', '/contacts'), ('/ru/contacts?lang=', '/ru/contacts'), ('/contacts?lang[]=ru', '/contacts'), ('/en?lang[a]=ru&cat=sun', '/en?cat=sun'),
        # совсем старые адреса: ?page= и ?product=
        (f'/?product={pid}&lang=en', f'/en/product/{pid}'), ('/?page=about&lang=ru', '/ru/about'), (f'/?page=blog&post={post}&lang=en', f'/en/blog/{post}'),
        ('/ru?page=blog', '/ru/blog'), (f'/en/?product={pid}', f'/en/product/{pid}'), ('/?page=catalog&cat=frames&aud=men&lang=ru', '/ru/catalog?cat=frames&aud=men'),
        # лишние «/» в адресе
        ('/en//catalog', '/en/catalog'), ('/ru//catalog?cat=sun', '/ru/catalog?cat=sun'), (f'/product//{pid}', f'/product/{pid}'),
    ]
    for path, to in moved:
        s, h, t = get(path)
        check(f'old address {path} → {to}', s == 301 and h.get('location') == to, (s, h.get('location')))
    for path, to in moved:   # и новый адрес открывается сразу, без второго перехода
        s, h, t = get(to)
        check(f'… {to} opens at once', s == 200, s)

    # 3. чужой сайт в переадресацию не подставить
    for path in ('/az//evil.example', '/ru//evil.example?lang=az', '//evil.example?lang=ru', '/az///evil.example/x', '/az/%5Cevil.example', '/en//evil.example?lang=az',
                 '/?lang=ru&page=//evil.example', '/?product=//evil.example&lang=en', '/az/%2F%2Fevil.example', '/ru/..%2F..%2Fevil.example?lang=az'):
        s, h, t = get(path); loc = h.get('location', '')
        check(f'redirect stays on the site: {path}', s in (301, 302, 400, 403, 404) and (not loc or (loc.startswith('/') and not loc.startswith('//') and '\\' not in loc and '://' not in loc)), (s, loc))

    # 4. неизвестная страница — ответ 404 и страница «не найдено» на языке адреса (переадресацию на главную поисковик считает ошибкой)
    for path, l in (('/en/nothing', 'en'), ('/ru/nothing/deeper', 'ru'), ('/nothing', 'az'), ('/ru/product/no-such', 'ru'), ('/en/blog/no-such', 'en'), ('/ru/brands/no-such', 'ru'),
                    ('/ru/en/catalog', 'ru'), ('/en/robots.txt', 'en'), ('/ru/sitemap.xml', 'ru'), ('/en/admin', 'en'), ('/en/catalog/extra', 'en')):
        s, h, t = get(path)
        check(f'unknown address {path}: 404 in its language', s == 404 and not h.get('location') and f'<html lang="{l}"' in t and '"notFound":1' in t, (s, h.get('location')))

    # 5. приём заказов — только по своему адресу, язык в адрес не добавляется
    s, h, t = get('/en/api/order', 'POST', '{}', {'Content-Type': 'application/json', 'Origin': B})
    check('orders are accepted only at /api/order', s == 404 and not h.get('location'), (s, h.get('location')))
    s, h, t = get('/api/order')
    check('/api/order itself is still the order endpoint', s == 405, s)

    # 6. robots.txt и карта сайта
    s, h, t = get('/robots.txt')
    check('robots.txt: checkout is closed in every language', all(f'Disallow: {x}checkout' in t for x in ('/', '/ru/', '/en/')) and 'lang=' not in t, t)
    s, h, t = get('/sitemap.xml')
    urls = re.findall(r'<url><loc>([^<]*)</loc>(.*?)</url>', t)
    locs = [u for u, _ in urls]
    check('sitemap: every page in three languages', len(locs) % 3 == 0 and len(locs) == len(set(locs)) and len([u for u in locs if u.startswith(SITE + '/ru')]) == len(locs) // 3
          and len([u for u in locs if u.startswith(SITE + '/en')]) == len(locs) // 3, len(locs))
    bad = []
    for u, rest in urls:
        alt = dict(re.findall(r'<xhtml:link rel="alternate" hreflang="([a-z]+)" href="([^"]*)"/>', rest))
        if set(alt) != set(LANGS) or u not in alt.values() or not all(v in locs for v in alt.values()): bad.append(u)
        else:
            az = alt['az'][len(SITE):]
            if alt['ru'] != site_url(html.unescape(az), 'ru') or alt['en'] != site_url(html.unescape(az), 'en'): bad.append(u)
    check('sitemap: translations are linked to each other', not bad, bad[:3])
    check('sitemap: no ?lang= and no checkout', '?lang=' not in t and ';lang=' not in t and 'checkout' not in t)
    for u in (SITE + '/', SITE + '/ru', SITE + '/en', SITE + '/ru/catalog', SITE + f'/en/product/{pid}', SITE + '/ru/catalog?cat=frames'):
        check(f'sitemap lists {u}', u in locs)
    print('server:', total, 'checks')
    return pid, post, brand


async def browser(pid, post, brand):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors = []
        async def new_page(w=1440, h=900, **kw):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, **kw)
            page = await ctx.new_page()
            page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and '/node_modules/@fontsource/' not in m.text and 'Failed to load resource' not in m.text else None)
            await setup(page)
            await page.route('https://images.pexels.com/**', lambda r: r.abort())
            return page
        pg = await new_page()
        tail = lambda: pg.evaluate('location.pathname + location.search + location.hash')
        doc = lambda: pg.evaluate("({lang: document.documentElement.lang, title: document.title, canon: document.querySelector('link[rel=canonical]').href, og: document.querySelector('meta[property=\"og:url\"]').content,"
                                  " alt: Object.fromEntries([...document.querySelectorAll('link[rel=alternate][hreflang]')].map(l => [l.hreflang, l.href])), mark: window.__mark || 0, saved: JSON.parse(localStorage.getItem('optika-lang'))})")
        async def agrees(name, path, lang):
            """Страница после работы скрипта называет тот же адрес и заголовок, что отдаёт сервер по этому адресу."""
            d = await doc(); s, h, t = get(lp(path, lang)); m = meta(t)
            check(name, (d['lang'], d['title'], d['canon'], d['og'], d['alt']) == (lang, m['title'], m['canon'], m['canon'], m['alt']) and m['canon'] == site_url(path, lang), (d, m['title'], m['canon']))
        async def go(path):
            await pg.goto(B + path); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(250)
        async def set_lang(l):
            await pg.locator(f'.hdr-right [data-set-lang="{l}"]').click(); await pg.wait_for_timeout(300)

        # 1. первое посещение: азербайджанский, адрес без языка
        await go('/')
        d = await doc()
        check('first visit: Azerbaijani at the plain address', await tail() == '/' and d['lang'] == 'az' and d['saved'] is None, (await tail(), d))

        # 2. кнопка языка меняет адрес, страница не перезагружается
        await pg.evaluate('window.__mark = 1')
        await set_lang('en'); d = await doc()
        check('EN button: the address becomes /en, no reload', await tail() == '/en' and d['mark'] == 1 and d['saved'] == 'en', (await tail(), d))
        await agrees('EN home agrees with the server', '/', 'en')
        nav = await pg.evaluate("[...document.querySelectorAll('a[data-view]')].map(a => a.getAttribute('href'))")
        check('EN: every link to a page of the site starts with /en/', len(nav) >= 8 and all(u.startswith('/en/') for u in nav), [u for u in nav if not u.startswith('/en/')][:3])
        await set_lang('ru')
        check('RU button: /ru', await tail() == '/ru' and (await doc())['mark'] == 1, await tail())
        await set_lang('az')
        check('AZ button: back to the plain address', await tail() == '/' and (await doc())['saved'] == 'az', await tail())
        nav = await pg.evaluate("[...document.querySelectorAll('a[data-view]')].map(a => a.getAttribute('href'))")
        check('AZ: links without a language', all(not re.match(r'/(ru|en)(/|$)', u) for u in nav), nav[:3])

        # 3. переходы по сайту остаются в выбранном языке
        await set_lang('en')
        await pg.locator('#siteNav a[data-view="catalog"]').first.click(); await pg.wait_for_timeout(500)
        check('EN: menu → /en/catalog', await tail() == '/en/catalog' and (await doc())['mark'] == 1, await tail())
        await agrees('EN catalog agrees with the server', '/catalog', 'en')
        cards = await pg.evaluate("[...document.querySelectorAll('#productsGrid .card-title a')].map(a => a.getAttribute('href'))")
        check('EN: product cards link to /en/product/…', len(cards) > 10 and all(u.startswith('/en/product/') for u in cards), cards[:2])
        await pg.locator('#productsGrid .card-title a').first.click(); await pg.wait_for_timeout(500)
        prod = (await tail()).split('/')[-1]
        check('EN: product page address', await tail() == f'/en/product/{prod}', await tail())
        await agrees('EN product agrees with the server', f'/product/{prod}', 'en')
        # смена языка на странице товара: тот же товар, другой адрес
        await set_lang('ru')
        check('product: RU button keeps the product', await tail() == f'/ru/product/{prod}' and (await doc())['mark'] == 1, await tail())
        await agrees('RU product agrees with the server', f'/product/{prod}', 'ru')
        await set_lang('az')
        check('product: AZ button → plain address', await tail() == f'/product/{prod}', await tail())
        await agrees('AZ product agrees with the server', f'/product/{prod}', 'az')
        # «Назад»: записи истории были сделаны на английском, а язык теперь азербайджанский — адрес его и показывает
        await pg.go_back(); await pg.wait_for_timeout(500)
        check('back after a language change: same page, current language', await tail() == '/catalog' and (await doc())['lang'] == 'az' and await pg.locator('#productsGrid .card').count() > 10, await tail())
        await agrees('… and it agrees with the server', '/catalog', 'az')
        await pg.go_back(); await pg.wait_for_timeout(500)
        check('back again: home in the current language', await tail() == '/', await tail())
        await pg.go_forward(); await pg.wait_for_timeout(500); await pg.go_forward(); await pg.wait_for_timeout(500)
        check('forward: the product, in the current language', await tail() == f'/product/{prod}' and await pg.locator('#ppName').is_visible(), await tail())

        # 4. раздел каталога и якорь при смене языка остаются
        await go('/ru/catalog?cat=frames&aud=men')
        await set_lang('en')
        check('section and audience survive a language change', await tail() == '/en/catalog?cat=frames&aud=men', await tail())
        await agrees('… and the page agrees with the server', '/catalog?cat=frames&aud=men', 'en')
        await go('/ru#repair'); await pg.wait_for_timeout(600)
        await set_lang('en')
        check('anchor survives a language change', await tail() == '/en#repair', await tail())
        for path in ('/about', '/blog', f'/blog/{post}', '/brands', f'/brands/{brand}', '/contacts', '/checkout'):
            await go(lp(path, 'ru')); await pg.evaluate('window.__mark = 1')
            await set_lang('en')
            check(f'{path}: RU → EN changes only the language', await tail() == lp(path, 'en') and (await doc())['mark'] == 1, await tail())
            await agrees(f'{path}: EN agrees with the server', path, 'en')
            await set_lang('az')
            check(f'{path}: EN → AZ', await tail() == path, await tail())
            await agrees(f'{path}: AZ agrees with the server', path, 'az')

        # 5. сайт помнит язык: адрес без языка открывается на нём, и адрес это показывает
        await go('/ru'); n0 = await pg.evaluate('history.length')
        await go('/contacts'); d = await doc()
        check('remembered language: /contacts opens as /ru/contacts', await tail() == '/ru/contacts' and d['lang'] == 'ru' and 'Контакты' in d['title'], (await tail(), d['title']))
        check('… without an extra step in the history', await pg.evaluate('history.length') == n0 + 1, (n0, await pg.evaluate('history.length')))
        await agrees('… and agrees with the server', '/contacts', 'ru')
        await pg.go_back(); await pg.wait_for_timeout(500)
        check('… back leads to the previous page, not to the same one', await tail() == '/ru', await tail())
        await go(f'/product/{pid}')
        check('remembered language: product address gets /ru too', await tail() == f'/ru/product/{pid}' and (await doc())['lang'] == 'ru', await tail())
        await go('/catalog?cat=sun#x')
        check('remembered language: query and anchor are kept', await tail() == '/ru/catalog?cat=sun#x', await tail())
        # язык в адресе важнее запомненного, и он запоминается
        await go('/en/about'); d = await doc()
        check('language in the address wins over the remembered one', await tail() == '/en/about' and d['lang'] == 'en' and d['saved'] == 'en', (await tail(), d['saved']))
        await go('/')
        check('… and is remembered for the next visit', await tail() == '/en' and (await doc())['lang'] == 'en', await tail())
        await pg.reload(); await pg.wait_for_function('window.Shop')
        check('reload keeps the address and the language', await tail() == '/en' and (await doc())['lang'] == 'en', await tail())

        # 6. прежние адреса в браузере
        await go('/catalog?lang=ru&cat=frames')
        check('old address with ?lang= opens the new one', await tail() == '/ru/catalog?cat=frames' and (await doc())['lang'] == 'ru', await tail())
        await go('/az/contacts'); d = await doc()
        check('/az/… drops the prefix; the remembered language still applies', await tail() == '/ru/contacts' and d['lang'] == 'ru', await tail())
        await go('/en/'); await pg.wait_for_timeout(200)
        check('slash at the end is removed from the address', await tail() == '/en', await tail())
        await go('/en/nothing')
        check('unknown page: «not found» in the same language, the address stays', await tail() == '/en/nothing' and await pg.evaluate("document.documentElement.lang") == 'en'
              and await pg.evaluate("document.body.classList.contains('is-view-notfound')"), await tail())

        # 7. телефон: язык переключается в меню, адрес меняется так же
        await pg.context.close()
        pg = await new_page(390, 844, is_mobile=True, has_touch=True, device_scale_factor=2)
        await go('/catalog')
        await pg.locator('.hdr-right .js-menu-toggle').click(); await pg.wait_for_timeout(400)
        await pg.locator('.nav-foot [data-set-lang=ru]').click(); await pg.wait_for_timeout(400)
        check('phone: language button in the menu changes the address', await tail() == '/ru/catalog' and (await doc())['lang'] == 'ru', await tail())
        await pg.locator('#siteNav .nav-links a[data-view="about"]').click(); await pg.wait_for_timeout(500)
        check('phone: menu link keeps the language', await tail() == '/ru/about', await tail())
        await pg.context.close()

        # 8. версия сайта одним файлом: язык остаётся в параметре, путь не меняется
        pg = await new_page()
        await pg.goto(ONE); await pg.wait_for_function('window.Shop'); path0 = await pg.evaluate('location.pathname')
        await set_lang('en')
        u = await pg.evaluate('location.pathname + location.search')
        check('one-file site: language stays in ?lang=', u == path0 + '?lang=en' and await pg.evaluate('document.documentElement.lang') == 'en', u)
        await pg.goto(ONE + '?lang=ru&page=catalog'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(300)
        check('one-file site: ?lang=ru&page=catalog opens the Russian catalog', await pg.evaluate('document.documentElement.lang') == 'ru' and await pg.locator('#productsGrid .card').count() > 10
              and await pg.evaluate('location.pathname') == path0, await pg.evaluate('location.href'))
        href = await pg.locator('#siteNav a[data-view="about"]').first.get_attribute('href')
        check('one-file site: links keep ?lang= and ?page=', 'lang=ru' in href and 'page=about' in href and not href.startswith('/'), href)
        await pg.context.close()
        check('no script errors in the browser', not errors, errors[:3])
        await b.close()


async def main():
    print('clean install:', reset())
    pid, post, brand = server()
    await browser(pid, post, brand)
    print(f'\n{total - len(fails)} of {total} checks passed')
    if fails:
        print('FAILED:', len(fails)); sys.exit(1)

asyncio.run(main())

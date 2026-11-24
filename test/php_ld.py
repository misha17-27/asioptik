"""SEO: поисковые слова в заголовках и описаниях, разметка для поисковиков (JSON-LD), x-default и картинка для ссылок.

Проверяется:
- слова «eynək satışı», «eynək sifarişi», «Bakıda», «açki» (и их соответствия на русском и английском) стоят в
  заголовке, описании и видимом тексте главной; метатега keywords нет (Google его не читает);
- заголовки всех страниц: не длиннее 70 знаков, разные, без повторов одной фразы; слишком длинное название товара
  даёт короткий заголовок — одинаково на сервере и в браузере;
- разметка: салоны (Optician) с адресом и точкой на карте, товар с ценой, статья, «хлебные крошки»; заготовки телефона
  и Instagram в неё не попадают; закрытые от поиска страницы идут без разметки; текст товара не ломает страницу;
- x-default на каждой странице и в карте сайта; og:image, og:locale;
- после перехода по сайту устаревшая разметка убирается.

Запуск: sh test/serve.sh, затем python3 test/php_ld.py (базу тест ставит заново сам).
"""
import asyncio, html, http.client, json, pathlib, re, sys
from playwright.async_api import async_playwright
from run import setup, lp
from php_reset import reset, sql

ROOT = pathlib.Path(__file__).resolve().parent.parent
B = 'http://127.0.0.1:8771'
SITE = 'https://asioptik.az'
LANGS = ('az', 'ru', 'en')
fails = []
total = 0
def check(name, ok, detail=''):
    global total
    total += 1
    if not ok:
        fails.append(name)
        print('  FAIL', name, '|', str(detail)[:500])
def get(path):
    c = http.client.HTTPConnection('127.0.0.1', 8771, timeout=60); c.request('GET', path)
    r = c.getresponse(); t = r.read().decode('utf-8', 'replace'); c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, t
def head(t):
    g = lambda pat: html.unescape((re.search(pat, t, re.S) or [None, ''])[1])
    lds = re.findall(r'<script type="application/ld\+json" data-ld>(.*?)</script>', t, re.S)
    return {'title': g(r'<title>(.*?)</title>'), 'desc': g(r'<meta name="description" content="([^"]*)"'), 'canon': g(r'<link rel="canonical" href="([^"]*)"'),
            'robots': g(r'<meta name="robots" content="([^"]*)"'), 'xdef': g(r'<link rel="alternate" hreflang="x-default" href="([^"]*)"'),
            'image': g(r'<meta property="og:image" content="([^"]*)"'), 'locale': g(r'<meta property="og:locale" content="([^"]*)"'), 'card': g(r'<meta name="twitter:card" content="([^"]*)"'),
            'ld': lds, 'graph': json.loads(lds[0])['@graph'] if len(lds) == 1 else []}
def const(t, name):
    return json.loads(re.search(r'const ' + name + r' = (\{.*?\}|\[.*?\]);\n', t, re.S).group(1))
def fresh():
    """Данные сайта меняются прямо в базе — готовая копия страниц (кэш) убирается."""
    for f in (ROOT / 'site/storage/cache').glob('*.json'): f.unlink()
def setting(name, change):
    v = json.loads(bytes.fromhex(sql(f"SELECT HEX(value) FROM ao_settings WHERE name = '{name}'")).decode('utf-8')); change(v)
    sql(f"UPDATE ao_settings SET value = UNHEX('{json.dumps(v, ensure_ascii=False).encode('utf-8').hex()}') WHERE name = '{name}'"); fresh()
def item(slug, change):
    v = json.loads(bytes.fromhex(sql(f"SELECT HEX(data) FROM ao_items WHERE slug = '{slug}'")).decode('utf-8')); change(v)
    sql(f"UPDATE ao_items SET data = UNHEX('{json.dumps(v, ensure_ascii=False).encode('utf-8').hex()}') WHERE slug = '{slug}'"); fresh()
def types(graph): return [x['@type'] for x in graph]
def node(graph, kind): return next((x for x in graph if x['@type'] == kind), {})


def server():
    s, h, t = get('/')
    P, POSTS, BRANDS, BR = const(t, 'PRODUCTS'), const(t, 'POSTS'), const(t, 'BRANDS'), const(t, 'BRANCHES')
    pid, post, brand = P[0]['id'], POSTS[0]['id'], BRANDS[0]['id']

    # 1. поисковые слова на главной
    words = {'az': (['Eynək satışı Bakıda', 'eynək sifarişi'], ['eynək satışı', 'eynək sifarişi', 'Bakıda', 'açki']),
             'ru': (['Продажа очков в Баку', 'заказ очков'], ['Продажа и заказ очков в Баку', 'оправы', 'контактные линзы']),
             'en': (['Glasses for sale in Baku', 'order glasses'], ['Glasses for sale and to order in Baku', 'sunglasses', 'contact lenses'])}
    for l in LANGS:
        m = head(get(lp('/', l))[2])
        check(f'{l}: the home title carries the search phrases and the shop name', all(w in m['title'] for w in words[l][0]) and m['title'].endswith('| Asioptik'), m['title'])
        check(f'{l}: the home description carries them too', all(w in m['desc'] for w in words[l][1]) and 'Asioptik' in m['desc'] and len(m['desc']) <= 160, m['desc'])
    check('no keywords meta tag: Google does not read it', 'name="keywords"' not in t)

    # 2. заголовки всех страниц
    s, h, sm = get('/sitemap.xml')
    paths = sorted({html.unescape(u)[len(SITE):] or '/' for u in re.findall(r'<loc>([^<]*)</loc>', sm)})
    check('sitemap gives the pages to look at', len(paths) > 100 and '/ru/catalog' in paths, len(paths))
    seen = {l: {} for l in LANGS}
    for path in paths:
        l = 'ru' if path.startswith('/ru') and (len(path) == 3 or path[3] in '/?') else 'en' if path.startswith('/en') and (len(path) == 3 or path[3] in '/?') else 'az'
        m = head(get(path)[2]); ti = m['title']
        check(f'{path}: title is 10–70 characters', 10 <= len(ti) <= 70, (len(ti), ti))
        check(f'{path}: description is 50–160 characters', 50 <= len(m['desc']) <= 160, (len(m['desc']), m['desc']))
        w = re.findall(r'\w+', ti.lower()); pairs = [' '.join(w[i:i + 2]) for i in range(len(w) - 1)]
        check(f'{path}: no phrase is repeated in the title', len(pairs) == len(set(pairs)), ti)
        check(f'{path}: the title ends with the shop name', re.search(r'(\| Asioptik(, (Bakı|Баку|Baku))?|\| Asioptik optika, Bakı|\| Оптика Asioptik, Баку|\| Asioptik optician, Baku|— Asioptik)$', ti) is not None, ti)
        check(f'{path}: x-default names the Azerbaijani page', m['xdef'] == SITE + re.sub(r'^/(ru|en)(?=/|\?|$)', '', path) or (m['xdef'] == SITE + '/' and re.fullmatch(r'/(ru|en)', path)), m['xdef'])
        check(f'{path}: share image and locale', m['image'] == SITE + '/assets/img/og.png' and m['locale'] == {'az': 'az_AZ', 'ru': 'ru_RU', 'en': 'en_US'}[l] and m['card'] == 'summary_large_image', (m['image'], m['locale']))
        check(f'{path}: one valid block of structured data', len(m['ld']) == 1 and isinstance(m['graph'], list) and m['graph'], m['ld'][:1])
        seen[l].setdefault(ti, []).append(path)
    for l in LANGS:
        dup = {k: v for k, v in seen[l].items() if len(v) > 1}
        check(f'{l}: every page has its own title', not dup, list(dup.items())[:2])
    for f, size in (('og.png', (1200, 630)), ('logo.png', (512, 512))):
        s, h, body = get('/assets/img/' + f)
        from PIL import Image
        check(f'{f} is served as a picture of the right size', s == 200 and h.get('content-type') == 'image/png' and Image.open(ROOT / 'site/assets/img' / f).size == size, (s, h.get('content-type')))
    check('sitemap: x-default next to every translation', sm.count('hreflang="x-default"') == sm.count('<url>') and f'<xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/catalog"/>' in sm)

    # 3. разметка: главная и контакты — салоны
    for l in LANGS:
        for page in ('/', '/contacts'):
            g = head(get(lp(page, l))[2])['graph']
            want = (['WebSite'] if page == '/' else []) + ['Organization'] + ['Optician'] * len(BR) + (['BreadcrumbList'] if page != '/' else [])
            check(f'{lp(page, l)}: shops are described', types(g) == want, types(g))
            for b, x in zip(BR, [x for x in g if x['@type'] == 'Optician']):
                check(f'{lp(page, l)}: shop «{b["id"]}» — name, address, map point', x['name'] == b['name'][l] and x['address'] == {'@type': 'PostalAddress', 'streetAddress': b['address'][l], 'addressCountry': 'AZ'}
                      and x['geo'] == {'@type': 'GeoCoordinates', 'latitude': b['lat'], 'longitude': b['lng']} and x['url'] == SITE + lp('/contacts', l) and x['@id'] == f'{SITE}/contacts#{b["id"]}', x)
            org = node(g, 'Organization')
            check(f'{lp(page, l)}: placeholders are not published as facts', 'telephone' not in org and 'sameAs' not in org and not any('telephone' in x for x in g) and org['logo'] == SITE + '/assets/img/logo.png', org)
    setting('config', lambda c: c.update({'phone': '+994 12 555 12 34', 'instagram': 'asioptik.baku'}))
    g = head(get('/')[2])['graph']; org = node(g, 'Organization')
    check('real phone and Instagram appear in the markup', org.get('telephone') == '+994 12 555 12 34' and org.get('sameAs') == ['https://www.instagram.com/asioptik.baku'] and all(x.get('telephone') == '+994 12 555 12 34' for x in g if x['@type'] == 'Optician'), org)

    # 4. товар
    p0 = next(p for p in P if p['id'] == pid)
    for l in LANGS:
        m = head(get(lp(f'/product/{pid}', l))[2]); x = node(m['graph'], 'Product'); bc = node(m['graph'], 'BreadcrumbList')['itemListElement']
        check(f'{l}: product — name, code, address, description', types(m['graph']) == ['Product', 'BreadcrumbList'] and x['name'] == p0['name'][l] and x['sku'] == pid and x['url'] == m['canon'] and x['description'] == m['desc'], x)
        check(f'{l}: product — price in manats, brand, section', x['offers']['price'] == str(p0['price']) and x['offers']['priceCurrency'] == 'AZN' and x['offers']['url'] == m['canon'] and x['brand']['name'] == 'Asi Classic' and x.get('category'), x.get('offers'))
        check(f'{l}: product without a photo claims no picture', 'image' not in x)
        check(f'{l}: breadcrumbs lead from the home page to the product', [c['position'] for c in bc] == [1, 2, 3, 4] and bc[0]['item'] == SITE + lp('/', l) and bc[1]['item'] == SITE + lp('/catalog', l)
              and bc[2]['item'] == SITE + lp('/catalog', l) + '?cat=' + p0['cat'] and bc[3] == {'@type': 'ListItem', 'position': 4, 'name': p0['name'][l], 'item': m['canon']}, bc)
        for c in bc:
            s, h, t2 = get(c['item'][len(SITE):] or '/')
            check(f'{l}: breadcrumb «{c["name"]}» opens', s == 200, (c['item'], s))
    # статья и бренд
    for l in LANGS:
        m = head(get(lp(f'/blog/{post}', l))[2]); x = node(m['graph'], 'Article')
        check(f'{l}: article — headline, date, address', types(m['graph']) == ['Article', 'BreadcrumbList'] and x['headline'] == POSTS[0]['title'][l] and x['datePublished'] == POSTS[0]['date'] and x['mainEntityOfPage'] == m['canon']
              and x['inLanguage'] == l and x['publisher']['logo']['url'] == SITE + '/assets/img/logo.png', x)
        m = head(get(lp(f'/brands/{brand}', l))[2]); bc = node(m['graph'], 'BreadcrumbList')['itemListElement']
        check(f'{l}: brand page — breadcrumbs', types(m['graph']) == ['BreadcrumbList'] and len(bc) == 3 and bc[2]['item'] == m['canon'] and bc[2]['name'] == BRANDS[0]['name'], bc)
    # закрытые от поиска страницы — без разметки
    for path in ('/checkout', '/ru/checkout'):
        m = head(get(path)[2])
        check(f'{path}: closed to search engines, no markup', m['robots'] == 'noindex' and m['ld'] == [], (m['robots'], m['ld']))

    # 5. товар без цены, с фото, с очень длинным названием и с «кодом» в названии
    item(pid, lambda d: d.update({'price': 0, 'img': 'uploads/p/0123456789abcdef.jpg'}))
    x = node(head(get(f'/product/{pid}')[2])['graph'], 'Product')
    check('product without a price: no offer is invented', 'offers' not in x, x.get('offers'))
    check('product with a photo: the photo is named, as the share image too', x.get('image') == [SITE + '/uploads/p/0123456789abcdef.jpg'] and head(get(f'/product/{pid}')[2])['image'] == SITE + '/uploads/p/0123456789abcdef.jpg', x.get('image'))
    long = 'Оправа с очень длинным названием, которое не помещается в заголовок страницы целиком'
    evil = 'Оправа </script><script>window.__x=1</script> «Тест»'
    item(pid, lambda d: (d['name'].update({'ru': long, 'az': evil}), d.update({'price': 140})))
    m = head(get(f'/ru/product/{pid}')[2])
    check('a long product name gives the short title form', m['title'] == long + ' — Asioptik' and len(long) > 70, m['title'])
    s, h, t = get(f'/product/{pid}'); m = head(t)
    check('markup survives a product name with script tags', len(m['ld']) == 1 and node(m['graph'], 'Product')['name'] == evil and '<script>window.__x' not in t and t.count('</script>') == t.count('<script'), m['ld'][0][:160])
    print('server:', total, 'checks')
    return pid, long, evil


async def browser(pid, long, evil):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await b.new_context(viewport={'width': 1366, 'height': 800}); pg = await ctx.new_page(); errors = []
        pg.on('pageerror', lambda e: errors.append(str(e)))
        await setup(pg); await pg.route('https://images.pexels.com/**', lambda r: r.abort())
        async def go(path):
            await pg.goto(B + path); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(300)
        # длинное название: браузер называет страницу так же, как сервер
        await go(f'/ru/product/{pid}')
        check('browser: the long name gives the same short title', await pg.title() == long + ' — Asioptik', await pg.title())
        await pg.evaluate("localStorage.clear()")   # иначе адрес без языка открылся бы на русском, выбранном выше
        await go(f'/product/{pid}')
        check('browser: a product name with script tags is only text', await pg.evaluate('window.__x') is None and evil in await pg.inner_text('#ppName'))
        # видимый текст главной
        await pg.evaluate("localStorage.clear()")
        for l, words in (('az', ['Bakıda eynək satışı və eynək sifarişi', 'açki']), ('ru', ['Продажа и заказ очков в Баку']), ('en', ['Glasses for sale and to order in Baku'])):
            await go(lp('/', l)); text = await pg.inner_text('#pageView, main')
            check(f'{l}: the search phrases are in the text visitors read', all(w in text for w in words), text[:300])
            # увеличительное стекло первого экрана повторяет его содержимое для красоты и скрыто от программ чтения (aria-hidden)
            n = await pg.evaluate("[...document.querySelectorAll('h1')].filter(h => h.offsetParent !== null && !h.closest('[aria-hidden=\"true\"]')).length")
            check(f'{l}: one main heading on the page', n == 1, n)
        # переход по сайту: разметка первой страницы убирается, x-default и заголовок — уже новой страницы
        await go('/ru')
        check('home page carries its markup', await pg.locator('script[data-ld]').count() == 1)
        await pg.locator('#siteNav a[data-view="catalog"]').first.click(); await pg.wait_for_timeout(500)
        xd = await pg.evaluate("document.querySelector('link[hreflang=\"x-default\"]').href")
        check('after moving to another page the old markup is gone', await pg.locator('script[data-ld]').count() == 0 and xd == SITE + '/catalog' and await pg.title() == 'Каталог — продажа и заказ очков в Баку | Asioptik', (xd, await pg.title()))
        s, h, t = get('/ru/catalog')
        check('… and the server names that page the same way', head(t)['title'] == await pg.title() and head(t)['desc'] == await pg.evaluate("document.querySelector('meta[name=description]').content"))
        check('no script errors in the browser', not errors, errors[:3])
        await b.close()


async def main():
    print('clean install:', reset())
    pid, long, evil = server()
    await browser(pid, long, evil)
    # тексты заголовков можно менять в админ-панели: «Страницы» → «Каталог»
    from php_client import admin_client
    s, h, t = admin_client().get('/admin/?p=page&id=catalog')
    check('admin: title templates of the catalog can be edited', s == 200 and '{name} — Bakıda satış və sifariş | {shop}' in html.unescape(t) and '{title} — eynək satışı və sifarişi, Bakı | {shop}' in html.unescape(t), s)
    print(f'\n{total - len(fails)} of {total} checks passed')
    if fails:
        print('FAILED:', len(fails)); sys.exit(1)

asyncio.run(main())

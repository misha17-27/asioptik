"""Заголовки и описания страниц (title и description) и страницы брендов.

У каждой страницы сайта — главной, каталога, разделов, страниц «для кого», брендов, товаров, статей — на всех трёх языках
должны быть свои заголовок и описание: непустые, разумной длины, без повторов. Страница, отданная сервером,
и та же страница после работы скрипта сайта должны называться одинаково.

Запуск: sh test/serve.sh, затем python3 test/php_seo.py (базу тест ставит заново сам).
"""
import asyncio, collections, html, http.client, json, re, sys, urllib.parse
from playwright.async_api import async_playwright
from run import setup, lp, FORGET
from php_reset import reset, PW

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
        print('  FAIL', name, '|', str(detail)[:400])
def get(path, follow=False):
    c = http.client.HTTPConnection('127.0.0.1', 8771, timeout=60)
    c.request('GET', path)
    r = c.getresponse(); body = r.read().decode('utf-8', 'replace'); c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, body
def meta(t):
    g = lambda pat: html.unescape((re.search(pat, t, re.S) or [None, ''])[1])
    return {'title': g(r'<title>(.*?)</title>'), 'desc': g(r'<meta name="description" content="([^"]*)"'),
            'ogt': g(r'<meta property="og:title" content="([^"]*)"'), 'ogd': g(r'<meta property="og:description" content="([^"]*)"'),
            'canon': g(r'<link rel="canonical" href="([^"]*)"'), 'robots': g(r'<meta name="robots" content="([^"]*)"'),
            'alt': [(l, html.unescape(u)) for l, u in re.findall(r'<link rel="alternate" hreflang="([a-z]+)" href="([^"]*)"', t)]}
def const(t, name):
    return json.loads(re.search(r'const ' + name + r' = (\{.*?\}|\[.*?\]);\n', t, re.S).group(1))
def with_lang(path, lang):
    """Адрес страницы на языке: язык — первая часть адреса (/ru/catalog, /en), у азербайджанского её нет."""
    return lp(path, lang)
def canon_of(path, lang):
    """Адрес страницы, как его ждут поисковики: язык в начале адреса, затем страница, раздел и «для кого»."""
    u = urllib.parse.urlparse(path); q = urllib.parse.parse_qsl(u.query)
    q = [(k, v) for k in ('cat', 'aud') for kk, v in q if kk == k]
    return SITE + ('' if lang == 'az' else '/' + lang) + ('' if u.path == '/' and lang != 'az' else u.path) + ('?' + urllib.parse.urlencode(q) if q else '')
CYR = re.compile('[А-Яа-яЁё]'); AZL = re.compile('[əƏğĞıİöÖüÜşŞçÇ]')


def addresses(t):
    """Все адреса сайта: (вид, адрес, попадает ли в карту сайта)."""
    P, POSTS, CATS, AUDS, BRANDS = (const(t, n) for n in ('PRODUCTS', 'POSTS', 'CATEGORIES', 'AUDIENCES', 'BRANDS'))
    def in_aud(p, a):
        ids = [x['id'] for x in a.get('parts', [])] or [a['id']]
        return any(f in ids for f in p.get('for', []))
    out = [('home', '/', True), ('catalog', '/catalog', True), ('brands', '/brands', True), ('about', '/about', True), ('blog', '/blog', True),
           ('contacts', '/contacts', True), ('checkout', '/checkout', False)]
    auds = []
    for a in AUDS:
        auds += [a] + a.get('parts', [])
    for c in CATS:
        if any(p['cat'] == c['id'] for p in P): out.append(('cat', '/catalog?cat=' + c['id'], True))
    for a in auds:
        if any(in_aud(p, a) for p in P): out.append(('aud', '/catalog?aud=' + a['id'], True))
        for c in CATS:   # раздел внутри страницы «для кого»: в карте сайта его нет, но ссылки на него стоят на плитках
            if any(p['cat'] == c['id'] and in_aud(p, a) for p in P): out.append(('cat+aud', f"/catalog?cat={c['id']}&aud={a['id']}", False))
    for b in BRANDS:
        if any(p.get('brand') == b['id'] for p in P): out.append(('brand', '/brands/' + b['id'], True))
    out += [('product', '/product/' + p['id'], True) for p in P]
    out += [('post', '/blog/' + p['id'], True) for p in POSTS]
    return out, P, BRANDS


def crawl(addrs):
    rows = {}
    for kind, path, _ in addrs:
        for lang in LANGS:
            s, h, t = get(with_lang(path, lang))
            m = meta(t); m.update(kind=kind, path=path, lang=lang, status=s)
            rows[(path, lang)] = m
    return rows


def server_checks(addrs, rows):
    print(f'server: {len(addrs)} addresses x {len(LANGS)} languages')
    for (path, lang), r in rows.items():
        k = f"{with_lang(path, lang)}"
        check(f'200 {k}', r['status'] == 200, r['status'])
        check(f'title {k}', 10 <= len(r['title']) <= 70 and r['title'].strip() == r['title'], f"{len(r['title'])}: {r['title']}")
        check(f'description {k}', 50 <= len(r['desc']) <= 160 and r['desc'].strip() == r['desc'], f"{len(r['desc'])}: {r['desc']}")
        check(f'no template marks {k}', not re.search(r'[{}]|\.\.|\s\s| \.|undefined|null', r['title'] + ' ' + r['desc']), r['title'] + ' | ' + r['desc'])
        check(f'og = title, description {k}', r['ogt'] == r['title'] and r['ogd'] == r['desc'], (r['ogt'], r['ogd']))
        check(f'canonical {k}', r['canon'] == canon_of(path, lang), (r['canon'], canon_of(path, lang)))
        check(f'hreflang {k}', dict(r['alt']) == {l: canon_of(path, l) for l in LANGS}, r['alt'])
        check(f'robots {k}', r['robots'] == ('noindex' if r['kind'] == 'checkout' else ''), r['robots'])
        txt = r['title'] + ' ' + r['desc']
        if lang == 'ru': check(f'russian text {k}', bool(CYR.search(r['desc'])), r['desc'])
        else: check(f'no cyrillic {k}', not CYR.search(txt), txt)
        if lang == 'en': check(f'no azerbaijani letters {k}', not AZL.search(txt), txt)
    # одинаковых заголовков и описаний у разных страниц быть не должно (страница оформления заказа поисковикам закрыта)
    for field in ('title', 'desc'):
        seen = collections.defaultdict(list)
        for (path, lang), r in rows.items():
            if r['kind'] != 'checkout': seen[(lang, r[field])].append(path)
        dup = {k: v for k, v in seen.items() if len(v) > 1}
        check(f'unique {field}', not dup, list(dup.items())[:3])


def sitemap_checks(addrs):
    s, h, t = get('/sitemap.xml')
    locs = re.findall(r'<loc>([^<]*)</loc>', t)
    # каждая страница названа на трёх языках: /catalog, /ru/catalog, /en/catalog
    want = [html.escape(canon_of(p, l), quote=False) for k, p, inmap in addrs if inmap for l in LANGS]
    check('sitemap: every page that search engines should see, in every language', sorted(locs) == sorted(want), (sorted(set(want) - set(locs))[:5], sorted(set(locs) - set(want))[:5]))
    check('sitemap: no repeats', len(locs) == len(set(locs)), len(locs))
    print('sitemap:', len(locs), 'addresses')


async def browser_checks(addrs, rows, P, BRANDS):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        errors = []
        async def new_page():
            # у каждой вкладки своя память: сайт запоминает выбранный язык, а проверке нужен язык из адреса
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
            page = await ctx.new_page()
            page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
            # шрифты в тесте подменены местными файлами с другого порта — политика сайта их справедливо не пускает
            # (и картинки с чужих сайтов в тесте не загружаются — отсюда «Failed to load resource»)
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and '/node_modules/@fontsource/' not in m.text and 'Failed to load resource' not in m.text else None)
            page.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
            await setup(page)
            await page.route('https://images.pexels.com/**', lambda r: r.abort())
            return page
        async def forget():
            """Сайт забывает выбранный язык: следующая страница откроется на языке из адреса."""
            await pg.evaluate('localStorage.clear()')
        READ = "() => ({title: document.title, desc: document.querySelector('meta[name=description]').content, canon: document.querySelector('link[rel=canonical]').href, ogt: document.querySelector('meta[property=\"og:title\"]').content, ogd: document.querySelector('meta[property=\"og:description\"]').content})"
        async def same(name, path, lang):
            got = await pg.evaluate(READ); r = rows[(path, lang)]
            check(f'{name} {with_lang(path, lang)}', (got['title'], got['desc'], got['canon'], got['ogt'], got['ogd']) == (r['title'], r['desc'], r['canon'], r['title'], r['desc']),
                  (got, r['title'], r['desc'], r['canon']))

        # 1. страница, открытая по адресу: после работы скрипта заголовок и описание те же, что отдал сервер
        n = 0
        for lang in LANGS:
            pg = await new_page()
            for kind, path, _ in addrs:
                if kind == 'product': continue
                await pg.goto(B + with_lang(path, lang)); await pg.wait_for_function('window.Shop')
                await same('opened by address:', path, lang); n += 1
            await pg.context.close()
        print('browser: opened by address', n)

        # 2. переходы по сайту без перезагрузки: товары, бренды, статьи — заголовок и описание те же, что у сервера
        n = 0
        for lang in LANGS:
            pg = await new_page()
            await pg.goto(B + with_lang('/', lang)); await pg.wait_for_function('window.Shop')
            for kind, path, _ in addrs:
                if kind == 'product': await pg.evaluate('id => Shop.go(id)', path.split('/')[-1])
                elif kind == 'brand': await pg.evaluate("id => Shop.go({view: 'brands', post: id})", path.split('/')[-1])
                elif kind == 'post': await pg.evaluate("id => Shop.go({view: 'blog', post: id})", path.split('/')[-1])
                elif kind in ('brands', 'about', 'blog', 'contacts'): await pg.evaluate("v => Shop.go({view: v})", path.strip('/'))
                else: continue
                await same('after a click:', path, lang); n += 1
            await pg.evaluate("Shop.go('')"); await same('back to home:', '/', lang)
            await pg.context.close()
        print('browser: in-site navigation', n)
        pg = await new_page()

        # 3. страница «Бренды» и страница бренда
        filled = [x for x in BRANDS if any(q.get('brand') == x['id'] for q in P)]
        await pg.goto(B + '/ru'); await pg.wait_for_function('window.Shop')
        nav = pg.locator('#siteNav a[data-view="brands"]')
        check('menu: link to brands', await nav.is_visible() and (await nav.inner_text()).strip() == 'Бренды' and await nav.get_attribute('href') == '/ru/brands', await nav.get_attribute('href'))
        check('footer: link to brands', await pg.locator('.ft-nav a[data-view="brands"]').is_visible())
        await nav.click(); await pg.wait_for_timeout(300)
        check('brands page: address and heading', pg.url == B + '/ru/brands' and await pg.inner_text('#pgTitle') == 'Бренды', pg.url)
        check('brands page: menu link is marked', await nav.get_attribute('aria-current') == 'page')
        tiles = pg.locator('.btiles .btile')
        check('brands page: a tile for every brand with products', await tiles.count() == len(filled) and await tiles.locator('b').all_inner_texts() == [x['name'] for x in filled], await tiles.locator('b').all_inner_texts())
        first = filled[0]; items = [q for q in P if q.get('brand') == first['id']]
        tile = tiles.first
        check('brand tile: text, count and price', first['text']['ru'] in await tile.inner_text() and str(len(items)) in await tile.inner_text() and str(min(q['price'] for q in items)) in await tile.inner_text(), await tile.inner_text())
        check('brand tile: pictures of its products', await tile.locator('.ctile-arts > span').count() == min(3, len(items)))
        await tile.click(); await pg.wait_for_timeout(300)
        check('brand page: address', pg.url == B + f"/ru/brands/{first['id']}", pg.url)
        check('brand page: heading and text', await pg.inner_text('#pgTitle') == first['name'] and await pg.inner_text('.pg-lead') == first['text']['ru'], await pg.inner_text('.pg-lead'))
        cards = pg.locator('#pageView .br-grid .card')
        check('brand page: only its products', await cards.evaluate_all('els => els.map(e => e.dataset.pid)') == [q['id'] for q in items], await cards.evaluate_all('els => els.map(e => e.dataset.pid)'))
        check('brand page: path back', await pg.locator('#pageView .pp-crumbs a').all_inner_texts() == ['Главная', 'Бренды'] and await pg.locator('#pageView .post-cta a').all_inner_texts() == ['Все бренды', 'Весь каталог'], await pg.locator('#pageView .pp-crumbs a').all_inner_texts())
        # карточка на странице бренда работает как в каталоге: цвет меняется, товар открывается
        sw = cards.first.locator('[data-swatch]')
        if await sw.count() > 1:
            await sw.nth(1).click()
            check('brand page: colour switch on a card', await sw.nth(1).get_attribute('aria-pressed') == 'true')
        await cards.first.locator('.card-title a').click(); await pg.wait_for_timeout(300)
        check('brand page → product', pg.url == B + f"/ru/product/{items[0]['id']}", pg.url)
        link = pg.locator('.pp-brand a')
        check('product page: brand is a link to the brand page', (await link.inner_text()).strip() == first['name'] and await link.get_attribute('href') == f"/ru/brands/{first['id']}", await link.get_attribute('href'))
        await link.click(); await pg.wait_for_timeout(300)
        check('product → brand page', pg.url == B + f"/ru/brands/{first['id']}" and await pg.inner_text('#pgTitle') == first['name'], pg.url)
        await pg.go_back(); await pg.wait_for_timeout(300)
        check('back button: product again', pg.url == B + f"/ru/product/{items[0]['id']}" and await pg.locator('#ppName').is_visible(), pg.url)
        await pg.go_back(); await pg.wait_for_timeout(300); await pg.go_back(); await pg.wait_for_timeout(300)
        check('back button: brands list again', pg.url == B + '/ru/brands' and await tiles.count() == len(filled), pg.url)
        # язык меняется на месте: страница бренда остаётся открытой, тексты — на новом языке
        await forget(); await pg.goto(B + f"/brands/{first['id']}"); await pg.wait_for_function('window.Shop')
        check('brand page: opened in the main language', await pg.inner_text('.pg-lead') == first['text']['az'], await pg.inner_text('.pg-lead'))
        await pg.evaluate("Shop.setLang('en')"); await pg.wait_for_timeout(300)
        check('brand page: language switch', await pg.inner_text('.pg-lead') == first['text']['en'] and await pg.title() == rows[('/brands/' + first['id'], 'en')]['title'], await pg.title())
        # телефон: плитки в два столбца, ничего не вылезает за экран
        for w in (390, 320):
            await pg.set_viewport_size({'width': w, 'height': 780})
            await pg.goto(B + '/ru/brands'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(200)
            box = await pg.evaluate("[...document.querySelectorAll('.btile')].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.right)]; })")
            check(f'phone {w}: brand tiles in two columns', len({x[0] for x in box}) == 2 and all(0 <= l and r <= w for l, r in box), box)
            check(f'phone {w}: no sideways scroll on brands', await pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
            await pg.goto(B + f"/ru/brands/{first['id']}"); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(200)
            check(f'phone {w}: no sideways scroll on a brand page', await pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
        await pg.set_viewport_size({'width': 1440, 'height': 900})

        # 4. прежние и неверные адреса
        s, h, t = get('/?page=brands&post=' + first['id'] + '&lang=ru')
        check('old address ?page=brands&post= → /brands/код', s == 301 and h.get('location') == f"/ru/brands/{first['id']}", (s, h.get('location')))
        s, h, t = get('/en/brands/no-such-brand')
        check('unknown brand → list of brands', s in (301, 302) and h.get('location') == '/en/brands', (s, h.get('location')))
        s, h, t = get('/brands/' + first['id'] + '/more')
        check('extra path after a brand → home', s in (301, 302) and h.get('location') == '/', (s, h.get('location')))
        s, h, t = get('/catalog?brand=' + first['id'])
        check('catalog filtered by brand keeps the catalog address for search engines', s == 200 and meta(t)['canon'] == SITE + '/catalog', meta(t)['canon'])
        s, h, t = get('/ru/catalog?cat=lenses&aud=kids')   # детских линз для очков в наборе нет: раздел не открывается, как и на самой странице
        m = meta(t)
        check('section without products for this audience is not opened', m['title'] == rows[('/catalog?aud=kids', 'ru')]['title'] and m['canon'] == SITE + '/ru/catalog?aud=kids', (m['title'], m['canon']))
        await pg.goto(B + '/ru/catalog?cat=lenses&aud=kids'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(300)
        check('… and the page agrees with the server', await pg.title() == m['title'] and await pg.evaluate("document.querySelector('link[rel=canonical]').href") == m['canon'], await pg.title())

        # 5. админ-панель: свои заголовки и описания, новые поля
        await pg.goto(B + '/admin/'); await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click(); await pg.wait_for_load_state()
        await pg.goto(B + '/admin/?p=pages')
        row = pg.locator('tr', has=pg.locator('a', has_text=re.compile('^Бренды$'))).first
        check('admin, pages: «Бренды» with its address', '/brands' in await row.inner_text(), await row.inner_text())
        await pg.goto(B + '/admin/?p=page&id=brands')
        ph = {l: (await pg.get_attribute(f'#f-seo-title--{l}', 'placeholder'), await pg.get_attribute(f'#f-seo-desc--{l}', 'placeholder')) for l in LANGS}
        check('admin, page «Бренды»: grey text = what the site shows', all(ph[l] == (rows[('/brands', l)]['title'], rows[('/brands', l)]['desc']) for l in LANGS), ph)
        for pid, path in (('home', '/'), ('catalog', '/catalog'), ('about', '/about'), ('blog', '/blog'), ('contacts', '/contacts')):
            await pg.goto(B + f'/admin/?p=page&id={pid}')
            ph = {l: (await pg.get_attribute(f'#f-seo-title--{l}', 'placeholder'), await pg.get_attribute(f'#f-seo-desc--{l}', 'placeholder')) for l in LANGS}
            check(f'admin, page {pid}: grey text = what the site shows', all(ph[l] == (rows[(path, l)]['title'], rows[(path, l)]['desc']) for l in LANGS), ph)
        # своё описание страницы «Бренды» и изменённое название каталога
        await pg.goto(B + '/admin/?p=page&id=brands')
        await pg.fill('#f-seo-title--az', 'Brendlər — test başlığı'); await pg.fill('#f-seo-desc--az', 'Brendlər səhifəsi üçün öz təsvirimiz: salonumuzdakı bütün markalar bir yerdə.')
        await pg.locator('.actions .btn').first.click(); await pg.wait_for_load_state()
        await pg.goto(B + '/admin/?p=page&id=catalog')
        await pg.locator('[data-lg-set=ru]').first.click()
        field = pg.locator('.field', has=pg.locator('code.key', has_text=re.compile(r'^cat\.title$'))).locator('.lang[data-lg=ru] input')
        await field.fill('Наш каталог'); await pg.locator('.actions .btn').first.click(); await pg.wait_for_load_state()
        s, h, t = get('/brands'); m = meta(t)
        check('own title and description of «Бренды» reach the page', (m['title'], m['desc']) == ('Brendlər — test başlığı', 'Brendlər səhifəsi üçün öz təsvirimiz: salonumuzdakı bütün markalar bir yerdə.'), m)
        s, h, t = get('/ru/brands'); check('… other languages keep the site text', meta(t)['title'] == rows[('/brands', 'ru')]['title'], meta(t)['title'])
        s, h, t = get('/ru/catalog'); m1 = meta(t)
        s, h, t = get('/ru/catalog?cat=frames'); m2 = meta(t)
        check('changed catalog name is in the server title', m1['title'] == 'Наш каталог — Asioptik' and m2['title'] == 'Оправы — Наш каталог — Asioptik', (m1['title'], m2['title']))
        for path, m in (('/brands', None), ('/ru/catalog', m1), ('/ru/catalog?cat=frames', m2)):
            s, h, t = get(path); m = m or meta(t)
            await forget(); await pg.goto(B + path); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(200)
            got = await pg.evaluate(READ)
            check(f'page agrees with the server after admin changes {path}', (got['title'], got['desc']) == (m['title'], m['desc']), (got, m['title'], m['desc']))

        # бренд: описание, логотип, свои заголовок и описание
        await pg.goto(B + '/admin/?p=list&type=brand')
        check('admin, brands: note about the brand pages', 'своя страница' in await pg.inner_text('.card-tools .note'))
        check('admin, brands: address and length of title and description in the list', f"/brands/{first['id']}" in await pg.inner_text('tbody tr >> nth=0') and await pg.locator('tbody tr >> nth=0').locator('.dot').count() == 1, await pg.inner_text('tbody tr >> nth=0'))
        await pg.locator('tbody tr >> nth=0').locator('a.strong').click(); await pg.wait_for_load_state()
        auto = rows[('/brands/' + first['id'], 'az')]
        check('admin, brand: fields', all([await pg.locator(s).count() == 1 for s in ('#f-text-az', '#f-text-ru', '#f-text-en', 'input[name="file[img]"]', '#f-seoTitle-az', '#f-seoDesc-az')]))
        check('admin, brand: description from the first data', await pg.input_value('#f-text-az') == first['text']['az'])
        check('admin, brand: grey text = what the site shows', (await pg.get_attribute('#f-seoTitle-az', 'placeholder'), await pg.get_attribute('#f-seoDesc-az', 'placeholder')) == (auto['title'], auto['desc']), await pg.get_attribute('#f-seoDesc-az', 'placeholder'))
        await pg.fill('#f-text-az', 'Yeni təsvir: hər gün üçün rahat çərçivələr'); await pg.fill('#f-seoTitle-az', 'Asi Classic çərçivələri — Bakıda Asioptik')
        await pg.set_input_files('input[name="file[img]"]', '/tmp/seo/logo.png')
        await pg.locator('.actions .btn').first.click(); await pg.wait_for_load_state()
        s, h, t = get('/brands/' + first['id']); m = meta(t)
        check('brand: own title', m['title'] == 'Asi Classic çərçivələri — Bakıda Asioptik', m['title'])
        check('brand: description follows the new text (a full stop is added)', m['desc'] == 'Asi Classic. Yeni təsvir: hər gün üçün rahat çərçivələr. Bakıda Asioptik optika salonu: saytda sifariş, WhatsApp-da təsdiq.', m['desc'])
        await forget(); await pg.goto(B + '/brands/' + first['id']); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(200)
        got = await pg.evaluate(READ)
        check('brand: page agrees with the server', (got['title'], got['desc']) == (m['title'], m['desc']), got)
        logo = pg.locator('.br-logo')
        check('brand page: logo', await logo.count() == 1 and await logo.evaluate('e => e.complete && e.naturalWidth > 0') and '/uploads/brand/' in await logo.get_attribute('src'), await logo.get_attribute('src') if await logo.count() else None)
        await pg.goto(B + '/brands'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(200)
        tl = pg.locator('.btile').first.locator('.btile-logo')
        check('brands page: logo instead of the name, the name stays for screen readers', await tl.count() == 1 and await tl.get_attribute('alt') == first['name'] and await pg.locator('.btile').first.locator('b').count() == 0)

        # раздел каталога: свои заголовок и описание
        await pg.goto(B + '/admin/?p=list&type=category')
        check('admin, sections: address in the list', '/catalog?cat=frames' in await pg.inner_text('tbody'), (await pg.inner_text('tbody'))[:200])
        await pg.locator('tbody tr', has_text='/catalog?cat=sun').locator('a.strong').click(); await pg.wait_for_load_state()
        s, h, t = get('/en/catalog?cat=sun'); auto = meta(t)
        await pg.locator('[data-lg-set=en]').first.click()
        check('admin, section: grey text = what the site shows', (await pg.get_attribute('#f-seoTitle-en', 'placeholder'), await pg.get_attribute('#f-seoDesc-en', 'placeholder')) == (auto['title'], auto['desc']), await pg.get_attribute('#f-seoDesc-en', 'placeholder'))
        await pg.fill('#f-seoTitle-en', 'Sunglasses in Baku — Asioptik'); await pg.fill('#f-seoDesc-en', 'Sunglasses with UV400 lenses at the Asioptik optician in Baku: aviators, cat-eye and round frames.')
        await pg.locator('.actions .btn').first.click(); await pg.wait_for_load_state()
        s, h, t = get('/en/catalog?cat=sun'); m = meta(t)
        check('section: own title and description', (m['title'], m['desc']) == ('Sunglasses in Baku — Asioptik', 'Sunglasses with UV400 lenses at the Asioptik optician in Baku: aviators, cat-eye and round frames.'), m)
        s, h, t = get('/en/catalog?cat=sun&aud=women')
        check('section inside «for whom» keeps its own text', meta(t)['title'] == rows[('/catalog?cat=sun&aud=women', 'en')]['title'], meta(t)['title'])
        await pg.goto(B + '/en/catalog?cat=sun'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(300)
        got = await pg.evaluate(READ)
        check('section: page agrees with the server', (got['title'], got['desc']) == (m['title'], m['desc']), got)

        # бренд без товаров: страницы в списке и в карте сайта нет, поисковикам она закрыта
        await pg.goto(B + '/admin/?p=edit&type=brand'); await pg.fill('#f-name', 'Empty Brand'); await pg.locator('.actions .btn').first.click(); await pg.wait_for_load_state()
        s, h, t = get('/ru/brands/empty-brand'); m = meta(t)
        check('brand without products: page opens, closed to search engines', s == 200 and m['robots'] == 'noindex' and m['title'] == 'Empty Brand — Asioptik', (s, m['robots'], m['title']))
        check('brand without products: description', m['desc'] == 'Empty Brand. Салон оптики Asioptik в Баку: заказ на сайте, подтверждение в WhatsApp.', m['desc'])
        s, h, t = get('/sitemap.xml')
        check('brand without products: not in the sitemap', 'empty-brand' not in t and '/brands/' + first['id'] in t)
        await pg.goto(B + '/ru/brands/empty-brand'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(200)
        check('brand without products: says so, offers the catalog', 'сейчас нет' in await pg.inner_text('#pageView .catalog-empty') and await pg.locator('#pageView .br-grid').count() == 0)
        check('brand without products: lead is written by the site', await pg.inner_text('.pg-lead') == 'Товары бренда Empty Brand в салоне оптики Asioptik.', await pg.inner_text('.pg-lead'))
        await pg.goto(B + '/ru/brands'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(200)
        check('brand without products: no tile', await pg.locator('.btile').count() == len(filled))

        # ни у одного бренда нет товаров: ссылки «Бренды» в меню нет, страница закрыта поисковикам
        ids = [int(x) for x in re.findall(r'p=edit&(?:amp;)?type=brand&(?:amp;)?id=(\d+)', (await pg.goto(B + '/admin/?p=list&type=brand') and await pg.content()))]
        for i in sorted(set(ids)):
            await pg.goto(B + f'/admin/?p=edit&type=brand&id={i}')
            if await pg.input_value('#f-name') != 'Empty Brand':
                await pg.uncheck('input[name=active]'); await pg.locator('.actions .btn').first.click(); await pg.wait_for_load_state()
        s, h, t = get('/ru/brands'); m = meta(t)
        s2, h2, t2 = get('/sitemap.xml')
        check('no brands with products: «Бренды» is closed to search engines and left out of the sitemap', s == 200 and m['robots'] == 'noindex' and '/brands' not in t2, (m['robots'], '/brands' in t2))
        await pg.goto(B + '/ru/brands'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(200)
        check('no brands with products: the page says so', 'скоро появятся' in await pg.inner_text('#pageView .catalog-empty'))
        check('no brands with products: no link in the menu and the footer', not await pg.locator('#siteNav a[data-view="brands"]').is_visible() and not await pg.locator('.ft-nav a[data-view="brands"]').is_visible())
        await pg.goto(B + f"/ru/product/{items[0]['id']}"); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(200)
        check('no brands: product page has no brand line', await pg.locator('.pp-brand').count() == 0)

        check('no script errors', not errors, errors[:5])
        await b.close()


def make_logo():
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (600, 160), (255, 255, 255, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 30, 592, 130), radius=18, outline=(15, 43, 91, 255), width=10)
    d.line((60, 80, 540, 80), fill=(29, 95, 209, 255), width=14)
    import pathlib; pathlib.Path('/tmp/seo').mkdir(exist_ok=True); im.save('/tmp/seo/logo.png')


async def main():
    print('clean install:', reset())
    make_logo()
    s, h, t = get('/')
    addrs, P, BRANDS = addresses(t)
    rows = crawl(addrs)
    server_checks(addrs, rows)
    sitemap_checks(addrs)
    await browser_checks(addrs, rows, P, BRANDS)
    print(f'\n{total - len(fails)} of {total} checks passed')
    if fails:
        print('FAILED:', len(fails)); sys.exit(1)

asyncio.run(main())

"""Сайт во временной подпапке чужого сайта (как mguliyev.com/asioptik на хостинге с cPanel) и переезд на свой домен.

Стенд — sh test/serve_sub.sh: «основной сайт» на http://127.0.0.1:8772/ со своими .htaccess, admin/ и assets/,
Asioptik чистой копией в его подпапке /asioptik/; та же папка отдаётся корнем отдельного сайта на http://127.0.0.1:8773/.
Проверка сама ставит сайт через install.php, поэтому перед каждым запуском стенд поднимается заново:

    sh test/serve.sh && sh test/serve_sub.sh && python3 test/php_subdir.py

Что проверяется: ни один адрес не выходит из подпапки (страницы, картинки, заказы, админ-панель, установщик),
основной сайт не задет, временный адрес закрыт от поисковиков, а после переезда на свой домен те же файлы и та же
база работают без правок.
"""
import asyncio, http.client, json, pathlib, re, subprocess, sys, time, urllib.parse
from playwright.async_api import async_playwright
from run import setup, ROOT
SUB, OWN = 8772, 8773                 # сайт в подпапке «основного» и та же папка корнем своего домена
PRE = '/asioptik'
TEMP = f'stage.example:{SUB}'         # временный адрес: домен «основного сайта»
MAIN = 'asioptik.az'                  # основной адрес из «Настроек сайта»
SITE = pathlib.Path('/tmp/asioptik-sub/root/asioptik')
DB = 'asioptik_sub'
PW = 'Test-Admin-2026'                # пароль только для локальной тестовой базы
DBPW = 'test-only-local'
FAILS = []


def check(name, ok, info=''):
    print(('ok   ' if ok else 'FAIL ') + name + (' | ' + str(info) if info != '' else ''))
    if not ok: FAILS.append(name)


def sql(q):
    return subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', DB, '-N', '--raw', '--default-character-set=utf8mb4', '-e', q], capture_output=True, text=True).stdout.strip()


class Jar:
    """Куки как в браузере: отправляются только на адреса внутри своего пути."""
    def __init__(self): self.c = {}

    def take(self, headers):
        for sc in headers.get('set-cookie', []):
            first, *attrs = [x.strip() for x in sc.split(';')]
            name, _, val = first.partition('=')
            path = next((a.partition('=')[2] for a in attrs if a.lower().startswith('path=')), '/')
            self.c[name] = (val, path)

    def header(self, path):
        p = path.split('?')[0]
        return '; '.join(f'{n}={v}' for n, (v, cp) in self.c.items() if p.startswith(cp))

    def path(self, name): return self.c.get(name, ('', None))[1]


def req(port, method, path, body=None, headers=None, host=TEMP, jar=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=60)
    h = {'Host': host}; h.update(headers or {})
    if jar is not None and jar.header(path): h['Cookie'] = jar.header(path)
    if isinstance(body, dict) and h.get('Content-Type') == 'application/json': body = json.dumps(body)
    elif isinstance(body, dict):
        body = urllib.parse.urlencode(body); h['Content-Type'] = 'application/x-www-form-urlencoded'
    if isinstance(body, str): body = body.encode()
    c.request(method, path, body=body, headers=h)
    r = c.getresponse(); data = r.read(); c.close()
    hs = {}
    for k, v in r.getheaders(): hs.setdefault(k.lower(), []).append(v)
    if jar is not None: jar.take(hs)
    return r.status, hs, data.decode('utf-8', 'replace')


def one(h, name): return (h.get(name) or [''])[0]
def is_main_site(h): return 'x-main-site' in h          # ответил «основной сайт», а не Asioptik
URL_ATTR = re.compile(r'(?:href|src|action|poster|data-src)="([^"]*)"')


def outside(html, pre):
    """Адреса со страницы, которые ведут на этот же домен, но мимо папки сайта."""
    out = []
    for u in set(URL_ATTR.findall(html)):
        u = u.replace('&amp;', '&')
        if u.startswith('//') or not u.startswith('/'): continue      # чужие сайты, якоря, data:, tel:, mailto:
        if pre and not (u == pre or u.startswith(pre + '/')): out.append(u)
    return sorted(out)


def stuck(html):
    """Адреса с названием временной папки, оставшиеся на странице после переезда."""
    return re.findall(r'["\'(=]' + re.escape(PRE) + r'/[^"\'\s)]*', html)[:3]


def page_const(html, name):
    m = re.search(r'const ' + name + r' = (\{.*?\}|\[.*?\]);\n', html, re.S)
    return json.loads(m.group(1)) if m else None


# ====================== до установки: сайт в подпапке, основной сайт рядом ======================
print('--- основной сайт и пустая подпапка')
if (SITE / 'storage/config.php').exists():
    sys.exit('Стенд уже установлен: поднимите его заново — sh test/serve_sub.sh')
s, h, t = req(SUB, 'GET', '/'); check('main site answers at the domain root', s == 200 and 'MAIN SITE' in t and is_main_site(h))
s, h, t = req(SUB, 'GET', '/admin/'); check('main site keeps its own /admin/', 'MAIN ADMIN' in t)
s, h, t = req(SUB, 'GET', '/assets/main.css'); check('main site keeps its own /assets/', s == 200 and 'color:red' in t)
s, h, t = req(SUB, 'GET', '/some/page'); check('main site handles its own unknown addresses', 'MAIN SITE' in t)
s, h, t = req(SUB, 'GET', PRE); check('folder without a slash goes to the folder', s == 301 and one(h, 'location').endswith(PRE + '/'), one(h, 'location'))
for p in ['/', '/catalog', '/admin/', '/product/f-milan']:
    s, h, t = req(SUB, 'GET', PRE + p)
    check(f'before install {p} leads to the installer in the folder', s == 302 and one(h, 'location') == PRE + '/install.php' and not is_main_site(h), one(h, 'location'))
s, h, t = req(SUB, 'GET', PRE + '/install.php')
check('installer opens in the folder', s == 200 and 'Установка' in t and not is_main_site(h))
check('installer takes its style and icon from the folder', f'href="{PRE}/assets/css/admin.css"' in t and f'rel="icon" href="{PRE}/favicon.ico"' in t and not outside(t, PRE), outside(t, PRE))
check('installer on a real domain does not offer the file database', 'file_db' not in t)
form = {'host': '127.0.0.1:3307', 'name': DB, 'user': 'aotest', 'pass': 'wrong-db-password', 'login': 'admin', 'password': PW, 'password2': PW}
s, h, t = req(SUB, 'POST', PRE + '/install.php', form)
check('wrong database password: nothing is installed', 'Готово' not in t and not (SITE / 'storage/config.php').exists() and (SITE / 'install.php').exists())
form['pass'] = DBPW
s, h, t = req(SUB, 'POST', PRE + '/install.php', form)
check('site installs from the folder', s == 200 and 'Готово' in t, re.sub(r'<[^>]+>', ' ', t)[-200:] if 'Готово' not in t else '')
check('links after install stay in the folder', f'href="{PRE}/admin/"' in t and f'href="{PRE}/"' in t and not outside(t, PRE), outside(t, PRE))
check('installer removed itself, settings file written', not (SITE / 'install.php').exists() and (SITE / 'storage/config.php').exists())
cfg_text = (SITE / 'storage/config.php').read_text()
check('settings file does not pin the folder name', "'base'" not in cfg_text)
s, h, t = req(SUB, 'GET', PRE + '/install.php'); check('installer address no longer opens', s in (302, 404) and not is_main_site(h), f'{s} {one(h, "location")}')
s, h, t = req(SUB, 'GET', '/'); check('main site is still intact after install', 'MAIN SITE' in t)

# ====================== страницы сайта во временной подпапке ======================
print('--- страницы сайта')
PAGES = ['/', '/catalog', '/catalog?cat=frames', '/catalog?aud=kids', '/about', '/blog', '/blog/care', '/contacts', '/checkout', '/product/f-milan', '/?lang=ru', '/catalog?lang=en', '/index.php']
home = ''
for p in PAGES:
    s, h, t = req(SUB, 'GET', PRE + p)
    if p == '/': home = t
    bad = outside(t, PRE)
    check(f'page {p}', s == 200 and not is_main_site(h) and '<title>' in t and not bad, bad or s)
cfg = page_const(home, 'CONFIG')
check('page script knows its folder', cfg['basePath'] == PRE + '/' and cfg['api'] == PRE + '/api/order', (cfg['basePath'], cfg['api']))
prods = page_const(home, 'PRODUCTS')
imgs = [p['img'] for p in prods if p.get('img')]
check('local product photos, if any, are addressed inside the folder', all(not i.startswith('/') or i.startswith(PRE + '/') for i in imgs), [i for i in imgs if i.startswith('/')][:3])
for a in sorted(set(re.findall(r'(?:href|src)="(' + PRE + r'/assets/[^"?]*)', home))):
    s, h, t = req(SUB, 'GET', a)
    check(f'asset {a.replace(PRE, "")}', s == 200 and not is_main_site(h) and len(t) > 1000, s)
s, h, t = req(SUB, 'GET', PRE + '/favicon.ico'); check('site icon is served from the folder', s == 200 and 'icon' in one(h, 'content-type'))
for p, to in [('/?page=about', '/about'), ('/?product=f-milan', '/product/f-milan'), ('/?page=blog&post=care&lang=ru', '/blog/care?lang=ru'), ('/nope', '/'), ('/nope/deeper?lang=ru', '/?lang=ru'), ('/product/no-such', '/catalog'), ('/blog/no-such', '/blog')]:
    s, h, t = req(SUB, 'GET', PRE + p)
    check(f'redirect {p} stays in the folder', s in (301, 302) and one(h, 'location') == PRE + to, f'{s} {one(h, "location")}')
print('--- закрытые папки и файлы')
for p in ['/app/', '/app/core/bootstrap.php', '/app/data/seed.json', '/app/site/shell.html', '/storage/', '/storage/config.php', '/storage/cache/site.json', '/storage/logs/php-errors.log', '/storage/sessions/',
          '/.htaccess', '/.user.ini', '/uploads/', '/uploads/.htaccess', '/README.md', '/.git/config', '/backup.sql']:
    s, h, t = req(SUB, 'GET', PRE + p)
    check(f'closed {p}', s in (403, 404) and not is_main_site(h) and 'MAIN SITE' not in t and '<?php' not in t, s)

# ====================== временный адрес закрыт от поисковиков ======================
print('--- поисковики и временный адрес')
s, h, t = req(SUB, 'GET', PRE + '/')
check('temporary address: header tells search engines not to index', 'noindex' in one(h, 'x-robots-tag') and 'nofollow' in one(h, 'x-robots-tag'), one(h, 'x-robots-tag'))
check('temporary address: the same in the page itself', '<meta name="robots" content="noindex, nofollow">' in t)
canon = re.search(r'rel="canonical" href="([^"]*)"', t).group(1)
check('page address for search engines is the main one, not the temporary', canon == f'https://{MAIN}/' and 'stage.example' not in t, canon)
s, h, t = req(SUB, 'GET', PRE + '/product/f-milan?lang=ru')
check('product page on the temporary address is closed too', 'noindex' in one(h, 'x-robots-tag') and t.count('name="robots"') == 1 and f'href="https://{MAIN}/product/f-milan?lang=ru"' in t)
s, h, t = req(SUB, 'GET', PRE + '/about', headers={'X-Forwarded-Proto': 'https'})
check('no domain-wide https rule is set from a folder of another site', 'strict-transport-security' not in h, one(h, 'strict-transport-security'))
s, h, t = req(SUB, 'GET', PRE + '/about', host='evil.example')
check('foreign Host header is not copied into the page', 'evil.example' not in t)
s, h, t = req(SUB, 'GET', PRE + '/robots.txt')
check('robots.txt names the folder', s == 200 and f'Disallow: {PRE}/admin/' in t and f'Disallow: {PRE}/api/' in t and f'Disallow: {PRE}/checkout' in t, t.replace('\n', ' | '))
check('robots.txt on the temporary address: no sitemap, pages stay readable', 'Sitemap' not in t and 'Disallow: /\n' not in t and 'noindex' in one(h, 'x-robots-tag'))
s, h, t = req(SUB, 'GET', PRE + '/sitemap.xml')
locs = re.findall(r'<loc>([^<]*)</loc>', t)
check('sitemap opens and lists main-address pages', s == 200 and len(locs) > 20 and all(u.startswith(f'https://{MAIN}/') for u in locs) and 'noindex' in one(h, 'x-robots-tag'), locs[:2])

# ====================== заказ ======================
print('--- заказ с сайта')
order = {'kind': 'order', 'lang': 'ru', 'token': cfg['apiToken'], 'name': 'Подпапка Тест', 'phone': '+994 50 123 45 67', 'total': 140, 'text': 'Заказ: Оправа «Милан» × 1 — 140 ₼',
         'details': {'items': [{'id': 'f-milan', 'name': 'Оправа «Милан»', 'qty': 1, 'price': 140, 'sum': 140}]}}
J = {'Content-Type': 'application/json'}
s, h, t = req(SUB, 'POST', PRE + '/api/order', dict(order), dict(J, Origin=f'http://{TEMP}'))
check('order is accepted at the folder address', s == 200 and json.loads(t).get('ok') is True and not is_main_site(h), t[:120])
check('order is in the database', sql("SELECT COUNT(*) FROM ao_orders WHERE name = 'Подпапка Тест'") == '1')
s, h, t = req(SUB, 'POST', PRE + '/api/order', dict(order), dict(J, Origin='http://evil.example'))
check('order from another site is refused', s == 403 and 'origin' in t, t[:80])
s, h, t = req(SUB, 'POST', '/api/order', dict(order), J)
check('same address outside the folder belongs to the main site', is_main_site(h) and sql("SELECT COUNT(*) FROM ao_orders WHERE name = 'Подпапка Тест'") == '1')

# ====================== админ-панель ======================
print('--- админ-панель')
jar = Jar()
s, h, t = req(SUB, 'GET', PRE + '/admin'); check('admin folder without a slash', s == 301 and one(h, 'location').endswith(PRE + '/admin/'), one(h, 'location'))
s, h, t = req(SUB, 'GET', PRE + '/admin/', jar=jar)
check('guest is sent to the login page in the folder', s == 302 and one(h, 'location') == PRE + '/admin/?p=login', one(h, 'location'))
check('session cookie is limited to the folder admin', jar.path('ao_admin') == PRE + '/admin/', jar.path('ao_admin'))
check('cookie is not sent to the main site admin or to the site pages', jar.header('/admin/') == '' and jar.header(PRE + '/') == '' and jar.header(PRE + '/admin/?p=login') != '')
s, h, t = req(SUB, 'GET', PRE + '/admin/?p=login', jar=jar)
check('login page: style, icon and links in the folder', s == 200 and f'rel="icon" href="{PRE}/favicon.ico"' in t and not outside(t, PRE), outside(t, PRE))
csrf = re.search(r'name="csrf" value="([a-f0-9]+)"', t).group(1)
s, h, t = req(SUB, 'POST', PRE + '/admin/?p=login', {'csrf': csrf, 'login': 'admin', 'password': PW}, jar=jar)
check('login works in the folder', s == 302 and one(h, 'location') == PRE + '/admin/' and jar.path('ao_admin') == PRE + '/admin/', f'{s} {one(h, "location")}')
s, h, t = req(SUB, 'GET', PRE + '/admin/', jar=jar)
note = re.search(r'<p class="note note-top">(.*?)</p>', t, re.S)
note_text = re.sub(r'<[^>]+>', '', note.group(1)) if note else ''
check('overview explains the temporary address', bool(note) and f'{TEMP}{PRE}' in note_text and MAIN in note_text and 'Поисковики его не показывают' in note_text, note_text[:140])
check('the note links to site settings', bool(note) and f'href="{PRE}/admin/?p=doc&amp;name=config"' in note.group(1))
check('top bar «Сайт» opens the folder', f'<a class="btn btn-line" href="{PRE}/" target="_blank"' in t)
menu = [u.replace('&amp;', '&') for u in re.findall(r'<a href="([^"]*)"', t[t.find('id="adm-nav"'):t.find('</nav>')])]
check('menu links', len(menu) >= 12 and all(u.startswith(PRE + '/admin/') for u in menu), len(menu))
seen, queue, crawled = set(), list(menu), 0
EDIT = re.compile(r'href="(' + re.escape(PRE) + r'/admin/\?p=(?:edit|page|order)&amp;[^"]*)"')      # формы правки и карточки заказов
while queue:
    u = queue.pop(0)
    if u in seen: continue
    seen.add(u)
    s, h, t = req(SUB, 'GET', u, jar=jar)
    bad = outside(t, PRE); crawled += 1
    if s != 200 or bad or is_main_site(h): check(f'admin page {u.replace(PRE, "")}', False, bad or s)
    # с каждой страницы списка — по форме правки и по карточке заказа
    # ссылки переключателя языка (…&ui=az) — не страницы, они проверяются отдельно ниже
    if crawled < 80: queue += [u for u in dict.fromkeys(x.replace('&amp;', '&') for x in EDIT.findall(t)) if u not in seen and 'ui=' not in u][:2]
check('every admin page keeps its links, forms and files in the folder', 25 <= crawled <= 90, f'{crawled} pages')
s, h, t = req(SUB, 'GET', PRE + '/admin/?p=pages', jar=jar)
check('pages list shows real addresses with the folder', f'<code>{PRE}/catalog</code>' in t and f'href="{PRE}/catalog" target="_blank"' in t)
s, h, t = req(SUB, 'GET', PRE + '/admin/?p=doc&name=config', jar=jar)
check('site address field explains the temporary folder', 'Основной адрес сайта' in t and f'value="https://{MAIN}/"' in t)
s, h, t = req(SUB, 'GET', PRE + '/admin/?p=security', jar=jar)
steps = re.sub(r'<[^>]+>', '', t[t.find('class="steps"'):t.find('</ol>')])
check('Cloudflare step names both the temporary domain and the main one', 'stage.example' in steps and MAIN in steps and 'переедет' in steps, steps[steps.find('Hostname'):][:150])
s, h, t = req(SUB, 'GET', PRE + '/admin/?p=orders&ui=az', jar=jar)
check('language switch stays in the folder', s == 302 and one(h, 'location') == PRE + '/admin/?p=orders' and jar.path('ao_ui') == PRE + '/admin/', f'{one(h, "location")} {jar.path("ao_ui")}')
s, h, t = req(SUB, 'GET', PRE + '/admin/', jar=jar)
check('the note is translated', 'müvəqqəti' in t and 'Поисковики' not in t)
req(SUB, 'GET', PRE + '/admin/?ui=ru', jar=jar)
s, h, t = req(SUB, 'GET', PRE + '/admin/', host=f'127.0.0.1:{SUB}', jar=jar)
check('on a local copy the note is not shown', s == 200 and 'note-top' not in t)


# ====================== браузер: ни один запрос не уходит мимо папки ======================
async def browser():
    print('--- браузер')
    ORIGIN = f'http://127.0.0.1:{SUB}'; B = ORIGIN + PRE
    from PIL import Image, ImageDraw
    pathlib.Path(f'{ROOT}/test/fake').mkdir(exist_ok=True)
    im = Image.new('RGB', (1200, 800), 'white'); d = ImageDraw.Draw(im)
    d.ellipse((250, 250, 550, 550), outline=(29, 95, 209), width=26); d.ellipse((650, 250, 950, 550), outline=(29, 95, 209), width=26); d.line((550, 400, 650, 400), fill=(29, 95, 209), width=22)
    im.save(f'{ROOT}/test/fake/product.jpg', quality=88)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900})
        pg = await ctx.new_page(); await setup(pg)
        errors, leaks, bad, api = [], [], [], []
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        ctx.on('request', lambda r: leaks.append(r.method + ' ' + r.url.replace(ORIGIN, '')) if r.url.startswith(ORIGIN) and not r.url.startswith(B + '/') else None)
        ctx.on('response', lambda r: bad.append(f'{r.status} {r.url.replace(ORIGIN, "")}') if r.status >= 400 and r.url.startswith(ORIGIN) else None)
        ctx.on('response', lambda r: api.append(f'{r.status} {r.url.replace(ORIGIN, "")}') if '/api/' in r.url else None)
        await ctx.route('https://images.pexels.com/**', lambda r: r.abort())
        tail = lambda: pg.url.replace(ORIGIN, '')
        await pg.goto(B + '/?lang=ru'); await pg.wait_for_timeout(1500)
        nav = await pg.evaluate("[...document.querySelectorAll('#siteNav a[data-view]')].map(a => a.getAttribute('href'))")
        check('home in the browser, menu links in the folder', tail() == PRE + '/?lang=ru' and len(nav) >= 5 and all(u.startswith(PRE + '/') for u in nav), nav[:2])
        loose = await pg.evaluate("[...document.querySelectorAll('a[href], img[src], link[href], script[src]')].map(e => e.getAttribute('href') || e.getAttribute('src')).filter(u => u.startsWith('/') && !u.startsWith('//') && !u.startsWith('%s/'))" % PRE)
        check('rendered home: every link and picture address in the folder', not loose, loose[:5])
        await pg.locator('#siteNav a[data-view="catalog"]').first.click(); await pg.wait_for_timeout(500)
        cards = await pg.evaluate("[...document.querySelectorAll('#productsGrid .card-title a')].map(a => a.getAttribute('href'))")
        check('catalog by menu', tail() == PRE + '/catalog?lang=ru' and len(cards) > 10 and all(u.startswith(PRE + '/product/') for u in cards), tail())
        await pg.locator('#productsGrid .card-title a').first.click(); await pg.wait_for_timeout(500)
        check('product by click', tail().startswith(PRE + '/product/') and await pg.evaluate('!!Shop.state.page'), tail())
        prod = tail()
        await pg.reload(); await pg.wait_for_timeout(1200)
        check('product page survives a reload', tail() == prod and await pg.evaluate('!!Shop.state.page') and await pg.locator('#ppName').is_visible())
        await pg.go_back(); await pg.wait_for_timeout(500); back1 = tail()
        await pg.go_back(); await pg.wait_for_timeout(500); back2 = tail()
        await pg.go_forward(); await pg.wait_for_timeout(500)
        check('back and forward stay in the folder', back1 == PRE + '/catalog?lang=ru' and back2 == PRE + '/?lang=ru' and tail() == PRE + '/catalog?lang=ru', (back1, back2, tail()))
        await pg.locator('#siteNav a[data-view="blog"]').click(); await pg.wait_for_timeout(400)
        await pg.locator('.bl-card h2 a').first.click(); await pg.wait_for_timeout(400)
        check('blog post by click', tail().startswith(PRE + '/blog/') and await pg.locator('#pgTitle').is_visible(), tail())
        await pg.locator('.hdr > .logo').click(); await pg.wait_for_timeout(400)
        check('logo leads to the folder home', tail().split('#')[0] == PRE + '/?lang=ru', tail())
        await pg.locator('.hdr-right [data-set-lang="en"]').click(); await pg.wait_for_timeout(300)
        check('language switch keeps the folder', tail().startswith(PRE + '/?lang=en') and await pg.evaluate('document.documentElement.lang') == 'en', tail())
        await pg.locator('.hdr-right [data-set-lang="ru"]').click(); await pg.wait_for_timeout(300)
        robots = await pg.evaluate("(document.querySelector('meta[name=robots]') || {}).content || ''")
        check('temporary address stays closed for search engines while browsing', 'noindex' in robots, robots)
        # заказ: товар → корзина → оформление
        await pg.goto(B + '/product/f-milan?lang=ru'); await pg.wait_for_timeout(1200)
        await pg.locator('#ppAdd').click(); await pg.wait_for_timeout(300)
        await pg.locator('.site-header [data-open-cart]').first.click(); await pg.wait_for_timeout(300)
        await pg.locator('#cartDrawer [data-checkout]').click(); await pg.wait_for_timeout(500)
        check('checkout page', tail() == PRE + '/checkout?lang=ru', tail())
        await pg.fill('#coName', 'Браузер Тест'); await pg.fill('#coPhone', '0501234567')
        await pg.locator('#checkoutForm [type=submit]').click(); await pg.wait_for_timeout(1200); await pg.keyboard.press('Escape')
        check('order from the browser is saved', api == [f'200 {PRE}/api/order'] and sql("SELECT CONCAT(kind, ' ', total) FROM ao_orders WHERE name = 'Браузер Тест'") == 'order 140.00', api)
        wa = await pg.evaluate('window.__opened'); check('WhatsApp opens with the order', len(wa) == 1 and wa[0].startswith('https://wa.me/'), wa[:1])
        await pg.goto(B + '/?lang=ru#repair'); await pg.wait_for_timeout(1300)
        await pg.locator('#servicesList [data-svc="pads"]').click(); await pg.fill('#rpName', 'Ремонт Тест'); await pg.fill('#rpPhone', '0551112233')
        await pg.locator('#repairForm [type=submit]').click(); await pg.wait_for_timeout(900); await pg.keyboard.press('Escape')
        await pg.goto(B + '/contacts?lang=ru'); await pg.wait_for_timeout(1200)
        await pg.fill('#ctName', 'Вопрос Тест'); await pg.locator('#ctPhone').click(); await pg.fill('#ctPhone', '0557778899'); await pg.select_option('#ctTopic', 'exam'); await pg.fill('#ctMsg', 'Можно прийти в субботу?')
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(900)
        kinds = sql("SELECT GROUP_CONCAT(kind ORDER BY id SEPARATOR ',') FROM ao_orders WHERE name LIKE '% Тест' AND name <> 'Подпапка Тест'")
        check('repair request and message are saved too', kinds == 'order,repair,message', kinds)
        # телефон: меню на весь экран
        mctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        m = await mctx.new_page(); await setup(m); await m.route('https://images.pexels.com/**', lambda r: r.abort())
        mleaks = []; mctx.on('request', lambda r: mleaks.append(r.url.replace(ORIGIN, '')) if r.url.startswith(ORIGIN) and not r.url.startswith(B + '/') else None)
        await m.goto(B + '/?lang=ru'); await m.wait_for_timeout(1200)
        await m.locator('.hdr-right .js-menu-toggle').click(); await m.wait_for_timeout(500)
        await m.locator('#siteNav a[data-aud=kids]').click(); await m.wait_for_timeout(700)
        check('phone: menu link opens the page in the folder', await m.evaluate('location.pathname + location.search') == PRE + '/catalog?lang=ru&aud=kids' and not mleaks, (await m.evaluate('location.pathname + location.search'), mleaks[:2]))
        await mctx.close()
        # админ-панель: вход, фото товара, язык, выход
        await pg.goto(B + '/admin/'); await pg.wait_for_timeout(300)
        check('admin: guest sees the login page in the folder', tail() == PRE + '/admin/?p=login', tail())
        await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click(); await pg.wait_for_load_state()
        check('admin: login', tail() == PRE + '/admin/' and await pg.locator('.tile').count() == 6, tail())
        icon = await pg.evaluate("document.querySelector('link[rel=icon]').href")
        check('admin: own icon instead of the main site icon', icon == B + '/favicon.ico', icon)
        mid = sql("SELECT id FROM ao_items WHERE type='product' AND slug='f-milan'")
        await pg.goto(B + f'/admin/?p=edit&type=product&id={mid}')
        await pg.set_input_files('input[name="file[img]"]', f'{ROOT}/test/fake/product.jpg'); await pg.wait_for_timeout(600)
        await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
        stored = sql(f"SELECT JSON_UNQUOTE(JSON_EXTRACT(data, '$.img')) FROM ao_items WHERE id={mid}")
        check('admin: photo upload, the stored path has no folder name in it', re.fullmatch(r'uploads/p/[a-f0-9]{16}\.jpg', stored) is not None and (SITE / stored).is_file(), stored)
        thumb = await pg.evaluate("(document.querySelector('img.thumb') || {}).src || ''")
        check('admin: preview of the photo comes from the folder', thumb == f'{B}/{stored}' and await pg.evaluate("document.querySelector('img.thumb').naturalWidth > 0"), thumb.replace(ORIGIN, ''))
        await pg.goto(B + '/product/f-milan?lang=ru'); await pg.wait_for_timeout(1200)
        shown = await pg.evaluate("[...document.querySelectorAll('img')].filter(i => i.src.includes('/uploads/')).map(i => [i.getAttribute('src'), i.naturalWidth > 0])")
        check('site: uploaded photo is shown from the folder', len(shown) >= 1 and all(u == f'{PRE}/{stored}' and ok for u, ok in shown), shown[:2])
        await pg.goto(B + '/admin/?p=doc&name=config'); await pg.fill('#f-phone', '+994 50 555 44 33'); await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
        check('admin: settings are saved, the page stays in the folder', tail().startswith(PRE + '/admin/?p=doc') and 'Сохранено' in await pg.locator('.flash').first.inner_text(), tail())
        await pg.goto(B + '/admin/?p=orders&ui=en'); await pg.wait_for_timeout(300)
        check('admin: language switch', tail() == PRE + '/admin/?p=orders' and await pg.inner_text('h1') == 'Orders', tail())
        await pg.goto(B + '/admin/?ui=ru'); await pg.wait_for_timeout(300)
        ck = {c['name']: c['path'] for c in await ctx.cookies()}
        check('admin: both cookies are limited to the folder admin', ck == {'ao_admin': PRE + '/admin/', 'ao_ui': PRE + '/admin/'}, ck)
        await pg.locator('form.logout button').click(); await pg.wait_for_load_state()
        check('admin: sign out returns to the folder login page', tail() == PRE + '/admin/?p=login', tail())
        check('no request left the folder for the main site', not leaks, leaks[:5])
        check('no failed requests', not bad, bad[:5])
        errors = [x for x in errors if 'ERR_FAILED' not in x and 'font' not in x.lower()]
        check('no script errors', not errors, errors[:3])
        await ctx.close(); await b.close()
    return stored


stored = asyncio.run(browser())

# ====================== переезд: та же папка и та же база на своём домене ======================
print('--- переезд на основной домен')
LIVE = {'X-Forwarded-Proto': 'https'}
s, h, t = req(OWN, 'GET', '/', host=MAIN, headers=LIVE)
check('same folder opens as the root of its own domain', s == 200 and '<title>' in t and not stuck(t), stuck(t))
cfg2 = page_const(t, 'CONFIG')
check('page script: root addresses', cfg2['basePath'] == '/' and cfg2['api'] == '/api/order')
check('main address: open for search engines', 'x-robots-tag' not in h and 'name="robots"' not in t, one(h, 'x-robots-tag'))
check('main address: page address for search engines', f'<link rel="canonical" href="https://{MAIN}/">' in t)
check('main address over https: browser is told to always use https', 'max-age' in one(h, 'strict-transport-security'))
for p in ['/catalog', '/product/f-milan', '/blog/care', '/about', '/contacts']:
    s, h, t = req(OWN, 'GET', p, host=MAIN, headers=LIVE)
    check(f'main address {p}', s == 200 and not stuck(t) and 'x-robots-tag' not in h, stuck(t) or s)
s, h, t = req(OWN, 'GET', '/checkout', host=MAIN, headers=LIVE)
check('checkout stays out of search on the main address as before', '<meta name="robots" content="noindex">' in t)
s, h, t = req(OWN, 'GET', '/product/f-milan', host=MAIN, headers=LIVE)
check('photo uploaded on the temporary address is shown at the new one', f'"img":"/{stored}"' in t)
s, h, t = req(OWN, 'GET', '/' + stored, host=MAIN, headers=LIVE)
check('the photo file opens at the new address', s == 200 and one(h, 'content-type') == 'image/jpeg' and len(t) > 2000, s)
s, h, t = req(OWN, 'GET', '/robots.txt', host=MAIN, headers=LIVE)
check('robots.txt on the main address', 'Disallow: /admin/' in t and f'Sitemap: https://{MAIN}/sitemap.xml' in t and PRE + '/' not in t and 'x-robots-tag' not in h, t.replace('\n', ' | '))
s, h, t = req(OWN, 'GET', '/sitemap.xml', host=MAIN, headers=LIVE)
check('sitemap on the main address', s == 200 and f'<loc>https://{MAIN}/catalog</loc>' in t and 'x-robots-tag' not in h)
s, h, t = req(OWN, 'GET', '/', host='www.' + MAIN, headers=LIVE)
check('www. is the same main address', 'x-robots-tag' not in h and 'name="robots"' not in t)
s, h, t = req(OWN, 'GET', '/', host='other.example', headers=LIVE)
check('another domain at its root is not treated as temporary', 'x-robots-tag' not in h and f'href="https://{MAIN}/"' in t and 'other.example' not in t)
order2 = dict(order, token=cfg2['apiToken'], name='Переезд Тест')
s, h, t = req(OWN, 'POST', '/api/order', order2, dict(J, Origin=f'https://{MAIN}', **LIVE), host=MAIN)
check('order at the new address goes to the same database', s == 200 and sql("SELECT COUNT(*) FROM ao_orders WHERE name = 'Переезд Тест'") == '1', t[:100])
jar2 = Jar()
s, h, t = req(OWN, 'GET', '/admin/', host=MAIN, headers=LIVE, jar=jar2)
check('admin at the new address', s == 302 and one(h, 'location') == '/admin/?p=login' and jar2.path('ao_admin') == '/admin/', f'{one(h, "location")} {jar2.path("ao_admin")}')
s, h, t = req(OWN, 'GET', '/admin/?p=login', host=MAIN, headers=LIVE, jar=jar2)
csrf2 = re.search(r'name="csrf" value="([a-f0-9]+)"', t).group(1)
check('login page at the new address', 'rel="icon" href="/favicon.ico"' in t and not stuck(t) and 'без шифрования' not in t, stuck(t))
s, h, t = req(OWN, 'POST', '/admin/?p=login', {'csrf': csrf2, 'login': 'admin', 'password': PW}, host=MAIN, headers=LIVE, jar=jar2)
check('same login and password work after the move', s == 302 and one(h, 'location') == '/admin/', f'{s} {one(h, "location")}')
s, h, t = req(OWN, 'GET', '/admin/', host=MAIN, headers=LIVE, jar=jar2)
check('overview at the main address: no note, orders from both addresses', 'note-top' not in t and 'Переезд Тест' in t and 'Браузер Тест' in t)
s, h, t = req(OWN, 'GET', '/admin/?p=security', host=MAIN, headers=LIVE, jar=jar2)
steps = re.sub(r'<[^>]+>', '', t[t.find('class="steps"'):t.find('</ol>')])
check('Cloudflare step at the main address names only the main domain', MAIN in steps and 'переедет' not in steps and 'stage.example' not in steps)
s, h, t = req(OWN, 'GET', '/admin/?p=pages', host=MAIN, headers=LIVE, jar=jar2)
check('pages list at the main address', '<code>/catalog</code>' in t and not stuck(t), stuck(t))
s, h, t = req(SUB, 'GET', PRE + '/', host=TEMP)
check('the temporary address keeps working and stays closed for search engines', s == 200 and 'noindex' in one(h, 'x-robots-tag') and f'"basePath":"{PRE}/"' in t)

# ====================== ручной переключатель в storage/config.php ======================
print('--- строка preview в config.php')
CFG = SITE / 'storage/config.php'
keep = CFG.read_text()
try:
    cut = keep.rstrip().rfind(');')      # строка добавляется перед последней строкой файла, как 'captcha' => false
    def flag(v):
        CFG.write_text(keep[:cut] + f"  'preview' => {v},\n);\n"); time.sleep(3.2)   # PHP перечитывает изменённый файл не сразу
    check('settings file has the expected shape', keep.rstrip().endswith(');') and cut > 0)
    flag('true')
    s, h, t = req(OWN, 'GET', '/', host=MAIN, headers=LIVE)
    check("'preview' => true closes even the main address", 'noindex' in one(h, 'x-robots-tag') and '<meta name="robots" content="noindex, nofollow">' in t)
    flag('false')
    s, h, t = req(SUB, 'GET', PRE + '/', host=TEMP)
    check("'preview' => false opens the temporary address", 'x-robots-tag' not in h and 'name="robots"' not in t)
finally:
    CFG.write_text(keep); time.sleep(3.2)
s, h, t = req(SUB, 'GET', PRE + '/', host=TEMP)
check('without the line the rule is automatic again', 'noindex' in one(h, 'x-robots-tag'))
# ====================== https: три строки в .htaccess действуют только на папку сайта ======================
print('--- https в .htaccess папки')
HT = SITE / '.htaccess'
ht = HT.read_text(encoding='utf-8')
lines = ['# RewriteCond %{HTTPS} !=on', '# RewriteCond %{HTTP:X-Forwarded-Proto} !https', '# RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]']
check('the three https lines are in .htaccess, switched off', all(ht.count(x) == 1 for x in lines))
try:
    on = ht
    for x in lines: on = on.replace(x, x[2:])
    HT.write_text(on, encoding='utf-8')
    s, h, t = req(SUB, 'GET', PRE + '/catalog?lang=ru')
    check('with the lines on, the folder goes to https at the same address', s == 301 and one(h, 'location') == f'https://{TEMP}{PRE}/catalog?lang=ru', f'{s} {one(h, "location")}')
    s, h, t = req(SUB, 'GET', PRE + '/admin/')
    check('the admin panel too', s == 301 and one(h, 'location') == f'https://{TEMP}{PRE}/admin/', f'{s} {one(h, "location")}')
    s, h, t = req(SUB, 'GET', PRE + '/catalog', headers={'X-Forwarded-Proto': 'https'})
    check('an https request is served as usual', s == 200 and '<title>' in t)
    s, h, t = req(SUB, 'GET', '/')
    check('the main site of the domain is not redirected', s == 200 and 'MAIN SITE' in t)
finally:
    HT.write_text(ht, encoding='utf-8')
s, h, t = req(SUB, 'GET', PRE + '/catalog'); check('.htaccess restored', s == 200)

log = SITE / 'storage/logs/php-errors.log'
check('no PHP errors in the log', not log.exists() or log.read_text().strip() == '', log.read_text()[-300:] if log.exists() else '')

print('\n' + ('ALL PASSED' if not FAILS else f'FAILED: {len(FAILS)}'), '|', 'checks failed:', FAILS or 'none')
sys.exit(1 if FAILS else 0)

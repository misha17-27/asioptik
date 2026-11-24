"""Защита сайта и админ-панели: закрытые папки, заголовки, вход, CSRF, приём заказов, загрузка файлов."""
import http.client, io, json, os, pathlib, re, struct, subprocess, tempfile, time, urllib.parse, zlib
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parent.parent
HOST, PORT = '127.0.0.1', 8771
PW = 'Test-Admin-2026'      # пароль только для локальной тестовой базы
FAILS = []

def sql(q):
    return subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', 'asioptik_test', '-N', '-e', q], capture_output=True, text=True).stdout.strip()

def sql_raw(q):
    """То же, но значение выводится как есть: без экранирования кавычек и переводов строк."""
    return subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', 'asioptik_test', '-N', '--raw', '-e', q], capture_output=True, text=True).stdout.strip()

def req(method, path, body=None, headers=None, cookie=None):
    c = http.client.HTTPConnection(HOST, PORT, timeout=30)
    h = dict(headers or {})
    if cookie: h['Cookie'] = cookie
    if isinstance(body, dict):
        body = urllib.parse.urlencode(body, doseq=True); h.setdefault('Content-Type', 'application/x-www-form-urlencoded')
    if isinstance(body, str): body = body.encode('utf-8')
    c.request(method, path, body=body, headers=h)
    r = c.getresponse(); data = r.read(); c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, data.decode('utf-8', 'replace'), r.getheaders()

def check(name, ok, info=''):
    print(('ok   ' if ok else 'FAIL ') + name + (' | ' + str(info) if info != '' else ''))
    if not ok: FAILS.append(name)

def cookie_of(raw):
    for k, v in raw:
        if k.lower() == 'set-cookie' and v.startswith('ao_admin='): return v
    return ''

def login(password=PW, user='admin'):
    s, h, t, raw = req('GET', '/admin/?p=login')
    ck = cookie_of(raw).split(';')[0]
    csrf = re.search(r'name="csrf" value="([a-f0-9]+)"', t).group(1)
    s, h, t, raw = req('POST', '/admin/?p=login', {'csrf': csrf, 'login': user, 'password': password}, cookie=ck)
    new = cookie_of(raw)
    return s, h, t, (new.split(';')[0] if new else ck), ck, new

def csrf_of(cookie, path='/admin/'):
    return re.search(r'name="csrf" value="([a-f0-9]+)"', req('GET', path, cookie=cookie)[2]).group(1)

def multipart(fields, files):
    b = '----aotest7f3a'; out = io.BytesIO()
    for k, v in fields.items():
        out.write(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode('utf-8'))
    for k, (fn, data, ct) in files.items():
        out.write(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ct}\r\n\r\n'.encode('utf-8')); out.write(data); out.write(b'\r\n')
    out.write(f'--{b}--\r\n'.encode()); return out.getvalue(), {'Content-Type': f'multipart/form-data; boundary={b}'}

sql('DELETE FROM ao_logins')
print('--- закрытые папки и файлы')
for p in ['/app/', '/app/core/bootstrap.php', '/app/core/db.php', '/app/data/seed.json', '/app/data/texts.json', '/app/site/shell.html', '/app/admin/admin.php', '/app/admin/pages.php', '/storage/', '/storage/config.php', '/storage/cache/site.json',
          '/storage/logs/php-errors.log', '/.htaccess', '/app/.htaccess', '/uploads/.htaccess', '/.git/config', '/.env', '/README.md', '/composer.json', '/backup.sql', '/dump.sqlite', '/asioptik-site.zip', '/backup.ZIP', '/site.tar.gz', '/DUMP.SQL', '/uploads/', '/assets/', '/assets/css/']:
    s = req('GET', p)[0]; check('closed ' + p, s in (403, 404), s)
for p in ['/', '/catalog', '/about', '/blog', '/contacts', '/checkout', '/robots.txt', '/sitemap.xml', '/assets/js/app.js', '/assets/css/app.css', '/favicon.ico', '/admin/?p=login']:
    s = req('GET', p)[0]; check('open ' + p, s == 200, s)

print('--- заголовки')
s, h, t, raw = req('GET', '/')
for k, want in [('x-content-type-options', 'nosniff'), ('x-frame-options', 'SAMEORIGIN'), ('referrer-policy', 'strict-origin-when-cross-origin'), ('content-security-policy', "default-src 'self'"), ('permissions-policy', 'camera=()')]:
    check('site header ' + k, want in h.get(k, ''), h.get(k, '')[:60])
check('site: no PHP version leak', 'x-powered-by' not in h or 'PHP' not in h.get('x-powered-by', ''), h.get('x-powered-by', 'нет'))
s, h, t, raw = req('GET', '/admin/?p=login')
for k, want in [('x-frame-options', 'DENY'), ('cache-control', 'no-store'), ('x-robots-tag', 'noindex'), ('content-security-policy', "script-src 'self'"), ('referrer-policy', 'same-origin')]:
    check('admin header ' + k, want in h.get(k, ''), h.get(k, '')[:60])
ck = cookie_of(raw)
check('admin cookie HttpOnly, SameSite, path', 'HttpOnly' in ck and 'SameSite=Lax' in ck and 'path=/admin/' in ck, ck.split(';', 1)[1].strip())
s, h, t, raw = req('GET', '/admin/?p=login', headers={'X-Forwarded-Proto': 'https'})
check('admin cookie Secure over https', 'secure' in cookie_of(raw).lower(), cookie_of(raw).split(';', 1)[1].strip())
check('HSTS over https', 'max-age' in req('GET', '/', headers={'X-Forwarded-Proto': 'https'})[1].get('strict-transport-security', ''))

# Политика Content-Security-Policy записана в app/core/bootstrap.php и повторена в .htaccess: сайт уровнем выше
# (когда Asioptik лежит в его папке) может задавать свою политику для всего домена, и строки .htaccess возвращают нашу
print('--- политика Content-Security-Policy')
CSP = json.loads(subprocess.run(['php', '-r', f'require "{ROOT}/site/app/core/bootstrap.php"; echo json_encode(["site" => CSP_SITE, "admin" => CSP_ADMIN, "install" => CSP_INSTALL]);'], capture_output=True, text=True).stdout)
csp_of = lambda raw: [v for k, v in raw if k.lower() == 'content-security-policy']
for path, kind in [('/', 'site'), ('/ru/catalog', 'site'), ('/product/f-milan', 'site'), ('/checkout', 'site'), ('/admin/?p=login', 'admin'), ('/install.php', 'install')]:
    got = csp_of(req('GET', path)[3])
    check(f'{path}: one policy, the {kind} one', got == [CSP[kind]], [g[:70] for g in got])
ht_root = (ROOT / 'site/.htaccess').read_text(encoding='utf-8'); ht_admin = (ROOT / 'site/admin/.htaccess').read_text(encoding='utf-8')
check('.htaccess repeats the site policy word for word', ht_root.count(f'Header set Content-Security-Policy "{CSP["site"]}"') == 1)
check('.htaccess repeats the installer policy inside <Files "install.php">', re.search(r'<Files "install\.php">\s*Header set Content-Security-Policy "' + re.escape(CSP['install']) + r'"\s*</Files>', ht_root) is not None)
check('admin/.htaccess repeats the admin policy word for word', ht_admin.count(f'Header set Content-Security-Policy "{CSP["admin"]}"') == 1)
check('both files also drop a policy set by a parent site with «always»', 'Header always unset Content-Security-Policy' in ht_root and 'Header always unset Content-Security-Policy' in ht_admin)
check('site policy: inline data and own scripts, fonts, map, https pictures', all(x in CSP['site'] for x in ["script-src 'self' 'unsafe-inline'", 'https://fonts.googleapis.com', 'https://fonts.gstatic.com', 'https://maps.google.com', "img-src 'self' data: blob: https:", "object-src 'none'", "frame-ancestors 'self'"]))
check('admin policy: no inline scripts, no framing', "'unsafe-inline'" not in CSP['admin'].split('script-src')[1].split(';')[0] and "frame-ancestors 'none'" in CSP['admin'] and "object-src 'none'" in CSP['admin'])
check('only one outside script origin is allowed anywhere: the Cloudflare check', re.findall(r'https://[^\s;]+', CSP['admin']) == ['https://challenges.cloudflare.com'] * 3 and re.findall(r'https://[^\s;]+', CSP['site'].split('script-src')[1].split(';')[0]) == ['https://challenges.cloudflare.com'])
check('uploads keep their own strict policy', "default-src 'none'" in ' '.join(csp_of(req('GET', '/uploads/')[3])), csp_of(req('GET', '/uploads/')[3]))

s, h, t, raw = req('GET', '/admin/?p=login', headers={'Host': 'asioptik.az'}); check('admin over plain http shows a warning', 'без шифрования' in t)
s, h, t, raw = req('GET', '/admin/?p=login', headers={'Host': 'asioptik.az', 'X-Forwarded-Proto': 'https'}); check('no warning over https', 'без шифрования' not in t)
check('no warning on a local test address', 'без шифрования' not in req('GET', '/admin/?p=login')[2])

print('--- вход')
for p in ['/admin/', '/admin/?p=list&type=product', '/admin/?p=orders', '/admin/?p=doc&name=config', '/admin/?p=order&id=1', '/admin/?p=clients', '/admin/?p=pages', '/admin/?p=page&id=home', '/admin/?p=banners']:
    s, h, t, raw = req('GET', p); check('guest ' + p, s == 302 and 'p=login' in h.get('location', ''), f"{s} {h.get('location', '')}")
pid = sql("SELECT id FROM ao_items WHERE type='product' AND slug='f-verona'")
s, h, t, raw = req('POST', f'/admin/?p=delete&type=product&id={pid}', {'csrf': 'x'})
check('guest cannot delete', s == 302 and sql(f'SELECT COUNT(*) FROM ao_items WHERE id={pid}') == '1', s)
s, h, t, raw = req('POST', '/admin/?p=login', {'login': 'admin', 'password': PW})
check('login without form token rejected', s == 400, s)
s, h, t, raw = req('POST', '/admin/?p=login', {'login': 'admin', 'password': PW, 'csrf': ''})
check('login with empty token rejected', s == 400, s)
for inj in ["admin' OR '1'='1", "admin'--", "' UNION SELECT 1,2,3,4 -- ", 'admin"; DROP TABLE ao_users; --']:
    s, h, t, ck, old, new = login('x', inj); check('sql injection in login: ' + inj[:22], s == 200 and 'Неверный логин или пароль' in t, s)
check('users table intact', sql('SELECT COUNT(*) FROM ao_users') == '1')
sql('DELETE FROM ao_logins')
s, h, t, ck, old, new = login()
check('login ok', s == 302 and 'p=login' not in h.get('location', ''), h.get('location'))
check('session id changes on login', new != '' and new.split(';')[0] != old, 'new cookie issued' if new else 'same cookie')
check('old session id is not logged in', req('GET', '/admin/', cookie=old)[0] == 302)
ADMIN = ck
s, h, t, raw = req('GET', '/admin/', cookie=ADMIN); check('admin page with session', s == 200 and 'Последние заказы' in t and 'Обзор' in t, s)

for weak in ['12345678', 'password', 'aaaaaaaa', 'admin']:
    s, h, t, raw = req('POST', '/admin/?p=password', {'csrf': csrf_of(ADMIN), 'old': PW, 'new': weak, 'new2': weak}, cookie=ADMIN)
    check('weak password refused: ' + weak, s == 200 and ('Слишком простой пароль' in t or 'не короче 8' in t), s)
check('password unchanged after weak attempts', login()[0] == 302)

print('--- подделка запросов (CSRF)')
before = sql(f"SELECT data FROM ao_items WHERE id={pid}")
for label, body in [('no token', {'f[price]': '1'}), ('wrong token', {'csrf': 'a' * 40, 'f[price]': '1'})]:
    s, h, t, raw = req('POST', f'/admin/?p=edit&type=product&id={pid}', body, cookie=ADMIN); check('edit, ' + label, s == 400 and sql(f"SELECT data FROM ao_items WHERE id={pid}") == before, s)
s, h, t, raw = req('POST', f'/admin/?p=delete&type=product&id={pid}', {}, cookie=ADMIN); check('delete without token', s == 400 and sql(f'SELECT COUNT(*) FROM ao_items WHERE id={pid}') == '1', s)
s, h, t, raw = req('GET', f'/admin/?p=delete&type=product&id={pid}', cookie=ADMIN); check('delete by GET link does nothing', sql(f'SELECT COUNT(*) FROM ao_items WHERE id={pid}') == '1', s)
s, h, t, raw = req('GET', '/admin/?p=logout', cookie=ADMIN); check('logout by GET link does nothing', req('GET', '/admin/', cookie=ADMIN)[0] == 200)
s, h, t, raw = req('POST', '/admin/?p=password', {'old': PW, 'new': 'hacked-123456', 'new2': 'hacked-123456'}, cookie=ADMIN); check('password change without token', s == 400, s)
texts_before = sql("SELECT IFNULL((SELECT value FROM ao_settings WHERE name='texts'), 'нет')")
for label, body in [('no token', {'t[hero.title][ru]': 'взлом'}), ('wrong token', {'csrf': 'b' * 40, 't[hero.title][ru]': 'взлом'})]:
    s, h, t, raw = req('POST', '/admin/?p=page&id=home', body, cookie=ADMIN); check('page texts, ' + label, s == 400 and sql("SELECT IFNULL((SELECT value FROM ao_settings WHERE name='texts'), 'нет')") == texts_before, s)
s, h, t, raw = req('POST', '/admin/?p=page&id=home', {'csrf': csrf_of(ADMIN), 't[hero.title][ru]': 'взлом'}); check('page texts by a guest with a real token', s == 302 and 'p=login' in h.get('location', '') and 'взлом' not in sql("SELECT IFNULL((SELECT value FROM ao_settings WHERE name='texts'), '')"), s)
s, h, t, raw = req('POST', f'/admin/?p=edit&type=product&id={pid}', 'x' * 100, headers={'Content-Type': 'multipart/form-data; boundary=zz'}, cookie=ADMIN); check('empty form body gets a clear answer', s in (400, 413), s)

print('--- приём заказов с сайта')
tok = re.search(r'"apiToken":"([a-f0-9]+)"', req('GET', '/')[2]).group(1)
def api(payload, headers=None, raw_body=None):
    s, h, t, raw = req('POST', '/api/order', raw_body if raw_body is not None else json.dumps(payload), headers={'Content-Type': 'application/json', **(headers or {})})
    try: return s, json.loads(t)
    except ValueError: return s, t[:80]
good = {'kind': 'order', 'token': tok, 'lang': 'ru', 'name': 'Проверка', 'phone': '+994 50 000 00 00', 'total': 10, 'text': 'текст заказа'}
n0 = int(sql('SELECT COUNT(*) FROM ao_orders'))
check('GET not allowed', req('GET', '/api/order')[0] == 405)
check('no token', api({**good, 'token': ''})[0] == 403)
check('wrong token', api({**good, 'token': 'f' * 32})[0] == 403)
check('foreign origin', api(good, {'Origin': 'https://evil.example'})[0] == 403)
check('broken json', api(None, raw_body='{oops')[0] == 400)
check('unknown kind', api({**good, 'kind': 'admin'})[0] == 400)
check('empty name', api({**good, 'name': ''})[0] == 422)
check('bad phone', api({**good, 'phone': 'abc'})[0] == 422)
check('too large', api({**good, 'text': 'x' * 70000})[0] == 413)
check('nothing saved by rejected requests', int(sql('SELECT COUNT(*) FROM ao_orders')) == n0, sql('SELECT COUNT(*) FROM ao_orders'))
evil = {**good, 'name': '<script>alert(1)</script>', 'phone': '+994 50 111 11 11"><img src=x onerror=alert(2)>', 'number': 'OP-<b>-1', 'total': '1e99', 'status': 'done', 'id': 1,
        'text': '</pre><script>alert(3)</script>',
        'details': {'comment': '<img src=x onerror=alert(4)>', 'evil': {'a': 1}, 'delivery': ['x'], 'subtotal': 'NaN', 'address': 'A' * 5000,
                    'items': [{'name': '<svg onload=alert(5)>', 'lines': [['nested'], '<i>line</i>', 7], 'qty': '-5', 'price': {'x': 1}, 'sum': '12.5', 'extra': 'x'}, 'not-an-item'] + [{'name': 'n'}] * 100}}
s, r = api(evil, {'Origin': f'http://{HOST}:{PORT}'}); check('order with hostile content accepted and cleaned', s == 200 and r.get('ok'), r)
row = sql("SELECT CONCAT(number, '|', status, '|', IFNULL(total, 'NULL'), '|', data) FROM ao_orders ORDER BY id DESC LIMIT 1")
num, st, total, data = row.split('|', 3); d = json.loads(data)['details']
check('number replaced, status forced, total dropped', re.match(r'^OP-\d{4}-\d{4}$', num) and st == 'new' and total == 'NULL', f'{num} {st} {total}')
check('details: unknown keys dropped, types fixed', set(d) <= {'comment', 'address', 'items'} and len(d['address']) == 300 and len(d['items']) == 59 and d['items'][0]['qty'] == 0 and d['items'][0]['price'] is None and d['items'][0]['sum'] == 12.5 and d['items'][0]['lines'] == ['<i>line</i>', '7'], sorted(d))
oid = sql('SELECT id FROM ao_orders ORDER BY id DESC LIMIT 1')
s, h, t, raw = req('GET', f'/admin/?p=order&id={oid}', cookie=ADMIN)
check('admin order page escapes everything', s == 200 and '<script>alert' not in t and 'onerror=alert' not in t.replace('onerror=alert(2)&gt;', '').replace('&lt;img src=x onerror=alert(4)&gt;', '') and '<svg onload' not in t and '&lt;script&gt;alert(1)&lt;/script&gt;' in t, s)
s, h, t, raw = req('GET', '/admin/?p=orders', cookie=ADMIN); check('admin orders list escapes everything', '<script>alert' not in t and '<img src=x' not in t)
for p, label in [('/admin/', 'overview'), ('/admin/?p=clients', 'clients list')]:
    s, h, t, raw = req('GET', p, cookie=ADMIN); check('admin ' + label + ' escapes everything', s == 200 and '<script>alert' not in t and '<img src=x' not in t and '<svg onload' not in t and '&lt;script&gt;alert' in t, s)
sql("DELETE FROM ao_orders WHERE name = 'Проверка' OR name LIKE '<script>%'")
codes = [api({**good, 'name': 'Поток'})[0] for _ in range(22)]
check('rate limit: 20 an hour from one address', codes.count(200) + int(sql("SELECT COUNT(*) FROM ao_orders WHERE name <> 'Поток'")) == 20 and codes[-1] == 429, f'{codes.count(200)} accepted, then {codes[-1]}')
sql("DELETE FROM ao_orders WHERE name = 'Поток'")

print('--- адреса страниц')
first = sql('SELECT CONCAT(id, " ", number) FROM ao_orders ORDER BY id LIMIT 1').split(' ')
s, h, t, raw = req('GET', f'/admin/?p=order&id={first[0]}%20OR%201=1', cookie=ADMIN); check('sql text in a number field is read as a number', s == 200 and first[1] in t and 'SQL' not in t, s)
for p in ["/product/x'%20OR%201=1--", '/product/..%2f..%2fstorage%2fconfig.php', '/blog/%3Cscript%3E', '/no-such-page']:
    s, h, t, raw = req('GET', p); check('odd address ' + p[:34], s in (302, 400, 403, 404) and h.get('location', '/').startswith('/'), f"{s} {h.get('location', '')}")
for p in ['/?page=//evil.example', '/?page=https://evil.example', '/?product=//evil.example', '/?page=about&post=%0d%0aSet-Cookie:x=1']:
    s, h, t, raw = req('GET', p); loc = h.get('location', ''); check('no open redirect ' + p[:30], s == 301 and loc.startswith('/') and not loc.startswith('//') and 'set-cookie' not in h, loc)
s, h, t, raw = req('GET', '/ru/catalog?cat=%22%3E%3Cscript%3Ealert(1)%3C/script%3E'); check('query text is escaped in the page', '<script>alert(1)' not in t, s)
s, h, t, raw = req('GET', '/about', headers={'Host': 'evil.example'}); check('foreign Host header does not reach canonical', 'evil.example' not in t, re.search(r'rel="canonical" href="([^"]*)"', t).group(1))
s, h, t, raw = req('GET', '/no-such-page', headers={'Host': 'evil.example'}); check('redirects are relative', h.get('location', '').startswith('/'), h.get('location'))

print('--- поиск и фильтры в админ-панели')
total = int(sql("SELECT COUNT(*) FROM ao_items WHERE type='product'"))
rows = lambda t: t.count('<tr><td')
s, h, t, raw = req('GET', '/admin/?p=list&type=product', cookie=ADMIN); check('products list shows every product', s == 200 and rows(t) == total, f'{rows(t)} of {total}')
for q in ["' OR '1'='1", "%' OR 1=1 -- ", '") UNION SELECT 1,2,3 -- ', '%', '_']:
    s, h, t, raw = req('GET', '/admin/?p=list&type=product&q=' + urllib.parse.quote(q), cookie=ADMIN)
    check('products search, sql text: ' + q[:14], s == 200 and rows(t) == 0 and 'SQL' not in t and 'PDO' not in t, f'{s}, rows {rows(t)}')
    s, h, t, raw = req('GET', '/admin/?p=orders&q=' + urllib.parse.quote(q), cookie=ADMIN)
    check('orders search, sql text: ' + q[:14], s == 200 and rows(t) == 0 and 'SQL' not in t and 'PDO' not in t, f'{s}, rows {rows(t)}')
xss = urllib.parse.quote('"><script>alert(1)</script>')
for p in ['/admin/?p=list&type=product&q=' + xss, '/admin/?p=list&type=product&cat=' + xss, '/admin/?p=orders&q=' + xss, '/admin/?p=orders&kind=' + xss + '&status=' + xss, '/admin/?p=page&id=' + xss, '/admin/?p=list&type=' + xss]:
    s, h, t, raw = req('GET', p, cookie=ADMIN); check('admin query text is escaped ' + p[7:36], s in (200, 302) and '<script>alert(1)' not in t, s)
s, h, t, raw = req('GET', '/admin/?p=page&id=..%2F..%2Fstorage%2Fconfig', cookie=ADMIN); check('unknown page id goes back to the list', s == 302 and h.get('location', '').endswith('p=pages'), h.get('location'))

print('--- надписи и SEO, которые правят в админ-панели')
setting = lambda name: json.loads(sql_raw(f"SELECT IFNULL((SELECT value FROM ao_settings WHERE name='{name}'), '{{}}')") or '{}')
keep = {name: sql_raw(f"SELECT IFNULL((SELECT value FROM ao_settings WHERE name='{name}'), '')") for name in ('texts', 'seo')}
body = {'csrf': csrf_of(ADMIN, '/admin/?p=page&id=home'), 't[hero.title][ru]': '<img src=x onerror=alert(7)>', 't[hero.title][az]': '</script><script>alert(8)</script>', 't[hero.lead][en]': 'L' * 5000,
        't[no.such.key][ru]': 'лишний ключ', 't[cart.title][ru]': 'надпись другой страницы', 't[hero.cta1][xx]': 'чужой язык', 't[hero.cta1][ru][]': 'массив вместо строки',
        'seo[title][ru]': '</title><script>alert(9)</script>', 'seo[desc][ru]': '"><script>alert(10)</script>', 'seo[title][xx]': 'чужой язык', 'seo[evil][ru]': 'лишнее поле'}
s, h, t, raw = req('POST', '/admin/?p=page&id=home', body, cookie=ADMIN); check('page texts are saved', s == 302, s)
tx, seo = setting('texts'), setting('seo')
check('only the keys of this page and the three languages are stored', set(tx) <= {'az', 'ru', 'en'} and not any(k in tx.get(l, {}) for l in tx for k in ('no.such.key', 'cart.title', 'hero.cta1')),
      {l: sorted(v) for l, v in tx.items()})
check('long text is cut', len(tx.get('en', {}).get('hero.lead', '')) == 600, len(tx.get('en', {}).get('hero.lead', '')))
check('seo: only title and description in the three languages', set(seo.get('home', {})) <= {'title', 'desc'} and set(seo['home']['title']) == {'ru'}, seo.get('home'))
for lang in ('ru', 'az'):
    s, h, t, raw = req('GET', '/' + ('' if lang == 'az' else lang))
    check(f'site ({lang}): text with markup cannot become markup', s == 200 and '<img src=x' not in t and '<script>alert' not in t and '</title><script>' not in t and t.count('</title>') == 1, s)
s, h, t, raw = req('GET', '/ru')
check('site: title and description are escaped', '&lt;/title&gt;&lt;script&gt;alert(9)&lt;/script&gt;' in t and '&quot;&gt;&lt;script&gt;alert(10)' in t)
s, h, t, raw = req('GET', '/admin/?p=page&id=home', cookie=ADMIN); check('admin page editor escapes stored texts', s == 200 and '<img src=x' not in t and '<script>alert' not in t and '&lt;img src=x onerror=alert(7)&gt;' in t, s)
s, h, t, raw = req('GET', '/admin/?p=pages', cookie=ADMIN); check('admin pages list is intact', s == 200 and '<script>alert' not in t and 'изменено' in t, s)
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox']); page = br.new_page(); fired = []
        page.on('dialog', lambda d: (fired.append(d.message), d.dismiss()))
        for lang in ('ru', 'az'):
            page.evaluate("try { localStorage.removeItem('optika-lang') } catch (e) {}")   # адрес без языка — азербайджанский, а не запомненный русский
            page.goto(f'http://{HOST}:{PORT}/' + ('' if lang == 'az' else lang)); page.wait_for_timeout(1500)
            seen = page.evaluate("({ h1: document.querySelector('h1').textContent.trim(), planted: document.querySelectorAll('img[src=\"x\"], h1 script, h1 img').length, title: document.title })")
            check(f'browser ({lang}): the text is shown as written, nothing runs', not fired and seen['planted'] == 0 and ('alert(7)' in seen['h1'] or 'alert(8)' in seen['h1']), seen)
        br.close()
except ImportError:
    print('skip browser check: playwright is not installed')
# вернуть надписи как были — через саму админ-панель: пустое поле возвращает встроенный текст
was_t, was_s = (json.loads(keep[n]) if keep[n] else {} for n in ('texts', 'seo'))
body = {'csrf': csrf_of(ADMIN, '/admin/?p=page&id=home')}
for key, lang in (('hero.title', 'ru'), ('hero.title', 'az'), ('hero.lead', 'en')):
    body[f't[{key}][{lang}]'] = was_t.get(lang, {}).get(key, '')
for part in ('title', 'desc'):
    for lang in ('az', 'ru', 'en'):
        body[f'seo[{part}][{lang}]'] = was_s.get('home', {}).get(part, {}).get(lang, '')
s, h, t, raw = req('POST', '/admin/?p=page&id=home', body, cookie=ADMIN)
check('texts put back through the page editor', s == 302 and setting('texts') == was_t and setting('seo') == was_s, s)
s, h, t, raw = req('GET', '/ru'); check('texts restored after the check', 'alert(7)' not in t and 'alert(9)' not in t)

print('--- обновление данных уже установленного сайта')
# сайт прежней версии: у слайдов разделов нет временных фото, у одного раздела стоит своё фото, версии данных в базе нет
def refresh():
    # любое сохранение в админ-панели сбрасывает готовые данные сайта; здесь — страница «Общие надписи» без правок
    return req('POST', '/admin/?p=page&id=common', {'csrf': csrf_of(ADMIN, '/admin/?p=page&id=common')}, cookie=ADMIN)[0]
def slides():
    t = req('GET', '/ru')[2]
    return {c['id']: c.get('banner', {}) for c in json.loads(re.search(r'const CATEGORIES = (\[.*?\]);\n', t).group(1))}
sql("UPDATE ao_items SET data = JSON_REMOVE(data, '$.banner.demo', '$.banner.pos', '$.banner.flip', '$.banner.img') WHERE type='category'")
sql("UPDATE ao_items SET data = JSON_SET(data, '$.banner.img', 'uploads/b/own-photo.jpg') WHERE type='category' AND slug='frames'")
sql("DELETE FROM ao_settings WHERE name='data_version'")
check('old data: cache dropped', refresh() == 302)
b = slides()
check('upgrade keeps the own slide photo and adds nothing to it', b['frames'].get('img', '').endswith('/uploads/b/own-photo.jpg') and 'demo' not in b['frames'], b['frames'].get('img'))
check('upgrade gives the other slides a temporary photo', all('images.pexels.com' in b[k].get('demo', '') for k in ('sun', 'contacts', 'lenses')), [k for k in b if b[k].get('demo')])
check('upgrade is recorded', sql("SELECT value FROM ao_settings WHERE name='data_version'") == '4')
sql("UPDATE ao_items SET data = JSON_REMOVE(data, '$.banner.demo', '$.banner.pos', '$.banner.flip') WHERE type='category' AND slug='sun'"); refresh()
check('a temporary photo removed by the owner does not come back', 'demo' not in slides()['sun'])
# вернуть как после чистой установки
sql("UPDATE ao_items SET data = JSON_REMOVE(data, '$.banner.img') WHERE type='category' AND slug='frames'"); sql("DELETE FROM ao_settings WHERE name='data_version'"); refresh()
check('slides restored', all('demo' in v for v in slides().values()))
# сайт версии до страниц брендов: у брендов нет описаний, один бренд переименован владельцем, у другого описание своё
def brands():
    t = req('GET', '/ru')[2]
    return {b['id']: b for b in json.loads(re.search(r'const BRANDS = (\[.*?\]);\n', t).group(1))}
seed_text = brands()['asi-sun'].get('text', {})
sql("UPDATE ao_items SET data = JSON_REMOVE(data, '$.text') WHERE type='brand'")
sql("UPDATE ao_items SET data = JSON_SET(data, '$.name', 'Sun Line') WHERE type='brand' AND slug='asi-metal'")
sql("UPDATE ao_items SET data = JSON_SET(data, '$.text', JSON_OBJECT('ru', 'Своё описание')) WHERE type='brand' AND slug='asi-kids'")
sql("UPDATE ao_settings SET value = '2' WHERE name='data_version'"); refresh()
b = brands()
check('upgrade gives the starter brands their descriptions', bool(seed_text.get('ru')) and b['asi-sun'].get('text') == seed_text and bool(b['asi-classic'].get('text', {}).get('az')), b['asi-sun'].get('text'))
check('upgrade leaves a renamed brand and an own description alone', 'text' not in b['asi-metal'] and b['asi-kids'].get('text') == {'ru': 'Своё описание'}, (b['asi-metal'], b['asi-kids'].get('text')))
check('brand upgrade is recorded', sql("SELECT value FROM ao_settings WHERE name='data_version'") == '4')
sql("UPDATE ao_items SET data = JSON_REMOVE(data, '$.text') WHERE type='brand' AND slug='asi-sun'"); refresh()
check('a description removed by the owner does not come back', 'text' not in brands()['asi-sun'])
# вернуть как после чистой установки
sql("UPDATE ao_items SET data = JSON_SET(data, '$.name', 'Asi Metal') WHERE type='brand' AND slug='asi-metal'"); sql("UPDATE ao_items SET data = JSON_REMOVE(data, '$.text') WHERE type='brand'")
sql("UPDATE ao_settings SET value = '2' WHERE name='data_version'"); refresh()
check('brands restored', all(x.get('text', {}).get('ru') for k, x in brands().items() if k.startswith('asi-')), [k for k, x in brands().items() if not x.get('text')])

print('--- загрузка файлов')
up = ROOT / 'site' / 'uploads' / 'p'; up.mkdir(parents=True, exist_ok=True)
planted = {'shell.php': b'<?php echo "RUN" . (6 * 7); ?>', 'shell.phtml': b'<?php echo "RUN" . (6 * 7); ?>', 'shell.php.jpg': b'<?php echo "RUN" . (6 * 7); ?>', 'x.html': b'<script>alert(1)</script>', 'x.svg': b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>', '.htaccess': b'php_flag engine on'}
for name, body in planted.items(): (up / name).write_bytes(body)
for name in planted:
    s, h, t, raw = req('GET', '/uploads/p/' + name); check('planted ' + name + ' is not served or run', s == 403 and 'RUN42' not in t, s)
for name in planted: (up / name).unlink()
edit = f'/admin/?p=edit&type=product&id={pid}'
def upload(fn, data, ct='image/jpeg'):
    body, hh = multipart({'csrf': csrf_of(ADMIN, edit), 'f[name][az]': '«Verona» çərçivəsi', 'f[cat]': 'frames', 'f[price]': '120', 'slug': 'f-verona', 'position': '20', 'active': '1'}, {'file[img]': (fn, data, ct)})
    s, h, t, raw = req('POST', edit, body, headers=hh, cookie=ADMIN)
    err = re.search(r'<p class="err">([^<]*)', t)
    return s, (err.group(1) if err else ''), sql(f"SELECT JSON_UNQUOTE(JSON_EXTRACT(data, '$.img')) FROM ao_items WHERE id={pid}")
buf = io.BytesIO(); Image.new('RGB', (900, 600), (240, 240, 240)).save(buf, 'JPEG', quality=85); jpg = buf.getvalue()
img0 = sql(f"SELECT JSON_UNQUOTE(JSON_EXTRACT(data, '$.img')) FROM ao_items WHERE id={pid}")
s, err, img = upload('photo.php', b'<?php echo 1; ?>', 'image/jpeg'); check('php renamed as image is refused', 'Подходят только картинки' in err and img == img0, err)
s, err, img = upload('page.svg', b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', 'image/svg+xml'); check('svg is refused', 'Подходят только картинки' in err, err)
s, err, img = upload('poly.php.jpg', jpg + b'<?php echo "RUN" . (6 * 7); ?>'); stored = (ROOT / 'site' / img).read_bytes() if img != 'NULL' else b''
check('image with code appended is re-saved clean', s == 302 and re.match(r'^uploads/p/[a-f0-9]{16}\.jpg$', img) and b'<?php' not in stored and stored[:2] == b'\xff\xd8', img)
s, h, t, raw = req('GET', '/' + img); check('stored image is served as an image', s == 200 and h.get('content-type') == 'image/jpeg' and h.get('x-content-type-options') == 'nosniff', f"{s} {h.get('content-type')}")
def png_bomb(w, h):   # крошечный файл, который заявляет огромный размер
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0); chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(b'\x00' * 64)) + chunk(b'IEND', b'')
s, err, img2 = upload('bomb.png', png_bomb(30000, 30000), 'image/png'); check('giant picture is refused with a clear message', 'слишком большая' in err and img2 == img, err)
s, err, img3 = upload('broken.png', png_bomb(1100, 500), 'image/png'); check('file that only pretends to be a picture is refused, not stored as is', 'Не удалось прочитать картинку' in err and img3 == img, err or 'saved ' + img3)
# снимок с телефона «на боку»: поворот записан пометкой EXIF, после пересохранения картинка должна стоять прямо
ph = Image.new('RGB', (800, 400), (255, 255, 255)); ph.paste((200, 30, 30), (0, 0, 400, 400)); ex = ph.getexif(); ex[0x0112] = 6; buf = io.BytesIO(); ph.save(buf, 'JPEG', quality=92, exif=ex)
s, err, img4 = upload('phone.jpg', buf.getvalue()); im = Image.open(ROOT / 'site' / img4).convert('RGB')
check('phone photo is turned upright (EXIF 6)', im.size == (400, 800) and im.getpixel((200, 100))[0] > 150 and im.getpixel((200, 100))[1] < 90 and im.getpixel((200, 700))[1] > 200, f'{im.size} top={im.getpixel((200, 100))} bottom={im.getpixel((200, 700))}')
ex[0x0112] = 8; buf = io.BytesIO(); ph.save(buf, 'JPEG', quality=92, exif=ex); s, err, img5 = upload('phone8.jpg', buf.getvalue()); im = Image.open(ROOT / 'site' / img5).convert('RGB')
check('phone photo is turned upright (EXIF 8)', im.size == (400, 800) and im.getpixel((200, 700))[0] > 150 and im.getpixel((200, 700))[1] < 90 and im.getpixel((200, 100))[1] > 200, f'{im.size} top={im.getpixel((200, 100))} bottom={im.getpixel((200, 700))}')
check('replaced photos are removed from disk', not (ROOT / 'site' / img).exists() and not (ROOT / 'site' / img4).exists() and (ROOT / 'site' / img5).exists(), sorted(x.name for x in up.iterdir() if x.suffix))
big = Image.effect_noise((3300, 2500), 90).convert('RGB'); nine = b''
for quality in (97, 98, 96, 95, 99):   # нужен файл между 8 и 10 МБ: больше предела сайта, но меньше предела хостинга
    buf = io.BytesIO(); big.save(buf, 'JPEG', quality=quality); nine = buf.getvalue()
    if 8.3 * 1048576 < len(nine) < 9.7 * 1048576: break
s, err, img6 = upload('huge.jpg', nine); check('file over the 8 MB limit gets a clear message', 8 * 1048576 < len(nine) < 10 * 1048576 and 'Файл больше 8 МБ' in err and img6 == img5, f'{len(nine) / 1048576:.1f} MB | {err}')
body, hh = multipart({'csrf': csrf_of(ADMIN, edit)}, {'file[img]': ('x.jpg', b'0' * (13 * 1048576), 'image/jpeg')})
s, h, t, raw = req('POST', edit, body, headers=hh, cookie=ADMIN); check('upload over the hosting limit gets a clear message', s == 413 and 'слишком большой для этого хостинга' in t, s)
log = ROOT / 'site' / 'storage' / 'logs' / 'php-errors.log'
check('no PHP errors logged so far', not log.exists() or log.stat().st_size == 0, log.read_text()[-400:] if log.exists() else '')

print('--- ограничение попыток входа')
sql('DELETE FROM ao_logins')
texts = [login('wrong-' + str(i))[2] for i in range(5)]
check('five wrong passwords are answered normally', all('Неверный логин или пароль' in t for t in texts))
s, h, t, ck2, old, new = login(); check('sixth attempt is blocked even with the right password', s == 200 and 'Слишком много попыток' in t, s)
check('attempts are stored as a hash, not as an address', re.match(r'^[a-f0-9]{64}$', sql('SELECT ip_hash FROM ao_logins LIMIT 1') or '') is not None)
sql('DELETE FROM ao_logins')
check('after the pause the right password works', login()[0] == 302)

print('--- выход и ошибки сервера')
s, h, t, raw = req('POST', '/admin/?p=logout', {'csrf': csrf_of(ADMIN)}, cookie=ADMIN); check('logout', s == 302)
check('session is dead after logout', req('GET', '/admin/', cookie=ADMIN)[0] == 302)
conf = ROOT / 'site' / 'storage' / 'config.php'; orig = conf.read_text()
try:
    conf.write_text(orig.replace("'3307'", "'3999'")); (ROOT / 'site' / 'storage' / 'cache' / 'site.json').unlink(missing_ok=True)
    time.sleep(2.6)   # сервер перечитывает изменённый файл настроек не сразу
    s, h, t, raw = req('GET', '/'); check('database down: plain message, no details', s == 500 and 'временно недоступен' in t and 'PDO' not in t and '/home/' not in t and 'aotest' not in t, s)
    s, r = api(good); check('database down: api answers without details', s == 500 and 'aotest' not in str(r) and '/home/' not in str(r), s)
finally:
    conf.write_text(orig); time.sleep(2.6)
check('error went to the log file', log.exists() and 'PDOException' in log.read_text(), log.stat().st_size if log.exists() else 'no log')
check('log file is not reachable from the web', req('GET', '/storage/logs/php-errors.log')[0] == 403)
for _ in range(16):   # сервер держит прежний файл настроек в памяти ещё несколько секунд
    if req('GET', '/')[0] == 200: break
    time.sleep(0.5)
check('site works again', req('GET', '/')[0] == 200)
sql('DELETE FROM ao_logins'); log.unlink(missing_ok=True)

print('--- установщик')
sql_root = lambda q: subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', '-N', '-e', q], capture_output=True, text=True).stdout.strip()
with tempfile.TemporaryDirectory() as tmp:
    site = pathlib.Path(tmp) / 'site'
    subprocess.run(['cp', '-r', str(ROOT / 'site'), str(site)], check=True)
    (site / 'storage' / 'config.php').unlink()
    # запрос к установщику «как будто» с нужного адреса и с нужным именем сайта
    php = "$_SERVER['REQUEST_METHOD']='POST'; $_SERVER['REMOTE_ADDR']=$argv[1]; $_SERVER['HTTP_HOST']=$argv[2]; parse_str($argv[4], $_POST); chdir($argv[3]); require $argv[3].'/install.php';"
    def install(addr, site_host, **post):
        post = {'login': 'admin', 'password': 'Test-Admin-2026', 'password2': 'Test-Admin-2026', 'host': '', 'name': '', 'user': '', 'pass': '', **post}
        return subprocess.run(['php', '-r', php, addr, site_host, str(site), urllib.parse.urlencode(post)], capture_output=True, text=True).stdout
    conf = site / 'storage' / 'config.php'
    out = install('203.0.113.7', 'asioptik.az', file_db='1')
    check('installer: no-MySQL mode is not offered to a remote visitor', 'Укажите имя базы данных' in out and 'file_db' not in out and not conf.exists())
    out = install('127.0.0.1', 'asioptik.az', file_db='1')
    check('installer: nor behind a proxy on the hosting itself', 'Укажите имя базы данных' in out and 'file_db' not in out and not conf.exists())
    sql_root("DROP DATABASE IF EXISTS asioptik_test2; CREATE DATABASE asioptik_test2 CHARACTER SET utf8mb4; GRANT ALL ON asioptik_test2.* TO 'aotest'@'127.0.0.1'")
    out = install('203.0.113.7', 'asioptik.az', host='127.0.0.1:3307', name='asioptik_test2', user='aotest', **{'pass': 'test-only-local'})
    check('installer on hosting: installs into MySQL and removes install.php', 'Готово: сайт установлен' in out and 'удалён с хостинга' in out and conf.exists() and not (site / 'install.php').exists(), 'install.php removed' if not (site / 'install.php').exists() else 'install.php still there')
    check('installer: config is private (0640)', oct(conf.stat().st_mode)[-3:] == '640', oct(conf.stat().st_mode)[-3:])
    sql_root('DROP DATABASE asioptik_test2')
    subprocess.run(['cp', str(ROOT / 'site' / 'install.php'), str(site / 'install.php')], check=True); conf.unlink()
    out = install('127.0.0.1', '127.0.0.1:8088', file_db='1')
    check('installer on own computer: file database, install.php stays', 'Готово: сайт установлен' in out and 'на вашем компьютере' in out and (site / 'storage' / 'site.sqlite').exists() and (site / 'install.php').exists())
print('\nFAILED: ' + ', '.join(FAILS) if FAILS else '\nall security checks passed')

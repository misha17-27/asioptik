"""Язык админ-панели (RU / AZ / EN): словари, переключатель, страницы и сообщения без русских надписей в переводах.

Русские строки в коде — ключи словарей site/app/admin/lang/az.php и en.php. Проверка собирает все строки,
которые код отдаёт на перевод, сверяет их со словарями и открывает каждую страницу админ-панели на двух языках."""
import asyncio, http.client, json, pathlib, re, subprocess, urllib.parse
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
HOST, PORT = '127.0.0.1', 8771
B = f'http://{HOST}:{PORT}'
PW = 'Test-Admin-2026'      # пароль только для локальной тестовой базы
CYR = re.compile('[А-Яа-яЁё]')
FAILS = []


def check(name, ok, info=''):
    print(('ok   ' if ok else 'FAIL ') + name + (' | ' + str(info) if info != '' else ''))
    if not ok: FAILS.append(name)


def sql(q):
    return subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', 'asioptik_test', '-N', '--raw', '--default-character-set=utf8mb4', '-e', q], capture_output=True, text=True).stdout.strip()


# ---------- строки, которые код отдаёт на перевод ----------
STR = r"'((?:[^'\\]|\\.)*)'"
CONSTS = {'pages.php': ['SITE_PAGES'], 'store.php': ['ORDER_KINDS', 'ORDER_STATUSES']}   # названия из постоянных списков переводятся при выводе


def code_keys():
    un = lambda s: s.replace("\\'", "'").replace('\\\\', '\\')
    out = {}
    files = sorted((ROOT / 'site/app/admin').glob('*.php')) + [ROOT / 'site/app/core/store.php', ROOT / 'site/app/core/captcha.php']
    for f in files:
        src = f.read_text(encoding='utf-8')
        for m in re.finditer(r"(?<![\w$>])__\(\s*" + STR, src): out.setdefault(un(m.group(1)), f.name)
        for m in re.finditer(r"(?<![\w$>])n__\(\s*[^,()]*(?:\([^()]*\))?[^,()]*,\s*" + STR + r"\s*,\s*" + STR + r"\s*,\s*" + STR + r"\s*\)", src):
            out.setdefault('|'.join(un(m.group(i)) for i in (1, 2, 3)), f.name)
        for name in CONSTS.get(f.name, []):
            block = re.search(r'const ' + name + r' = \[(.*?)\];', src, re.S).group(1)
            for s in re.findall(STR, block):
                if CYR.search(s): out.setdefault(un(s), f.name)
    out.setdefault('Прочее', 'pages.php')   # блок для надписей, не попавших ни в одну страницу
    return out


def dictionary(lang):
    r = subprocess.run(['php', '-r', f'echo json_encode(require "{ROOT}/site/app/admin/lang/{lang}.php", JSON_UNESCAPED_UNICODE);'], capture_output=True, text=True)
    return json.loads(r.stdout)


# ---------- запросы ----------
def req(method, path, body=None, headers=None, cookie=None):
    c = http.client.HTTPConnection(HOST, PORT, timeout=40)
    h = dict(headers or {})
    if cookie: h['Cookie'] = cookie
    if isinstance(body, dict) and h.get('Content-Type') == 'application/json': body = json.dumps(body)
    elif isinstance(body, (dict, list)):
        body = urllib.parse.urlencode(body, doseq=True); h.setdefault('Content-Type', 'application/x-www-form-urlencoded')
    if isinstance(body, str): body = body.encode()
    c.request(method, path, body=body, headers=h)
    r = c.getresponse(); data = r.read(); c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, data.decode('utf-8', 'replace'), r.getheaders()


def set_cookies(raw):
    return {v.split(';')[0].split('=', 1)[0]: v for k, v in raw if k.lower() == 'set-cookie'}


class Admin:
    """Вошедший администратор с выбранным языком интерфейса."""
    def __init__(self, ui=''):
        self.jar = {}
        if ui: self.jar['ao_ui'] = ui
        s, h, page, raw = self.get('/admin/?p=login')
        self.login_page = page
        s, h, t, raw = self.post('/admin/?p=login', {'login': 'admin', 'password': PW}, page=page)
        assert s == 302, s

    def cookie(self):
        return '; '.join(f'{k}={v}' for k, v in self.jar.items())

    def keep(self, raw):
        for name, v in set_cookies(raw).items(): self.jar[name] = v.split(';')[0].split('=', 1)[1]

    def get(self, path):
        s, h, t, raw = req('GET', path, cookie=self.cookie())
        self.keep(raw)
        return s, h, t, raw

    def post(self, path, fields, page=None, follow=False):
        if page is None: page = self.get(path)[2]
        f = dict(fields); f['csrf'] = re.search(r'name="csrf" value="([a-f0-9]+)"', page).group(1)
        s, h, t, raw = req('POST', path, f, cookie=self.cookie())
        self.keep(raw)
        if follow and s == 302: return self.get(h['location'])
        return s, h, t, raw


def urls():
    one = lambda t: sql(f"SELECT id FROM ao_items WHERE type = '{t}' ORDER BY position, id LIMIT 1")
    u = ['/admin/', '/admin/?p=orders', '/admin/?p=orders&kind=repair', '/admin/?p=orders&status=done&q=zzz', '/admin/?p=clients', '/admin/?p=pages']
    u += [f'/admin/?p=page&id={i}' for i in ('home', 'catalog', 'product', 'checkout', 'about', 'blog', 'contacts', 'common')]
    u += [f'/admin/?p=list&type={t}' for t in ('product', 'category', 'brand', 'service', 'post')]
    u += ['/admin/?p=list&type=product&cat=sun&q=a', '/admin/?p=list&type=product&q=zzzzzz', '/admin/?p=edit&type=product', '/admin/?p=edit&type=product&cat=frames',
          '/admin/?p=edit&type=brand', '/admin/?p=edit&type=service', '/admin/?p=edit&type=post']
    u += [f"/admin/?p=edit&type={t}&id={one(t)}" for t in ('product', 'category', 'brand', 'service', 'post')]
    u += [f"/admin/?p=edit&type=product&copy={one('product')}", '/admin/?p=doc&name=config', '/admin/?p=doc&name=about', '/admin/?p=banners', '/admin/?p=security', '/admin/?p=password']
    u += [f"/admin/?p=order&id={i}" for i in sql('SELECT id FROM ao_orders ORDER BY id').split()]
    return u


def left(html):
    """Русские надписи интерфейса: текст страницы и подсказки. Содержимое полей (тексты сайта) не в счёт."""
    t = re.sub(r'(?s)<script.*?</script>|<style.*?</style>', ' ', html)
    t = re.sub(r'(?s)(<textarea[^>]*>).*?</textarea>', r'\1', t)
    out = []
    for m in re.finditer(r'<(?:input|textarea)\b[^>]*>', t):
        tag = re.sub(r'\svalue="[^"]*"', '', m.group(0))
        if re.search(r'\slang="(ru|az|en)"', tag): tag = re.sub(r'\splaceholder="[^"]*"', '', tag)   # подсказка в поле с текстом сайта — сам текст сайта
        out += [a for a in re.findall(r'[\w-]+="[^"]*"', tag) if CYR.search(a)]
    t = re.sub(r'<(?:input|textarea)\b[^>]*>', ' ', t)
    out += [a for a in re.findall(r'\s(?:title|aria-label|placeholder|data-confirm|alt)="([^"]*)"', t) if CYR.search(a)]
    out += [x.strip() for x in re.split(r'<[^>]+>', t) if CYR.search(x)]
    return [x for x in out if x != 'Русский']   # название языка в переключателе написано на самом языке


def text(html):
    html = html[html.find('<body'):]
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'(?s)<script.*?</script>|<svg.*?</svg>', ' ', html))).replace('&quot;', '"').replace('&#039;', "'")


def flash(html):
    m = re.search(r'<p class="flash flash-(\w+)"[^>]*>(.*?)</p>', html, re.S)
    return re.sub(r'<[^>]+>', '', m.group(2)) if m else ''


# =====================================================================
print('--- словари')
keys = code_keys()
check('interface strings found in the code', len(keys) > 400, len(keys))
dicts = {l: dictionary(l) for l in ('az', 'en')}
for l, d in dicts.items():
    missing = sorted(k for k in keys if k not in d)
    extra = sorted(k for k in d if k not in keys)
    check(f'{l}: every string has a translation', not missing, missing[:5])
    check(f'{l}: no translations for strings that are gone', not extra, extra[:5])
    bad = [k for k, v in d.items() if not isinstance(v, str) or not v.strip() or CYR.search(v)]
    check(f'{l}: translations are not empty and have no Russian in them', not bad, bad[:3])
    bad = [k for k, v in d.items() if sorted(re.findall(r'\{\w+\}', k)) != sorted(re.findall(r'\{\w+\}', v))]
    check(f'{l}: words in curly braces are kept', not bad, bad[:3])
    bad = [k for k, v in d.items() if sorted(re.findall(r'</?\w+>', k)) != sorted(re.findall(r'</?\w+>', v))]
    check(f'{l}: markup is kept where the source has it', not bad, bad[:3])
    bad = [k for k, v in d.items() if '<' not in k and ('<' in v or '>' in v or '&' in v)]
    check(f'{l}: plain strings stay plain (no markup sneaks in)', not bad, bad[:3])
    forms = {k: v for k, v in d.items() if re.fullmatch(r'[^|]+\|[^|]+\|[^|]+', k)}
    want = 2 if l == 'en' else 1
    bad = [k for k, v in forms.items() if len(v.split('|')) != want]
    check(f'{l}: number forms — {want} per word', len(forms) >= 7 and not bad, bad[:3])
same = [k for k in keys if CYR.search(k) and (dicts['en'].get(k) == k or dicts['az'].get(k) == k)]
check('nothing is left untranslated by copying the Russian string', not same, same[:3])

print('--- переключатель')
sql('DELETE FROM ao_logins')
s, h, t, raw = req('GET', '/admin/?p=login')
check('without a choice the panel is in Russian', '<html lang="ru">' in t and 'Вход в админ-панель' in t and 'ao_ui' not in set_cookies(raw))
sw = re.search(r'<div class="uis".*?</div>', t, re.S)
check('login page has the switcher with three languages, current one marked', bool(sw) and re.findall(r'\slang="(\w+)"', sw.group(0)) == ['ru', 'az', 'en'] and len(re.findall(r'aria-current', sw.group(0))) == 1 and 'lang="ru" hreflang="ru" title="Русский" aria-current="true"' in sw.group(0), sw.group(0)[:200] if sw else '')
s, h, t, raw = req('GET', '/admin/?p=login&ui=az')
ck = set_cookies(raw).get('ao_ui', '')
check('choosing a language: cookie for a year, only for the admin panel, not readable by scripts', s == 302 and ck.startswith('ao_ui=az;') and 'path=/admin/' in ck.lower() and 'httponly' in ck.lower() and 'samesite=lax' in ck.lower() and ('max-age=31536000' in ck.lower() or 'expires=' in ck.lower()), ck)
check('… and the same page opens again without the switch in the address', h.get('location') == '/admin/?p=login', h.get('location'))
s, h, t, raw = req('GET', '/admin/?p=login', cookie='ao_ui=az')
check('login page in Azerbaijani', '<html lang="az">' in t and 'Admin panelə giriş' in t and 'Daxil ol' in t and not left(t), left(t)[:3])
s, h, t, raw = req('GET', '/admin/?p=login', cookie='ao_ui=en')
check('login page in English', '<html lang="en">' in t and 'Admin panel sign-in' in t and 'Sign in' in t and not left(t), left(t)[:3])
for bad in ('xx', '../../etc/passwd', '"><script>alert(1)</script>', 'RU', ''):
    s, h, t, raw = req('GET', '/admin/?p=login&ui=' + urllib.parse.quote(bad))
    s2, h2, t2, raw2 = req('GET', '/admin/?p=login', cookie='ao_ui=' + urllib.parse.quote(bad))
    check(f'unknown language «{bad[:12]}» is ignored', s == 200 and 'ao_ui' not in set_cookies(raw) and '<html lang="ru">' in t and '<html lang="ru">' in t2 and '<script>alert' not in t + t2)
s, h, t, raw = req('GET', '/admin/?ui=en&p=' + urllib.parse.quote('//evil.example/x'))
check('the switch cannot send the visitor to another site', s == 302 and h.get('location', '').startswith('/admin/?p='), h.get('location'))
s, h, t, raw = req('GET', '/admin/?p=orders&kind=repair&q=' + urllib.parse.quote('a"><b>') + '&ui=en')
check('other parameters of the address survive the switch, safely encoded', s == 302 and h.get('location') == '/admin/?p=orders&kind=repair&q=a%22%3E%3Cb%3E', h.get('location'))
s, h, t, raw = req('GET', '/admin/?p=login&x=' + urllib.parse.quote('"><script>alert(1)</script>') + '&y[]=' + urllib.parse.quote("'onmouseover='1"))
check('switcher links carry odd address parameters only in encoded form', s == 200 and '<script>alert(1)' not in t and "'onmouseover='" not in t and 'x=%22%3E%3Cscript%3Ealert%281%29%3C%2Fscript%3E' in t, re.findall(r'<a href="([^"]*)" lang="az"', t)[:1])
s, h, t, raw = req('GET', '/ru', cookie='ao_ui=en')
check('the public site does not depend on the admin language', '<html lang="ru"' in t and 'ao_ui' not in set_cookies(raw))

print('--- все страницы на двух языках')
# свои три записи: заказ, заявка на ремонт и сообщение (проверка не зависит от того, что осталось после других)
sql('DELETE FROM ao_orders')
tok = re.search(r'"apiToken":"([a-f0-9]+)"', req('GET', '/')[2]).group(1)
for body in (
    {'kind': 'order', 'name': 'Leyla Test', 'phone': '+994 50 123 45 67', 'total': 255, 'text': 'Order text', 'details': {'delivery': 'courier', 'address': 'Baku', 'items': [
        {'name': 'Milan frame', 'qty': 1, 'price': 185, 'sum': 185, 'lines': ['Colour: black']}, {'name': 'Case', 'qty': 2, 'price': 35, 'sum': 70}]}},
    {'kind': 'repair', 'name': 'Kamran', 'phone': '+994 55 111 22 33', 'text': 'Repair text', 'details': {'services': ['Nose pads', 'Screws'], 'handover': 'courier'}},
    {'kind': 'message', 'name': 'Aydan', 'phone': '+994 55 777 88 99', 'text': 'Message text', 'details': {'topic': 'Eye test', 'comment': 'Can I come on Saturday?'}},
):
    req('POST', '/api/order', dict(body, lang='en', token=tok), headers={'Content-Type': 'application/json', 'Origin': B})
check('three sample records for the pages', sql('SELECT COUNT(*) FROM ao_orders') == '3', sql('SELECT COUNT(*) FROM ao_orders'))
goods = int(sql("SELECT COUNT(*) FROM ao_items WHERE type = 'product'"))
en, az, ru = Admin('en'), Admin('az'), Admin()
check('signing in keeps the chosen language', '<html lang="en">' in en.get('/admin/')[2] and '<html lang="az">' in az.get('/admin/')[2] and '<html lang="ru">' in ru.get('/admin/')[2])
pages = urls()
for name, adm, lang in (('en', en, 'en'), ('az', az, 'az')):
    bad, n = {}, 0
    for u in pages:
        s, h, t, raw = adm.get(u)
        n += s == 200
        if f'<html lang="{lang}">' not in t: bad[u] = ['wrong page language']
        elif left(t): bad[u] = left(t)[:3]
    check(f'{name}: {len(pages)} pages open', n == len(pages), n)
    check(f'{name}: no Russian interface text on any page', not bad, list(bad.items())[:4])
s, h, t, raw = en.get('/admin/')
check('en: overview reads naturally', all(x in text(t) for x in ['Overview', 'Latest orders', 'What was ordered', 'Sign out', 'Workshop services']) and f'<b>{goods}</b><span>products</span>' in t and '<b>1</b><span>order in total</span>' in t and '<b>3</b><span>new requests</span>' in t, text(t)[:200])
s, h, t, raw = az.get('/admin/')
check('az: overview reads naturally', all(x in text(t) for x in ['İcmal', 'Son sifarişlər', 'Nə sifariş edilib', 'Çıxış', 'Emalatxana xidmətləri']) and f'<b>{goods}</b><span>məhsul</span>' in t and '<b>1</b><span>cəmi sifariş</span>' in t and '<b>3</b><span>yeni müraciət</span>' in t, text(t)[:200])
names = lambda adm: re.findall(r'<a class="strong" href="[^"]*">([^<]*)</a>', adm.get('/admin/?p=list&type=product&cat=frames')[2])[:2]
check('lists show product names in the panel language', names(en) != names(az) != names(ru) and not CYR.search(''.join(names(en) + names(az))) and CYR.search(''.join(names(ru))), (names(en), names(az), names(ru)))
lbl = lambda adm: re.search(r'<span class="lbl">([^<]*) <code class="key">co\.title</code>', adm.get('/admin/?p=page&id=checkout')[2]).group(1)
check('page editor labels its fields with the text in the panel language', (lbl(en), lbl(az), lbl(ru)) == ('Checkout', 'Sifarişin rəsmiləşdirilməsi', 'Оформление заказа'), (lbl(en), lbl(az), lbl(ru)))
s, h, t, raw = en.get('/admin/?p=edit&type=product')
check('script texts come with the page in its language', '"filePrep":"Preparing the photo…"' in t and 'id="ao-i18n"' in t)

print('--- сообщения и ошибки на двух языках')
pid = sql("SELECT id FROM ao_items WHERE type = 'product' ORDER BY position, id LIMIT 1")
for name, adm, want in (('en', en, {
        'login': 'Wrong login or password.', 'pass': 'The current password is wrong.', 'item': 'Not saved: check the fields marked in red.', 'num': 'Enter a number.',
        'page': 'The text must keep {id}', 'conf': 'Enter the full number with the country code', 'sec': 'Paste the Site Key from Cloudflare.', 'old': 'The page is out of date.'}),
                        ('az', az, {
        'login': 'Login və ya parol səhvdir.', 'pass': 'Cari parol səhv göstərilib.', 'item': 'Yadda saxlanmadı: qırmızı ilə işarələnmiş xanaları yoxlayın.', 'num': 'Rəqəm yazın.',
        'page': 'Mətndə {id} qalmalıdır', 'conf': 'Nömrəni tam şəkildə, ölkə kodu ilə yazın', 'sec': 'Cloudflare-dən Site Key-i daxil edin.', 'old': 'Səhifə köhnəlib.'})):
    lang = name
    s, h, t, raw = req('GET', '/admin/?p=login', cookie='ao_ui=' + lang)
    c2 = '; '.join(v.split(';')[0] for v in set_cookies(raw).values()) + '; ao_ui=' + lang
    s, h, t, raw = req('POST', '/admin/?p=login', {'csrf': re.search(r'name="csrf" value="([a-f0-9]+)"', t).group(1), 'login': 'admin', 'password': 'wrong'}, cookie=c2)
    check(f'{name}: wrong password message', want['login'] in t and not left(t), left(t)[:2])
    s, h, t, raw = adm.post('/admin/?p=password', {'old': 'nope', 'new': 'abcdefgh1', 'new2': 'abcdefgh1'})
    check(f'{name}: password form error', want['pass'] in t and not left(t), left(t)[:2])
    s, h, t, raw = adm.post(f'/admin/?p=edit&type=product&id={pid}', {'f[name][az]': '', 'f[name][ru]': '', 'f[name][en]': '', 'f[price]': '', 'active': '1'})
    check(f'{name}: product form errors', s == 200 and want['item'] in t and want['num'] in t and not left(t), left(t)[:2])
    s, h, t, raw = adm.post('/admin/?p=page&id=checkout', {f't[ok.orderText][{lang}]': 'no braces here'})
    check(f'{name}: page text error names the missing word', s == 200 and want['page'] in text(t) and not left(t), left(t)[:2])
    s, h, t, raw = adm.post('/admin/?p=doc&name=config', {'f[shopName]': 'Asioptik', 'f[whatsapp]': '12'})
    check(f'{name}: settings error', s == 200 and want['conf'] in t and not left(t), left(t)[:2])
    s, h, t, raw = adm.post('/admin/?p=security', {'site': '', 'secret': 'x'})
    check(f'{name}: security form error', s == 200 and want['sec'] in t and not left(t), left(t)[:2])
    s, h, t, raw = req('POST', '/admin/?p=password', {'csrf': 'bad', 'old': 'x'}, cookie=adm.cookie())
    check(f'{name}: stale page message', s == 400 and want['old'] in t and not CYR.search(t), t[-160:])
oid = sql("SELECT id FROM ao_orders WHERE kind = 'repair' ORDER BY id LIMIT 1")
num = sql(f'SELECT number FROM ao_orders WHERE id = {oid}')
s, h, t, raw = en.post(f'/admin/?p=order&id={oid}', {'status': 'work'}, follow=True)
check('en: message with a value inside', flash(t) == 'Status changed: In progress.' and f'Request {num}' in text(t), flash(t))
s, h, t, raw = az.post(f'/admin/?p=order&id={oid}', {'status': 'done'}, follow=True)
check('az: message with a value inside', flash(t) == 'Status dəyişdirildi: Tamamlandı.' and f'Müraciət {num}' in text(t), flash(t))
s, h, t, raw = ru.post(f'/admin/?p=order&id={oid}', {'status': 'new'}, follow=True)
check('ru: the same message in Russian', flash(t) == 'Статус изменён: Новый.' and f'Заявка {num}' in text(t), flash(t))
s, h, t, raw = en.post('/admin/?p=security', {'site': '1x00000000000000000000AA', 'secret': '1x0000000000000000000000000000000AA', 'login': '1', 'forms': '1'}, follow=True)
check('en: security messages and the trial block', flash(t).startswith('Keys saved. One step is left') and 'Waiting for the trial check' in t and 'data-language="en"' in t and not left(t), (flash(t), left(t)[:2]))
s, h, t, raw = az.get('/admin/?p=security')
check('az: the widget takes the browser language (it has no Azerbaijani)', 'data-language="auto"' in t and 'Sınaq yoxlamasını gözləyir' in t and not left(t), left(t)[:2])
s, h, t, raw = az.post('/admin/?p=security', {'act': 'check'}, follow=True)
check('az: failed trial check explained', flash(t).startswith('CAPTCHA qoşulmayıb. Yoxlama keçilmədi') and not left(t), flash(t))
s, h, t, raw = en.post('/admin/?p=security', {'site': '', 'secret': ''}, follow=True)
check('en: keys deleted message', flash(t) == 'Keys deleted, the CAPTCHA is off.' and not sql("SELECT value FROM ao_settings WHERE name = 'turnstile'").strip('{}'), flash(t))


async def browser():
    pid = sql("SELECT id FROM ao_items WHERE type = 'product' ORDER BY position, id LIMIT 1")
    fake = ROOT / 'test/fake'; fake.mkdir(exist_ok=True); (fake / 'note.txt').write_text('not an image')
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await b.new_context(viewport={'width': 1280, 'height': 860})
        pg = await ctx.new_page()
        errors = []
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        await pg.route('https://fonts.gstatic.com/**', lambda r: r.abort())
        await pg.goto(B + '/admin/?p=login')
        await pg.locator('.uis a[lang=en]').click(); await pg.wait_for_load_state()
        check('browser: one click on the login page switches it to English', await pg.inner_text('h1') == 'Admin panel sign-in' and pg.url.endswith('/admin/?p=login') and await pg.locator('.uis a[aria-current]').inner_text() == 'EN', await pg.inner_text('h1'))
        box = await pg.locator('.uis').bounding_box(); card = await pg.locator('main.card').bounding_box(); brand = await pg.locator('.brand').bounding_box()
        check('browser: the switcher sits inside the login card, clear of the logo', box['x'] >= card['x'] and box['x'] + box['width'] <= card['x'] + card['width'] and box['x'] > brand['x'] + 110, (box, brand))
        await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click(); await pg.wait_for_load_state()
        check('browser: the choice survives signing in', await pg.inner_text('h1') == 'Overview' and await pg.evaluate('document.documentElement.lang') == 'en')
        acts = await pg.locator('.top-acts').evaluate("e => [...e.children].map(c => Math.round(c.getBoundingClientRect().top))")
        check('browser: switcher, «Site» and «Sign out» stand in one row', len(set(acts)) == 1, acts)
        await pg.goto(B + f'/admin/?p=edit&type=product&id={pid}'); await pg.wait_for_timeout(300)
        # перевод в две колонки: слева основной язык сайта (az), справа — язык панели
        check('browser: main language on the left, the panel language on the right', await pg.evaluate('document.documentElement.dataset.lg') == 'en' and await pg.locator('#f-name-az').is_visible() and await pg.locator('#f-name-en').is_visible() and not await pg.locator('#f-name-ru').is_visible()
              and await pg.evaluate("document.querySelector('#f-name-az').getBoundingClientRect().right <= document.querySelector('#f-name-en').getBoundingClientRect().left"))
        check('browser: translation switch in English', await pg.get_attribute('.lgs', 'aria-label') == 'Languages in the form' and await pg.get_attribute('.lg-main', 'title') == 'The main language of the site: always on the left' and await pg.get_attribute('[data-lg-set=ru]', 'title') == 'Show on the right: RU', await pg.get_attribute('.lgs', 'aria-label'))
        check('browser: character counter in English', 'of 60 characters' in await pg.locator('.count').first.inner_text(), await pg.locator('.count').first.inner_text())
        await pg.set_input_files('input[type=file]', str(fake / 'note.txt')); await pg.wait_for_timeout(200)
        note = await pg.locator('.file-note').first.inner_text()
        check('browser: script message in English', note == 'The file “note.txt” does not fit: a JPG, PNG or WebP image is needed.', note)
        await pg.locator('[data-lg-set=ru]').first.click()
        await pg.reload(); await pg.wait_for_timeout(300)
        check('browser: a manual choice of the second language is remembered', await pg.evaluate('document.documentElement.dataset.lg') == 'ru' and await pg.locator('#f-name-ru').is_visible() and not await pg.locator('#f-name-en').is_visible())
        await pg.locator('.uis a[lang=az]').click(); await pg.wait_for_load_state(); await pg.wait_for_timeout(300)
        check('browser: switching the panel keeps the page and the chosen second language', f'id={pid}' in pg.url and 'ui=' not in pg.url and await pg.evaluate('document.documentElement.dataset.lg') == 'ru' and await pg.locator('#f-name-az').is_visible() and await pg.locator('.actions .btn').first.inner_text() == 'Yadda saxla', pg.url)
        await pg.evaluate("sessionStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(300)
        check('browser: with the panel in the main language the second column is Russian', await pg.evaluate('document.documentElement.dataset.lg') == 'ru' and await pg.get_attribute('.lg-main', 'title') == 'Saytın əsas dili: həmişə solda')
        check('browser: counter in Azerbaijani', 'işarə' in await pg.locator('.count').first.inner_text(), await pg.locator('.count').first.inner_text())
        await pg.set_viewport_size({'width': 390, 'height': 800}); await pg.goto(B + '/admin/'); await pg.wait_for_timeout(300)
        acts = await pg.locator('.top-acts').evaluate("e => [...e.children].map(c => Math.round(c.getBoundingClientRect().top))")
        check('browser: on a phone the three controls fit one row, no sideways scroll', len(set(acts)) == 1 and await pg.evaluate('document.documentElement.scrollWidth - innerWidth') <= 0, acts)
        await pg.screenshot(path=str(ROOT / 'shots/ui-az-390.png'))
        await pg.set_viewport_size({'width': 1280, 'height': 860})
        await pg.locator('.uis a[lang=ru]').click(); await pg.wait_for_load_state()
        check('browser: back to Russian', await pg.inner_text('h1') == 'Обзор' and await pg.evaluate('document.documentElement.lang') == 'ru')
        check('browser: no console errors', not [e for e in errors if 'font' not in e.lower() and 'ERR_FAILED' not in e], errors[:3])
        await ctx.close(); await b.close()


asyncio.run(browser())
sql("DELETE FROM ao_settings WHERE name = 'turnstile'"); sql('DELETE FROM ao_logins'); sql('DELETE FROM ao_orders')
print('\n' + ('ALL PASSED' if not FAILS else 'FAILED: ' + '; '.join(FAILS)))
print('checks failed:', len(FAILS))

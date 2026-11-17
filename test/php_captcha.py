"""Раздел «Безопасность» и капча (Cloudflare Turnstile): ключи, пробная проверка, вход, формы сайта, отказы.

Настоящий Cloudflare здесь не нужен: вместо него отвечает маленький сервер на 127.0.0.1:8779, который ведёт себя
как описано в документации для тестовых ключей, а в браузере скрипт виджета подменяется заглушкой.
Адрес этого сервера на время проверок дописывается в site/storage/config.php и в конце убирается."""
import asyncio, http.client, http.server, json, pathlib, re, subprocess, threading, time, urllib.parse
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
HOST, PORT, MOCK = '127.0.0.1', 8771, 8779
B = f'http://{HOST}:{PORT}'
PW = 'Test-Admin-2026'      # пароль только для локальной тестовой базы
SITE_KEY, SITE_KEY_2 = '1x00000000000000000000AA', '3x00000000000000000000FF'          # тестовые ключи из документации Cloudflare
SECRET_TEST, SECRET_NO = '1x0000000000000000000000000000000AA', '2x0000000000000000000000000000000AA'
SECRET = '0x4AAAAAAAcheckSecretKeyForTests0001'   # «свой» секретный ключ: его знает только сервер-заглушка
TOKEN = 'XXXX.DUMMY.TOKEN.XXXX'
CF = 'https://challenges.cloudflare.com'
CFG = ROOT / 'site/storage/config.php'
LOG = ROOT / 'site/storage/logs/php-errors.log'
FAILS = []


def check(name, ok, info=''):
    print(('ok   ' if ok else 'FAIL ') + name + (' | ' + str(info) if info != '' else ''))
    if not ok: FAILS.append(name)


def sql(q):
    return subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', 'asioptik_test', '-N', '--raw', '--default-character-set=utf8mb4', '-e', q], capture_output=True, text=True).stdout.strip()


def saved():
    v = sql("SELECT value FROM ao_settings WHERE name = 'turnstile'")
    return json.loads(v) if v else {}


def req(method, path, body=None, headers=None, cookie=None):
    c = http.client.HTTPConnection(HOST, PORT, timeout=40)
    h = dict(headers or {})
    if cookie: h['Cookie'] = cookie
    if isinstance(body, (dict, list)) and h.get('Content-Type') != 'application/json':
        body = urllib.parse.urlencode(body, doseq=True); h.setdefault('Content-Type', 'application/x-www-form-urlencoded')
    elif isinstance(body, (dict, list)):
        body = json.dumps(body)
    if isinstance(body, str): body = body.encode('utf-8')
    c.request(method, path, body=body, headers=h)
    r = c.getresponse(); data = r.read(); c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, data.decode('utf-8', 'replace'), r.getheaders()


def cookie_of(raw):
    for k, v in raw:
        if k.lower() == 'set-cookie' and v.startswith('ao_admin='): return v.split(';')[0]
    return ''


def login(password=PW, token=None, extra=None):
    """Вход в админ-панель: (код ответа, заголовки, страница ответа, cookie, страница входа)."""
    s, h, page, raw = req('GET', '/admin/?p=login')
    ck = cookie_of(raw)
    body = {'csrf': re.search(r'name="csrf" value="([a-f0-9]+)"', page).group(1), 'login': 'admin', 'password': password}
    if token is not None: body['cf-turnstile-response'] = token
    body.update(extra or {})
    s, h, t, raw = req('POST', '/admin/?p=login', body, cookie=ck)
    return s, h, t, (cookie_of(raw) or ck), page


def logged_in(ck):
    return req('GET', '/admin/', cookie=ck)[0] == 200


def page(ck, headers=None):
    return req('GET', '/admin/?p=security', cookie=ck, headers=headers)


def post(ck, fields, headers=None, csrf=True):
    """Отправляет форму раздела «Безопасность» и возвращает страницу после перехода."""
    f = dict(fields)
    if csrf: f['csrf'] = re.search(r'name="csrf" value="([a-f0-9]+)"', page(ck, headers)[2]).group(1)
    s, h, t, raw = req('POST', '/admin/?p=security', f, cookie=ck, headers=headers)
    if s == 302: return (s,) + page(ck, headers)[1:3]
    return s, h, t


def text(html):
    html = html[html.find('<main'):] if '<main' in html else html
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'(?s)<script.*?</script>', ' ', html))).replace('&gt;', '>').replace('&quot;', '"').replace('&#039;', "'")


def flash(html):
    m = re.search(r'<p class="flash flash-(\w+)"[^>]*>(.*?)</p>', html, re.S)
    return (m.group(1), re.sub(r'<[^>]+>', '', m.group(2))) if m else ('', '')


def pill(html):
    m = re.search(r'<div class="card-side"><span class="st st-\w+">([^<]*)</span>', html)
    return m.group(1) if m else ''


def site_page(path='/'):
    s, h, t, raw = req('GET', path)
    key = re.search(r'"captchaKey":"([^"]*)"', t)
    return h.get('content-security-policy', ''), (key.group(1) if key else ''), t


def api(captcha='-', **over):
    """Сообщение с сайта. captcha='-' — поле не передаётся."""
    tok = re.search(r'"apiToken":"([a-f0-9]+)"', req('GET', '/')[2]).group(1)
    body = {'kind': 'message', 'lang': 'ru', 'token': tok, 'name': 'Проверка Формы', 'phone': '0501234567', 'text': 'проверка «не робот»'}
    if captcha != '-': body['captcha'] = captcha
    body.update(over)
    s, h, t, raw = req('POST', '/api/order', body, headers={'Content-Type': 'application/json', 'Origin': B})
    try: j = json.loads(t)
    except ValueError: j = {'raw': t[:120]}
    return s, j.get('error', 'ok' if j.get('ok') else j)


def orders():
    return int(sql('SELECT COUNT(*) FROM ao_orders') or 0)


def tries():
    return int(sql('SELECT COUNT(*) FROM ao_logins') or 0)


def log_size():
    """Сколько в журнале PHP строк об ошибках; собственные записи сайта о несработавшей капче не в счёт."""
    if not LOG.exists(): return 0
    return len([x for x in LOG.read_text(errors='replace').splitlines() if x.strip() and '[asioptik] капча не сработала' not in x])


# ---------- сервер вместо Cloudflare ----------
class Mock(http.server.BaseHTTPRequestHandler):
    calls, mode = [], 'normal'

    def log_message(self, *a): pass

    def do_POST(self):
        q = urllib.parse.parse_qs(self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8'))
        secret, resp = q.get('secret', [''])[0], q.get('response', [''])[0]
        Mock.calls.append((secret, resp))
        if Mock.mode == 'drop': return                      # связь оборвалась без ответа
        if Mock.mode == 'html':
            out, ct = b'<html><body>502 Bad Gateway</body></html>', 'text/html'
        else:
            if Mock.mode in ('internal-error', 'bad-request'): j = {'success': False, 'error-codes': [Mock.mode]}
            elif secret == SECRET: j = {'success': True, 'challenge_ts': '2026-11-17T10:00:00.000Z', 'hostname': 'example.com', 'error-codes': []} if resp == TOKEN else {'success': False, 'error-codes': ['invalid-input-response']}
            elif secret == SECRET_NO: j = {'success': False, 'error-codes': ['invalid-input-response']}
            else: j = {'success': False, 'error-codes': ['invalid-input-secret']}
            out, ct = json.dumps(j).encode(), 'application/json'
        self.send_response(200); self.send_header('Content-Type', ct); self.send_header('Content-Length', str(len(out))); self.end_headers(); self.wfile.write(out)


def cfg_write(extra):
    """Дописывает строки в конец настроек сайта и ждёт, пока PHP перечитает файл."""
    CFG.write_text(ORIG[:ORIG.rindex(');')] + ''.join(f"  '{k}' => {v},\n" for k, v in extra.items()) + ');\n')
    time.sleep(3.2)


ORIG = CFG.read_text()
VERIFY = {'turnstile_verify': f"'http://127.0.0.1:{MOCK}/siteverify'"}
srv = http.server.ThreadingHTTPServer(('127.0.0.1', MOCK), Mock)
threading.Thread(target=srv.serve_forever, daemon=True).start()

# заглушка виджета: ведёт себя как api.js — ставит ответ в форму и зовёт обработчики
STUB = r"""
(function () {
  var n = 0, widgets = {}, src = document.currentScript ? document.currentScript.src : '';
  window.__cap = window.__cap || { log: [] };
  function make(container, o) {
    var el = typeof container === 'string' ? document.querySelector(container) : container, id = 'w' + (++n), w = widgets[id] = { el: el, o: o, token: '' };
    el.setAttribute('data-stub', id);
    window.__cap.log.push('render ' + o.sitekey + ' ' + (o.appearance || '') + ' ' + (o.language || ''));
    w.solve = function () {
      w.token = window.__cap.token || 'XXXX.DUMMY.TOKEN.XXXX';
      if (el.closest('form')) {
        var i = el.querySelector('input[name="cf-turnstile-response"]');
        if (!i) { i = document.createElement('input'); i.type = 'hidden'; i.name = 'cf-turnstile-response'; el.appendChild(i); }
        i.value = w.token;
      }
      if (o.callback) o.callback(w.token);
    };
    w.run = function () {
      if (window.__cap.error) { if (o['error-callback']) o['error-callback'](window.__cap.error); return; }
      if (window.__cap.interactive) {
        if (o['before-interactive-callback']) o['before-interactive-callback']();
        window.__cap.finish = function () { if (o['after-interactive-callback']) o['after-interactive-callback'](); w.solve(); };
        return;
      }
      setTimeout(w.solve, window.__cap.delay || 40);
    };
    w.run();
    return id;
  }
  window.turnstile = {
    render: make,
    reset: function (id) { window.__cap.log.push('reset'); if (widgets[id]) { widgets[id].token = ''; widgets[id].run(); } },
    remove: function (id) { delete widgets[id]; },
    getResponse: function (id) { return widgets[id] ? widgets[id].token : undefined; }
  };
  function scan() {
    [].forEach.call(document.querySelectorAll('.cf-turnstile'), function (el) {
      if (!el.getAttribute('data-stub')) make(el, { sitekey: el.getAttribute('data-sitekey'), language: el.getAttribute('data-language') });
    });
  }
  if (!/render=explicit/.test(src)) { if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', scan); else scan(); }
})();
"""


async def browser():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await b.new_context(viewport={'width': 1280, 'height': 900})
        pg = await ctx.new_page()
        errors, cf, posts = [], [], []
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        state = {'script': 'stub'}

        async def cloud(route):
            cf.append(route.request.url)
            if state['script'] == 'blocked': return await route.abort()
            await route.fulfill(status=200, content_type='application/javascript', body=STUB)
        await pg.route(CF + '/**', cloud)
        await pg.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body=''))
        await pg.route('https://fonts.gstatic.com/**', lambda r: r.abort())
        await pg.route('https://images.pexels.com/**', lambda r: r.abort())
        await pg.route('https://maps.google.com/**', lambda r: r.fulfill(status=200, content_type='text/html', body='<html></html>'))
        await pg.route('https://www.google.com/**', lambda r: r.fulfill(status=200, content_type='text/html', body='<html></html>'))
        await pg.add_init_script("window.__opened=[]; window.open=function(u){window.__opened.push(u); return {opener:null};};")

        def seen(r):
            if r.method == 'POST' and r.url.endswith('/api/order'):
                try: posts.append(json.loads(r.post_data or '{}'))
                except ValueError: posts.append({})
        pg.on('request', seen)
        real = lambda: [e for e in errors if 'font' not in e.lower() and 'ERR_FAILED' not in e and 'pexels' not in e and '403' not in e]

        print('--- браузер: пробная проверка в разделе «Безопасность»')
        await pg.goto(B + '/admin/?p=login')
        check('browser: login page without the check loads nothing from Cloudflare', not cf and await pg.locator('.cf-turnstile').count() == 0, cf)
        await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click(); await pg.wait_for_load_state()
        await pg.goto(B + '/admin/?p=security')
        await pg.fill('#cap-site', SITE_KEY); await pg.fill('#cap-secret', SECRET)
        await pg.locator('.sec-form button[type=submit]').click(); await pg.wait_for_load_state(); await pg.wait_for_timeout(400)
        check('browser: after saving the keys the trial widget is drawn by the Cloudflare script', await pg.locator('.sec-check .cf-turnstile[data-stub]').count() == 1 and len(cf) == 1, cf)
        check('browser: the widget put its answer into the form', await pg.input_value('.sec-check input[name="cf-turnstile-response"]') == TOKEN)
        check('browser: the secret is not in the page', SECRET not in await pg.content() and await pg.input_value('#cap-secret') == '')
        box = await pg.locator('.sec-check').bounding_box()
        check('browser: trial block fits the card', box and box['width'] > 300 and box['x'] >= 0, box)
        await pg.screenshot(path=str(ROOT / 'shots/sec-wait.png'), full_page=True)
        await pg.locator('.sec-check button[type=submit]').click(); await pg.wait_for_load_state(); await pg.wait_for_timeout(300)
        check('browser: «Включить капчу» turns the check on', await pg.locator('.card-side .st-done').count() == 1 and saved().get('ok') is True, await pg.locator('.card-side').first.inner_text())
        check('browser: no widget once the keys are verified', await pg.locator('.cf-turnstile').count() == 0)
        await pg.screenshot(path=str(ROOT / 'shots/sec-on.png'), full_page=True)
        over = await pg.evaluate("[...document.querySelectorAll('.main *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).length")
        check('browser: nothing sticks out of the page (1280)', over == 0, over)
        await pg.set_viewport_size({'width': 390, 'height': 800}); await pg.wait_for_timeout(200)
        over = await pg.evaluate("document.documentElement.scrollWidth - innerWidth")
        check('browser: no sideways scroll on a phone (390)', over <= 0, over)
        await pg.screenshot(path=str(ROOT / 'shots/sec-on-390.png'), full_page=True)
        await pg.set_viewport_size({'width': 1280, 'height': 900})
        check('browser: admin pages without console errors', not real(), real()[:3])

        print('--- браузер: вход с проверкой')
        await pg.locator('.logout button').click(); await pg.wait_for_load_state()
        n = len(cf)
        await pg.goto(B + '/admin/?p=login'); await pg.wait_for_timeout(300)
        check('browser: login page draws the widget', await pg.locator('.cf-turnstile[data-stub]').count() == 1 and len(cf) == n + 1)
        box = await pg.locator('.cap').bounding_box(); card = await pg.locator('main.card').bounding_box()
        check('browser: widget place fits the login card', box and card and box['x'] >= card['x'] and box['x'] + box['width'] <= card['x'] + card['width'] + 1, (box, card))
        await pg.screenshot(path=str(ROOT / 'shots/sec-login.png'))
        await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click(); await pg.wait_for_load_state()
        check('browser: login with the check passes', '/admin/' in pg.url and 'p=login' not in pg.url and await pg.locator('.side nav').count() == 1, pg.url)
        check('browser: login without console errors', not real(), real()[:3])

        print('--- браузер: формы сайта')
        n = len(cf)
        await pg.goto(B + '/contacts?lang=ru'); await pg.wait_for_timeout(1200)
        check('browser: site page loads nothing from Cloudflare until a form is touched', len(cf) == n and await pg.locator('.cap-dock').count() == 0, cf[n:])
        await pg.locator('#ctName').click(); await pg.wait_for_timeout(300)
        check('browser: touching a form field loads the widget once', len(cf) == n + 1 and await pg.locator('.cap-dock').count() == 1, cf[n:])
        log = await pg.evaluate('window.__cap.log')
        check('browser: widget is hidden until Cloudflare asks, language follows the page', log == [f'render {SITE_KEY} interaction-only ru'], log)
        check('browser: nothing visible while the check passes by itself', not await pg.locator('.cap-dock').evaluate("e => e.classList.contains('is-on') || e.getBoundingClientRect().height > 0"))
        await pg.fill('#ctName', 'Айдан Проверка'); await pg.fill('#ctPhone', '0557778899'); await pg.select_option('#ctTopic', 'exam'); await pg.fill('#ctMsg', 'Сообщение с проверкой')
        before = orders()
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(700)
        check('browser: message goes out with the answer of the check', len(posts) == 1 and posts[0].get('captcha') == TOKEN, [p.get('captcha') for p in posts])
        check('browser: message saved', orders() == before + 1, orders() - before)
        check('browser: WhatsApp opened as before', len(await pg.evaluate('window.__opened')) == 1)
        await pg.fill('#ctPhone', '0557778899'); await pg.select_option('#ctTopic', 'exam'); await pg.fill('#ctMsg', 'Второе сообщение')
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(700)
        check('browser: the next message gets a fresh answer', len(posts) == 2 and posts[1].get('captcha') == TOKEN and 'reset' in await pg.evaluate('window.__cap.log'), await pg.evaluate('window.__cap.log'))
        check('browser: second message saved', orders() == before + 2)
        check('browser: one script request for the whole visit', len(cf) == n + 1, cf[n:])

        # Cloudflare просит поставить отметку: окно появляется, отправка ждёт
        await pg.evaluate("window.__cap.interactive = true")
        await pg.fill('#ctPhone', '0557778899'); await pg.select_option('#ctTopic', 'exam'); await pg.fill('#ctMsg', 'Третье сообщение')
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(500)
        dock = await pg.locator('.cap-dock').evaluate("e => ({ on: e.classList.contains('is-on'), note: e.querySelector('.cap-note').textContent, shown: getComputedStyle(e.querySelector('.cap-note')).display, r: e.getBoundingClientRect().toJSON(), z: getComputedStyle(e).zIndex })")
        check('browser: when Cloudflare asks for a tick, a small window appears', dock['on'] and dock['shown'] == 'block' and 'не робот' in dock['note'] and dock['r']['width'] > 100, dock)
        check('browser: the window stays inside the screen and above other layers', dock['r']['left'] >= 0 and dock['r']['bottom'] <= 900 and int(dock['z']) > 120, dock['r'])
        check('browser: the message waits for the tick', len(posts) == 2 and len(await pg.evaluate('window.__opened')) == 3, len(posts))
        await pg.screenshot(path=str(ROOT / 'shots/sec-dock.png'))
        await pg.locator('.hdr-right [data-set-lang="en"]').click(); await pg.wait_for_timeout(200)
        check('browser: the window text follows the page language', 'robot' in await pg.locator('.cap-note').inner_text(), await pg.locator('.cap-note').inner_text())
        await pg.locator('.hdr-right [data-set-lang="ru"]').click()
        await pg.evaluate("window.__cap.interactive = false; window.__cap.finish()"); await pg.wait_for_timeout(600)
        check('browser: after the tick the window hides and the message is sent', len(posts) == 3 and posts[2].get('captcha') == TOKEN and not await pg.locator('.cap-dock').evaluate("e => e.classList.contains('is-on')"))
        check('browser: third message saved', orders() == before + 3)

        # оформление заказа: проверка стартует сразу при открытии страницы
        n = len(cf)
        await pg.goto(B + '/product/f-milan?lang=ru'); await pg.wait_for_timeout(1000)
        await pg.locator('#ppAdd').click(); await pg.wait_for_timeout(300)
        check('browser: product page still loads nothing from Cloudflare', len(cf) == n)
        await pg.goto(B + '/checkout?lang=ru'); await pg.wait_for_timeout(1200)
        check('browser: opening the checkout starts the check', len(cf) == n + 1 and await pg.locator('.cap-dock').count() == 1, cf[n:])
        await pg.fill('#coName', 'Лейла Проверка'); await pg.fill('#coPhone', '0501234567')
        await pg.locator('#checkoutForm [type=submit]').click(); await pg.wait_for_timeout(800)
        check('browser: order goes out with the answer and is saved', posts[-1].get('kind') == 'order' and posts[-1].get('captcha') == TOKEN and orders() == before + 4, posts[-1].get('captcha'))
        check('browser: site pages without console errors', not real(), real()[:3])

        # скрипт Cloudflare недоступен (блокировщик, сеть): заказ в WhatsApp уходит, запись не сохраняется, страница не ломается
        state['script'] = 'blocked'; errors.clear()
        await pg.goto(B + '/contacts?lang=ru'); await pg.wait_for_timeout(1000)
        await pg.fill('#ctName', 'Без Проверки'); await pg.fill('#ctPhone', '0557778899'); await pg.select_option('#ctTopic', 'exam')
        k = len(posts)
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(900)
        check('browser: with the script blocked the request is sent at once, without an answer', len(posts) == k + 1 and 'captcha' not in posts[-1], posts[k:])
        check('browser: … the server does not save it, WhatsApp still opens', orders() == before + 4 and len(await pg.evaluate('window.__opened')) == 1)
        check('browser: … and the page has no script errors', not [e for e in errors if e.startswith('pageerror')], errors[:3])
        # неверный ключ или чужой домен (ошибка 110200): ждать бессмысленно
        state['script'] = 'stub'
        await pg.add_init_script("window.__cap = { log: [], error: '110200' };")
        await pg.goto(B + '/contacts?lang=ru'); await pg.wait_for_timeout(1000)
        await pg.fill('#ctName', 'Чужой Домен'); await pg.fill('#ctPhone', '0557778899'); await pg.select_option('#ctTopic', 'exam')
        k = len(posts)
        await pg.locator('#contactForm [type=submit]').click(); await pg.wait_for_timeout(900)
        check('browser: a key error from Cloudflare does not hold the request', len(posts) == k + 1 and 'captcha' not in posts[-1], posts[k:])
        await ctx.close(); await b.close()


try:
    cfg_write(VERIFY)
    sql('DELETE FROM ao_logins'); sql("DELETE FROM ao_settings WHERE name = 'turnstile'")
    (ROOT / 'shots').mkdir(exist_ok=True)
    log0 = log_size()

    print('--- раздел «Безопасность»: доступ и первый вид')
    s, h, t, raw = req('GET', '/admin/?p=security')
    check('security page needs a login', s == 302 and 'p=login' in h.get('location', ''), (s, h.get('location')))
    s, h, t, ck, _ = login()
    check('login works without the check while it is off', s == 302 and logged_in(ck), s)
    s, h, t, raw = page(ck)
    tx = text(t)
    check('page opens', s == 200 and all(x in tx for x in ['Капча Cloudflare Turnstile', 'Где взять ключи', 'Что уже защищено']), s)
    check('status: off', pill(t) == 'Выключена', pill(t))
    check('menu has «Безопасность», marked current', bool(re.search(r'<a href="[^"]*\?p=security" aria-current="page">', t)))
    check('nothing is loaded from Cloudflare without keys', 'cf-turnstile' not in t and CF not in t.replace('challenges.cloudflare.com по https', ''))
    check('five steps to get the keys, with the site domain', len(re.findall(r'<li>', t[t.find('class="steps"'):t.find('</ol>')])) == 5 and 'Add widget' in tx and 'asioptik.az' in tx)
    check('protection list: live items and constant ones', tx.count('Неудачных попыток за сутки: 0.') == 1 and 'Капча Выключена. Чтобы включить' in tx and len(re.findall(r'<li class="ok">', t)) == 12 and len(re.findall(r'<li class="warn">', t)) == 1, re.findall(r'<li class="(\w+)">', t))
    check('recovery hint mentions config.php', "'captcha' => false" in tx)
    s, h, t = post(ck, {'act': 'save', 'site': SITE_KEY, 'secret': SECRET}, csrf=False)
    check('saving needs the CSRF key', s == 400 and not saved(), s)

    print('--- проверка полей')
    for name, f, want in [
        ('nothing entered', {'site': '', 'secret': ''}, 'Вставьте Secret Key'),
        ('empty site key', {'site': '', 'secret': SECRET}, 'Вставьте Site Key'),
        ('short site key', {'site': 'abc', 'secret': SECRET}, 'Ключ выглядит иначе'),
        ('markup in the site key', {'site': '"><script>alert(1)</script>', 'secret': SECRET}, 'Ключ выглядит иначе'),
        ('no secret', {'site': SITE_KEY, 'secret': ''}, 'Вставьте Secret Key'),
        ('spaces inside the secret', {'site': SITE_KEY, 'secret': 'abc def ghi jkl mno pqr'}, 'Ключ выглядит иначе'),
        ('the same key twice', {'site': SITE_KEY, 'secret': SITE_KEY}, 'два разных ключа'),
    ]:
        s, h, t = post(ck, dict(f, act='save', login='1', forms='1'))
        check('refused: ' + name, s == 200 and want in text(t) and not saved() and '<script>alert' not in t, (s, flash(t)))
    https = {'Host': 'asioptik.az', 'X-Forwarded-Proto': 'https'}
    s, h, t = post(ck, {'act': 'save', 'site': SITE_KEY, 'secret': SECRET_TEST, 'login': '1', 'forms': '1'}, headers=https)
    check('on a real domain Cloudflare test keys are refused', s == 200 and text(t).count('тестовый ключ Cloudflare') == 2 and not saved(), flash(t))
    check('… and the local hint with test keys is not shown there', 'Сайт открыт на этом компьютере' not in text(t) and SECRET_TEST not in t and 'Сайт открыт по https' in text(t))

    print('--- ключи сохранены, пробная проверка ещё не пройдена')
    s, h, t = post(ck, {'act': 'save', 'site': '  ' + SITE_KEY + ' ', 'secret': SECRET, 'login': '1', 'forms': '1'})
    v = saved()
    check('keys saved, not active yet', v.get('site') == SITE_KEY and v.get('secret') == SECRET and not v.get('ok') and v.get('login') and v.get('forms'), {k: v.get(k) for k in ('site', 'ok', 'login', 'forms')})
    check('message explains the last step', flash(t)[0] == 'ok' and 'пробную проверку' in flash(t)[1], flash(t))
    check('status: waiting for the trial check', pill(t) == 'Ждёт пробной проверки', pill(t))
    check('secret is never sent back to the page', SECRET not in t and 'name="secret" value=""' in t and 'сохранён — оставьте пустым' in t and 'очистите оба поля' in t)
    check('trial widget with the site key and the Cloudflare script', f'class="cf-turnstile" data-sitekey="{SITE_KEY}"' in t and f'<script src="{CF}/turnstile/v0/api.js" async defer></script>' in t)
    csp = page(ck)[1].get('content-security-policy', '')
    check('CSP of this page lets the widget in', f"script-src 'self' {CF};" in csp and f'frame-src {CF};' in csp and f"connect-src 'self' {CF};" in csp, csp)
    check('… other admin pages load nothing from Cloudflare', all(CF not in req('GET', u, cookie=ck)[2] and 'cf-turnstile' not in req('GET', u, cookie=ck)[2] for u in ('/admin/', '/admin/?p=orders')))
    s, h, t2, ck2, lp = login()
    check('login is not affected before the trial check', s == 302 and 'cf-turnstile' not in lp, s)
    csp, key, t2 = site_page()
    check('site is not affected before the trial check', key == '' and CF not in t2 and api()[0] == 200, key)
    sql('DELETE FROM ao_orders')

    print('--- пробная проверка')
    n = len(Mock.calls)
    s, h, t = post(ck, {'act': 'check'})
    check('no answer from the widget: refused without asking Cloudflare', flash(t)[0] == 'err' and 'дождитесь отметки' in flash(t)[1] and len(Mock.calls) == n and not saved().get('ok'), flash(t))
    s, h, t = post(ck, {'act': 'check', 'cf-turnstile-response': 'SOME.OTHER.TOKEN.VALUE'})
    check('wrong answer: refused, reason shown', 'от разных виджетов' in flash(t)[1] and len(Mock.calls) == n + 1 and Mock.calls[-1] == (SECRET, 'SOME.OTHER.TOKEN.VALUE') and not saved().get('ok'), flash(t))
    Mock.mode = 'drop'
    s, h, t = post(ck, {'act': 'check', 'cf-turnstile-response': TOKEN})
    check('no connection to Cloudflare: not turned on, hosting hint', 'не смог связаться' in flash(t)[1] and not saved().get('ok'), flash(t))
    Mock.mode = 'html'
    s, h, t = post(ck, {'act': 'check', 'cf-turnstile-response': TOKEN})
    check('garbage instead of an answer: not turned on', 'ответил с ошибкой' in flash(t)[1] and not saved().get('ok'), flash(t))
    Mock.mode = 'normal'
    # ключи от разных виджетов и неверный секретный ключ
    post(ck, {'act': 'save', 'site': SITE_KEY, 'secret': 'wrong-secret-key-0000000000', 'login': '1', 'forms': '1'})
    s, h, t = post(ck, {'act': 'check', 'cf-turnstile-response': TOKEN})
    check('Cloudflare does not know the secret: clear reason', 'не принял Secret Key' in flash(t)[1] and not saved().get('ok'), flash(t))
    post(ck, {'act': 'save', 'site': SITE_KEY, 'secret': SECRET, 'login': '1', 'forms': '1'})
    s, h, t = post(ck, {'act': 'check', 'cf-turnstile-response': TOKEN})
    v = saved()
    check('right answer: the check is on', flash(t) == ('ok', 'Ключи проверены, капча включена.') and v.get('ok') is True and v.get('checked'), flash(t))
    check('status: works, places listed', pill(t) == 'Работает' and 'Сейчас проверяется: вход в админ-панель и формы сайта.' in text(t) and 'Капча Работает: вход в админ-панель и формы сайта.' in text(t), pill(t))
    check('no widget on the page any more, secret still hidden', 'cf-turnstile' not in t and SECRET not in t)

    print('--- вход в админ-панель с проверкой')
    s, h, lp, raw = req('GET', '/admin/?p=login')
    csp = h.get('content-security-policy', '')
    check('login page has the widget and lets Cloudflare in', f'data-sitekey="{SITE_KEY}"' in lp and CF + '/turnstile/v0/api.js' in lp and f"script-src 'self' {CF};" in csp and f'frame-src {CF};' in csp, csp)
    check('secret is not on the login page', SECRET not in lp)
    n, a = len(Mock.calls), tries()
    s, h, t, bad, _ = login()
    check('right password without the check: not let in', s == 200 and 'Подтвердите, что вы не робот' in t and not logged_in(bad), s)
    check('… the attempt is not counted and Cloudflare is not asked', tries() == a and len(Mock.calls) == n, (tries(), len(Mock.calls) - n))
    s, h, t, bad, _ = login(token='SOME.OTHER.TOKEN.VALUE')
    check('wrong answer of the check: not let in', s == 200 and 'Подтвердите, что вы не робот' in t and not logged_in(bad) and len(Mock.calls) == n + 1 and tries() == a)
    s, h, t, bad, _ = login(extra={'cf-turnstile-response[]': 'x'})
    check('answer sent as a list: not let in, no PHP warnings', s == 200 and 'Подтвердите, что вы не робот' in t and log_size() == log0, log_size() - log0)
    s, h, t, bad, _ = login(password='wrong-password', token=TOKEN)
    check('check passed, wrong password: usual message, attempt counted', s == 200 and 'Неверный логин или пароль' in t and tries() == a + 1, tries() - a)
    s, h, t, ck, _ = login(token=TOKEN)
    check('check passed, right password: in', s == 302 and logged_in(ck) and tries() == 0, s)
    for i in range(5): login(password='wrong-password', token=TOKEN)
    n = len(Mock.calls)
    s, h, t, bad, _ = login(token=TOKEN)
    check('five wrong passwords still close the door first', 'Слишком много попыток' in t and len(Mock.calls) == n, flash(t))
    sql('DELETE FROM ao_logins')

    print('--- формы сайта с проверкой')
    csp, key, t = site_page()
    check('site page gets the public key only', key == SITE_KEY and SECRET not in t, key)
    check('site CSP lets the widget in', f"script-src 'self' 'unsafe-inline' {CF};" in csp and f'https://maps.google.com {CF};' in csp and f"connect-src 'self' {CF};" in csp, csp)
    check('… on every page', all(site_page(p)[1] == SITE_KEY for p in ('/contacts', '/checkout', '/product/f-milan', '/catalog?aud=kids')))
    n, o = len(Mock.calls), orders()
    check('message without the check: refused', api() == (403, 'captcha') and orders() == o and len(Mock.calls) == n, api())
    check('wrong answer: refused', api('SOME.OTHER.TOKEN.VALUE') == (403, 'captcha') and orders() == o and len(Mock.calls) == n + 1)
    n = len(Mock.calls)
    for name, val in [('empty', ''), ('a list', ['x', 'y']), ('an object', {'a': 1}), ('a number', 5), ('too long', 'A' * 3000), ('with spaces', 'aaaa bbbb cccc dddd'), ('with a line break', 'aaaaaaaaaaaa\nsecret=x')]:
        check('answer ' + name + ': refused without asking Cloudflare', api(val) == (403, 'captcha') and len(Mock.calls) == n, len(Mock.calls) - n)
    check('no PHP warnings from odd answers', log_size() == log0, log_size() - log0)
    check('cheaper checks still come first', api(TOKEN, token='0' * 32) == (403, 'token') and api(TOKEN, name='') == (422, 'fields') and len(Mock.calls) == n, len(Mock.calls) - n)
    check('right answer: saved', api(TOKEN) == (200, 'ok') and orders() == o + 1 and Mock.calls[-1] == (SECRET, TOKEN), orders() - o)

    print('--- где проверять')
    s, h, t = post(ck, {'act': 'save', 'site': SITE_KEY, 'secret': '', 'login': '1'})
    v = saved()
    check('forms off: saved without a new trial check, secret kept', flash(t) == ('ok', 'Сохранено.') and v.get('ok') is True and v.get('secret') == SECRET and not v.get('forms') and v.get('login'), flash(t))
    csp, key, t2 = site_page()
    check('… site: no key, no Cloudflare, messages accepted', key == '' and CF not in t2 and api() == (200, 'ok'), key)
    check('… login still asks for the check', 'Подтвердите, что вы не робот' in login()[2] and 'Сейчас проверяется: вход в админ-панель.' in text(t))
    post(ck, {'act': 'save', 'site': SITE_KEY, 'secret': '', 'forms': '1'})
    s, h, t2, ck3, lp = login()
    check('login off: in without the check, no widget', s == 302 and 'cf-turnstile' not in lp and CF not in req('GET', '/admin/?p=login')[2])
    check('… forms ask for the check', api() == (403, 'captcha') and site_page()[1] == SITE_KEY)
    s, h, t = post(ck, {'act': 'save', 'site': SITE_KEY, 'secret': ''})
    check('both off: status «Выключена», keys stay verified', pill(t) == 'Выключена' and saved().get('ok') is True and api() == (200, 'ok') and 'Отметьте в форме выше' in text(t), pill(t))
    s, h, t = post(ck, {'act': 'save', 'site': SITE_KEY, 'secret': '', 'login': '1', 'forms': '1'})
    check('both on again', pill(t) == 'Работает' and api() == (403, 'captcha'))

    print('--- неисправности')
    Mock.mode = 'drop'
    o = orders()
    check('Cloudflare unreachable: a message with an answer is let through', api('ANY.TOKEN.FROM.THE.VISITOR') == (200, 'ok') and orders() == o + 1)
    check('… but without any answer it is still refused', api() == (403, 'captcha') and orders() == o + 1)
    s, h, t, raw = page(ck)
    check('… and the section shows that the check stops nobody', flash(t)[0] == 'warn' and 'Сервер сайта не может связаться с Cloudflare' in flash(t)[1] and 'Капча Никого не останавливает.' in text(t) and '<li class="bad">' in t and saved().get('fault') == 'no-connection', flash(t))
    s, h, t2, ck3, _ = login(token='ANY.TOKEN.FROM.THE.VISITOR')
    check('Cloudflare unreachable: login is not locked (password still needed)', s == 302 and logged_in(ck3) and 'Неверный логин или пароль' in login(password='wrong-password', token='ANY.TOKEN.FROM.THE.VISITOR')[2])
    sql('DELETE FROM ao_logins')
    Mock.mode = 'normal'
    check('first passed check clears the warning', api(TOKEN) == (200, 'ok') and 'fault' not in saved() and flash(page(ck)[2])[0] == '', saved().get('fault'))
    for mode in ('internal-error', 'bad-request', 'html'):
        Mock.mode = mode
        want = (200, 'ok') if mode == 'html' else (403, 'captcha')
        check(f'Cloudflare answers «{mode}»: ' + ('let through' if want[0] == 200 else 'refused'), api(TOKEN) == want, api(TOKEN))
    Mock.mode = 'normal'
    api(TOKEN)
    # секретный ключ отозвали в Cloudflare: вход не должен закрыться
    v = saved(); v['secret'] = 'revoked-secret-key-0000000000'
    sql("UPDATE ao_settings SET value = '" + json.dumps(v).replace("'", "''") + "' WHERE name = 'turnstile'")
    s, h, t2, ck3, _ = login(token=TOKEN)
    check('secret revoked at Cloudflare: login is not locked', s == 302 and logged_in(ck3), s)
    s, h, t, raw = page(ck)
    check('… and the section says which key to replace', 'Cloudflare не принимает Secret Key' in flash(t)[1] and saved().get('fault') == 'invalid-input-secret', flash(t))
    s, h, t = post(ck, {'act': 'save', 'site': SITE_KEY, 'secret': SECRET, 'login': '1', 'forms': '1'})
    check('a new secret needs a new trial check', pill(t) == 'Ждёт пробной проверки' and not saved().get('ok') and 'fault' not in saved() and login()[0] == 302, pill(t))
    post(ck, {'act': 'check', 'cf-turnstile-response': TOKEN})

    print('--- смена ключа сайта')
    s, h, t = post(ck, {'act': 'save', 'site': SITE_KEY_2, 'secret': '', 'login': '1', 'forms': '1'})
    check('new site key: the check waits again and stops asking', pill(t) == 'Ждёт пробной проверки' and site_page()[1] == '' and api() == (200, 'ok') and login()[0] == 302 and f'data-sitekey="{SITE_KEY_2}"' in t, pill(t))
    s, h, t = post(ck, {'act': 'check', 'cf-turnstile-response': TOKEN})
    check('… and works after the trial check', pill(t) == 'Работает' and site_page()[1] == SITE_KEY_2)
    post(ck, {'act': 'save', 'site': SITE_KEY, 'secret': '', 'login': '1', 'forms': '1'}); post(ck, {'act': 'check', 'cf-turnstile-response': TOKEN})

    print('--- запасной выключатель в storage/config.php')
    cfg_write(dict(VERIFY, captcha='false'))
    s, h, t2, ck3, lp = login()
    check('switch off: login without the check, no widget', s == 302 and 'cf-turnstile' not in lp)
    csp, key, t2 = site_page()
    check('switch off: site without the key and Cloudflare, messages accepted', key == '' and CF not in t2 and api() == (200, 'ok'), key)
    s, h, t, raw = page(ck3)
    check('switch off: the section says where it is turned off', pill(t) == 'Отключена в config.php' and 'storage/config.php' in flash(t)[1] and 'Капча Отключена в файле storage/config.php.' in text(t), pill(t))
    cfg_write(VERIFY)
    back = (site_page()[1], api(), 'Подтвердите, что вы не робот' in login()[2])
    check('switch removed: the check is back at once', back == (SITE_KEY, (403, 'captcha'), True), back)

    print('--- удаление ключей')
    s, h, t, ck, _ = login(token=TOKEN)
    s, h, t = post(ck, {'site': '', 'secret': ''}, csrf=False)
    check('deleting needs the CSRF key', s == 400 and saved().get('site') == SITE_KEY, s)
    s, h, t = post(ck, {'site': '', 'secret': '', 'login': '1', 'forms': '1'})
    check('both fields cleared: keys deleted, captcha off', flash(t) == ('ok', 'Ключи удалены, капча выключена.') and saved() == {} and pill(t) == 'Выключена' and 'очистите оба поля' not in t, (flash(t), saved(), pill(t)))
    check('everything works as before the keys', login()[0] == 302 and site_page()[1] == '' and CF not in site_page()[2] and api() == (200, 'ok'))
    check('no PHP errors during all checks', log_size() == log0, log_size() - log0)
    sql('DELETE FROM ao_orders'); sql('DELETE FROM ao_logins')

    asyncio.run(browser())
    check('no PHP errors after the browser part', log_size() == log0, log_size() - log0)
finally:
    CFG.write_text(ORIG)
    sql("DELETE FROM ao_settings WHERE name = 'turnstile'"); sql('DELETE FROM ao_orders'); sql('DELETE FROM ao_logins')
    cache = ROOT / 'site/storage/cache/site.json'
    if cache.exists(): cache.unlink()
    srv.shutdown()
    time.sleep(3.2)

print('\n' + ('ALL PASSED' if not FAILS else 'FAILED: ' + '; '.join(FAILS)))
print('checks failed:', len(FAILS))

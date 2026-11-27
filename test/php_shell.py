"""Страница без прыжков (CLS), на своём языке ещё до работы скрипта; страница «не найдено» (404); свои шрифты.

Проверяется:
- сервер отдаёт каркас страницы на её языке: надписи, подписи кнопок, подсказки, телефон, переключатель языка, значки
  кнопок, ссылка «Бренды» — такими, какими их потом ставит скрипт сайта (после запуска скрипта ничего не меняется);
  надпись и телефон, изменённые в админ-панели, стоят и в ответе сервера;
- при загрузке ничего не сдвигается (сумма сдвигов CLS около нуля) на телефоне и компьютере при медленной сети и медленном
  процессоре; до запуска скрипта на главной виден текст первого экрана, остальное — когда страница собрана;
  посетитель с запомненным другим языком видит страницу уже на нём; без скриптов и когда скрипт не загрузился — сразу,
  а если скрипт сломался до запуска — через 5 с;
- адреса, которых нет: ответ 404, «не показывать поисковикам», без canonical, hreflang и разметки; на странице —
  «не найдено» со ссылками на главную и каталог; смена языка и кнопка «Назад» оставляют её на месте;
- шрифты — с самого сайта: правила @font-face, файлы отдаются, страница заранее просит шрифты своего языка,
  к Google Fonts страница не обращается;
- точки слайдера не меньше 24×24, текст таблицы проверки зрения до её появления не бледнее контраста 4,5:1.

Запуск: sh test/serve.sh, затем python3 test/php_shell.py (базу тест ставит заново сам).
"""
import asyncio, html, http.client, json, pathlib, re, sys
from playwright.async_api import async_playwright
from run import setup, lp, FORGET
from php_reset import reset, sql

ROOT = pathlib.Path(__file__).resolve().parent.parent
B = 'http://127.0.0.1:8771'
LANGS = ('az', 'ru', 'en')
TEXTS = json.loads((ROOT / 'site/app/data/texts.json').read_text(encoding='utf-8'))
OG = (ROOT / 'site/assets/img/og.png').read_bytes()
fails = []
total = 0
def check(name, ok, detail=''):
    global total
    total += 1
    if not ok:
        fails.append(name)
        print('  FAIL', name, '|', str(detail)[:500])
def get(path, headers=None):
    c = http.client.HTTPConnection('127.0.0.1', 8771, timeout=60); c.request('GET', path, headers=headers or {})
    r = c.getresponse(); body = r.read(); c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, body
def page(path):
    s, h, b = get(path)
    return s, h, b.decode('utf-8', 'replace')
def fresh():
    for f in (ROOT / 'site/storage/cache').glob('*.json'): f.unlink()
def setting(name, change):
    v = json.loads(bytes.fromhex(sql(f"SELECT HEX(value) FROM ao_settings WHERE name = '{name}'") or '7b7d').decode('utf-8')); change(v)
    sql(f"DELETE FROM ao_settings WHERE name = '{name}'")
    sql(f"INSERT INTO ao_settings (name, value) VALUES ('{name}', UNHEX('{json.dumps(v, ensure_ascii=False).encode('utf-8').hex()}'))"); fresh()
def nf_title(l):
    t, n = TEXTS['seo.tPage'][l], TEXTS['nf.title'][l]
    s = t.replace('{title}', n).replace('{shop}', 'Asioptik')
    return s if len(s) <= 70 else n + ' — Asioptik'

PAGES = ['/', '/catalog', '/catalog?cat=sun', '/product/f-milan', '/blog', '/blog/care', '/brands', '/about', '/contacts', '/checkout']
LOST = ['/nothing', '/product/no-such', '/blog/no-such', '/brands/no-such', '/catalog/extra', '/notfound', '/brands/asi-sun/more', '/en/robots.txt', '/ru/admin']

# Сравнение каркаса, который отдал сервер, с тем, что сделал из него скрипт сайта: страницу запрашиваем ещё раз и разбираем
# её как документ; JS-части (лупа, страница товара, окна, чат, страницы сайта) не сравниваются — их рисует только скрипт
COMPARE = r'''async () => {
  const raw = new DOMParser().parseFromString(await (await fetch(location.href, { cache: 'no-store' })).text(), 'text/html');
  const skip = '#loupeInner, #pageView, #productPage, #checkoutPage, .layer, #chatBox, #heroKit, [data-cat-tiles], [data-audiences], #productsGrid, #catTabs, [data-branches], [data-branches-mini], #rxCards, .nav-logo';
  const own = doc => el => !el.closest(skip);
  const out = { diff: [], counts: {} };
  const group = (doc, sel, val) => {
    const m = {};
    doc.querySelectorAll(sel).forEach(el => { if (!own(doc)(el)) return; const k = val(el)[0]; (m[k] = m[k] || []).push(val(el)[1]); });
    Object.keys(m).forEach(k => m[k].sort());
    return m;
  };
  const cmp = (name, sel, val) => {
    const a = group(raw, sel, val), b = group(document, sel, val);
    out.counts[name] = Object.keys(a).length;
    Object.keys(a).forEach(k => { if (JSON.stringify(a[k]) !== JSON.stringify(b[k] || [])) out.diff.push([name, k, a[k].slice(0, 2), (b[k] || []).slice(0, 2)]); });
  };
  cmp('text', '[data-i18n]', el => [el.dataset.i18n, el.textContent]);
  cmp('attr', '[data-i18n-attr]', el => [el.tagName + ' ' + el.dataset.i18nAttr, el.dataset.i18nAttr.split(';').map(p => p.split(':')[0].trim()).map(a => a + '=' + el.getAttribute(a)).join(' | ')]);
  cmp('cfg', '[data-cfg]', el => [el.dataset.cfg, el.textContent]);
  cmp('tel', '[data-cfg-href="tel"]', el => ['tel', el.getAttribute('href')]);
  cmp('icon', '[data-icon]', el => [el.dataset.icon, el.innerHTML]);
  cmp('lang', '[data-lang-switch]', el => ['switch', el.innerHTML]);
  out.noBrands = [raw.body.classList.contains('no-brands'), document.body.classList.contains('no-brands')];
  out.boot = document.documentElement.classList.contains('boot');
  return out;
}'''
SHIFTS = '''window.__ls = []; try { new PerformanceObserver(l => l.getEntries().forEach(e => window.__ls.push({ v: e.value, input: e.hadRecentInput,
  src: (e.sources || []).map(s => s.node ? (s.node.nodeName + (s.node.id ? '#' + s.node.id : '') + (typeof s.node.className === 'string' && s.node.className ? '.' + s.node.className.trim().split(/\\s+/).join('.') : '')) : '?') })))
  .observe({ type: 'layout-shift', buffered: true }); } catch (e) {}'''


async def main():
    reset()
    print('--- каркас страницы на её языке (ответ сервера)')
    for l in LANGS:
        for p in PAGES:
            s, h, t = page(lp(p, l))
            check(f'{l} {p}: 200', s == 200, s)
            mark = 'boot' if p == '/' else 'boot boot-view'   # не главная: первый экран главной до скрипта не показывается
            check(f'{l} {p}: language of the page and «boot» mark', f'<html lang="{l}" class="{mark}">' in t, re.search(r'<html[^>]*>', t).group(0))
            check(f'{l} {p}: no template marks left', '%%' not in t)
            h1 = re.search(r'<h1 data-i18n="hero.title">([^<]*)</h1>', t)
            check(f'{l} {p}: hero title in the page language', h1 and html.unescape(h1.group(1)) == TEXTS['hero.title'][l], h1 and h1.group(1))
            sw = re.findall(r'<div class="lang" data-lang-switch[^>]*>(.*?)</div>', t)
            check(f'{l} {p}: language switch is in the page, own language pressed', len(sw) == 2 and all(f'data-set-lang="{l}" lang="{l}"' in x and re.search(f'data-set-lang="{l}"[^>]*aria-pressed="true"', x) for x in sw), sw[:1])
            check(f'{l} {p}: icons are in the page', not re.search(r'data-icon="[a-z]+"[^<>]*></span>', t) and t.count('data-icon=') >= 10)
            check(f'{l} {p}: no Google Fonts', 'fonts.googleapis' not in t and 'fonts.gstatic' not in t)
            pre = re.findall(r'<link rel="preload" href="(/assets/fonts/[^"]+)" as="font" type="font/woff2" crossorigin>', t)
            want = {'az': ['latin', 'az'], 'ru': ['latin', 'cyrillic'], 'en': ['latin']}[l]
            files = sorted('/assets/fonts/' + (f % x) + '.woff2' for f in ('noto-serif-display-%s-300', 'ysabeau-office-%s-400') for x in want)
            check(f'{l} {p}: fonts of the language are asked in advance', sorted(pre) == files, pre)
    s, h, t = page('/ru')
    check('ru: menu button label in Russian', 'aria-label="' + TEXTS['nav.menu']['ru'] + '" data-i18n-attr="aria-label:nav.menu"' in t)
    check('ru: search placeholder in Russian', 'placeholder="' + TEXTS['cat.searchPh']['ru'] + '"' in t)
    check('phone and call link come from the settings', re.search(r'<a class="hdr-phone" data-cfg-href="tel" href="tel:\+994000000000" data-cfg="phone">\+994 00 000 00 00</a>', t))
    fine = re.search(r'<p class="fine" id="finePrint" data-i18n="hero.fine">([^<]*)</p>', t)
    check('price in a text: written like the page script writes it', fine and '150 ₼' in html.unescape(fine.group(1)), fine and fine.group(1))
    # 3 файла за язык без лишних: у каждого предзагруженного файла правильный тип
    for f in sorted(set(re.findall(r'href="(/assets/fonts/[^"]+\.woff2)"', page('/')[2] + page('/ru')[2] + page('/en')[2]))):
        s2, h2, b2 = get(f)
        check(f'font {f} is served', s2 == 200 and h2.get('content-type') == 'font/woff2' and b2[:4] == b'wOF2', (s2, h2.get('content-type')))

    print('--- шрифты в оформлении')
    css = get('/assets/css/app.css')[2].decode('utf-8')
    faces = re.findall(r"@font-face\{font-family:'([^']+)';font-style:normal;font-weight:(\d+);font-display:swap;src:url\(\.\./fonts/([^)]+)\) format\('woff2'\);unicode-range:([^}]+)\}", css)
    check('24 font rules in app.css', len(faces) == 24, len(faces))
    check('font families and weights as on Google Fonts', sorted({(f, w) for f, w, _, _ in faces}) == sorted({('Noto Serif Display', '300'), ('Noto Serif Display', '400'), ('Onest', '500'), ('Onest', '700'),
          ('Ysabeau Office', '400'), ('Ysabeau Office', '500'), ('Ysabeau Office', '600'), ('Ysabeau Office', '700')}))
    for fam, w, f, rng in faces:
        s2, h2, b2 = get('/assets/fonts/' + f)
        check(f'font file {f}', s2 == 200 and b2[:4] == b'wOF2' and len(b2) > 3000, (s2, len(b2)))
    check('the latin set is the last rule of each weight (it wins for shared letters)', all(re.findall(r"font-weight:%s;[^}]*src:url\(\.\./fonts/%s-(\w+)-%s\.woff2" % (w, pkg, w), css)[-1] == 'latin'
          for pkg, w in (('noto-serif-display', 300), ('onest', 700), ('ysabeau-office', 400))))
    for lic in ('noto-serif-display', 'onest', 'ysabeau-office'):
        s2, h2, b2 = get(f'/assets/fonts/{lic}-OFL.txt')
        check(f'font license {lic} is next to the files', s2 == 200 and b'Open Font License' in b2, s2)

    print('--- адреса, которых нет: 404')
    for p in LOST:
        for l in LANGS:
            path = lp(p, l) if not p.startswith('/en/') and not p.startswith('/ru/') else p
            if p.startswith(('/en/', '/ru/')) and l != 'az': continue
            s, h, t = page(path)
            pl = p[1:3] if p.startswith(('/en/', '/ru/')) else l
            check(f'{path}: 404', s == 404, s)
            check(f'{path}: page in its language', f'<html lang="{pl}" class="boot boot-view">' in t, re.search(r'<html[^>]*>', t).group(0))
            check(f'{path}: not for search engines', re.search(r'<meta name="robots" content="noindex', t))
            check(f'{path}: no canonical, hreflang, og:url and markup', 'rel="canonical"' not in t and 'hreflang=' not in t and 'og:url' not in t and 'application/ld+json' not in t)
            ttl = html.unescape(re.search(r'<title>([^<]*)</title>', t).group(1))
            check(f'{path}: title «not found»', ttl == nf_title(pl), ttl)
            check(f'{path}: page script gets the 404 mark', '"notFound":1' in t)
    s, h, t = page('/ru/catalog')
    check('existing page: no 404 mark', s == 200 and 'notFound' not in t)
    s, h, t = page('/?page=nothing&lang=ru')
    check('old address of a page that does not exist: 301 to the new address, then 404', s == 301 and h.get('location') == '/ru/nothing' and page('/ru/nothing')[0] == 404, (s, h.get('location')))

    print('--- изменения из админ-панели — уже в ответе сервера')
    setting('texts', lambda v: v.setdefault('ru', {}).update({'hero.title': 'Свой заголовок <b>&</b> «тест»'}))
    setting('config', lambda v: v.update({'phone': '+994 50 123 45 67'}))
    s, h, t = page('/ru')
    check('own text from the admin panel, escaped', '<h1 data-i18n="hero.title">Свой заголовок &lt;b&gt;&amp;&lt;/b&gt; «тест»</h1>' in t, re.search(r'<h1[^>]*>[^<]*</h1>', t).group(0))
    check('own phone with its call link', '<a class="hdr-phone" data-cfg-href="tel" href="tel:+994501234567" data-cfg="phone">+994 50 123 45 67</a>' in t)
    check('other languages keep their texts', html.unescape(re.search(r'<h1 data-i18n="hero.title">([^<]*)</h1>', page('/en')[2]).group(1)) == TEXTS['hero.title']['en'])

    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])

        async def new(w, h, mobile=False, js=True, slow=False):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=mobile, has_touch=mobile, device_scale_factor=2 if mobile else 1, java_script_enabled=js)
            pg = await ctx.new_page()
            await setup(pg)
            # в интернет стенд не ходит: фото-заготовки с images.pexels.com подменяются картинкой сайта (как будто загрузились)
            await pg.route('https://images.pexels.com/**', lambda r: r.fulfill(status=200, content_type='image/png', body=OG))
            await pg.add_init_script(FORGET)
            pg.reqs = []
            pg.on('request', lambda r: pg.reqs.append(r.url))
            pg.errors = []
            pg.on('pageerror', lambda e: pg.errors.append(str(e)))
            if slow:
                cdp = await ctx.new_cdp_session(pg)
                await cdp.send('Network.enable')
                await cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 150, 'downloadThroughput': 1.6 * 1024 * 1024 / 8, 'uploadThroughput': 750 * 1024 / 8})
                await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
            return pg

        print('--- скрипт сайта ничего не меняет в каркасе страницы')
        pg = await new(1350, 940)
        for l in LANGS:
            for p in PAGES + ['/nothing']:
                await pg.goto(B + lp(p, l)); await pg.wait_for_timeout(500)
                r = await pg.evaluate(COMPARE)
                check(f'{l} {p}: server texts, labels, phone, icons and language switch = what the script sets', not r['diff'] and r['counts']['text'] > 40 and r['counts']['icon'] >= 8 and r['counts']['lang'] == 1, r['diff'][:3])
                check(f'{l} {p}: «Brands» link visibility decided by the server like by the script', r['noBrands'][0] == r['noBrands'][1], r['noBrands'])
                check(f'{l} {p}: page is shown after the script assembled it', not r['boot'])
        check('no page errors', not pg.errors, pg.errors[:2])
        await pg.goto(B + '/ru'); await pg.wait_for_timeout(500)
        check('own text from the admin panel is the same after the script', await pg.inner_text('#top h1') == 'Свой заголовок <b>&</b> «тест»', await pg.inner_text('#top h1'))
        await pg.context.close()
        setting('texts', lambda v: v['ru'].pop('hero.title'))
        setting('config', lambda v: v.update({'phone': '+994 00 000 00 00'}))

        # ни у одного бренда нет товаров — ссылки «Бренды» нет уже в ответе сервера
        sql("UPDATE ao_items SET type = 'brand_off' WHERE type = 'brand'"); fresh()
        s, h, t = page('/ru/catalog')
        check('no brands with products: «Brands» link hidden by the server', '<body class="no-brands">' in t)
        pg = await new(1350, 940)
        await pg.goto(B + '/ru/catalog'); await pg.wait_for_timeout(400)
        r = await pg.evaluate(COMPARE)
        check('no brands: the script agrees', r['noBrands'] == [True, True] and not r['diff'], (r['noBrands'], r['diff'][:2]))
        await pg.context.close()
        sql("UPDATE ao_items SET type = 'brand' WHERE type = 'brand_off'"); fresh()
        check('brands back: link shown again', '<body>' in page('/ru/catalog')[2])

        print('--- при загрузке ничего не сдвигается (медленная сеть, медленный процессор)')
        for w, h, mob in ((412, 823, True), (1350, 940, False)):
            for p in ('/', '/ru', '/en/catalog', '/ru/catalog?cat=frames', '/product/f-milan', '/ru/blog/care', '/en/contacts', '/ru/nothing'):
                pg = await new(w, h, mobile=mob, slow=True)
                await pg.add_init_script(SHIFTS)
                await pg.goto(B + p, wait_until='load'); await pg.wait_for_timeout(2500)
                ls = await pg.evaluate('window.__ls')
                cls = sum(e['v'] for e in ls if not e['input'])
                check(f'{w}px {p}: no layout shift on load (CLS {cls:.4f})', cls < 0.01, [e for e in ls if not e['input']][:3])
                check(f'{w}px {p}: no requests to Google Fonts', not any('fonts.googleapis' in u or 'fonts.gstatic' in u for u in pg.reqs))
                await pg.context.close()

        # прокрутка главной до конца: фото, которые подгружаются по дороге, не сдвигают страницу
        for w, h, mob in ((412, 823, True), (1350, 940, False)):
            for p in ('/', '/ru/catalog', '/en/about'):
                pg = await new(w, h, mobile=mob)
                await pg.add_init_script(SHIFTS)
                await pg.goto(B + p, wait_until='load'); await pg.wait_for_timeout(600)
                await pg.evaluate('async () => { for (let i = 0; i < 60 && innerHeight + scrollY < document.documentElement.scrollHeight - 2; i++) { scrollBy(0, Math.round(innerHeight * .6)); await new Promise(r => setTimeout(r, 160)); } await new Promise(r => setTimeout(r, 900)); }')
                ls = await pg.evaluate('window.__ls')
                cls = sum(e['v'] for e in ls if not e['input'])
                check(f'{w}px {p}: no layout shift while scrolling to the end (CLS {cls:.4f})', cls < 0.01, [e for e in ls if not e['input']][:3])
                await pg.context.close()

        print('--- до запуска скрипта: на главной виден текст первого экрана, остальное скрыто')
        async def late(route):
            await asyncio.sleep(2.5); await route.continue_()
        for p, hero in (('/', 'visible'), ('/ru', 'visible'), ('/ru/catalog', 'hidden'), ('/product/f-milan', 'hidden'), ('/en/nothing', 'hidden')):
            pg = await new(412, 823, mobile=True)
            await pg.add_init_script(SHIFTS)
            await pg.route('**/assets/js/app.js*', late)
            await pg.goto(B + p, wait_until='commit'); await pg.wait_for_timeout(1200)
            st = await pg.evaluate('''() => ({ hero: getComputedStyle(document.querySelector('#top')).visibility, h1: document.querySelector('#top h1').innerText,
              rest: getComputedStyle(document.querySelector('#cats')).visibility, foot: getComputedStyle(document.querySelector('.site-footer')).visibility,
              loupe: getComputedStyle(document.querySelector('#loupe')).visibility })''')
            check(f'{p}: before the script, the home hero is {hero}, the rest is hidden', st['hero'] == hero and st['rest'] == st['foot'] == st['loupe'] == 'hidden' and (hero == 'hidden' or len(st['h1']) > 10), st)
            await pg.wait_for_timeout(3500)
            ls = await pg.evaluate('window.__ls')
            cls = sum(e['v'] for e in ls if not e['input'])
            check(f'{p}: the slow script assembles the page without shifts (CLS {cls:.4f})', cls < 0.01, [e for e in ls if not e['input']][:3])
            await pg.context.close()
        # язык, выбранный раньше: адрес без языка открывается на нём — первый экран ждёт скрипт, ничего не прыгает
        pg = await new(412, 823, mobile=True)
        await pg.add_init_script("try { localStorage.setItem('optika-lang', JSON.stringify('ru')) } catch (e) {}")
        await pg.add_init_script(SHIFTS)
        await pg.route('**/assets/js/app.js*', late)
        await pg.goto(B + '/', wait_until='commit'); await pg.wait_for_timeout(1200)
        before = await pg.evaluate("[document.documentElement.className, getComputedStyle(document.querySelector('#top')).visibility]")
        await pg.wait_for_timeout(3500)
        ls = await pg.evaluate('window.__ls')
        cls = sum(e['v'] for e in ls if not e['input'])
        check('remembered language: hero waits for the script (it will switch the language)', 'boot-view' in before[0] and before[1] == 'hidden', before)
        check(f'remembered language: page switches to it without shifts (CLS {cls:.4f})', cls < 0.01 and await pg.evaluate('location.pathname') == '/ru' and await pg.inner_text('#top h1') == TEXTS['hero.title']['ru'], [e for e in ls if not e['input']][:3])
        await pg.context.close()

        print('--- без скрипта и с упавшим скриптом страница всё равно видна')
        pg = await new(1350, 940, js=False)
        await pg.goto(B + '/ru')
        check('without scripts: the page is visible at once', await pg.evaluate("getComputedStyle(document.querySelector('#cats')).visibility") == 'visible')
        check('without scripts: the text is in Russian', await pg.inner_text('#top h1') == TEXTS['hero.title']['ru'])
        await pg.context.close()
        pg = await new(1350, 940)
        await pg.route('**/assets/js/app.js*', lambda r: r.abort())
        await pg.goto(B + '/'); await pg.wait_for_timeout(300)
        check('script did not load: the page is visible at once', await pg.evaluate("getComputedStyle(document.querySelector('#cats')).visibility") == 'visible')
        await pg.context.close()
        pg = await new(1350, 940)
        await pg.route('**/assets/js/app.js*', lambda r: r.fulfill(status=200, content_type='text/javascript', body='throw new Error("broken on purpose");'))
        await pg.goto(B + '/'); await pg.wait_for_timeout(1500)
        hidden = await pg.evaluate("getComputedStyle(document.querySelector('#cats')).visibility")
        await pg.wait_for_timeout(4000)
        shown = await pg.evaluate("getComputedStyle(document.querySelector('#cats')).visibility")
        check('script broke before start: page hidden only for 5 seconds', hidden == 'hidden' and shown == 'visible', (hidden, shown))
        await pg.context.close()

        print('--- страница «не найдено» в браузере')
        pg = await new(1350, 940)
        tail = lambda: pg.evaluate('location.pathname + location.search')
        for p, l in (('/ru/nothing', 'ru'), ('/product/no-such', 'az'), ('/en/blog/no-such', 'en'), ('/ru/brands/no-such', 'ru')):
            await pg.goto(B + p); await pg.wait_for_timeout(500)
            st = await pg.evaluate('''() => ({ view: document.body.classList.contains('is-view-notfound'), h1: (document.querySelector('#pgTitle') || {}).textContent,
              shown: !document.querySelector('#pageView').hidden, hero: getComputedStyle(document.querySelector('#top')).display, title: document.title,
              links: [...document.querySelectorAll('#pageView .pg-parts a')].map(a => [a.getAttribute('href'), a.textContent]), canon: !!document.querySelector('link[rel=canonical]') })''')
            check(f'{p}: «not found» page is shown, home sections are not', st['view'] and st['shown'] and st['h1'] == TEXTS['nf.title'][l] and st['hero'] == 'none', st)
            check(f'{p}: title is the same as from the server', st['title'] == nf_title(l), st['title'])
            check(f'{p}: links to the home page and the catalog', st['links'] == [['#top', TEXTS['nf.home'][l]], [lp('/catalog', l), TEXTS['nf.catalog'][l]]], st['links'])
            check(f'{p}: address stays, no canonical', await tail() == p and not st['canon'], await tail())
        await pg.goto(B + '/ru/nothing'); await pg.wait_for_timeout(400)
        await pg.locator('#pageView .pg-parts a[data-view="catalog"]').click(); await pg.wait_for_timeout(500)
        check('«not found» → catalog link opens the catalog', await tail() == '/ru/catalog' and await pg.evaluate("document.body.classList.contains('is-view-catalog')"), await tail())
        await pg.go_back(); await pg.wait_for_timeout(500)
        check('back from the catalog: «not found» again', await tail() == '/ru/nothing' and await pg.inner_text('#pgTitle') == TEXTS['nf.title']['ru'], await tail())
        await pg.locator('.hdr-right [data-set-lang="en"]').click(); await pg.wait_for_timeout(400)
        check('language switch on «not found»: same page in English', await tail() == '/en/nothing' and await pg.inner_text('#pgTitle') == TEXTS['nf.title']['en'] and await pg.title() == nf_title('en'), await tail())
        await pg.locator('#pageView .pg-parts a[href="#top"]').click(); await pg.wait_for_timeout(500)
        check('«not found» → home link opens the home page', await tail() == '/en' and await pg.evaluate("!document.body.classList.contains('is-view')"), await tail())
        await pg.goto(B + '/notfound'); await pg.wait_for_timeout(300)
        await pg.goto(B + '/catalog'); await pg.wait_for_timeout(300)
        check('«notfound» is not a page of its own', await pg.evaluate("!document.body.classList.contains('is-view-notfound')"))
        check('no page errors on «not found»', not pg.errors, pg.errors[:2])
        await pg.context.close()

        print('--- точки слайдера и таблица проверки зрения')
        for w, h, mob in ((412, 823, True), (1350, 940, False)):
            pg = await new(w, h, mobile=mob)
            await pg.goto(B + '/'); await pg.wait_for_timeout(600)
            dots = await pg.evaluate("[...document.querySelectorAll('#heroStage .hs:not(#loupeInner .hs) .hs-dot')].map(d => { const r = d.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })")
            check(f'{w}px: slider dots at least 24×24', dots and all(x >= 24 and y >= 24 for x, y in dots), dots)
            op = await pg.evaluate("[...document.querySelectorAll('.chart:not(.is-visible) .chart-row b')].map(b => +getComputedStyle(b).opacity)")
            check(f'{w}px: eye chart text before it appears is not paler than 0.6', op and min(op) >= 0.6, op)
            await pg.context.close()
        await b.close()

    print(f'\n{total - len(fails)}/{total} passed')
    if fails:
        print('FAILED:', len(fails)); sys.exit(1)
    print('ALL PASSED')

asyncio.run(main())

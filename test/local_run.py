"""Просмотр на своём компьютере: встроенный сервер PHP + local/router.php, установка без MySQL, заказ, админ-панель.
Запускается на чистой копии проекта во временной папке, рабочую папку не трогает."""
import asyncio, json, pathlib, shutil, sqlite3, subprocess, tempfile, time, urllib.request
from playwright.async_api import async_playwright
from run import setup, ROOT, pick_branch
PORT = 8089
B = f'http://127.0.0.1:{PORT}'
SH = ROOT / 'shots'
PW = 'Local-Check-2026'     # пароль только для этой временной копии

def code(path):
    try:
        req = urllib.request.Request(B + path); op = urllib.request.build_opener(type('NoRedirect', (urllib.request.HTTPRedirectHandler,), {'redirect_request': lambda *a, **k: None}))
        return op.open(req).status
    except urllib.error.HTTPError as e:
        return e.code

async def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='asioptik-local-'))
    files = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', 'site', 'local'], cwd=ROOT, capture_output=True, text=True).stdout.split('\n') if (ROOT / '.git').exists() else []
    if files and files[0]:
        for f in filter(None, files):
            (tmp / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy(ROOT / f, tmp / f)
    else:   # вне репозитория: копируем папки, пропуская то, что появляется после установки
        shutil.copytree(ROOT / 'local', tmp / 'local')
        shutil.copytree(ROOT / 'site', tmp / 'site', ignore=lambda d, names: [n for n in names if n in ('config.php', 'sessions', 'site.json', 'site.sqlite') or (pathlib.Path(d).name == 'uploads' and (pathlib.Path(d) / n).is_dir()) or n.endswith('.log')])
    srv = subprocess.Popen(['php', '-S', f'127.0.0.1:{PORT}', '-t', 'site', 'local/router.php'], cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        time.sleep(1)
        print('before install:', {p: code(p) for p in ['/', '/install.php', '/admin/', '/assets/css/app.css', '/app/core/db.php', '/storage/', '/.htaccess', '/uploads/']})
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
            ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); pg = await ctx.new_page(); await setup(pg)
            await pg.route('https://images.pexels.com/**', lambda r: r.abort())
            errors = []; pg.on('pageerror', lambda e: errors.append(str(e)))
            pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'font' not in m.text.lower() and 'ERR_' not in m.text and 'CORS' not in m.text else None)
            await pg.goto(B + '/'); tail = lambda: pg.url.replace(B, '')
            print('first open →', tail(), '| file switch:', await pg.locator('#file_db').count(), 'checked', await pg.is_checked('#file_db'), '| MySQL fields visible:', await pg.locator('.db-fields').is_visible())
            print('checks:', await pg.locator('.checks-list li').evaluate_all("els => els.map(e => e.className)"))
            await pg.screenshot(path=f'{SH}/local-install.png', full_page=True)
            await pg.uncheck('#file_db'); print('unchecked → MySQL fields visible:', await pg.locator('.db-fields').is_visible()); await pg.check('#file_db')
            await pg.fill('#password', PW); await pg.fill('#password2', PW); await pg.locator('button[type=submit]').click(); await pg.wait_for_load_state()
            print('install:', await pg.locator('.flash').first.inner_text(), '|', (await pg.locator('.hint').last.inner_text())[:170])
            print('install.php kept on a local copy:', (tmp / 'site/install.php').exists(), '| data file:', (tmp / 'site/storage/site.sqlite').exists())
            await pg.goto(B + '/?lang=ru'); await pg.wait_for_timeout(1800)
            print('home:', await pg.title(), '| tiles:', await pg.locator('#cats .ctile').count())
            await pg.screenshot(path=f'{SH}/local-home.png')
            await pg.goto(B + '/catalog?lang=ru&cat=frames'); await pg.wait_for_timeout(1200); print('catalog:', tail(), '| cards', await pg.locator('#productsGrid .card').count())
            await pg.goto(B + '/product/f-milan?lang=ru'); await pg.wait_for_timeout(1200); await pg.locator('#ppAdd').click(); await pg.wait_for_timeout(300)
            await pg.goto(B + '/checkout?lang=ru'); await pg.wait_for_timeout(1000)
            await pg.fill('#coName', 'Локальная проверка'); await pick_branch(pg); await pg.fill('#coPhone', '0501234567'); await pg.locator('#checkoutForm [type=submit]').click(); await pg.wait_for_timeout(1200)
            db = sqlite3.connect(tmp / 'site/storage/site.sqlite'); print('order saved:', db.execute('SELECT number, kind, name, phone, total, status FROM ao_orders').fetchall()); db.close()
            await pg.goto(B + '/admin/'); print('admin →', tail())
            await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click(); await pg.wait_for_load_state()
            print('login →', tail(), '|', await pg.inner_text('h1'), '| tiles:', [' '.join(x.split()) for x in await pg.locator('.tile').all_inner_texts()], '| last orders:', await pg.locator('.table tbody tr').count(), '| http warning:', await pg.locator('.flash-warn').count())
            await pg.screenshot(path=f'{SH}/local-admin-home.png')
            # те же экраны на файловой базе (SQLite): заказы с поиском, клиенты, страницы
            await pg.goto(B + '/admin/?p=orders&q=локальная'); print('orders search:', await pg.locator('.table tbody tr').count(), end=' | ')
            await pg.goto(B + '/admin/?p=clients'); print('clients:', [' '.join(x.split())[:60] for x in await pg.locator('.table tbody tr').all_inner_texts()], end=' | ')
            await pg.goto(B + '/admin/?p=pages'); print('pages:', await pg.locator('.table tbody tr').count())
            await pg.goto(B + '/admin/?p=security'); print('security:', await pg.locator('.card-side .st').inner_text(), '| protected items:', await pg.locator('.sec-list li').count(), '| local hint:', await pg.locator('.sec-local').count())
            await pg.goto(B + '/admin/?p=page&id=home'); await pg.fill('#f-t-hero-title--ru', 'Локальная проверка надписи'); await pg.fill('#f-seo-title--ru', 'Локальный заголовок для поиска')
            await pg.locator('.actions .btn').click(); await pg.wait_for_load_state(); print('page texts:', await pg.locator('.flash').first.inner_text(), end=' | ')
            await pg.goto(B + '/?lang=ru'); await pg.wait_for_timeout(1500); print('on site:', await pg.inner_text('h1'), '|', await pg.title())
            await pg.goto(B + '/admin/?p=list&type=product&cat=frames'); print('products in «Оправы»:', await pg.locator('.table tbody tr').count(), end=' | ')
            await pg.goto(B + '/admin/?p=list&type=product&q=милан'); print('search «милан»:', await pg.locator('.table tbody tr').count())
            await pg.locator('.table tbody tr a.strong').first.click(); await pg.fill('#f-price', '155'); await pg.locator('.actions .btn').click(); await pg.wait_for_load_state()
            print('edit:', await pg.locator('.flash').first.inner_text())
            await pg.goto(B + '/product/f-milan?lang=ru'); await pg.wait_for_timeout(1200); print('price on site:', (await pg.inner_text('.pp-price')).replace('\n', ' '))
            print('errors:', errors or 'none')
            await b.close()
        print('after install:', {p: code(p) for p in ['/', '/catalog', '/product/f-milan', '/blog/care', '/admin', '/storage/config.php', '/storage/site.sqlite', '/storage/sessions/', '/app/data/seed.json', '/install.php', '/sitemap.xml']})
    finally:
        srv.terminate(); err = srv.stderr.read().decode('utf-8', 'replace')
        bad = [l for l in err.split('\n') if 'Warning' in l or 'Fatal' in l or 'Notice' in l or 'Deprecated' in l]
        print('php messages:', bad[:5] or 'none')
        shutil.rmtree(tmp, ignore_errors=True)
asyncio.run(main())

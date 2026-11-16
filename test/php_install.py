"""Установщик: проверки хостинга, ошибки формы, установка, повторный запуск."""
import asyncio, subprocess
from playwright.async_api import async_playwright
from run import ROOT
B = 'http://127.0.0.1:8771'
SH = f'{ROOT}/shots'
PW = 'Test-Admin-2026'      # пароль только для локальной тестовой базы
DBPW = 'test-only-local'
def sql(q):
    return subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', 'asioptik_test', '-N', '-e', q], capture_output=True, text=True).stdout.strip()
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await b.new_context(viewport={'width': 1280, 'height': 900}); pg = await ctx.new_page()
        errors = []
        pg.on('pageerror', lambda e: errors.append(str(e))); pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        await pg.goto(B + '/'); print('before install / →', pg.url.replace(B, ''))
        print('checks:', await pg.locator('.checks-list li').evaluate_all("els => els.map(e => e.className + ' ' + e.firstChild.textContent)"))
        print('local switch offered on a local address:', await pg.locator('#file_db').count(), '| MySQL fields hidden until it is unchecked:', not await pg.locator('.db-fields').is_visible())
        await pg.screenshot(path=f'{SH}/install.png', full_page=True)
        async def fill(host, name, user, dbpw, login, p1, p2):
            if await pg.locator('#file_db').count(): await pg.uncheck('#file_db')   # на тестовом стенде проверяем установку с MySQL, как на хостинге
            for k, v in dict(host=host, name=name, user=user, **{'pass': dbpw}, login=login, password=p1, password2=p2).items():
                await pg.fill(f'#{k}', v)
            await pg.locator('button[type=submit]').click(); await pg.wait_for_load_state()
        err = lambda: pg.locator('.flash-err').first.inner_text()
        await fill('127.0.0.1:3307', 'asioptik_test', 'aotest', DBPW, 'admin', 'short', 'short'); print('short password:', await err())
        await fill('127.0.0.1:3307', 'asioptik_test', 'aotest', DBPW, 'admin', PW, PW + 'x'); print('mismatch:', await err())
        await fill('127.0.0.1:3307', 'asioptik_test', 'aotest', 'wrong-db-password', 'admin', PW, PW); print('wrong db password:', (await err())[:120])
        print('  password fields empty after error:', [await pg.input_value(f'#{k}') for k in ('pass', 'password', 'password2')], '| kept:', await pg.input_value('#name'), await pg.input_value('#user'))
        await fill('127.0.0.1:3307', '', '', '', 'admin', PW, PW); print('empty db:', await err())
        print('  tables before real install:', sql('SHOW TABLES').replace('\n', ' ') or 'none', '| config exists:', (ROOT / 'site/storage/config.php').exists())
        await fill('127.0.0.1:3307', 'asioptik_test', 'aotest', DBPW, 'admin', PW, PW)
        print('install:', await pg.locator('.flash').first.inner_text(), '|', (await pg.locator('.hint').last.inner_text())[:150])
        await pg.screenshot(path=f'{SH}/install-done.png', full_page=True)
        print('tables:', sql('SHOW TABLES').replace('\n', ' '))
        print('rows:', sql("SELECT CONCAT(type, '=', COUNT(*)) FROM ao_items GROUP BY type").replace('\n', ' '), '| settings:', sql('SELECT name FROM ao_settings').replace('\n', ' '), '| users:', sql('SELECT login FROM ao_users'), '| hash:', sql('SELECT LEFT(pass_hash, 7) FROM ao_users'))
        await pg.goto(B + '/install.php'); print('again:', (await pg.inner_text('main')).replace('\n', ' ')[:160])
        r = await pg.request.post(B + '/install.php', form={'host': '127.0.0.1:3307', 'name': 'asioptik_test', 'user': 'aotest', 'pass': DBPW, 'login': 'hacker', 'password': 'hacker-pass-123', 'password2': 'hacker-pass-123'})
        print('second install attempt:', r.status, '| users:', sql('SELECT GROUP_CONCAT(login) FROM ao_users'))
        await pg.goto(B + '/'); await pg.wait_for_timeout(800); print('site after install:', pg.url.replace(B, ''), '|', await pg.title())
        # забытый пароль: удалить storage/config.php и пройти установку ещё раз — данные остаются, пароль новый
        sql("UPDATE ao_items SET data = JSON_SET(data, '$.price', 777) WHERE type='product' AND slug='f-milan'")
        (ROOT / 'site/storage/config.php').unlink(); await pg.wait_for_timeout(2600)
        await pg.goto(B + '/install.php')
        await fill('127.0.0.1:3307', 'asioptik_test', 'aotest', DBPW, 'admin', '12345678', '12345678'); print('weak password:', await err())
        await fill('127.0.0.1:3307', 'asioptik_test', 'aotest', DBPW, 'admin', 'Second-Pass-2026', 'Second-Pass-2026')
        print('reinstall:', await pg.locator('.flash').first.inner_text(), '| users:', sql('SELECT COUNT(*) FROM ao_users'), '| products:', sql("SELECT COUNT(*) FROM ao_items WHERE type='product'"), '| edited price kept:', sql("SELECT JSON_EXTRACT(data, '$.price') FROM ao_items WHERE slug='f-milan'"))
        await pg.goto(B + '/admin/'); await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click(); print('old password:', await pg.locator('.flash-err').inner_text())
        await pg.fill('#login', 'admin'); await pg.fill('#password', 'Second-Pass-2026'); await pg.locator('button[type=submit]').click(); print('new password →', pg.url.replace(B, ''), '|', await pg.inner_text('h1'))
        print('console:', [e for e in errors if 'font' not in e.lower() and 'CORS' not in e and 'ERR_' not in e] or 'none')
        await b.close()
asyncio.run(main())

"""Чистая установка сайта на тестовом сервере: пустая база, без загруженных фото, установщик запускается заново."""
import pathlib, shutil, subprocess, urllib.parse, urllib.request
ROOT = pathlib.Path(__file__).resolve().parent.parent
B = 'http://127.0.0.1:8771'
PW = 'Test-Admin-2026'      # пароль только для локальной тестовой базы
def sql(q):
    return subprocess.run(['mariadb', '--socket=/tmp/mysql-run/mysqld.sock', '-uroot', 'asioptik_test', '-N', '-e', q], capture_output=True, text=True).stdout.strip()
def reset():
    sql('DROP TABLE IF EXISTS ao_settings, ao_items, ao_orders, ao_users, ao_logins')
    for f in ('storage/config.php', 'storage/site.sqlite', 'storage/cache/site.json', 'storage/logs/php-errors.log'):
        (ROOT / 'site' / f).unlink(missing_ok=True)
    for d in (ROOT / 'site' / 'uploads').iterdir():
        if d.is_dir():
            shutil.rmtree(d)
    shutil.rmtree(ROOT / 'site' / 'storage' / 'sessions', ignore_errors=True)
    body = urllib.parse.urlencode({'host': '127.0.0.1:3307', 'name': 'asioptik_test', 'user': 'aotest', 'pass': 'test-only-local', 'login': 'admin', 'password': PW, 'password2': PW}).encode()
    html = urllib.request.urlopen(urllib.request.Request(B + '/install.php', data=body)).read().decode('utf-8')
    assert 'Готово: сайт установлен' in html, html[-600:]
    return sql("SELECT GROUP_CONCAT(CONCAT(type, '=', n) SEPARATOR ' ') FROM (SELECT type, COUNT(*) AS n FROM ao_items GROUP BY type) t")
if __name__ == '__main__':
    print('clean install:', reset())

"""Новые разделы админ-панели: «Пользователи» и роли, «Мой профиль», «Изображения», «Почта (SMTP)».

Проверяется:
- обновление базы прежней версии (у таблицы пользователей появляются столбцы, прежний пользователь — администратор);
- пользователи: добавление с проверками и подтверждением своим паролем, роли на сервере (403 на закрытые разделы,
  в том числе при отправке форм), отключение, сброс пароля и конец прежних сеансов, «Мой профиль»;
- изображения: загрузка нескольких фото, отказ не-картинкам, путь в тексте статьи → фото на сайте, отметка
  «используется», удаление только неиспользуемых, чужой путь не подставить;
- почта: настройки с проверками, пароль в базе зашифрован и на странице не показывается, проверочное письмо,
  письмо о заказе после ответа покупателю, ошибки входа, соединения и сертификата, предел писем в час.

Письма принимает учебный сервер test/smtp_sink.py — наружу ничего не уходит. Адреса и пароли в этом файле
выдуманы для стенда. Запуск: sh test/serve.sh, затем python3 test/php_panel.py (базу тест ставит заново сам).
"""
import asyncio, base64, http.client, io, json, os, pathlib, re, subprocess, sys, tempfile, time, urllib.parse, uuid
from PIL import Image
from playwright.async_api import async_playwright
from run import setup
from php_reset import reset, sql, PW

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOST, PORT = '127.0.0.1', 8771
B = f'http://{HOST}:{PORT}'
USER_PW = 'Editor-Pass-2026'        # пароли учебных пользователей стенда
SINK_USER, SINK_PW = 'sink@asioptik.test', 'Sink-Pass-2026'
fails = []
total = 0
def check(name, ok, detail=''):
    global total
    total += 1
    if not ok:
        fails.append(name)
        print('  FAIL', name, '|', str(detail)[:500])
def flashes(t):
    return [(k, re.sub(r'<[^>]+>', ' ', v).strip()) for k, v in re.findall(r'class="flash flash-(\w+)"[^>]*>(.*?)</(?:p|div)>', t, re.S)]


class Client:
    """Браузер без браузера: помнит cookie и ключ форм."""
    def __init__(self):
        self.jar = {}; self.token = ''
    def req(self, method, path, data=None, files=None, js=None, headers=None):
        h = dict(headers or {})
        if self.jar: h['Cookie'] = '; '.join(f'{k}={v}' for k, v in self.jar.items())
        body = None
        if js is not None:
            body = json.dumps(js).encode(); h['Content-Type'] = 'application/json'; h.setdefault('Origin', B)
        elif files is not None:
            bd = uuid.uuid4().hex; parts = []
            for k, v in (data or {}).items():
                parts.append(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
            for field, name, mime, content in files:
                parts.append(f'--{bd}\r\nContent-Disposition: form-data; name="{field}"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n'.encode() + content + b'\r\n')
            body = b''.join(parts) + f'--{bd}--\r\n'.encode(); h['Content-Type'] = f'multipart/form-data; boundary={bd}'
        elif data is not None:
            body = urllib.parse.urlencode(data, doseq=True).encode(); h['Content-Type'] = 'application/x-www-form-urlencoded'
        c = http.client.HTTPConnection(HOST, PORT, timeout=60)
        c.request(method, path, body=body, headers=h); r = c.getresponse(); t = r.read().decode('utf-8', 'replace'); hs = r.getheaders(); c.close()
        for k, v in hs:
            if k.lower() == 'set-cookie':
                n, _, val = v.split(';')[0].partition('=')
                if val in ('', 'deleted'): self.jar.pop(n, None)
                else: self.jar[n] = val
        m = re.search(r'name="csrf" value="([^"]+)"', t)
        if m: self.token = m.group(1)
        return r.status, {k.lower(): v for k, v in hs}, t
    def get(self, path): return self.req('GET', path)
    def post(self, path, data, files=None):
        """Форма админ-панели с ключом CSRF; после переадресации открывает страницу, куда она ведёт."""
        s, h, t = self.req('POST', path, dict(data, csrf=self.token), files)
        if s in (301, 302) and h.get('location'): s2, h2, t = self.get(h['location']); return s, h, t
        return s, h, t
    def login(self, user, pw):
        self.jar = {}; self.get('/admin/?p=login')
        s, h, t = self.req('POST', '/admin/?p=login', {'csrf': self.token, 'login': user, 'password': pw})
        if s == 302 and h.get('location', '').endswith('/admin/'): self.get('/admin/?p=profile'); return ''
        return (flashes(t) or [('', 'no message')])[0][1]
    def menu(self):
        t = self.get('/admin/')[2]
        nav = re.search(r'<nav id="adm-nav".*?</nav>', t, re.S).group(0)
        return re.findall(r'<span>([^<]+)</span>', nav), t


def image(kind='JPEG', size=(900, 600), color=(210, 225, 245)):
    b = io.BytesIO(); Image.new('RGB', size, color).save(b, kind, quality=88); return b.getvalue()


def users():
    admin = Client()
    # 1. база прежней версии: столбцов пользователей ещё нет
    sql('ALTER TABLE ao_users DROP COLUMN name, DROP COLUMN role, DROP COLUMN active, DROP COLUMN last_login')
    sql("DELETE FROM ao_settings WHERE name = 'db_version'")
    s, h, t = admin.get('/admin/?p=login')
    cols = sql("SELECT GROUP_CONCAT(column_name ORDER BY ordinal_position) FROM information_schema.columns WHERE table_schema = 'asioptik_test' AND table_name = 'ao_users'")
    check('old database: the sign-in page opens and the user columns are added', s == 200 and all(c in cols for c in ('name', 'role', 'active', 'last_login')), cols)
    check('old database: the existing user becomes an active administrator', sql("SELECT CONCAT(role, active) FROM ao_users WHERE login = 'admin'") == 'admin1')
    check('old database: version is recorded, the public site is intact', sql("SELECT value FROM ao_settings WHERE name = 'db_version'") == '2' and admin.get('/')[0] == 200)

    # 2. вход
    check('sign-in: wrong password is refused', 'Неверный логин или пароль' in admin.login('admin', 'wrong-pass-1'))
    check('sign-in: letter case of the login does not matter', admin.login('ADMIN', PW) == '')
    items, t = admin.menu()
    check('administrator menu has the new sections', all(x in items for x in ('Изображения', 'Почта (SMTP)', 'Пользователи', 'Мой профиль', 'Заказы', 'Настройки сайта')) and 'Пароль' not in items, items)
    check('menu footer names the signed-in user and the role', re.search(r'class="who">Вы вошли как <b>admin</b><span class="role">Администратор</span>', t) is not None)
    check('last sign-in time is recorded', sql("SELECT last_login IS NOT NULL FROM ao_users WHERE login = 'admin'") == '1')
    s, h, t = admin.get('/admin/?p=password')
    check('old «Пароль» address opens «Мой профиль»', s == 200 and '<h1>Мой профиль</h1>' in t)

    # 3. добавление пользователя: проверки
    n0 = sql('SELECT COUNT(*) FROM ao_users')
    add = lambda **kw: admin.post('/admin/?p=users', dict({'act': 'add', 'name': 'Имя', 'login': 'newuser', 'password': USER_PW, 'role': 'editor', 'confirm': PW}, **kw))
    for label, kw, want in (
        ('login with spaces', {'login': 'two words'}, 'Логин: от 3 до 60 знаков'), ('login too short', {'login': 'ab'}, 'Логин: от 3 до 60 знаков'),
        ('login taken, another letter case', {'login': 'Admin'}, 'уже есть'), ('short password', {'password': 'Ab1-xyz'}, 'не короче 8'),
        ('common password', {'password': 'password123'}, 'Слишком простой пароль'), ('password equal to the login', {'login': 'newuser99', 'password': 'NewUser99'}, 'Слишком простой пароль'),
        ('unknown role', {'role': 'owner'}, 'Выберите роль'), ('no confirmation', {'confirm': ''}, 'Ваш пароль указан неверно'), ('wrong confirmation', {'confirm': 'not-my-pass-1'}, 'Ваш пароль указан неверно')):
        s, h, t = add(**kw)
        check(f'add user: {label} is refused', s == 200 and any(want in f[1] for f in flashes(t)) and sql('SELECT COUNT(*) FROM ao_users') == n0, flashes(t))
    check('add user: a typo in a field does not spend a confirmation attempt', sql('SELECT COUNT(*) FROM ao_logins') == '2', sql('SELECT COUNT(*) FROM ao_logins'))
    s, h, t = admin.req('POST', '/admin/?p=users', {'act': 'add', 'name': 'X', 'login': 'nocsrf', 'password': USER_PW, 'role': 'admin', 'confirm': PW})
    check('add user: form without the CSRF key is refused', s == 400 and sql('SELECT COUNT(*) FROM ao_users') == n0, s)
    # пять неверных подтверждений — пауза
    for _ in range(3): add(confirm='guess-000')
    s, h, t = add()
    check('five wrong confirmations: even the right password waits', any('Слишком много неверных попыток' in f[1] for f in flashes(t)) and sql('SELECT COUNT(*) FROM ao_users') == n0, flashes(t))
    sql('DELETE FROM ao_logins')

    # 4. добавление
    s, h, t = add(name='Лейла <script>alert(1)</script>', login='leyla')
    check('add user: editor is added', any('добавлен' in f[1] for f in flashes(t)) and sql("SELECT CONCAT(role, active) FROM ao_users WHERE login = 'leyla'") == 'editor1', flashes(t))
    check('user name is shown as text, not as markup', '<script>alert(1)' not in t and 'Лейла &lt;script&gt;' in t)
    check('new user: «ещё не входил», own row marked «это вы»', 'ещё не входил' in t and 'это вы' in t)
    add(name='Анар', login='anar@asioptik.test', role='manager'); add(name='Второй админ', login='admin2', role='admin')
    check('add user: manager and second administrator', sql("SELECT GROUP_CONCAT(role ORDER BY id) FROM ao_users") == 'admin,editor,manager,admin')
    check('password is stored as a hash', sql("SELECT pass_hash LIKE '$2y$%' AND pass_hash NOT LIKE '%Editor-Pass%' FROM ao_users WHERE login = 'leyla'") == '1')
    ids = dict(line.split('\t') for line in sql('SELECT login, id FROM ao_users').split('\n'))

    # 5. редактор: меню и доступ
    ed = Client()
    check('editor signs in', ed.login('leyla', USER_PW) == '')
    items, t = ed.menu()
    check('editor menu: content only', all(x in items for x in ('Обзор', 'Страницы', 'Блог', 'Изображения', 'Товары', 'Бренды', 'Филиалы', 'Мой профиль'))
          and not any(x in items for x in ('Заказы', 'Клиенты', 'Настройки сайта', 'Почта (SMTP)', 'Безопасность', 'Пользователи')), items)
    check('editor overview: no orders, no customers', 'Последние заказы' not in t and 'p=orders' not in t and 'p=clients' not in t and 'class="tile' in t)
    closed = ['/admin/?p=orders', '/admin/?p=order&id=1', '/admin/?p=clients', '/admin/?p=doc&name=config', '/admin/?p=security', '/admin/?p=users', '/admin/?p=mail']
    opened = ['/admin/', '/admin/?p=pages', '/admin/?p=page&id=home', '/admin/?p=list&type=product', '/admin/?p=list&type=post', '/admin/?p=list&type=branch', '/admin/?p=banners',
              '/admin/?p=media', '/admin/?p=doc&name=about', '/admin/?p=profile']
    for u in closed:
        s, h, t = ed.get(u)
        check(f'editor: {u} is closed', s == 403 and 'нет доступа' in t and 'name="confirm"' not in t and 'ml-host' not in t, s)
    for u in opened:
        s, h, t = ed.get(u)
        check(f'editor: {u} opens', s == 200, s)
    ed.get('/admin/?p=profile')
    s, h, t = ed.post('/admin/?p=users', {'act': 'add', 'name': 'x', 'login': 'sneaky', 'password': USER_PW, 'role': 'admin', 'confirm': USER_PW})
    check('editor cannot add a user by sending the form directly', s == 403 and sql("SELECT COUNT(*) FROM ao_users WHERE login = 'sneaky'") == '0', s)
    s, h, t = ed.post('/admin/?p=users', {'act': 'save', f'u[{ids["leyla"]}][name]': 'x', f'u[{ids["leyla"]}][role]': 'admin', f'u[{ids["leyla"]}][active]': '1', 'confirm': USER_PW})
    check('editor cannot raise the own role', s == 403 and sql("SELECT role FROM ao_users WHERE login = 'leyla'") == 'editor', s)
    s, h, t = ed.post('/admin/?p=mail', {'to': 'thief@asioptik.test', 'host': '', 'port': '465', 'enc': 'ssl', 'user': '', 'pass': '', 'from': '', 'fromName': '', 'lang': 'ru'})
    check('editor cannot change the mail settings', s == 403 and sql("SELECT COUNT(*) FROM ao_settings WHERE name = 'mail'") == '0', s)
    s, h, t = ed.post('/admin/?p=doc&name=config', {'f[shopName]': 'Hacked', 'f[whatsapp]': '994501112233'})
    check('editor cannot change the site settings', s == 403 and 'Hacked' not in sql("SELECT value FROM ao_settings WHERE name = 'config'"), s)

    # 6. менеджер
    mg = Client()
    check('manager signs in with an e-mail-like login', mg.login('anar@asioptik.test', USER_PW) == '')
    items, t = mg.menu()
    check('manager menu: orders and content, no settings', all(x in items for x in ('Заказы', 'Клиенты', 'Товары', 'Изображения')) and not any(x in items for x in ('Настройки сайта', 'Почта (SMTP)', 'Безопасность', 'Пользователи')), items)
    for u in ('/admin/?p=orders', '/admin/?p=clients', '/admin/?p=list&type=product'):
        check(f'manager: {u} opens', mg.get(u)[0] == 200)
    for u in ('/admin/?p=doc&name=config', '/admin/?p=security', '/admin/?p=users', '/admin/?p=mail'):
        check(f'manager: {u} is closed', mg.get(u)[0] == 403)

    # 7. администратор меняет других
    admin.get('/admin/?p=users')
    row = lambda login, **kw: {f'u[{ids[login]}][{k}]': v for k, v in kw.items()}
    base = {'act': 'save', 'confirm': PW}
    s, h, t = admin.post('/admin/?p=users', dict(base, **row('leyla', name='Лейла', role='manager', active='1'), confirm=''))
    check('saving users without the own password is refused', any('Ваш пароль указан неверно' in f[1] for f in flashes(t)) and sql("SELECT role FROM ao_users WHERE login = 'leyla'") == 'editor', flashes(t))
    check('… and what was typed stays in the form', 'value="Лейла"' in t and re.search(r'<option value="manager" selected>', t) is not None)
    sql('DELETE FROM ao_logins')
    s, h, t = admin.post('/admin/?p=users', dict(base, **row('leyla', name='Лейла', role='manager', active='1')))
    check('role change is saved', any('Изменения сохранены' in f[1] for f in flashes(t)) and sql("SELECT CONCAT(name, role) FROM ao_users WHERE login = 'leyla'") == 'Лейлаmanager', flashes(t))
    check('the new role works at once, in the session already open', ed.get('/admin/?p=orders')[0] == 200 and ed.get('/admin/?p=users')[0] == 403)
    s, h, t = admin.post('/admin/?p=users', dict(base, **row('leyla', name='Лейла', role='manager', active='1')))
    check('saving without changes asks for nothing', any('Изменений нет' in f[1] for f in flashes(t)), flashes(t))
    s, h, t = admin.post('/admin/?p=users', dict(base, **row('leyla', name='Лейла', role='manager', active='1', password='short')))
    check('new password for a user: too short is refused', any('leyla' in f[1] and 'не короче 8' in f[1] for f in flashes(t)), flashes(t))
    s, h, t = admin.post('/admin/?p=users', dict(base, **row('leyla', name='Лейла', role='manager', active='1', password='Reset-Pass-2026')))
    check('new password for a user is saved', any('Изменения сохранены' in f[1] for f in flashes(t)), flashes(t))
    s, h, t = ed.get('/admin/?p=profile')
    check('after a password reset the old session of that user ends', s == 302 and 'p=login' in h.get('location', ''), (s, h.get('location')))
    check('… the old password no longer works, the new one does', 'Неверный логин' in ed.login('leyla', USER_PW) and ed.login('leyla', 'Reset-Pass-2026') == '')
    sql('DELETE FROM ao_logins')
    # отключение
    s, h, t = admin.post('/admin/?p=users', dict(base, **row('leyla', name='Лейла', role='manager')))   # галочка «Активен» снята
    check('user is switched off', sql("SELECT active FROM ao_users WHERE login = 'leyla'") == '0' and '<tr class="off">' in t)
    s, h, t = ed.get('/admin/')
    check('a switched-off user is signed out at once', s == 302 and 'p=login' in h.get('location', ''), (s, h.get('location')))
    check('… and cannot sign in: told so only with the right password', 'учётная запись отключена' in ed.login('leyla', 'Reset-Pass-2026') and 'Неверный логин' in ed.login('leyla', 'wrong-pass-9'))
    sql('DELETE FROM ao_logins')
    # себя не понизить и не отключить
    s, h, t = admin.post('/admin/?p=users', dict(base, **row('admin', name='Главный', role='editor')))
    check('administrator cannot lower or switch off the own account', sql("SELECT CONCAT(name, role, active) FROM ao_users WHERE login = 'admin'") == 'Главныйadmin1', flashes(t))
    check('own row: role and «Активен» are locked, password is changed in the profile', re.search(r'<select name="u\[' + ids['admin'] + r'\]\[role\]"[^>]*disabled', t) is not None and 'В «Моём профиле»' in t)
    check('menu footer shows the new name', 'Вы вошли как <b>Главный</b>' in t)
    # несуществующая роль в базе — входа нет
    sql("UPDATE ao_users SET role = 'owner' WHERE login = 'admin2'")
    a2 = Client(); a2.login('admin2', USER_PW)
    check('a role the site does not know gives no access', a2.get('/admin/')[0] == 302)
    sql("UPDATE ao_users SET role = 'admin' WHERE login = 'admin2'")

    # 8. «Мой профиль»
    a2 = Client(); check('second administrator signs in', a2.login('admin2', USER_PW) == '')
    a2b = Client(); a2b.login('admin2', USER_PW)   # второй сеанс того же пользователя, на другом устройстве
    s, h, t = a2.post('/admin/?p=profile', {'act': 'name', 'name': '  Камран  '})
    check('profile: own name is saved', sql("SELECT name FROM ao_users WHERE login = 'admin2'") == 'Камран' and 'Вы вошли как <b>Камран</b>' in t)
    s, h, t = a2.post('/admin/?p=profile', {'act': 'pass', 'old': 'wrong-old-1', 'new': 'Fresh-Pass-2026', 'new2': 'Fresh-Pass-2026'})
    check('profile: wrong current password is refused', any('Текущий пароль указан неверно' in f[1] for f in flashes(t)), flashes(t))
    s, h, t = a2.post('/admin/?p=profile', {'act': 'pass', 'old': USER_PW, 'new': 'Fresh-Pass-2026', 'new2': 'Fresh-Pass-2027'})
    check('profile: repeat must match', any('не совпадают' in f[1] for f in flashes(t)), flashes(t))
    s, h, t = a2.post('/admin/?p=profile', {'old': USER_PW, 'new': 'Fresh-Pass-2026', 'new2': 'Fresh-Pass-2026'})
    check('profile: password is changed, this session stays', any('Пароль изменён' in f[1] for f in flashes(t)) and a2.get('/admin/?p=users')[0] == 200, flashes(t))
    check('profile: the other session of the same user ends', a2b.get('/admin/')[0] == 302)
    sql('DELETE FROM ao_logins')
    # второй администратор отключает первого — тот выходит; последний администратор остаётся
    a2.get('/admin/?p=users')
    s, h, t = a2.post('/admin/?p=users', {'act': 'save', 'confirm': 'Fresh-Pass-2026', f'u[{ids["admin"]}][name]': 'Главный', f'u[{ids["admin"]}][role]': 'admin'})
    check('one administrator can switch off another', sql("SELECT active FROM ao_users WHERE login = 'admin'") == '0' and admin.get('/admin/')[0] == 302)
    sql("UPDATE ao_users SET active = 1 WHERE login = 'admin'"); sql('DELETE FROM ao_logins')
    check('administrator signs in again', admin.login('admin', PW) == '')
    print('users:', total, 'checks')
    return admin, ids


def media(admin):
    n0 = total
    up = ROOT / 'site' / 'uploads' / 'media'
    s, h, t = admin.get('/admin/?p=media')
    check('images: the section opens, empty at first', s == 200 and 'Медиа сайта (0)' in t and 'Фото пока нет' in t)
    s, h, t = admin.post('/admin/?p=media', {'act': 'upload'}, files=[('files[]', 'salon.jpg', 'image/jpeg', image('JPEG', (2600, 1500))), ('files[]', 'logo.png', 'image/png', image('PNG', (400, 300)))])
    files = sorted(p.name for p in up.glob('*')) if up.is_dir() else []
    check('images: two photos are uploaded at once', any('Загружено фото: 2' in f[1] for f in flashes(t)) and len(files) == 2 and all(re.fullmatch(r'[a-f0-9]{16}\.(jpg|png)', f) for f in files), (flashes(t), files))
    big = next(up / f for f in files if f.endswith('.jpg'))
    check('images: a large photo is reduced to 2000 px', max(Image.open(big).size) == 2000, Image.open(big).size)
    check('images: the list shows both with paths to copy', 'Медиа сайта (2)' in t and all(f'data-copy="uploads/media/{f}"' in t for f in files) and t.count('не используется') == 2)
    # не картинки
    bad = [('files[]', 'shell.php.jpg', 'image/jpeg', b'<?php echo 1; ?>'), ('files[]', 'vector.svg', 'image/svg+xml', b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'),
           ('files[]', 'text.jpg', 'image/jpeg', b'just text, not a picture'), ('files[]', 'anim.gif', 'image/gif', image('GIF', (50, 50)))]
    s, h, t = admin.post('/admin/?p=media', {'act': 'upload'}, files=bad)
    check('images: scripts, SVG, text and GIF are refused', len(list(up.glob('*'))) == 2 and len(flashes(t)) >= 1 and t.count('Подходят только картинки JPG, PNG или WebP') == 4, flashes(t))
    check('images: nothing executable lands in uploads', not [p for p in (ROOT / 'site' / 'uploads').rglob('*') if p.is_file() and p.suffix.lower() not in ('.jpg', '.png', '.webp', '.htaccess', '.gitkeep') and p.name not in ('.htaccess', '.gitkeep')])
    s, h, t = admin.post('/admin/?p=media', {'act': 'upload'}, files=[])
    check('images: empty upload asks to choose a photo', any('Выберите хотя бы одно фото' in f[1] for f in flashes(t)), flashes(t))

    # путь в тексте статьи
    jpg, png = (f'uploads/media/{f}' for f in sorted(files, key=lambda f: f.endswith('.png')))
    post_id = sql("SELECT id FROM ao_items WHERE type = 'post' ORDER BY id LIMIT 1"); slug = sql(f'SELECT slug FROM ao_items WHERE id = {post_id}')
    s, h, t = admin.get(f'/admin/?p=edit&type=post&id={post_id}')
    form = dict(re.findall(r'<input[^>]*name="(f\[[^"]+\])"[^>]*value="([^"]*)"', t))
    for name, val in re.findall(r'<textarea[^>]*name="(f\[[^"]+\])"[^>]*>(.*?)</textarea>', t, re.S): form[name] = val
    import html as H
    form = {k: H.unescape(v) for k, v in form.items()}
    for name, sel in re.findall(r'<select[^>]*name="(f\[[^"]+\])"[^>]*>(.*?)</select>', t, re.S):
        m = re.search(r'<option value="([^"]*)" selected', sel); form[name] = H.unescape(m.group(1)) if m else ''
    for k in ('slug', 'position'):
        m = re.search(r'name="' + k + r'"[^>]*value="([^"]*)"', t)
        if m: form[k] = m.group(1)
    if re.search(r'name="active"[^>]*checked', t): form['active'] = '1'
    body0 = form['f[body][ru]']
    form['f[body][ru]'] = body0 + f'\n{jpg} Наш салон\nТекст с путём {png} внутри абзаца\n{png}\nuploads/../storage/config.php\nhttps://evil.example/x.jpg\nuploads/media/zzzzzzzzzzzzzzzz.jpg'
    s, h, t = admin.post(f'/admin/?p=edit&type=post&id={post_id}', form)
    check('article with photo paths is saved', any('Сохранено' in f[1] for f in flashes(t)), (s, flashes(t)))
    s, h, t = admin.get('/admin/?p=media')
    check('images: both photos are now marked as used in the article', t.count('не используется') == 0 and t.count('Статья: ') == 2 and 'name="act" value="delete"' not in t, re.findall(r'class="media-meta">(.*?)</p>', t))
    s, h, t = admin.post('/admin/?p=media', {'act': 'delete', 'path': jpg})
    check('images: a photo in use cannot be deleted', any('используется на сайте' in f[1] for f in flashes(t)) and (ROOT / 'site' / jpg).is_file(), flashes(t))
    for evil in ('uploads/../storage/config.php', 'storage/config.php', 'uploads/media/../../index.php', '../../../etc/passwd', 'uploads/media/.htaccess', '/etc/passwd', 'index.php'):
        s, h, t = admin.post('/admin/?p=media', {'act': 'delete', 'path': evil})
        check(f'images: delete with a foreign path {evil} does nothing', any('Такого фото уже нет' in f[1] for f in flashes(t)), flashes(t))
    check('… the site files are in place', (ROOT / 'site/storage/config.php').is_file() and (ROOT / 'site/index.php').is_file() and (ROOT / 'site/uploads/.htaccess').is_file())
    # фото товара, которое стоит ещё и в статье, при замене не удаляется (delete_upload считает упоминания)
    php = lambda code: subprocess.run(['php', '-r', "define('IN_ADMIN', true); require '" + str(ROOT / 'site/app/core/bootstrap.php') + "'; " + code], capture_output=True, text=True, cwd=str(ROOT / 'site')).stdout.strip()
    check('a photo mentioned in the article is counted', php(f"echo upload_refs('{jpg}'), '|', upload_refs('{png}'), '|', upload_refs('uploads/media/0000000000000000.jpg');") == '1|2|0', php(f"echo upload_refs('{jpg}'), '|', upload_refs('{png}');"))
    php(f"delete_upload('{png}');")
    check('a photo used in two places survives the removal from one', (ROOT / 'site' / png).is_file())
    # убираем пути из статьи — фото снова свободны и удаляются
    form['f[body][ru]'] = body0 + f'\n{jpg} Наш салон\nТекст с путём {png} внутри абзаца\nuploads/../storage/config.php\nhttps://evil.example/x.jpg\nuploads/media/zzzzzzzzzzzzzzzz.jpg'
    admin.get(f'/admin/?p=edit&type=post&id={post_id}'); admin.post(f'/admin/?p=edit&type=post&id={post_id}', form)
    s, h, t = admin.get('/admin/?p=media')
    check('images: a path inside a paragraph still counts as use', t.count('Статья: ') == 2, re.findall(r'class="media-meta">(.*?)</p>', t))
    form['f[body][ru]'] = body0 + f'\n{jpg} Наш салон\nuploads/../storage/config.php\nhttps://evil.example/x.jpg'
    admin.get(f'/admin/?p=edit&type=post&id={post_id}'); admin.post(f'/admin/?p=edit&type=post&id={post_id}', form)
    s, h, t = admin.get('/admin/?p=media')
    check('images: the photo removed from the article is free again', t.count('не используется') == 1 and t.count('name="act" value="delete"') == 1)
    s, h, t = admin.post('/admin/?p=media', {'act': 'delete', 'path': png})
    check('images: a free photo is deleted', any('Фото удалено' in f[1] for f in flashes(t)) and not (ROOT / 'site' / png).exists() and 'Медиа сайта (1)' in t, flashes(t))
    print('images:', total - n0, 'checks')
    return slug, jpg


async def media_browser(slug, jpg):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await b.new_context(viewport={'width': 1280, 'height': 900}); pg = await ctx.new_page(); errors = []
        pg.on('pageerror', lambda e: errors.append(str(e)))
        await setup(pg); await pg.route('https://images.pexels.com/**', lambda r: r.abort())
        await pg.goto(B + f'/ru/blog/{slug}'); await pg.wait_for_function('window.Shop'); await pg.wait_for_timeout(600)
        figs = await pg.evaluate("[...document.querySelectorAll('.post-body figure')].map(f => ({src: f.querySelector('img').getAttribute('src'), alt: f.querySelector('img').alt, cap: (f.querySelector('figcaption') || {}).textContent || '', w: f.querySelector('img').naturalWidth}))")
        check('site: the path line in the article is a photo with a caption', figs == [{'src': '/' + jpg, 'alt': 'Наш салон', 'cap': 'Наш салон', 'w': 2000}], figs)
        text = await pg.inner_text('.post-body')
        check('site: foreign and broken paths stay plain text', 'uploads/../storage/config.php' in text and 'https://evil.example/x.jpg' in text and await pg.locator('.post-body img').count() == 1, text[-200:])
        check('site: the photo fits the column', await pg.evaluate("(() => { const i = document.querySelector('.post-body figure img'), r = i.getBoundingClientRect(), c = document.querySelector('.post-body').getBoundingClientRect(); return r.width <= c.width + 1 && r.width > 300 })()"))
        # админ-панель в браузере: несколько фото, копирование пути
        await ctx.grant_permissions(['clipboard-read', 'clipboard-write'], origin=B)
        await pg.goto(B + '/admin/?p=login'); await pg.fill('#login', 'admin'); await pg.fill('#password', PW); await pg.locator('button[type=submit]').click(); await pg.wait_for_load_state()
        await pg.goto(B + '/admin/?p=media')
        tmp = tempfile.mkdtemp()
        for n, kind, size in (('a.jpg', 'JPEG', (3200, 2000)), ('b.png', 'PNG', (500, 500)), ('c.webp', 'WEBP', (800, 600))):
            open(os.path.join(tmp, n), 'wb').write(image(kind, size))
        open(os.path.join(tmp, 'd.txt'), 'w').write('no')
        await pg.set_input_files('#lib-files', [os.path.join(tmp, 'a.jpg'), os.path.join(tmp, 'd.txt')]); await pg.wait_for_timeout(600)
        note = await pg.locator('.lib .file-note').inner_text()
        check('browser: a non-picture among the chosen files is named at once', 'd.txt' in note and await pg.evaluate("document.getElementById('lib-files').files.length") == 0, note)
        await pg.set_input_files('#lib-files', [os.path.join(tmp, n) for n in ('a.jpg', 'b.png', 'c.webp')]); await pg.wait_for_timeout(2500)
        note = await pg.locator('.lib .file-note').inner_text()
        check('browser: three photos are prepared, the note counts them', note.startswith('Выбрано фото: 3') and await pg.evaluate("document.getElementById('lib-files').files.length") == 3, note)
        await pg.locator('.lib form button[type=submit]').first.click(); await pg.wait_for_load_state(); await pg.wait_for_timeout(400)
        check('browser: three photos are uploaded', 'Загружено фото: 3' in await pg.locator('.flash').inner_text() and await pg.locator('.media-item').count() == 4)
        first = pg.locator('.media-path').first; path = await first.get_attribute('data-copy')
        await first.click(); await pg.wait_for_timeout(300)
        check('browser: a click on the path copies it', await pg.evaluate('navigator.clipboard.readText()') == path and await first.inner_text() == 'Скопировано', await first.inner_text())
        await pg.wait_for_timeout(1900)
        check('browser: the path is shown again after a moment', (await first.inner_text()).strip() == path, await first.inner_text())
        pg.once('dialog', lambda d: asyncio.ensure_future(d.dismiss()))
        await pg.locator('.media-item.is-free form button').first.click(); await pg.wait_for_timeout(500)
        check('browser: delete asks first, «Cancel» keeps the photo', await pg.locator('.media-item').count() == 4)
        pg.once('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pg.locator('.media-item.is-free form button').first.click(); await pg.wait_for_load_state(); await pg.wait_for_timeout(400)
        check('browser: confirmed delete removes it', await pg.locator('.media-item').count() == 3 and 'Фото удалено' in await pg.locator('.flash').inner_text())
        # страницы новых разделов: в ширину экрана телефона ничего не вылезает (таблица пользователей листается внутри своей рамки)
        m = await (await b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True)).new_page()
        await m.goto(B + '/admin/?p=login'); await m.fill('#login', 'admin'); await m.fill('#password', PW); await m.locator('button[type=submit]').click(); await m.wait_for_load_state()
        for sec in ('users', 'profile', 'media', 'mail'):
            await m.goto(B + f'/admin/?p={sec}'); await m.wait_for_timeout(250)
            over = await m.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(f'phone: «{sec}» fits the screen width', over <= 1, over)
        await m.locator('.menu-btn').click(); await m.wait_for_timeout(200)
        check('phone: the open menu shows who is signed in', await m.locator('.who').is_visible() and 'Вы вошли как' in await m.locator('.who').inner_text())
        check('no script errors in the browser', not errors, errors[:3])
        await b.close()


def certs(d):
    """Учебный удостоверяющий центр и сертификат сервера localhost — только для стенда."""
    run = lambda *a: subprocess.run(a, check=True, capture_output=True, cwd=d)
    run('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'ca.key', '-out', 'ca.pem', '-days', '2', '-subj', '/CN=Asioptik Test CA')
    run('openssl', 'req', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'srv.key', '-out', 'srv.csr', '-subj', '/CN=localhost')
    open(os.path.join(d, 'ext.cnf'), 'w').write('subjectAltName=DNS:localhost,IP:127.0.0.1\n')
    run('openssl', 'x509', '-req', '-in', 'srv.csr', '-CA', 'ca.pem', '-CAkey', 'ca.key', '-CAcreateserial', '-out', 'srv.pem', '-days', '2', '-extfile', 'ext.cnf')


def mail(admin):
    n0 = total
    d = tempfile.mkdtemp(); certs(d)
    box = lambda name: json.load(open(os.path.join(d, name), encoding='utf-8'))
    sinks = []
    def sink(port, name, mode='plain'):
        args = [sys.executable, str(ROOT / 'test' / 'smtp_sink.py'), str(port), os.path.join(d, name)] + ([mode, os.path.join(d, 'srv.pem'), os.path.join(d, 'srv.key')] if mode != 'plain' else [])
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT); sinks.append(p); p.stdout.readline(); return p
    try:
        sink(2525, 'plain.json'); sink(465, 'tls.json', 'tls'); sink(587, 'starttls.json', 'starttls')
        form = {'to': 'orders@asioptik.test, owner@asioptik.test', 'host': '127.0.0.1', 'port': '2525', 'enc': 'none', 'user': SINK_USER, 'pass': SINK_PW, 'from': '', 'fromName': 'Оптика «Asioptik»', 'lang': 'ru'}
        s, h, t = admin.get('/admin/?p=mail')
        check('mail: the section opens, nothing is sent yet', s == 200 and 'письма не отправляются' in t and 'Последняя отправка' not in t)
        # заказ без настроек почты: письма нет, ответ обычный
        tok = re.search(r'"apiToken":"([^"]+)"', admin.get('/')[2]).group(1)
        order = lambda **kw: Client().req('POST', '/api/order', js=dict({'kind': 'order', 'lang': 'ru', 'token': tok, 'name': 'Айдан Покупатель', 'phone': '+994 50 111 22 33', 'total': 120,
                                                                         'text': 'Здравствуйте! Заказ с сайта.\n\n1. Оправа «Милан» — 1 шт. — 120 ₼\n.строка с точки в начале\n\nИтого: 120 ₼', 'details': {}}, **kw))
        s, h, t = order(number='OP-2411-1001')
        check('order without mail settings: accepted as before', s == 200 and json.loads(t) == {'ok': True, 'number': 'OP-2411-1001'} and box('plain.json') == [], t)
        # проверки формы
        for label, kw, want in (('address without @', {'to': 'orders.asioptik.test'}, 'Проверьте адрес'), ('one bad address among good ones', {'to': 'a@asioptik.test, b@@x'}, 'Проверьте адрес'),
                                ('server with https://', {'host': 'https://mail.asioptik.test'}, 'Имя сервера'), ('server with a path', {'host': 'mail.asioptik.test/x'}, 'Имя сервера'),
                                ('unusual port', {'port': '8080'}, 'Порт — 465'), ('port with letters', {'port': '46a'}, 'Порт — 465'), ('sender without a domain', {'from': 'shop@'}, 'Адрес отправителя'),
                                ('password over a plain connection to a remote server', {'host': 'mail.asioptik.test'}, 'Без шифрования пароль не отправляется')):
            s, h, t = admin.post('/admin/?p=mail', dict(form, **kw))
            check(f'mail settings: {label} is refused', s == 200 and want in t and sql("SELECT COUNT(*) FROM ao_settings WHERE name = 'mail'") == '0', re.findall(r'class="err">(.*?)</p>', t))
        check('… and the typed password is not echoed back', SINK_PW not in t)
        s, h, t = admin.post('/admin/?p=mail', form)
        stored = json.loads(sql("SELECT value FROM ao_settings WHERE name = 'mail'"))
        check('mail settings are saved', any('Сохранено' in f[1] for f in flashes(t)) and 'сейчас: SMTP' in t and stored['to'] == 'orders@asioptik.test, owner@asioptik.test' and stored['port'] == 2525, flashes(t))
        check('the mail password is encrypted in the database', stored['pass'].startswith('g1:') and SINK_PW not in json.dumps(stored) and base64.b64encode(SINK_PW.encode()).decode() not in stored['pass'], stored['pass'][:12])
        check('… and is never shown on the page', SINK_PW not in t and 'сохранён — оставьте пустым' in t and re.search(r'name="pass" value=""', t) is not None)
        check('the admin address for links in letters is the one the administrator uses', stored['adminUrl'] == B + '/admin/', stored.get('adminUrl'))
        check('the public pages and their cache know nothing about the mail settings', SINK_USER not in admin.get('/')[2] and SINK_USER not in (ROOT / 'site/storage/cache/site.json').read_text(encoding='utf-8'))
        # проверочное письмо
        s, h, t = admin.post('/admin/?p=mail', {'act': 'test', 'to': 'not an address'})
        check('test letter: an address is required', any('Впишите адрес' in f[1] for f in flashes(t)) and box('plain.json') == [], flashes(t))
        s, h, t = admin.post('/admin/?p=mail', {'act': 'test', 'to': 'check@asioptik.test'})
        m = box('plain.json')
        check('test letter is sent and received', any('Письмо отправлено на check@asioptik.test' in f[1] for f in flashes(t)) and len(m) == 1 and m[0]['to'] == ['check@asioptik.test'] and m[0]['authed'], (flashes(t), m))
        check('test letter: subject, sender and text arrive readable', m[0]['subject'] == 'Проверка почты — Asioptik' and m[0]['from'] == SINK_USER and m[0]['from_header'] == f'Оптика «Asioptik» <{SINK_USER}>'
              and 'проверочное письмо с сайта' in m[0]['body'], (m[0]['subject'], m[0]['from_header']))
        hd = m[0]['headers']
        check('letter headers follow the mail rules', hd.get('MIME-Version') == '1.0' and hd.get('Content-Type') == 'text/plain; charset=UTF-8' and hd.get('Content-Transfer-Encoding') == 'base64'
              and re.fullmatch(r'<[a-f0-9]{24}@asioptik\.test>', hd.get('Message-ID', '')) and 'Date' in hd and m[0]['longest_line'] <= 78 and hd.get('Auto-Submitted') == 'auto-generated', hd)
        check('the section reports the last sending', 'Последняя отправка' in t and 'проверочное письмо. Письмо ушло.' in t)
        # пустое поле пароля прежний пароль не стирает
        s, h, t = admin.post('/admin/?p=mail', dict(form, **{'pass': '', 'fromName': 'Asioptik'}))
        admin.post('/admin/?p=mail', {'act': 'test', 'to': 'check@asioptik.test'})
        check('empty password field keeps the saved password', len(box('plain.json')) == 2 and box('plain.json')[1]['authed'] and box('plain.json')[1]['from_header'] == f'"Asioptik" <{SINK_USER}>', box('plain.json')[-1]['from_header'])

        # письмо о заказе
        t0 = time.time(); s, h, t = order(number='OP-2411-1002'); dt = time.time() - t0
        check('order with mail on: the buyer gets the same answer at once', s == 200 and json.loads(t) == {'ok': True, 'number': 'OP-2411-1002'} and dt < 2 and h.get('content-length') == str(len(t.encode())), (s, t, dt))
        for _ in range(30):
            if len(box('plain.json')) >= 3: break
            time.sleep(0.2)
        m = box('plain.json')[-1]; oid = sql("SELECT id FROM ao_orders WHERE number = 'OP-2411-1002'")
        check('order letter goes to both addresses', len(box('plain.json')) == 3 and m['to'] == ['orders@asioptik.test', 'owner@asioptik.test'] and m['to_header'] == 'orders@asioptik.test, owner@asioptik.test', m['to'])
        check('order letter: subject and text', m['subject'] == 'Asioptik: новый заказ OP-2411-1002' and all(x in m['body'] for x in ('Новый заказ OP-2411-1002', 'Имя: Айдан Покупатель', 'Телефон: +994 50 111 22 33', 'Сумма: 120 ₼',
              'Оправа «Милан» — 1 шт.', '\n.строка с точки в начале', f'Открыть в админ-панели: {B}/admin/?p=order&id={oid}')), (m['subject'], m['body']))
        # в заголовки письма ничего подставить нельзя
        s, h, t = order(number='OP-2411-1003', name='Злой\r\nBcc: thief@evil.example\r\nSubject: взлом', kind='repair', text='Ремонт\r\n.\r\nMAIL FROM:<x@evil.example>')
        for _ in range(30):
            if len(box('plain.json')) >= 4: break
            time.sleep(0.2)
        m = box('plain.json')[-1]
        check('order letter: line breaks in the name cannot add headers or recipients', len(box('plain.json')) == 4 and 'Bcc' not in m['headers'] and m['to'] == ['orders@asioptik.test', 'owner@asioptik.test']
              and m['subject'] == 'Asioptik: заявка на ремонт OP-2411-1003' and 'thief@evil.example' in m['body'], (m['headers'].keys(), m['to'], m['subject']))
        check('order letter: a lone dot in the text does not cut the letter', 'MAIL FROM:<x@evil.example>' in m['body'] and 'Письмо отправил сайт' in m['body'])
        # адрес в письме берётся из настроек, а не из запроса покупателя
        s, h, t = Client().req('POST', '/api/order', js={'kind': 'message', 'lang': 'ru', 'token': tok, 'name': 'Хост', 'phone': '+994501112233', 'text': 'Вопрос', 'number': 'M-2411-1004', 'details': {}}, headers={'Host': 'evil.example', 'Origin': 'http://evil.example'})
        time.sleep(1.2); m = box('plain.json')[-1]
        check('order letter: a forged Host header does not get into the link', 'evil.example' not in m['body'] and (m['subject'] != 'Asioptik: сообщение с сайта M-2411-1004' or f'{B}/admin/?p=order' in m['body']), (s, m['subject']))
        # язык писем
        admin.get('/admin/?p=mail'); admin.post('/admin/?p=mail', dict(form, **{'pass': '', 'lang': 'az', 'to': 'orders@asioptik.test'}))
        n = len(box('plain.json')); order(number='OP-2411-1005')
        for _ in range(30):
            if len(box('plain.json')) > n: break
            time.sleep(0.2)
        m = box('plain.json')[-1]
        check('letters in Azerbaijani when chosen', m['subject'] == 'Asioptik: yeni sifariş OP-2411-1005' and 'Ad: Айдан Покупатель' in m['body'] and 'Admin paneldə aç' in m['body'], m['subject'])
        # предел писем в час
        st = json.loads(sql("SELECT value FROM ao_settings WHERE name = 'mail_state'")); st['n'] = 60
        sql("UPDATE ao_settings SET value = '" + json.dumps(st, ensure_ascii=False).replace("'", "''").replace('\\', '\\\\') + "' WHERE name = 'mail_state'")
        n = len(box('plain.json')); s, h, t = order(number='OP-2411-1006'); time.sleep(1.2)
        check('no more than 60 order letters an hour; the order itself is kept', len(box('plain.json')) == n and s == 200 and sql("SELECT COUNT(*) FROM ao_orders WHERE number = 'OP-2411-1006'") == '1')
        sql("DELETE FROM ao_settings WHERE name = 'mail_state'")
        # адрес убран — писем нет
        admin.get('/admin/?p=mail'); s, h, t = admin.post('/admin/?p=mail', dict(form, **{'pass': '', 'to': ''}))
        n = len(box('plain.json')); order(number='OP-2411-1007'); time.sleep(1.0)
        check('no address — no letters', 'Адрес для заявок не указан' in ' '.join(f[1] for f in flashes(t)) and 'письма не отправляются' in t and len(box('plain.json')) == n)

        # ошибки: пароль, соединение, сертификат
        admin.get('/admin/?p=mail'); admin.post('/admin/?p=mail', dict(form, **{'pass': 'Wrong-Sink-Pass-1'}))
        s, h, t = admin.post('/admin/?p=mail', {'act': 'test', 'to': 'check@asioptik.test'})
        check('wrong mail password: clear reason, nothing sent', any(f[0] == 'err' and 'Сервер не принял имя пользователя или пароль' in f[1] for f in flashes(t)) and 'Wrong-Sink-Pass-1' not in t
              and base64.b64encode(b'Wrong-Sink-Pass-1').decode() not in t and 'Письмо не ушло' in t, flashes(t))
        admin.post('/admin/?p=mail', dict(form, **{'port': '25', 'user': '', 'pass': ''}))
        s, h, t = admin.post('/admin/?p=mail', {'act': 'test', 'to': 'check@asioptik.test'})
        check('no server on the port: «не удалось подключиться»', any(f[0] == 'err' and 'Не удалось подключиться к 127.0.0.1:25' in f[1] for f in flashes(t)), flashes(t))
        admin.post('/admin/?p=mail', dict(form, **{'host': 'localhost', 'port': '2525', 'user': '', 'pass': ''}))
        s, h, t = admin.post('/admin/?p=mail', {'act': 'test', 'to': 'nobody@reject.test'})
        check('recipient refused by the server: its answer is shown', any(f[0] == 'err' and 'Ответ почтового сервера' in f[1] and '550' in f[1] for f in flashes(t)), flashes(t))
        for port, enc, label in (('465', 'ssl', 'SSL/TLS'), ('587', 'tls', 'STARTTLS')):
            admin.post('/admin/?p=mail', dict(form, **{'host': 'localhost', 'port': port, 'enc': enc}))
            s, h, t = admin.post('/admin/?p=mail', {'act': 'test', 'to': 'check@asioptik.test'})
            check(f'{label}: a certificate the server cannot verify stops the sending', any(f[0] == 'err' and 'сертификат сервера не подходит' in f[1] for f in flashes(t)) and box('tls.json') == [] and box('starttls.json') == [], flashes(t))
        # с доверенным сертификатом оба вида шифрования проходят (проверка самой функции, вне сайта)
        harness = os.path.join(d, 'h.php')
        open(harness, 'w', encoding='utf-8').write("""<?php
function config() { return ['secret' => 'cli-test-secret']; }
function host_key($h) { return strtolower($h); }
function site_origin_url() { return 'https://asioptik.test'; }
require $argv[1];
$c = ['host' => 'localhost', 'port' => (int) $argv[2], 'enc' => $argv[3], 'user' => $argv[4], 'pass' => $argv[5], 'fromName' => 'Тест', 'from' => '', 'to' => ''];
$m = mail_build('sink@asioptik.test', 'Тест', ['a@asioptik.test'], 'Тема ' . $argv[3], "Строка\\n.точка\\n");
$err = null; $ok = smtp_send($c, 'sink@asioptik.test', ['a@asioptik.test'], $m['data'], $err, 5);
$s = secret_seal('p@ss ворд');
echo json_encode(['ok' => $ok, 'err' => $err, 'round' => secret_open($s) === 'p@ss ворд', 'sealed' => $s, 'again' => secret_seal('p@ss ворд') !== $s,
    'tamper' => secret_open(substr($s, 0, 20) . ($s[20] === 'A' ? 'B' : 'A') . substr($s, 21)), 'empty' => secret_seal('') . secret_open('') . secret_open('junk')]);
""")
        cli = lambda port, enc, user=SINK_USER, pw=SINK_PW, ca=True: json.loads(subprocess.run(['php'] + (['-d', 'openssl.cafile=' + os.path.join(d, 'ca.pem')] if ca else []) + [harness, str(ROOT / 'site/app/core/mail.php'), str(port), enc, user, pw], capture_output=True, text=True).stdout or '{}')
        r = cli(465, 'ssl'); m = box('tls.json')
        check('SSL/TLS with a trusted certificate: the letter goes through, encrypted and signed in', r.get('ok') is True and len(m) == 1 and m[0]['secure'] and m[0]['authed'] and m[0]['subject'] == 'Тема ssl' and m[0]['body'] == 'Строка\r\n.точка\r\n', (r, m))
        r = cli(587, 'tls'); m = box('starttls.json')
        check('STARTTLS with a trusted certificate: the letter goes through, the password travels only after encryption', r.get('ok') is True and len(m) == 1 and m[0]['secure'] and m[0]['authed'], (r, m))
        r2 = cli(465, 'ssl', ca=False)
        check('the same server without the trusted certificate is refused', r2.get('ok') is False and str(r2.get('err', '')).startswith('certificate'), r2)
        r3 = cli(587, 'tls', pw='Wrong-Pass-000')
        check('wrong password over STARTTLS: refused, the password is not in the reason', r3.get('ok') is False and r3['err'].startswith('AUTH') and 'Wrong-Pass-000' not in r3['err'] and base64.b64encode(b'Wrong-Pass-000').decode() not in r3['err'], r3)
        check('password sealing: opens back, differs each time, breaks when altered, empty stays empty', r['round'] and r['sealed'].startswith('g1:') and r['again'] and r['tamper'] == '' and r['empty'] == '', r)
        r4 = cli(2525, 'none')
        check('plain connection to this very machine is allowed with a password', r4.get('ok') is True, r4)
    finally:
        for p in sinks: p.kill()
    print('mail:', total - n0, 'checks')


async def main():
    print('clean install:', reset())
    admin, ids = users()
    slug, jpg = media(admin)
    await media_browser(slug, jpg)
    mail(admin)
    log = ROOT / 'site/storage/logs/php-errors.log'
    errs = [l for l in (log.read_text(encoding='utf-8', errors='replace').split('\n') if log.exists() else []) if l.strip() and 'order mail' not in l]
    check('no PHP errors in the log', not errs, errs[:3])
    print(f'\n{total - len(fails)} of {total} checks passed')
    if fails:
        print('FAILED:', len(fails)); sys.exit(1)

asyncio.run(main())

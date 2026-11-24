"""Браузер без браузера для проверок админ-панели: помнит cookie и ключ форм (CSRF).

    from php_client import Client, flashes, admin_client
"""
import http.client, json, re, urllib.parse, uuid
from php_reset import PW

HOST, PORT = '127.0.0.1', 8771
B = f'http://{HOST}:{PORT}'

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


def admin_client():
    """Клиент, вошедший учебным администратором стенда."""
    c = Client()
    err = c.login('admin', PW)
    assert err == '', err
    return c

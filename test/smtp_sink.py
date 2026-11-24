"""Учебный почтовый сервер для проверок: принимает письма и складывает их в файл, наружу ничего не отправляет.

    python3 test/smtp_sink.py ПОРТ ФАЙЛ.json [tls|starttls] [cert.pem key.pem]

Понимает EHLO, STARTTLS, AUTH LOGIN и AUTH PLAIN (пользователь sink@asioptik.test, пароль Sink-Pass-2026 — значения
только для этого стенда), MAIL, RCPT, DATA, QUIT. Адресу на @reject.test отвечает отказом. Каждое принятое письмо
дописывается в ФАЙЛ.json: кто, кому, заголовки, текст, был ли вход и шифрование.
"""
import base64, email, email.header, json, socket, ssl, sys, threading

USER, PASSWORD = 'sink@asioptik.test', 'Sink-Pass-2026'

def handle(conn, out, mode, ctx):
    secure = mode == 'tls'
    f = conn.makefile('rwb', buffering=0)
    def say(s): f.write((s + '\r\n').encode())
    def line():
        b = f.readline()
        return b.decode('utf-8', 'replace').rstrip('\r\n') if b else None
    authed = False; frm = ''; rcpt = []
    try:
        say('220 sink.asioptik.test ESMTP')
        while True:
            l = line()
            if l is None: break
            u = l.upper()
            if u.startswith('EHLO') or u.startswith('HELO'):
                say('250-sink.asioptik.test'); say('250-SIZE 10485760')
                if mode == 'starttls' and not secure: say('250-STARTTLS')
                say('250 AUTH LOGIN PLAIN')
            elif u == 'STARTTLS' and mode == 'starttls' and not secure:
                say('220 go ahead')
                conn = ctx.wrap_socket(conn, server_side=True); f = conn.makefile('rwb', buffering=0); secure = True
            elif u == 'AUTH LOGIN':
                say('334 VXNlcm5hbWU6'); user = base64.b64decode(line() or '').decode('utf-8', 'replace')
                say('334 UGFzc3dvcmQ6'); pw = base64.b64decode(line() or '').decode('utf-8', 'replace')
                authed = (user, pw) == (USER, PASSWORD)
                say('235 2.7.0 accepted' if authed else '535 5.7.8 authentication failed')
            elif u.startswith('AUTH PLAIN'):
                parts = base64.b64decode(l[11:] or '').decode('utf-8', 'replace').split('\0')
                authed = parts[-2:] == [USER, PASSWORD]
                say('235 2.7.0 accepted' if authed else '535 5.7.8 authentication failed')
            elif u.startswith('MAIL FROM:'):
                frm = l[10:].strip().strip('<>'); rcpt = []; say('250 ok')
            elif u.startswith('RCPT TO:'):
                a = l[8:].strip().strip('<>')
                if a.endswith('@reject.test'): say('550 5.1.1 no such user')
                else: rcpt.append(a); say('250 ok')
            elif u == 'DATA':
                say('354 end with .')
                raw = []
                while True:
                    d = line()
                    if d is None or d == '.': break
                    raw.append(d[1:] if d.startswith('..') else d)
                text = '\r\n'.join(raw)
                msg = email.message_from_string(text)
                def dec(v): return str(email.header.make_header(email.header.decode_header(v or '')))
                body = msg.get_payload(decode=True)
                rec = {'from': frm, 'to': rcpt, 'authed': authed, 'secure': secure, 'subject': dec(msg['Subject']), 'from_header': dec(msg['From']), 'to_header': msg['To'],
                       'headers': {k: v for k, v in msg.items()}, 'body': (body or b'').decode('utf-8', 'replace'), 'raw_lines': len(raw), 'longest_line': max([len(x) for x in raw] or [0])}
                with LOCK:
                    try: all_ = json.load(open(out, encoding='utf-8'))
                    except Exception: all_ = []
                    all_.append(rec); json.dump(all_, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                say('250 queued')
            elif u == 'QUIT':
                say('221 bye'); break
            else:
                say('502 not implemented')
    except Exception:
        pass
    finally:
        try: conn.close()
        except Exception: pass

LOCK = threading.Lock()
def main():
    port, out = int(sys.argv[1]), sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else 'plain'
    ctx = None
    if mode in ('tls', 'starttls'):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(sys.argv[4], sys.argv[5])
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); srv.bind(('127.0.0.1', port)); srv.listen(20)
    json.dump([], open(out, 'w'))
    print('smtp sink on', port, mode, flush=True)
    while True:
        conn, _ = srv.accept()
        if mode == 'tls':
            try: conn = ctx.wrap_socket(conn, server_side=True)
            except Exception: conn.close(); continue
        threading.Thread(target=handle, args=(conn, out, mode, ctx), daemon=True).start()
main()

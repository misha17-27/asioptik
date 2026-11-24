<?php
/* Почта: письмо о каждом новом заказе, заявке на ремонт и сообщении с сайта — на адрес из раздела «Почта (SMTP)».
   Отправка идёт через SMTP-сервер из настроек, а пока он не задан — средствами самого хостинга (функция mail).
   Сторонних библиотек нет: почтовый разговор с сервером ведёт smtp_send() ниже. */
declare(strict_types=1);

const MAIL_ADDR = '~^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9.\-]{0,251}[A-Za-z0-9])?\.[A-Za-z]{2,24}$~';
const MAIL_PORTS = [465, 587, 25, 2525];   // обычные почтовые порты; к другим сайт не подключается
const MAIL_PER_HOUR = 60;                  // не больше стольких писем о заказах в час: защита ящика от наплыва

/* ---------- хранение пароля от почты ---------- */
/** Шифрует пароль ключом сайта (storage/config.php): в базе и в её копиях пароль не лежит открытым текстом. */
function secret_seal(string $plain): string
{
    if ($plain === '') return '';
    if (function_exists('openssl_encrypt')) {
        $iv = random_bytes(12);
        $tag = '';
        $c = openssl_encrypt($plain, 'aes-256-gcm', secret_key(), OPENSSL_RAW_DATA, $iv, $tag);
        if (is_string($c) && strlen((string) $tag) === 16) return 'g1:' . base64_encode($iv . $tag . $c);
    }
    return 'p0:' . base64_encode($plain);   // без модуля OpenSSL зашифровать нечем (и SMTP с шифрованием тоже не заработает)
}

function secret_open(string $sealed): string
{
    if (strncmp($sealed, 'g1:', 3) === 0 && function_exists('openssl_decrypt')) {
        $raw = base64_decode(substr($sealed, 3), true);
        if ($raw === false || strlen($raw) < 29) return '';
        $p = openssl_decrypt(substr($raw, 28), 'aes-256-gcm', secret_key(), OPENSSL_RAW_DATA, substr($raw, 0, 12), substr($raw, 12, 16));
        return is_string($p) ? $p : '';   // ключ сайта сменился (сайт ставили заново) — пароль нужно ввести ещё раз
    }
    if (strncmp($sealed, 'p0:', 3) === 0) return (string) base64_decode(substr($sealed, 3), true);
    return '';
}

function secret_key(): string
{
    return hash('sha256', 'mail|' . (string) (config()['secret'] ?? ''), true);
}

/* ---------- настройки ---------- */
/** Настройки почты из раздела «Почта (SMTP)», с расшифрованным паролем. */
function mail_cfg(): array
{
    $m = setting('mail', []);
    $m = is_array($m) ? $m : [];
    $s = function (string $k) use ($m): string {
        return is_string($m[$k] ?? null) ? $m[$k] : '';
    };
    return [
        'to' => $s('to'), 'host' => $s('host'), 'port' => in_array((int) ($m['port'] ?? 0), MAIL_PORTS, true) ? (int) $m['port'] : 465,
        'enc' => in_array($s('enc'), ['ssl', 'tls', 'none'], true) ? $s('enc') : 'ssl',
        'user' => $s('user'), 'pass' => secret_open($s('pass')), 'from' => $s('from'), 'fromName' => $s('fromName'),
        'lang' => in_array($s('lang'), ['ru', 'az', 'en'], true) ? $s('lang') : 'ru', 'adminUrl' => $s('adminUrl'),
    ];
}

/** Адреса получателей из строки «a@b.az, c@d.az»: только правильные, не больше трёх. */
function mail_list(string $s): array
{
    $out = [];
    foreach (preg_split('~[,;\s]+~', $s, -1, PREG_SPLIT_NO_EMPTY) ?: [] as $a) {
        if (preg_match(MAIL_ADDR, $a) && !in_array(strtolower($a), array_map('strtolower', $out), true)) $out[] = $a;
    }
    return array_slice($out, 0, 3);
}

/** Чем сейчас отправляется почта: 'smtp', 'mail' (сам хостинг) или '' — отправить нечем. */
function mail_mode(array $c): string
{
    if ($c['host'] !== '') return 'smtp';
    return function_exists('mail') ? 'mail' : '';
}

/** Адрес отправителя: из настроек; если он пуст — пользователь SMTP, если это адрес; иначе noreply@домен сайта. */
function mail_from(array $c): string
{
    foreach ([$c['from'], $c['user']] as $a) {
        if (preg_match(MAIL_ADDR, $a)) return $a;
    }
    $host = host_key((string) parse_url(site_origin_url(), PHP_URL_HOST));
    return 'noreply@' . (preg_match('~^[a-z0-9.\-]+\.[a-z]{2,24}$~', $host) ? $host : 'localhost.localdomain');
}

/* ---------- письмо ---------- */
/** Значение для заголовка письма: без переводов строки (иначе в письмо можно подставить свои заголовки). */
function mail_line(string $s, int $max = 200): string
{
    return mb_substr(trim((string) preg_replace('/[\x00-\x1F\x7F]+/u', ' ', $s)), 0, $max);
}

/** Текст заголовка с буквами не из латиницы — в виде, понятном почтовым программам. */
function mail_word(string $s, int $indent = 0): string
{
    if (!preg_match('/[^\x20-\x7E]/', $s)) return $s;
    return function_exists('mb_encode_mimeheader') ? mb_encode_mimeheader($s, 'UTF-8', 'B', "\r\n", $indent) : '=?UTF-8?B?' . base64_encode($s) . '?=';
}

/** Готовое письмо: заголовки и текст. Текст письма обычный, без разметки. */
function mail_build(string $from, string $fromName, array $to, string $subject, string $body, bool $forMailFn = false): array
{
    $fromName = mail_line($fromName, 80);
    $subject = mail_line($subject, 180);
    $name = $fromName === '' ? '' : (preg_match('/[^\x20-\x7E]/', $fromName) ? mail_word($fromName, 6) : '"' . addcslashes($fromName, '"\\') . '"');
    $domain = substr((string) strrchr($from, '@'), 1);
    $head = [
        'Date: ' . date('r'),
        'From: ' . ($name !== '' ? $name . ' <' . $from . '>' : $from),
        'Message-ID: <' . bin2hex(random_bytes(12)) . '@' . $domain . '>',
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: base64',
        'Auto-Submitted: auto-generated',
    ];
    $text = rtrim(chunk_split(base64_encode((string) preg_replace('~\r\n?|\n~', "\r\n", $body)), 76, "\r\n"));
    if ($forMailFn) return ['headers' => implode("\r\n", $head), 'subject' => mail_word($subject, 9), 'body' => $text];
    array_splice($head, 2, 0, ['To: ' . implode(', ', $to), 'Subject: ' . mail_word($subject, 9)]);
    return ['data' => implode("\r\n", $head) . "\r\n\r\n" . $text . "\r\n"];
}

/**
 * Отправляет письмо по настройкам $c (mail_cfg()). $to — список адресов. Возвращает true, а при неудаче — false
 * и причину в $error (её видит только администратор; пароля в ней не бывает). $patient — отправка из админ-панели,
 * где можно подождать ответа сервера подольше; письмо о заказе долго не ждёт.
 */
function mail_send(array $c, array $to, string $subject, string $body, ?string &$error = null, bool $patient = false): bool
{
    $error = null;
    $to = array_values(array_filter($to, function ($a) {
        return is_string($a) && preg_match(MAIL_ADDR, $a);
    }));
    if (!$to) {
        $error = 'no recipient';
        return false;
    }
    $from = mail_from($c);
    $mode = mail_mode($c);
    if ($mode === 'smtp') {
        $m = mail_build($from, $c['fromName'], $to, $subject, $body);
        return smtp_send($c, $from, $to, $m['data'], $error, $patient ? 12 : 6);
    }
    if ($mode === 'mail') {
        $m = mail_build($from, $c['fromName'], $to, $subject, $body, true);
        $ok = @mail(implode(', ', $to), $m['subject'], $m['body'], $m['headers'], '-f' . $from);
        if (!$ok) $error = 'mail() returned false';
        return $ok;
    }
    $error = 'no transport';
    return false;
}

/**
 * Разговор с почтовым сервером: приветствие, шифрование, вход, письмо.
 * Сертификат сервера проверяется; без шифрования пароль передаётся только серверу на этой же машине.
 */
function smtp_send(array $c, string $from, array $to, string $data, ?string &$error = null, int $wait = 8): bool
{
    $error = null;
    $host = (string) $c['host'];
    $port = (int) $c['port'];
    $enc = (string) $c['enc'];
    if (!preg_match('~^[A-Za-z0-9](?:[A-Za-z0-9.\-]{0,251}[A-Za-z0-9])?$~', $host) || !in_array($port, MAIL_PORTS, true)) {
        $error = 'bad server settings';
        return false;
    }
    if ($enc !== 'none' && !extension_loaded('openssl')) {
        $error = 'no openssl';
        return false;
    }
    $local = in_array(strtolower($host), ['localhost', '127.0.0.1'], true);
    if ($enc === 'none' && $c['user'] !== '' && !$local) {
        $error = 'no password without encryption';
        return false;
    }
    $ctx = stream_context_create(['ssl' => ['verify_peer' => true, 'verify_peer_name' => true, 'peer_name' => $host, 'SNI_enabled' => true]]);
    // Предупреждения PHP на время соединения собираются сюда: по ним видно, что подвёл именно сертификат сервера
    $notes = [];
    $listen = function (int $no, string $msg) use (&$notes): bool {
        $notes[] = $msg;
        return true;
    };
    $certFault = function () use (&$notes): bool {
        return (bool) preg_match('~certificate|peer name|did not match|CN=~i', implode(' | ', $notes));
    };
    set_error_handler($listen);
    $fp = stream_socket_client(($enc === 'ssl' ? 'ssl://' : 'tcp://') . $host . ':' . $port, $errno, $errstr, $wait, STREAM_CLIENT_CONNECT, $ctx);
    restore_error_handler();
    if (!$fp) {
        $error = ($certFault() ? 'certificate: ' : 'connect: ') . mail_line((string) $errstr !== '' ? (string) $errstr : implode(' | ', $notes), 160);
        return false;
    }
    stream_set_timeout($fp, $wait);
    $read = function () use ($fp): array {
        $text = '';
        while (($line = fgets($fp, 2048)) !== false) {
            $text .= $line;
            if (strlen($line) < 4 || $line[3] !== '-' || strlen($text) > 16384) break;   // «250-…» — ответ продолжается, «250 …» — последняя строка
        }
        return [(int) substr($text, 0, 3), mail_line($text, 1000)];
    };
    $say = function (string $line, array $want, string $shown = '') use ($fp, $read, &$error): string {
        if ($line !== '') fwrite($fp, $line . "\r\n");
        [$code, $text] = $read();
        if (in_array($code, $want, true)) return $text === '' ? ' ' : $text;
        // в причину попадает команда без секретов ($shown) и ответ сервера
        $error = ($shown !== '' ? $shown : ($line !== '' ? strtok($line, ' ') : 'greeting')) . ': ' . ($text !== '' ? $text : 'no answer');
        return '';
    };
    $me = host_key((string) parse_url(site_origin_url(), PHP_URL_HOST));
    $me = preg_match('~^[a-z0-9.\-]+$~', $me) && $me !== '' ? $me : 'localhost';
    $ok = false;
    do {
        if ($say('', [220]) === '') break;
        if (($caps = $say('EHLO ' . $me, [250])) === '') break;
        if ($enc === 'tls') {
            if ($say('STARTTLS', [220]) === '') break;
            $notes = [];
            set_error_handler($listen);
            $tls = stream_socket_enable_crypto($fp, true, STREAM_CRYPTO_METHOD_TLSv1_2_CLIENT | (defined('STREAM_CRYPTO_METHOD_TLSv1_3_CLIENT') ? STREAM_CRYPTO_METHOD_TLSv1_3_CLIENT : 0));
            restore_error_handler();
            if ($tls !== true) {
                $error = ($certFault() ? 'certificate: ' : 'connect: ') . mail_line(implode(' | ', $notes) ?: 'TLS failed', 160);
                break;
            }
            if (($caps = $say('EHLO ' . $me, [250])) === '') break;
        }
        if ($c['user'] !== '') {
            if (stripos($caps, 'AUTH') !== false && stripos($caps, 'LOGIN') === false && stripos($caps, 'PLAIN') !== false) {
                if ($say('AUTH PLAIN ' . base64_encode("\0" . $c['user'] . "\0" . $c['pass']), [235], 'AUTH') === '') break;
            } else {
                if ($say('AUTH LOGIN', [334]) === '') break;
                if ($say(base64_encode($c['user']), [334], 'AUTH user') === '') break;
                if ($say(base64_encode($c['pass']), [235], 'AUTH') === '') break;
            }
        }
        if ($say('MAIL FROM:<' . $from . '>', [250]) === '') break;
        $sent = true;
        foreach ($to as $a) {
            if ($say('RCPT TO:<' . $a . '>', [250, 251]) === '') {
                $sent = false;
                break;
            }
        }
        if (!$sent) break;
        if ($say('DATA', [354]) === '') break;
        // строка, начинающаяся с точки, удваивает её: одинокая точка завершает письмо
        fwrite($fp, (string) preg_replace('~^\.~m', '..', $data));
        if ($say('.', [250], 'DATA end') === '') break;
        $ok = true;
    } while (false);
    @fwrite($fp, "QUIT\r\n");
    @fclose($fp);
    return $ok;
}

/* ---------- письма сайта ---------- */
/** Надписи писем на трёх языках (язык писем выбирается в разделе «Почта (SMTP)»). */
function mail_text(string $key, string $lang): string
{
    static $t = [
        'order' => ['ru' => 'Новый заказ', 'az' => 'Yeni sifariş', 'en' => 'New order'],
        'repair' => ['ru' => 'Заявка на ремонт', 'az' => 'Təmir üçün müraciət', 'en' => 'Repair request'],
        'message' => ['ru' => 'Сообщение с сайта', 'az' => 'Saytdan mesaj', 'en' => 'Message from the site'],
        'name' => ['ru' => 'Имя', 'az' => 'Ad', 'en' => 'Name'],
        'phone' => ['ru' => 'Телефон', 'az' => 'Telefon', 'en' => 'Phone'],
        'total' => ['ru' => 'Сумма', 'az' => 'Məbləğ', 'en' => 'Total'],
        'open' => ['ru' => 'Открыть в админ-панели', 'az' => 'Admin paneldə aç', 'en' => 'Open in the admin panel'],
        'foot' => ['ru' => 'Письмо отправил сайт. Отвечать на него не нужно: покупатель ждёт ответа в WhatsApp или по телефону.',
            'az' => 'Bu məktubu sayt göndərib. Ona cavab yazmaq lazım deyil: müştəri cavabı WhatsApp-da və ya telefonla gözləyir.',
            'en' => 'This message was sent by the site. There is no need to reply to it: the customer expects an answer on WhatsApp or by phone.'],
        'test' => ['ru' => 'Проверка почты', 'az' => 'Poçtun yoxlanması', 'en' => 'Mail check'],
        'testBody' => ['ru' => 'Это проверочное письмо с сайта. Если вы его читаете, отправка почты настроена верно: письма о новых заказах будут приходить на адрес из настроек.',
            'az' => 'Bu, saytdan göndərilən yoxlama məktubudur. Onu oxuyursunuzsa, poçt düzgün qurulub: yeni sifarişlər haqqında məktublar ayarlardakı ünvana gələcək.',
            'en' => 'This is a test message from the site. If you are reading it, mail is set up correctly: messages about new orders will arrive at the address from the settings.'],
    ];
    return $t[$key][$lang] ?? $t[$key]['ru'] ?? $key;
}

/** Запоминает, чем закончилась последняя отправка, — это видно в разделе «Почта (SMTP)». */
function mail_note(string $what, bool $ok, ?string $error, array $extra = []): void
{
    $prev = setting('mail_state', []);
    $prev = is_array($prev) ? $prev : [];
    $keep = array_intersect_key($prev, ['hour' => 1, 'n' => 1]);
    $state = $extra + $keep + ['at' => now(), 'what' => $what, 'ok' => $ok, 'error' => $ok ? '' : mail_line((string) $error, 300)];
    $pdo = db();
    $pdo->beginTransaction();
    q('DELETE FROM ao_settings WHERE name = ?', ['mail_state']);
    q('INSERT INTO ao_settings (name, value) VALUES (?, ?)', ['mail_state', to_json($state)]);
    $pdo->commit();   // без cache_clear(): страницы сайта от этой записи не зависят
}

/**
 * Письмо о новом заказе, заявке или сообщении. Ничего не возвращает и не бросает ошибок: покупатель уже получил ответ,
 * а запись в разделе «Заказы» сохранена в любом случае. Причина неудачи видна в разделе «Почта (SMTP)».
 */
function order_mail(array $o): void
{
    try {
        $c = mail_cfg();
        $to = mail_list($c['to']);
        if (!$to || mail_mode($c) === '') return;
        // не больше MAIL_PER_HOUR писем в час
        $st = setting('mail_state', []);
        $st = is_array($st) ? $st : [];
        $hour = date('YmdH');
        $n = ($st['hour'] ?? '') === $hour ? (int) ($st['n'] ?? 0) : 0;
        if ($n >= MAIL_PER_HOUR) return;
        $l = $c['lang'];
        $shop = mail_line((string) (setting('config', [])['shopName'] ?? 'Asioptik'), 60);
        $kind = mail_text(isset(ORDER_KINDS[$o['kind']]) ? $o['kind'] : 'message', $l);
        $lines = [$kind . ' ' . $o['number'], date('d.m.Y H:i'), '', mail_text('name', $l) . ': ' . $o['name'], mail_text('phone', $l) . ': ' . $o['phone']];
        if ($o['total'] !== null) $lines[] = mail_text('total', $l) . ': ' . rtrim(rtrim(number_format((float) $o['total'], 2, '.', ' '), '0'), '.') . ' ₼';
        array_push($lines, '', (string) $o['text'], '');
        if ($c['adminUrl'] !== '' && !empty($o['id'])) array_push($lines, mail_text('open', $l) . ': ' . $c['adminUrl'] . '?p=order&id=' . (int) $o['id'], '');
        $lines[] = mail_text('foot', $l);
        $err = null;
        $ok = mail_send($c, $to, $shop . ': ' . mb_strtolower(mb_substr($kind, 0, 1)) . mb_substr($kind, 1) . ' ' . $o['number'], implode("\n", $lines), $err);
        mail_note('order', $ok, $err, ['hour' => $hour, 'n' => $n + 1]);
    } catch (Throwable $e) {
        error_log('[asioptik] order mail: ' . $e->getMessage());
    }
}

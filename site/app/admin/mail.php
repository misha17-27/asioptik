<?php
/* Раздел «Почта (SMTP)»: куда приходят письма о заказах, через какой сервер они уходят, и проверка отправки. */
declare(strict_types=1);

/** Причина, по которой письмо не ушло, — словами (коды причин задаёт app/core/mail.php). */
function mail_fault_text(string $error, array $c): string
{
    $server = $c['host'] . ':' . $c['port'];
    if (strncmp($error, 'certificate', 11) === 0) return __('Не удалось установить защищённое соединение с {server}: сертификат сервера не подходит к этому имени. Впишите имя сервера так, как оно указано в настройках почтового ящика на хостинге.', ['server' => $server]);
    if (strncmp($error, 'connect', 7) === 0) return __('Не удалось подключиться к {server}. Проверьте имя сервера, порт и вид шифрования: порту 465 соответствует SSL/TLS, порту 587 — STARTTLS.', ['server' => $server]);
    if (strncmp($error, 'AUTH', 4) === 0) return __('Сервер не принял имя пользователя или пароль. Проверьте их. Почтовые службы вроде Gmail, Яндекса и Mail.ru обычно требуют для сайтов отдельный «пароль приложения» — он создаётся в настройках безопасности почты.');
    if ($error === 'no password without encryption') return __('Без шифрования пароль не отправляется: выберите SSL/TLS или STARTTLS.');
    if ($error === 'no openssl') return __('На хостинге не включён модуль PHP OpenSSL — без него защищённое соединение с почтовым сервером невозможно. Включите модуль в панели хостинга.');
    if ($error === 'no transport') return __('Отправить письмо нечем: SMTP-сервер не указан, а отправка средствами хостинга отключена.');
    if ($error === 'mail() returned false') return __('Хостинг не принял письмо к отправке. Укажите SMTP-сервер почтового ящика — так надёжнее.');
    if ($error === 'no recipient') return __('Не указан адрес получателя.');
    return '';
}

function admin_mail(): void
{
    $c = mail_cfg();
    $errors = [];
    // Адрес админ-панели для ссылок в письмах — тот, по которому сюда вошёл администратор (а не адрес из запроса покупателя)
    $here = origin() . base_path() . 'admin/';
    if (!preg_match('~^https?://[A-Za-z0-9.\-]+(?::\d{1,5})?/[A-Za-z0-9._\~/\-]*$~', $here)) $here = '';
    $encs = ['ssl' => __('SSL/TLS (обычно порт 465)'), 'tls' => __('STARTTLS (обычно порт 587)'), 'none' => __('Без шифрования (порт 25)')];
    $langs = ['ru' => 'Русский', 'az' => 'Azərbaycan dili', 'en' => 'English'];
    $v = ['to' => $c['to'], 'host' => $c['host'], 'port' => (string) $c['port'], 'enc' => $c['enc'], 'user' => $c['user'], 'from' => $c['from'], 'fromName' => $c['fromName'], 'lang' => $c['lang']];
    $line = function (string $name, int $max): string {
        return mail_line(is_string($_POST[$name] ?? null) ? $_POST[$name] : '', $max);
    };
    $stored = setting('mail', []);
    $stored = is_array($stored) ? $stored : [];

    if (is_post() && ($_POST['act'] ?? '') === 'test') {
        $to = mail_list($line('to', 200));
        if (!$to) {
            flash(__('Впишите адрес, на который отправить проверочное письмо.'), 'err');
        } else {
            $shop = mail_line((string) (setting('config', [])['shopName'] ?? 'Asioptik'), 60);
            $err = null;
            $ok = mail_send($c, $to, mail_text('test', $c['lang']) . ' — ' . $shop, mail_text('testBody', $c['lang']) . "\n\n" . site_origin_url() . "\n", $err, true);
            mail_note('test', $ok, $err);
            if ($ok) flash(__('Письмо отправлено на {to}. Если его нет во «Входящих», загляните в «Спам».', ['to' => implode(', ', $to)]));
            else flash(__('Письмо не отправлено.') . ' ' . (mail_fault_text((string) $err, $c) ?: __('Ответ почтового сервера: {text}', ['text' => (string) $err])), 'err');
        }
        redirect(admin_url('mail'));
    }
    if (is_post()) {
        $v = ['to' => $line('to', 200), 'host' => strtolower($line('host', 253)), 'port' => $line('port', 5), 'enc' => $line('enc', 4), 'user' => $line('user', 190),
            'from' => $line('from', 190), 'fromName' => $line('fromName', 80), 'lang' => $line('lang', 2)];
        $pass = is_string($_POST['pass'] ?? null) ? (string) preg_replace('/[\r\n\0]/', '', $_POST['pass']) : '';
        $to = mail_list($v['to']);
        if ($v['to'] !== '' && count($to) !== count(preg_split('~[,;\s]+~', $v['to'], -1, PREG_SPLIT_NO_EMPTY) ?: [])) $errors['to'] = __('Проверьте адрес: он должен выглядеть как name@example.com. Несколько адресов (до трёх) разделяйте запятой.');
        if ($v['host'] !== '' && !preg_match('~^[a-z0-9](?:[a-z0-9.\-]{0,251}[a-z0-9])?$~', $v['host'])) $errors['host'] = __('Имя сервера — как в настройках почты, например smtp.gmail.com или mail.asioptik.az. Без https:// и без пробелов.');
        if (!in_array((int) $v['port'], MAIL_PORTS, true) || !ctype_digit($v['port'])) $errors['port'] = __('Порт — 465, 587, 25 или 2525.');
        if (!isset($encs[$v['enc']])) $v['enc'] = 'ssl';
        if (!isset($langs[$v['lang']])) $v['lang'] = 'ru';
        if ($v['from'] !== '' && !preg_match(MAIL_ADDR, $v['from'])) $errors['from'] = __('Адрес отправителя должен выглядеть как name@example.com.');
        if ($v['host'] !== '' && $v['enc'] === 'none' && $v['user'] !== '' && !in_array($v['host'], ['localhost', '127.0.0.1'], true)) $errors['enc'] = __('Без шифрования пароль не отправляется: выберите SSL/TLS или STARTTLS.');
        if (strlen($pass) > 500) $errors['pass'] = __('Слишком длинный пароль.');
        if (!$errors) {
            $new = ['to' => implode(', ', $to), 'host' => $v['host'], 'port' => (int) $v['port'], 'enc' => $v['enc'], 'user' => $v['user'], 'from' => $v['from'], 'fromName' => $v['fromName'], 'lang' => $v['lang'], 'adminUrl' => $here];
            // пароль: новый, если его вписали; прежний, если поле оставили пустым; никакого, если убрали пользователя или сервер
            $new['pass'] = $v['host'] === '' || $v['user'] === '' ? '' : ($pass !== '' ? secret_seal($pass) : (string) ($stored['pass'] ?? ''));
            set_setting('mail', $new);
            flash(!$to ? __('Сохранено. Адрес для заявок не указан — письма о заказах не отправляются.') : __('Сохранено. Отправьте проверочное письмо ниже — так вы убедитесь, что почта доходит.'));
            redirect(admin_url('mail'));
        }
    } elseif ($stored && $here !== '' && ($stored['adminUrl'] ?? '') !== $here) {
        $stored['adminUrl'] = $here;   // сайт переехал на другой адрес — ссылки в письмах ведут на нынешний
        set_setting('mail', $stored);
    }

    $mode = mail_mode($c);
    $on = $mode !== '' && mail_list($c['to']);
    $pill = !$on ? '<span class="st st-cancel">' . e(__('письма не отправляются')) . '</span>'
        : '<span class="st st-done">' . e($mode === 'smtp' ? __('сейчас: SMTP') : __('сейчас: почта хостинга')) . '</span>';
    $hasPass = ($stored['pass'] ?? '') !== '';
    $field = function (string $name, string $label, string $input, string $hint = '') use ($errors): string {
        return '<div class="field' . (isset($errors[$name]) ? ' is-invalid' : '') . '"><label class="lbl" for="ml-' . $name . '">' . e($label) . '</label>' . $input
            . (isset($errors[$name]) ? '<p class="err">' . e($errors[$name]) . '</p>' : '') . ($hint !== '' ? '<p class="hint">' . e($hint) . '</p>' : '') . '</div>';
    };
    $text = function (string $name, string $more = '') use ($v): string {
        return '<input id="ml-' . $name . '" type="text" name="' . $name . '" value="' . e($v[$name]) . '" autocomplete="off" spellcheck="false"' . $more . '>';
    };
    $select = function (string $name, array $opts) use ($v): string {
        $h = '<select id="ml-' . $name . '" name="' . $name . '">';
        foreach ($opts as $k => $label) $h .= '<option value="' . e((string) $k) . '"' . ((string) $k === (string) $v[$name] ? ' selected' : '') . '>' . e($label) . '</option>';
        return $h . '</select>';
    };

    $out = '<div class="mailp">';
    if ($errors) $out .= '<p class="flash flash-err" role="alert">' . e(__('Не сохранено: проверьте поля, отмеченные красным.')) . '</p>';
    $out .= '<section class="card form-card">' . card_head(__('Отправка почты'), $pill)
        . '<form method="post" class="card-body" autocomplete="off">' . csrf_field()
        . '<p class="note">' . e(__('О каждом новом заказе, заявке на ремонт и сообщении с сайта на этот адрес приходит письмо. Заказ покупателя по-прежнему уходит вам в WhatsApp и сохраняется в разделе «Заказы» — письмо приходит в дополнение.')) . '</p>'
        . $field('to', __('Куда приходят заказы и заявки с сайта'), $text('to', ' inputmode="email" placeholder="info@asioptik.az"'), __('Адрес почты салона. Можно до трёх адресов через запятую. Пустое поле — письма не отправляются.'))
        . '<h3 class="block">' . e(__('Почтовый сервер (SMTP)')) . '</h3>'
        . '<p class="hint hint-block">' . e(__('Данные почтового ящика, с которого сайт отправляет письма: они есть в настройках почты на хостинге или у почтовой службы. Пока сервер не указан, письма отправляет сам хостинг — так они чаще попадают в «Спам».')) . '</p>'
        . '<div class="field-row cols3">' . $field('host', __('SMTP-сервер'), $text('host', ' placeholder="mail.asioptik.az"'))
        . $field('port', __('Порт'), $text('port', ' inputmode="numeric" maxlength="5" class="short"'))
        . $field('enc', __('Шифрование'), $select('enc', $encs)) . '</div>'
        . '<div class="field-row cols2">' . $field('user', __('Пользователь (полный адрес почты)'), $text('user', ' inputmode="email"'))
        . $field('pass', __('Пароль'), '<input id="ml-pass" type="password" name="pass" value="" autocomplete="new-password"' . ($hasPass ? ' placeholder="' . e(__('сохранён — оставьте пустым, чтобы не менять')) . '"' : '') . '>',
            __('Хранится на сервере в зашифрованном виде и здесь больше не показывается.')) . '</div>'
        . '<div class="field-row cols2">' . $field('from', __('Адрес отправителя'), $text('from', ' inputmode="email"'), __('Обычно тот же адрес, что и пользователь. Если пусто, берётся он.'))
        . $field('fromName', __('Имя отправителя'), $text('fromName', ' maxlength="80" placeholder="Asioptik"')) . '</div>'
        . $field('lang', __('Язык писем'), $select('lang', $langs))
        . '<div class="actions"><button type="submit" class="btn">' . e(__('Сохранить')) . '</button></div></form></section>';

    // --- проверка отправки
    $st = setting('mail_state', []);
    $st = is_array($st) ? $st : [];
    $last = '';
    if (!empty($st['at'])) {
        $what = ($st['what'] ?? '') === 'test' ? __('проверочное письмо') : __('письмо о заказе');
        $last = '<p class="mail-last ' . (!empty($st['ok']) ? 'ok' : 'bad') . '">' . e(__('Последняя отправка: {date}, {what}.', ['date' => fmt_date((string) $st['at']), 'what' => $what]) . ' '
            . (!empty($st['ok']) ? __('Письмо ушло.') : __('Письмо не ушло.') . ' ' . (mail_fault_text((string) ($st['error'] ?? ''), $c) ?: __('Ответ почтового сервера: {text}', ['text' => (string) ($st['error'] ?? '')])))) . '</p>';
    }
    $out .= '<section class="card form-card">' . card_head(__('Проверка отправки'))
        . '<form method="post" class="card-body">' . csrf_field() . '<input type="hidden" name="act" value="test">'
        . '<p class="hint hint-block">' . e(__('Отправим проверочное письмо, чтобы убедиться, что настройки верные. Проверяются сохранённые настройки: сначала нажмите «Сохранить» выше.')) . '</p>' . $last
        . '<div class="mail-test"><div class="field"><label class="lbl" for="ml-test">' . e(__('Адрес получателя')) . '</label><input id="ml-test" type="text" name="to" value="' . e(mail_list($c['to'])[0] ?? '') . '" inputmode="email" autocomplete="off" spellcheck="false" required></div>'
        . '<button type="submit" class="btn btn-line"' . ($mode === '' ? ' disabled' : '') . '>' . icon('mail') . e(__('Отправить тест')) . '</button></div></form></section></div>';

    admin_page(__('Почта (SMTP)'), $out, 'mail');
}

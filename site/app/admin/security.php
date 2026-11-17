<?php
/* Раздел «Безопасность»: ключи капчи (Cloudflare Turnstile), где их взять и что на сайте уже защищено. */
declare(strict_types=1);

/** Виджет капчи для формы админ-панели. Ответ посетителя уходит вместе с формой в поле cf-turnstile-response. */
function captcha_widget(): string
{
    $lang = ui_lang() === 'az' ? 'auto' : ui_lang();   // азербайджанского у виджета нет: он берёт язык браузера
    return '<div class="cap"><div class="cf-turnstile" data-sitekey="' . e(captcha_cfg()['site']) . '" data-theme="light" data-size="flexible" data-language="' . $lang . '"></div></div>'
        . '<script src="' . e(TURNSTILE_SCRIPT) . '" async defer></script>';
}

/** Почему пробная проверка не прошла — понятными словами. */
function captcha_reason(array $r): string
{
    $codes = $r['codes'];
    if (in_array('invalid-input-secret', $codes, true) || in_array('missing-input-secret', $codes, true)) {
        return __('Cloudflare не принял Secret Key. Скопируйте его из настроек виджета ещё раз, целиком, и сохраните.');
    }
    if (in_array('no-connection', $codes, true)) {
        return __('Сервер сайта не смог связаться с Cloudflare: на хостинге запрещены исходящие запросы или нет модуля cURL. Напишите в поддержку хостинга: нужен доступ к challenges.cloudflare.com по https.');
    }
    if (in_array('bad-answer', $codes, true) || in_array('internal-error', $codes, true)) return __('Cloudflare ответил с ошибкой. Попробуйте ещё раз через минуту.');
    if (in_array('missing-input-response', $codes, true)) return __('Проверка не пройдена: дождитесь отметки Cloudflare над кнопкой и нажмите её ещё раз.');
    return __('Cloudflare не принял ответ: он устарел или получен с другим ключом. Обновите страницу и пройдите проверку ещё раз. Если ошибка повторяется, Site Key и Secret Key взяты от разных виджетов.');
}

/** Неисправность, из-за которой включённая капча никого не останавливает. */
function captcha_fault_text(string $code): string
{
    if ($code === 'invalid-input-secret' || $code === 'missing-input-secret') return __('Cloudflare не принимает Secret Key. Вставьте действующий ключ, сохраните и пройдите пробную проверку заново.');
    if ($code === 'no-connection') return __('Сервер сайта не может связаться с Cloudflare.');
    return __('Cloudflare отвечает с ошибкой.');
}

function admin_security(): void
{
    $c = captcha_cfg();
    $local = is_local();
    $errors = [];
    $site = $c['site'];
    $login = $c['site'] === '' ? true : $c['login'];   // пока ключей нет, оба места отмечены заранее
    $forms = $c['site'] === '' ? true : $c['forms'];
    $hasKeys = $c['site'] !== '' && $c['secret'] !== '';

    if (is_post()) {
        if (($_POST['act'] ?? '') === 'check') {   // пробная проверка: только после неё капча начинает действовать
            if (!$hasKeys) redirect(admin_url('security'));
            $r = captcha_verify(is_string($_POST['cf-turnstile-response'] ?? null) ? $_POST['cf-turnstile-response'] : '', $c);
            if ($r['state'] === 'pass') {
                set_setting('turnstile', ['site' => $c['site'], 'secret' => $c['secret'], 'login' => $c['login'], 'forms' => $c['forms'], 'ok' => true, 'checked' => now()]);
                flash(__('Ключи проверены, капча включена.'));
            } else {
                flash(__('Капча не включена.') . ' ' . captcha_reason($r), 'err');
            }
            redirect(admin_url('security'));
        }
        $key = function (string $name): string {
            return is_string($_POST[$name] ?? null) ? trim($_POST[$name]) : '';
        };
        $site = $key('site');
        $secret = $key('secret');
        $login = !empty($_POST['login']);
        $forms = !empty($_POST['forms']);
        if ($site === '' && $secret === '' && ($c['site'] !== '' || $c['secret'] !== '')) {   // оба поля очищены — капча выключается
            set_setting('turnstile', new stdClass());
            flash(__('Ключи удалены, капча выключена.'));
            redirect(admin_url('security'));
        }
        $shape = '~^[A-Za-z0-9_\-]{16,120}$~';
        $odd = __('Ключ выглядит иначе. Скопируйте его из Cloudflare целиком, без пробелов.');
        $dummy = __('Это тестовый ключ Cloudflare: он пропускает всех подряд. Для сайта нужны ключи своего виджета.');
        if ($site === '') $errors['site'] = __('Вставьте Site Key из Cloudflare.');
        elseif (!preg_match($shape, $site)) $errors['site'] = $odd;
        if ($secret === '' && $c['secret'] === '') $errors['secret'] = __('Вставьте Secret Key из Cloudflare.');
        elseif ($secret !== '' && !preg_match($shape, $secret)) $errors['secret'] = $odd;
        elseif ($secret !== '' && $secret === $site) $errors['secret'] = __('Site Key и Secret Key — два разных ключа. Скопируйте из Cloudflare оба.');
        if (!$local && !$errors) {   // тестовые ключи годятся только для пробы на своём компьютере
            if (captcha_dummy_key($site)) $errors['site'] = $dummy;
            if (captcha_dummy_key($secret !== '' ? $secret : $c['secret'])) $errors['secret'] = $dummy;
        }
        if (!$errors) {
            $new = ['site' => $site, 'secret' => $secret !== '' ? $secret : $c['secret'], 'login' => $login, 'forms' => $forms];
            // ключи те же — пробная проверка остаётся в силе; сменился хоть один — её нужно пройти заново
            $same = $new['site'] === $c['site'] && $new['secret'] === $c['secret'];
            if ($same && $c['ok']) $new += ['ok' => true, 'checked' => $c['checked']];
            set_setting('turnstile', $new);
            flash($same && $c['ok'] ? __('Сохранено.') : __('Ключи сохранены. Остался один шаг: пройдите пробную проверку ниже, и капча включится.'));
            redirect(admin_url('security'));
        }
    }

    // Ключи Cloudflare привязаны к домену, на котором открыт сайт. Во временной папке это чужой домен, а не тот,
    // что в «Адресе сайта»: виджету нужны оба, иначе после переезда капча перестанет проходить.
    $preview = site_is_preview();
    $main = host_key((string) parse_url(site_origin_url(), PHP_URL_HOST));
    $host = $preview ? host_key((string) ($_SERVER['HTTP_HOST'] ?? '')) : $main;
    $domain = $host === '' || in_array($host, ['localhost', '127.0.0.1', '[::1]'], true) || preg_match('~\.(localhost|test)$~', $host) ? '' : $host;
    $later = $preview && $domain !== '' && $main !== '' && $main !== $domain ? $main : '';
    $active = $hasKeys && $c['ok'] && ($c['login'] || $c['forms']);
    $blocked = !captcha_allowed();
    if ($c['login'] && $c['forms']) $where = __('{a} и {b}', ['a' => __('вход в админ-панель'), 'b' => __('формы сайта')]);
    else $where = $c['login'] ? __('вход в админ-панель') : ($c['forms'] ? __('формы сайта') : '');
    $code = '<code>\'captcha\' =&gt; false</code>';

    if ($blocked) $pill = '<span class="st st-cancel">' . e(__('Отключена в config.php')) . '</span>';
    elseif ($active) $pill = '<span class="st st-done">' . e(__('Работает')) . '</span>';
    elseif ($hasKeys && !$c['ok']) $pill = '<span class="st st-new">' . e(__('Ждёт пробной проверки')) . '</span>';
    else $pill = '<span class="st st-cancel">' . e(__('Выключена')) . '</span>';

    $out = '<div class="sec">';
    if ($errors) $out .= '<p class="flash flash-err" role="alert">' . e(__('Не сохранено: проверьте поля, отмеченные красным.')) . '</p>';
    if ($blocked) {
        $out .= '<p class="flash flash-warn" role="status">' . strtr(e(__('Капча отключена строкой {code} в файле storage/config.php. Уберите эту строку, когда капча снова понадобится.')), ['{code}' => $code]) . '</p>';
    } elseif ($active && $c['fault'] !== '') {
        $out .= '<p class="flash flash-warn" role="alert">' . e(__('Капча сейчас никого не останавливает.') . ' ' . captcha_fault_text($c['fault'])
            . ($c['fault_at'] !== '' ? ' ' . __('Замечено {date}.', ['date' => fmt_date($c['fault_at'])]) : '')) . '</p>';
    }

    // --- ключи и места проверки
    $field = function (string $name, string $label, string $input, string $hint) use ($errors): string {
        return '<div class="field' . (isset($errors[$name]) ? ' is-invalid' : '') . '"><label class="lbl" for="cap-' . $name . '">' . e($label) . '</label>' . $input
            . (isset($errors[$name]) ? '<p class="err">' . e($errors[$name]) . '</p>' : '') . '<p class="hint">' . e($hint) . '</p></div>';
    };
    $out .= '<section class="card form-card">' . card_head(__('Капча Cloudflare Turnstile'), $pill)
        . '<form method="post" class="card-body sec-form">' . csrf_field()
        . '<p class="note">' . e(__('Капча отличает людей от программ-роботов без картинок и задачек: обычному посетителю делать ничего не нужно. Она защищает вход в админ-панель от подбора пароля, а раздел «Заказы» — от спама. Сервис бесплатный.')) . '</p>'
        . ($active ? '<p class="sec-state">' . e(__('Сейчас проверяется: {where}.', ['where' => $where]) . ($c['checked'] !== '' ? ' ' . __('Ключи проверены {date}.', ['date' => fmt_date($c['checked'])]) : '')) . '</p>' : '')
        . $field('site', __('Site Key (публичный)'), '<input id="cap-site" class="mono" type="text" name="site" value="' . e($site) . '" autocomplete="off" spellcheck="false">',
            __('Виден в коде страницы — так и должно быть.'))
        . $field('secret', __('Secret Key (секретный)'), '<input id="cap-secret" class="mono" type="password" name="secret" value="" autocomplete="off" spellcheck="false"'
            . ($c['secret'] !== '' ? ' placeholder="' . e(__('сохранён — оставьте пустым, чтобы не менять')) . '"' : '') . '>',
            __('Хранится на сервере и здесь больше не показывается.') . ($c['site'] !== '' || $c['secret'] !== '' ? ' ' . __('Чтобы выключить капчу, очистите оба поля и сохраните.') : ''))
        . '<div class="field"><span class="lbl">' . e(__('Где проверять')) . '</span><div class="checks">'
        . '<label class="check"><input type="checkbox" name="login" value="1"' . ($login ? ' checked' : '') . '> <span>' . e(__('Вход в админ-панель')) . '</span></label>'
        . '<label class="check"><input type="checkbox" name="forms" value="1"' . ($forms ? ' checked' : '') . '> <span>' . e(__('Формы сайта: заказ, заявка на ремонт и сообщение')) . '</span></label></div>'
        . '<p class="hint">' . e(__('Заказ покупателя в любом случае уходит вам в WhatsApp. Капча решает только, сохранять ли запись в разделе «Заказы»: записи от роботов не сохраняются.')) . '</p></div>'
        . ($local ? '<p class="hint hint-block sec-local">' . strtr(e(__('Сайт открыт на этом компьютере. Настоящие ключи привязаны к домену и здесь проверку не пройдут: вводите их в админ-панели на хостинге. Посмотреть, как всё работает, можно с тестовыми ключами Cloudflare, которые пропускают всех: Site Key {site}, Secret Key {secret}.')),
            ['{site}' => '<code>1x00000000000000000000AA</code>', '{secret}' => '<code>1x0000000000000000000000000000000AA</code>']) . '</p>' : '')
        . '<div class="actions"><button type="submit" class="btn">' . e(__('Сохранить')) . '</button></div></form>';
    if ($hasKeys && !$c['ok']) {
        $out .= '<form method="post" class="sec-check">' . csrf_field() . '<input type="hidden" name="act" value="check">'
            . '<h3 class="block">' . e(__('Последний шаг — пробная проверка')) . '</h3>'
            . '<p class="hint hint-block">' . e(__('Ниже появится отметка Cloudflare. Когда она станет зелёной, нажмите «Включить капчу»: сайт проверит оба ключа и только после этого начнёт требовать проверку.')) . ' '
            . ($domain !== ''
                ? strtr(e(__('Если вместо отметки видна ошибка, значит, Site Key и Secret Key перепутаны местами или в настройках виджета в Cloudflare не указан домен {domain}.')), ['{domain}' => '<b>' . e($domain) . '</b>'])
                : e(__('Если вместо отметки видна ошибка, значит, Site Key и Secret Key перепутаны местами или в настройках виджета в Cloudflare не указан домен сайта.'))) . '</p>'
            . captcha_widget() . '<button type="submit" class="btn">' . e(__('Включить капчу')) . '</button></form>';
    }
    $out .= '</section>';

    // --- где взять ключи (в этих строках есть разметка: названия кнопок Cloudflare выделены)
    $steps = [
        strtr(__('Зайдите на {link} → раздел <b>Turnstile</b>. Регистрация бесплатная, переносить сайт в Cloudflare не нужно.'), ['{link}' => '<a href="https://dash.cloudflare.com/" target="_blank" rel="noopener">dash.cloudflare.com</a>']),
        __('Нажмите <b>Add widget</b> и назовите виджет, например Asioptik.'),
        $later !== '' ? strtr(__('<b>Hostname</b> — добавьте {domain} и сразу {main}: когда сайт переедет на основной адрес, капча продолжит работать.'), ['{domain}' => '<b>' . e($domain) . '</b>', '{main}' => '<b>' . e($later) . '</b>'])
            : ($domain !== '' ? strtr(__('<b>Hostname</b> — укажите {domain}.'), ['{domain}' => '<b>' . e($domain) . '</b>']) : __('<b>Hostname</b> — укажите домен сайта, например <b>asioptik.az</b>.')),
        __('<b>Widget Mode</b> — <b>Managed</b>.'),
        __('Нажмите <b>Create</b> и скопируйте <b>Site Key</b> и <b>Secret Key</b> в поля выше.'),
    ];
    $out .= '<section class="card">' . card_head(__('Где взять ключи')) . '<ol class="steps">';
    foreach ($steps as $s) $out .= '<li>' . $s . '</li>';
    $out .= '</ol><p class="hint sec-foot">' . strtr(e(__('Если после включения капчи не получается войти в админ-панель, откройте в файловом менеджере хостинга файл storage/config.php и добавьте перед последней строкой {code} — капча отключится.')),
        ['{code}' => '<code>\'captcha\' =&gt; false,</code>']) . '</p></section>';

    // --- что уже защищено: сначала то, что зависит от настроек, потом постоянное
    $bad = (int) q('SELECT COUNT(*) AS n FROM ao_logins WHERE created_at > ?', [date('Y-m-d H:i:s', time() - 86400)])->fetch()['n'];
    $list = [];
    if ($local) $list[] = ['ok', __('Соединение'), __('Сайт открыт на этом компьютере. На хостинге включите сертификат SSL, чтобы пароль и данные покупателей передавались в зашифрованном виде.')];
    elseif (is_https()) $list[] = ['ok', __('Соединение'), __('Сайт открыт по https: пароль и данные покупателей передаются в зашифрованном виде.')];
    else $list[] = ['bad', __('Соединение'), __('Сайт открыт по http, без шифрования. Включите сертификат SSL в панели хостинга и уберите решётки в трёх строках файла .htaccess.')];
    if ($blocked) $list[] = ['warn', __('Капча'), __('Отключена в файле storage/config.php.')];
    elseif ($active && $c['fault'] !== '') $list[] = ['bad', __('Капча'), __('Никого не останавливает.') . ' ' . captcha_fault_text($c['fault'])];
    elseif ($active) $list[] = ['ok', __('Капча'), __('Работает: {where}.', ['where' => $where])];
    elseif ($hasKeys && !$c['ok']) $list[] = ['warn', __('Капча'), __('Ждёт пробной проверки: пройдите её в форме выше.')];
    elseif ($hasKeys) $list[] = ['warn', __('Капча'), __('Выключена. Отметьте в форме выше, где проверять, и сохраните.')];
    else $list[] = ['warn', __('Капча'), __('Выключена. Чтобы включить, вставьте ключи Cloudflare в форму выше.')];
    $list[] = [$bad > 20 ? 'warn' : 'ok', __('Вход в панель'), __('После 5 неудачных попыток вход с этого адреса блокируется на 15 минут. Неудачных попыток за сутки: {n}.', ['n' => $bad])
        . ($bad > 20 ? ' ' . __('Похоже, кто-то подбирает пароль: включите капчу для входа и проверьте, что пароль длинный.') : '')];
    if (!$local && is_file(ROOT . '/install.php')) $list[] = ['warn', __('Файл install.php'), __('Сайт уже установлен, файл больше не нужен. Удалите его в файловом менеджере хостинга.')];
    foreach ([
        [__('Пароль'), __('Хранится необратимым хэшем: узнать его из базы данных нельзя.')],
        [__('Сеанс входа'), __('Заканчивается через 8 часов без действий. Ключ входа недоступен скриптам страницы и не уходит на чужие сайты.')],
        [__('Все формы админ-панели'), __('Защищены токеном CSRF: отправить их с чужого сайта не получится.')],
        [__('Заявки с сайта'), __('Принимаются только со страниц самого сайта, не больше 20 в час с одного адреса. Длина и состав каждого поля ограничены.')],
        [__('Адреса посетителей'), __('Не хранятся: в базе остаётся только необратимый отпечаток адреса, по нему считается число попыток.')],
        [__('Загрузка файлов'), __('Только картинки JPG, PNG и WebP. Файл проверяется и пересохраняется, имя задаёт сайт, скрипты в папке uploads не выполняются.')],
        [__('Служебные папки'), __('Папки app и storage с настройками и базой с сайта не открываются.')],
        [__('База данных'), __('Всё, что вводят посетители, передаётся в базу отдельно от команд и выводится на страницы как текст.')],
        [__('Заголовки безопасности'), __('Браузеру запрещено выполнять чужие скрипты и показывать сайт внутри чужих страниц; по https включается HSTS.')],
        [__('Поисковики'), __('Админ-панель и служебные адреса закрыты от индексации.')],
    ] as [$title, $text]) $list[] = ['ok', $title, $text];
    $out .= '<section class="card">' . card_head(__('Что уже защищено')) . '<ul class="sec-list">';
    foreach ($list as [$kind, $title, $text]) $out .= '<li class="' . $kind . '"><b>' . e($title) . '</b><span>' . e($text) . '</span></li>';
    $out .= '</ul></section></div>';

    admin_page(__('Безопасность'), $out, 'security');
}

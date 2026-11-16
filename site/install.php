<?php
/* Установка сайта: подключение к базе данных, создание таблиц, первые данные и вход в админ-панель.
   Запускается один раз. После установки этот файл лучше удалить с хостинга. */
require __DIR__ . '/app/core/bootstrap.php';

header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex, nofollow');
header('X-Frame-Options: DENY');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');
header("Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'none'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'");

function install_page(string $body): void
{
    $base = base_path();
    echo '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow">'
        . '<title>Установка сайта — Asioptik</title><link rel="stylesheet" href="' . e($base) . 'assets/css/admin.css"></head><body class="bare">'
        . '<main class="card card-wide"><p class="brand">asi<b>optik</b></p><h1>Установка сайта</h1>' . $body . '</main></body></html>';
    exit;
}

/** Первые данные сайта: товары, разделы, бренды, статьи, услуги и настройки из app/data/seed.json. */
function seed_import(PDO $pdo): void
{
    $seed = json_decode((string) file_get_contents(APP . '/data/seed.json'), true);
    if (!is_array($seed)) throw new RuntimeException('Файл app/data/seed.json повреждён');
    $pdo->beginTransaction();
    $insS = $pdo->prepare('INSERT INTO ao_settings (name, value) VALUES (?, ?)');
    foreach ($seed['settings'] as $name => $value) $insS->execute([$name, to_json($value)]);
    $insI = $pdo->prepare('INSERT INTO ao_items (type, slug, position, active, data, updated_at) VALUES (?, ?, ?, 1, ?, ?)');
    foreach ($seed['items'] as $type => $rows) {
        foreach ($rows as $i => $r) $insI->execute([$type, $r['slug'], ($i + 1) * 10, to_json($r['data']), now()]);
    }
    $pdo->commit();
}

if (config()) {
    install_page('<p>Сайт уже установлен.</p><p><a class="btn" href="' . e(base_path()) . 'admin/">Открыть админ-панель</a></p>'
        . '<p class="hint">Файл install.php больше не нужен — удалите его с хостинга. Чтобы установить сайт заново, сначала удалите файл storage/config.php.</p>');
}

// что нужно от хостинга
$checks = [
    ['PHP 8.0 или новее', PHP_VERSION_ID >= 80000, 'Сейчас ' . PHP_VERSION . '. Версию PHP можно сменить в панели хостинга.'],
    ['Модуль PDO MySQL', extension_loaded('pdo_mysql'), 'Включите расширение pdo_mysql в настройках PHP на хостинге.'],
    ['Модуль mbstring', extension_loaded('mbstring'), 'Включите расширение mbstring в настройках PHP.'],
    ['Папка storage доступна для записи', is_writable(STORAGE), 'Дайте права на запись папке storage (обычно 755 или 775).'],
    ['Папка uploads доступна для записи', is_writable(UPLOADS), 'Дайте права на запись папке uploads (обычно 755 или 775).'],
];
$ready = true;
$list = '<ul class="checks-list">';
foreach ($checks as $c) {
    $ready = $ready && $c[1];
    $list .= '<li class="' . ($c[1] ? 'ok' : 'bad') . '">' . e($c[0]) . ($c[1] ? '' : '<small>' . e($c[2]) . '</small>') . '</li>';
}
$list .= '<li class="' . (function_exists('imagecreatetruecolor') ? 'ok' : 'warn') . '">Модуль GD для уменьшения фото' . (function_exists('imagecreatetruecolor') ? '' : '<small>Не обязателен: без него фото сохраняются как есть.</small>') . '</li></ul>';

$v = ['host' => 'localhost', 'name' => '', 'user' => '', 'login' => 'admin'];
$error = '';
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && $ready) {
    foreach ($v as $k => $_) $v[$k] = trim((string) ($_POST[$k] ?? ''));
    $dbPass = (string) ($_POST['pass'] ?? '');
    $p1 = (string) ($_POST['password'] ?? '');
    try {
        if ($v['login'] === '' || !preg_match('~^[A-Za-z0-9._@-]{3,60}$~', $v['login'])) throw new InvalidArgumentException('Логин: от 3 символов, латинские буквы, цифры, точка, дефис.');
        if (mb_strlen($p1) < 8) throw new InvalidArgumentException('Пароль для админ-панели должен быть не короче 8 символов.');
        if (weak_password($p1, $v['login'])) throw new InvalidArgumentException('Слишком простой пароль: такие подбирают первыми. Придумайте другой.');
        if ($p1 !== (string) ($_POST['password2'] ?? '')) throw new InvalidArgumentException('Пароль и его повтор не совпадают.');
        if ($v['host'] === 'sqlite') {   // проверка сайта на своём компьютере без MySQL
            if (!in_array($_SERVER['REMOTE_ADDR'] ?? '', ['127.0.0.1', '::1'], true)) throw new InvalidArgumentException('SQLite подходит только для проверки сайта на своём компьютере. На хостинге укажите сервер MySQL, обычно localhost.');
            if (!extension_loaded('pdo_sqlite')) throw new InvalidArgumentException('Для проверки без MySQL нужно расширение pdo_sqlite.');
            $db = ['driver' => 'sqlite', 'path' => STORAGE . '/site.sqlite'];
        } else {
            if ($v['name'] === '' || $v['user'] === '') throw new InvalidArgumentException('Укажите имя базы данных и пользователя.');
            $hp = explode(':', $v['host'], 2);
            $db = ['driver' => 'mysql', 'host' => $hp[0] ?: 'localhost', 'port' => $hp[1] ?? '', 'name' => $v['name'], 'user' => $v['user'], 'pass' => $dbPass];
        }
        try {
            $pdo = db_connect($db);
        } catch (PDOException $e) {
            throw new InvalidArgumentException('Не удалось подключиться к базе данных. Проверьте сервер, имя базы, пользователя и пароль. Ответ базы: ' . $e->getMessage());
        }
        db_schema($pdo);
        if ((int) $pdo->query('SELECT COUNT(*) FROM ao_items')->fetchColumn() === 0) seed_import($pdo);
        $st = $pdo->prepare('SELECT id FROM ao_users WHERE login = ?');
        $st->execute([$v['login']]);
        if ($st->fetch()) {
            $pdo->prepare('UPDATE ao_users SET pass_hash = ? WHERE login = ?')->execute([password_hash($p1, PASSWORD_DEFAULT), $v['login']]);
        } else {
            $pdo->prepare('INSERT INTO ao_users (login, pass_hash, created_at) VALUES (?, ?, ?)')->execute([$v['login'], password_hash($p1, PASSWORD_DEFAULT), now()]);
        }
        $conf = ['db' => $db, 'secret' => bin2hex(random_bytes(32)), 'installed' => now()];
        $code = "<?php\n/* Подключение к базе данных и секретный ключ сайта. Этот файл никому не передавайте. */\nreturn " . var_export($conf, true) . ";\n";
        if (@file_put_contents(STORAGE . '/config.php', $code, LOCK_EX) === false) throw new RuntimeException('Не удалось записать storage/config.php. Проверьте права на папку storage.');
        @chmod(STORAGE . '/config.php', 0640);
        if (function_exists('opcache_invalidate')) @opcache_invalidate(STORAGE . '/config.php', true);
        // Установщик больше не нужен: убираем его сами, а если хостинг не дал — просим удалить вручную
        $removed = @unlink(__FILE__);
        install_page('<p class="flash flash-ok">Готово: сайт установлен.</p>'
            . '<p><a class="btn" href="' . e(base_path()) . 'admin/">Войти в админ-панель</a> <a href="' . e(base_path()) . '">Открыть сайт</a></p>'
            . '<p class="hint">Логин: <b>' . e($v['login']) . '</b>. Пароль — тот, что вы только что задали. '
            . ($removed ? 'Файл install.php удалён с хостинга: он больше не нужен.' : 'Теперь удалите файл install.php с хостинга: он больше не нужен.') . '</p>');
    } catch (Throwable $e) {
        $error = $e instanceof InvalidArgumentException ? $e->getMessage() : 'Установка не завершилась: ' . $e->getMessage();
    }
}

$f = function (string $name, string $label, string $type = 'text', string $hint = '', string $auto = 'off') use ($v): string {
    return '<div class="field"><label class="lbl" for="' . $name . '">' . e($label) . '</label><input id="' . $name . '" name="' . $name . '" type="' . $type . '" value="' . e($type === 'password' ? '' : ($v[$name] ?? '')) . '" autocomplete="' . $auto . '">'
        . ($hint ? '<p class="hint">' . e($hint) . '</p>' : '') . '</div>';
};
install_page($list
    . ($ready ? '' : '<p class="flash flash-err">Сначала исправьте пункты, отмеченные красным, и обновите страницу.</p>')
    . ($error ? '<p class="flash flash-err" role="alert">' . e($error) . '</p>' : '')
    . '<form method="post"' . ($ready ? '' : ' hidden') . '>'
    . '<h2>База данных MySQL</h2><p class="hint">Базу и пользователя создайте в панели хостинга (раздел «Базы данных») и впишите их сюда.</p>'
    . $f('host', 'Сервер базы данных', 'text', 'Обычно localhost.')
    . $f('name', 'Имя базы данных')
    . $f('user', 'Пользователь базы данных')
    . $f('pass', 'Пароль пользователя базы данных', 'password')
    . '<h2>Вход в админ-панель</h2>'
    . $f('login', 'Логин', 'text', '', 'username')
    . $f('password', 'Пароль', 'password', 'Не короче 8 символов. Придумайте новый, не используйте пароль от почты или хостинга.', 'new-password')
    . $f('password2', 'Пароль ещё раз', 'password', '', 'new-password')
    . '<button type="submit" class="btn">Установить сайт</button></form>');

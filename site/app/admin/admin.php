<?php
/* Админ-панель: вход, заказы, товары и остальные разделы. */
declare(strict_types=1);

function admin_session(): void
{
    // Файлы сессий держим у себя, а не в общей папке сервера: на общем хостинге её видят соседние сайты
    $dir = STORAGE . '/sessions';
    if ((is_dir($dir) || @mkdir($dir, 0700, true)) && is_writable($dir)) {
        session_save_path($dir);
        ini_set('session.gc_probability', '1');
        ini_set('session.gc_divisor', '50');
    }
    ini_set('session.gc_maxlifetime', '28800');   // восемь часов, как и предел бездействия ниже
    session_name('ao_admin');
    session_set_cookie_params(['lifetime' => 0, 'path' => base_path() . 'admin/', 'httponly' => true, 'samesite' => 'Lax', 'secure' => is_https()]);
    session_start();
}

function csrf_token(): string
{
    if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(20));
    return $_SESSION['csrf'];
}

function csrf_check(): void
{
    if (hash_equals((string) ($_SESSION['csrf'] ?? ''), (string) ($_POST['csrf'] ?? '')) && !empty($_SESSION['csrf'])) return;
    // Когда файл больше, чем принимает хостинг, форма приходит пустой — объясняем это, а не ругаемся на устаревшую страницу
    $tooBig = !$_POST && (int) ($_SERVER['CONTENT_LENGTH'] ?? 0) > 0;
    http_response_code($tooBig ? 413 : 400);
    header('Content-Type: text/html; charset=utf-8');
    $msg = $tooBig
        ? 'Файл слишком большой для этого хостинга: за один раз он принимает не больше ' . e((string) ini_get('post_max_size')) . '. Уменьшите фото и загрузите снова.'
        : 'Страница устарела. Вернитесь назад, обновите её и повторите действие.';
    exit('<!doctype html><meta charset="utf-8"><title>Не сохранено</title><p style="font:16px/1.5 sans-serif;margin:40px">' . $msg . '</p>');
}

function is_post(): bool
{
    return ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST';
}

function admin_run(): void
{
    if (!config()) redirect(base_path() . 'install.php');
    header('X-Frame-Options: DENY');
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: same-origin');
    header('Cache-Control: no-store');
    header('X-Robots-Tag: noindex, nofollow');
    $p = (string) ($_GET['p'] ?? '');
    // Адрес Cloudflare разрешён только там, где стоит проверка «не робот»: на странице входа и в разделе «Безопасность»
    $cf = ($p === 'login' && captcha_on('login')) || ($p === 'security' && captcha_cfg()['site'] !== '') ? ' ' . TURNSTILE_ORIGIN : '';
    header("Content-Security-Policy: default-src 'self'; img-src 'self' data: blob: https:; style-src 'self' 'unsafe-inline'; script-src 'self'$cf;"
        . ($cf !== '' ? " frame-src$cf; connect-src 'self'$cf;" : '') . " frame-ancestors 'none'; form-action 'self'; base-uri 'self'");
    admin_session();
    if ($p === 'login') admin_login();
    if (empty($_SESSION['uid'])) redirect(admin_url('login'));
    if (time() - (int) ($_SESSION['seen'] ?? 0) > 8 * 3600) {   // восемь часов без действий — входим заново
        $_SESSION = [];
        session_destroy();
        redirect(admin_url('login'));
    }
    $_SESSION['seen'] = time();
    if (is_post()) csrf_check();
    switch ($p) {
        case '': admin_home(); break;
        case 'orders': admin_orders(); break;
        case 'clients': admin_clients(); break;
        case 'pages': admin_pages(); break;
        case 'page': admin_page_edit(); break;
        case 'order': admin_order(); break;
        case 'list': admin_list(); break;
        case 'edit': admin_edit(); break;
        case 'delete': admin_delete(); break;
        case 'doc': admin_doc(); break;
        case 'banners': admin_banners(); break;
        case 'security': admin_security(); break;
        case 'password': admin_password(); break;
        case 'logout': admin_logout(); break;
    }
    redirect(admin_url());
}

/* ---------- вход и выход ---------- */
function admin_login(): void
{
    if (!empty($_SESSION['uid'])) redirect(admin_url());
    $error = '';
    $login = '';
    $cap = captcha_on('login');   // проверка «не робот» от Cloudflare, если она включена в разделе «Безопасность»
    if (is_post()) {
        csrf_check();
        $ip = client_ip_hash();
        q('DELETE FROM ao_logins WHERE created_at < ?', [date('Y-m-d H:i:s', time() - 86400)]);
        $tries = (int) q('SELECT COUNT(*) AS n FROM ao_logins WHERE ip_hash = ? AND created_at > ?', [$ip, date('Y-m-d H:i:s', time() - 900)])->fetch()['n'];
        $login = mb_substr(trim((string) ($_POST['login'] ?? '')), 0, 60);
        $pass = (string) ($_POST['password'] ?? '');
        if ($tries >= 5) {
            $error = 'Слишком много попыток входа. Подождите 15 минут и попробуйте снова.';
        } elseif ($cap && !captcha_pass(is_string($_POST['cf-turnstile-response'] ?? null) ? $_POST['cf-turnstile-response'] : '')) {
            // пароль не проверяем и попытку не считаем: человек мог просто не дождаться отметки
            $error = 'Подтвердите, что вы не робот: дождитесь зелёной отметки под паролем и нажмите «Войти» ещё раз.';
        } else {
            $u = q('SELECT * FROM ao_users WHERE login = ?', [$login])->fetch();
            // проверяем пароль и для несуществующего логина, чтобы по времени ответа нельзя было подобрать логин
            $hash = $u ? $u['pass_hash'] : '$2y$10$usesomesillystringfore7hnbRJHxXVLeakoG8K30oukPsA.ztMG';
            if (password_verify($pass, $hash) && $u) {
                session_regenerate_id(true);
                $_SESSION = ['uid' => (int) $u['id'], 'login' => $u['login'], 'seen' => time()];
                q('DELETE FROM ao_logins WHERE ip_hash = ?', [$ip]);
                if (password_needs_rehash($u['pass_hash'], PASSWORD_DEFAULT)) {
                    q('UPDATE ao_users SET pass_hash = ? WHERE id = ?', [password_hash($pass, PASSWORD_DEFAULT), $u['id']]);
                }
                redirect(admin_url());
            }
            q('INSERT INTO ao_logins (ip_hash, created_at) VALUES (?, ?)', [$ip, now()]);
            $error = 'Неверный логин или пароль.';
        }
    }
    admin_bare('Вход в админ-панель',
        ($error ? '<p class="flash flash-err" role="alert">' . e($error) . '</p>' : '')
        . '<form method="post" action="' . e(admin_url('login')) . '">' . csrf_field()
        . '<div class="field"><label class="lbl" for="login">Логин</label><input id="login" name="login" type="text" value="' . e($login) . '" autocomplete="username" required autofocus></div>'
        . '<div class="field"><label class="lbl" for="password">Пароль</label><input id="password" name="password" type="password" autocomplete="current-password" required></div>'
        . ($cap ? captcha_widget() : '')
        . '<button type="submit" class="btn">Войти</button></form>');
}

function admin_logout(): void
{
    if (!is_post()) redirect(admin_url());
    $_SESSION = [];
    session_destroy();
    redirect(admin_url('login'));
}

function admin_password(): void
{
    $error = '';
    if (is_post()) {
        $u = q('SELECT * FROM ao_users WHERE id = ?', [(int) $_SESSION['uid']])->fetch();
        $old = (string) ($_POST['old'] ?? '');
        $new = (string) ($_POST['new'] ?? '');
        if (!$u || !password_verify($old, $u['pass_hash'])) $error = 'Текущий пароль указан неверно.';
        elseif (mb_strlen($new) < 8) $error = 'Новый пароль должен быть не короче 8 символов.';
        elseif (weak_password($new, (string) $u['login'])) $error = 'Слишком простой пароль: такие подбирают первыми. Придумайте другой.';
        elseif ($new !== (string) ($_POST['new2'] ?? '')) $error = 'Новый пароль и его повтор не совпадают.';
        else {
            q('UPDATE ao_users SET pass_hash = ? WHERE id = ?', [password_hash($new, PASSWORD_DEFAULT), $u['id']]);
            session_regenerate_id(true);
            flash('Пароль изменён.');
            redirect(admin_url('password'));
        }
    }
    admin_page('Пароль',
        ($error ? '<p class="flash flash-err" role="alert">' . e($error) . '</p>' : '')
        . '<form method="post" class="form narrow">' . csrf_field()
        . '<div class="field"><label class="lbl" for="old">Текущий пароль</label><input id="old" name="old" type="password" autocomplete="current-password" required></div>'
        . '<div class="field"><label class="lbl" for="new">Новый пароль</label><input id="new" name="new" type="password" autocomplete="new-password" required minlength="8"><p class="hint">Не короче 8 символов.</p></div>'
        . '<div class="field"><label class="lbl" for="new2">Новый пароль ещё раз</label><input id="new2" name="new2" type="password" autocomplete="new-password" required></div>'
        . '<button type="submit" class="btn">Изменить пароль</button></form>', 'password');
}

/* ---------- заказы, заявки и сообщения ---------- */
function admin_orders(): void
{
    $kind = isset(ORDER_KINDS[$_GET['kind'] ?? '']) ? (string) $_GET['kind'] : '';
    $status = isset(ORDER_STATUSES[$_GET['status'] ?? '']) ? (string) $_GET['status'] : '';
    $find = trim((string) ($_GET['q'] ?? ''));
    if (mb_strlen($find) > 60) $find = mb_substr($find, 0, 60);
    $where = [];
    $args = [];
    if ($kind) { $where[] = 'kind = ?'; $args[] = $kind; }
    if ($status) { $where[] = 'status = ?'; $args[] = $status; }
    if ($find !== '') {
        // знаки % и _ ищутся как обычные символы, а не как «что угодно»
        $like = '%' . strtr(mb_strtolower($find), ['!' => '!!', '%' => '!%', '_' => '!_']) . '%';
        $cond = "LOWER(name) LIKE ? ESCAPE '!' OR phone LIKE ? ESCAPE '!' OR LOWER(number) LIKE ? ESCAPE '!'";
        array_push($args, $like, $like, $like);
        $digits = ltrim((string) preg_replace('/\D/', '', $find), '0');
        if (strlen($digits) >= 3 && preg_match('/^[\d\s+()\-]+$/', $find)) {   // телефон находится и без пробелов, скобок и кода страны: 0501234567
            $cond .= " OR REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '(', ''), ')', ''), '+', '') LIKE ?";
            $args[] = '%' . $digits . '%';
        }
        $where[] = '(' . $cond . ')';
    }
    $w = $where ? ' WHERE ' . implode(' AND ', $where) : '';
    $total = (int) q('SELECT COUNT(*) AS n FROM ao_orders' . $w, $args)->fetch()['n'];
    $per = 40;
    $page = max(1, (int) ($_GET['pg'] ?? 1));
    $rows = q('SELECT id, number, kind, status, created_at, name, phone, total, data FROM ao_orders' . $w . ' ORDER BY created_at DESC, id DESC LIMIT ' . $per . ' OFFSET ' . (($page - 1) * $per), $args)->fetchAll();

    $tab = function (string $label, array $q) use ($kind, $status, $find): string {
        $on = ($q['kind'] ?? '') === $kind && ($q['status'] ?? '') === $status;
        return '<a href="' . e(admin_url('orders', array_filter($q + ['q' => $find]))) . '"' . ($on ? ' aria-current="true"' : '') . '>' . e($label) . '</a>';
    };
    $out = '<section class="card"><div class="card-tools"><div class="tabs">' . $tab('Все', ['status' => $status]);
    foreach (ORDER_KINDS as $k => $l) $out .= $tab($l === 'Заказ' ? 'Заказы' : ($l === 'Ремонт' ? 'Ремонт' : 'Сообщения'), ['kind' => $k, 'status' => $status]);
    $out .= '</div><div class="tabs tabs-sub">' . $tab('Любой статус', ['kind' => $kind]);
    foreach (ORDER_STATUSES as $k => $l) $out .= $tab($l, ['kind' => $kind, 'status' => $k]);
    $out .= '</div><form method="get" class="filter"><input type="hidden" name="p" value="orders">'
        . ($kind ? '<input type="hidden" name="kind" value="' . e($kind) . '">' : '') . ($status ? '<input type="hidden" name="status" value="' . e($status) . '">' : '')
        . '<input type="search" name="q" value="' . e($find) . '" placeholder="Имя, телефон или номер заказа…" aria-label="Поиск по имени, телефону или номеру"><button type="submit" class="btn btn-line">Найти</button></form></div>';
    if (!$rows) {
        $out .= '<p class="empty">' . ($kind || $status || $find !== '' ? 'С такими условиями ничего нет.' : 'Заказов пока нет. Когда покупатель оформит заказ, оставит заявку на ремонт или напишет с сайта, запись появится здесь.') . '</p>';
    } else {
        $out .= orders_table($rows);
        if ($total > $per) {
            $out .= '<p class="pager">';
            for ($i = 1; $i <= (int) ceil($total / $per); $i++) $out .= '<a href="' . e(admin_url('orders', array_filter(['kind' => $kind, 'status' => $status, 'q' => $find, 'pg' => $i]))) . '"' . ($i === $page ? ' aria-current="page"' : '') . '>' . $i . '</a>';
            $out .= '</p>';
        }
    }
    admin_page('Заказы', $out . '</section>', 'orders');
}

function admin_order(): void
{
    $id = (int) ($_GET['id'] ?? 0);
    $o = q('SELECT * FROM ao_orders WHERE id = ?', [$id])->fetch();
    if (!$o) redirect(admin_url('orders'));
    if (is_post()) {
        if (isset($_POST['delete'])) {
            q('DELETE FROM ao_orders WHERE id = ?', [$id]);
            flash('Запись ' . $o['number'] . ' удалена.');
            redirect(admin_url('orders'));
        }
        $st = (string) ($_POST['status'] ?? '');
        if (isset(ORDER_STATUSES[$st])) {
            q('UPDATE ao_orders SET status = ? WHERE id = ?', [$st, $id]);
            flash('Статус изменён: ' . ORDER_STATUSES[$st] . '.');
        }
        redirect(admin_url('order', ['id' => $id]));
    }
    $d = json_decode((string) $o['data'], true) ?: [];
    $det = is_array($d['details'] ?? null) ? $d['details'] : [];
    $digits = preg_replace('/\D/', '', (string) $o['phone']);
    $out = '<p class="back"><a href="' . e(admin_url('orders')) . '">Все заказы и заявки</a></p>';
    $out .= '<div class="cols"><div><dl class="dl">'
        . '<dt>Тип</dt><dd>' . e(ORDER_KINDS[$o['kind']] ?? $o['kind']) . '</dd>'
        . '<dt>Дата</dt><dd>' . e(fmt_date($o['created_at'])) . '</dd>'
        . '<dt>Имя</dt><dd>' . e($o['name']) . '</dd>'
        . '<dt>Телефон</dt><dd><a href="tel:+' . e($digits) . '">' . e($o['phone']) . '</a> · <a href="https://wa.me/' . e($digits) . '" target="_blank" rel="noopener">написать в WhatsApp</a></dd>'
        . ($o['total'] !== null ? '<dt>Сумма</dt><dd><b>' . e(fmt_money($o['total'])) . '</b><small>Сумму считает страница покупателя. Перед подтверждением заказа сверьте цены с каталогом.</small></dd>' : '')
        . '</dl>';
    if (!empty($det['items']) && is_array($det['items'])) {
        $out .= '<h2>Товары</h2><div class="table-wrap"><table class="table"><thead><tr><th>Товар</th><th class="num">Кол-во</th><th class="num">Цена</th><th class="num">Сумма</th></tr></thead><tbody>';
        foreach ($det['items'] as $it) {
            if (!is_array($it)) continue;
            $lines = '';
            foreach (is_array($it['lines'] ?? null) ? $it['lines'] : [] as $l) $lines .= '<small>' . e(is_scalar($l) ? $l : '') . '</small>';
            $out .= '<tr><td>' . e(is_scalar($it['name'] ?? '') ? $it['name'] : '') . $lines . '</td><td class="num">' . e((string) (int) ($it['qty'] ?? 0)) . '</td><td class="num">' . e(fmt_money($it['price'] ?? null)) . '</td><td class="num">' . e(fmt_money($it['sum'] ?? null)) . '</td></tr>';
        }
        $out .= '</tbody></table></div>';
    }
    $out .= '<h2>Текст, который покупатель отправляет в WhatsApp</h2><pre class="msg">' . e((string) ($d['text'] ?? '')) . '</pre></div>';
    $out .= '<aside class="panel"><form method="post">' . csrf_field() . '<div class="field"><label class="lbl" for="status">Статус</label><select id="status" name="status">';
    foreach (ORDER_STATUSES as $k => $l) $out .= '<option value="' . $k . '"' . ($o['status'] === $k ? ' selected' : '') . '>' . e($l) . '</option>';
    $out .= '</select></div><button type="submit" class="btn">Сохранить статус</button></form>'
        . '<form method="post" class="danger" data-confirm="Удалить запись ' . e($o['number']) . '? Вернуть её будет нельзя.">' . csrf_field() . '<button type="submit" name="delete" value="1" class="link link-danger">Удалить запись</button></form></aside></div>';
    admin_page(($o['kind'] === 'message' ? 'Сообщение ' : ($o['kind'] === 'repair' ? 'Заявка ' : 'Заказ ')) . $o['number'], $out, 'orders');
}

/* ---------- товары, разделы, бренды, статьи, услуги ---------- */
function admin_type(): array
{
    $type = (string) ($_GET['type'] ?? '');
    $all = schemas();
    if (!isset($all[$type])) redirect(admin_url());
    return [$type, $all[$type]];
}

/** Заголовок и описание страницы товара или статьи, которые сайт ставит сам, пока свои не заданы. */
function item_seo_auto(string $type, array $d, string $lang, array $catRows, string $shop): array
{
    $name = tr($d['name'] ?? ($d['title'] ?? ''), $lang);
    if ($name === '') return ['', ''];
    return [$name . ' — ' . $shop, $type === 'product' ? product_desc($d, $lang, ['CATEGORIES' => $catRows, 'CONFIG' => ['shopName' => $shop]]) : tr($d['lead'] ?? '', $lang)];
}

/** Разделы каталога в том виде, в каком их ждёт product_desc(). */
function category_rows(): array
{
    return array_map(function ($r) {
        return ['id' => $r['slug']] + $r['data'];
    }, items('category'));
}

function admin_list(): void
{
    [$type, $S] = admin_type();
    $rows = items($type);
    $cats = opt_categories();
    $brands = opt_brands();
    $base = base_path();
    $shop = (string) (setting('config', [])['shopName'] ?? 'Asioptik');
    $actions = empty($S['fixed']) ? '<a class="btn" href="' . e(admin_url('edit', ['type' => $type])) . '">' . icon('plus') . e($S['add']) . '</a>' : '';
    $out = '<section class="card">';
    $tools = '';
    if ($type === 'product') {
        $fc = (string) ($_GET['cat'] ?? '');
        $fq = mb_strtolower(trim((string) ($_GET['q'] ?? '')));
        $chip = function (string $label, string $cat) use ($fc, $fq): string {
            return '<a href="' . e(admin_url('list', array_filter(['type' => 'product', 'cat' => $cat, 'q' => $fq]))) . '"' . ($fc === $cat ? ' aria-current="true"' : '') . '>' . e($label) . '</a>';
        };
        $tools = '<div class="tabs">' . $chip('Все', '');
        foreach ($cats as $k => $l) $tools .= $chip($l, (string) $k);
        $tools .= '</div><form method="get" class="filter"><input type="hidden" name="p" value="list"><input type="hidden" name="type" value="product">'
            . ($fc !== '' ? '<input type="hidden" name="cat" value="' . e($fc) . '">' : '')
            . '<input type="search" name="q" value="' . e($fq) . '" placeholder="Поиск по названию или коду…" aria-label="Поиск по названию или коду"><button type="submit" class="btn btn-line">Найти</button></form>';
        $rows = array_values(array_filter($rows, function ($r) use ($fc, $fq) {
            if ($fc !== '' && ($r['data']['cat'] ?? '') !== $fc) return false;
            if ($fq === '') return true;
            return mb_strpos(mb_strtolower($r['slug'] . ' ' . implode(' ', (array) ($r['data']['name'] ?? []))), $fq) !== false;
        }));
    }
    if (!empty($S['note'])) $tools = '<p class="note">' . e($S['note']) . '</p>' . $tools;
    if ($tools !== '') $out .= '<div class="card-tools">' . $tools . '</div>';
    if (!$rows) admin_page($S['title'], $out . '<p class="empty">Здесь пока пусто.</p></section>', 'list:' . $type, $actions);

    $hasPage = $type === 'product' || $type === 'post';   // у товара и статьи есть своя страница на сайте
    $catRows = category_rows();
    $head = $type === 'product' ? ['', 'Название', 'Раздел', 'Цена'] : ['Название'];
    if ($type === 'service') $head[] = 'Цена';
    if ($type === 'post') $head[] = 'Дата';
    if ($hasPage) $head[] = 'SEO';
    $head[] = 'Изменено';
    $out .= '<div class="table-wrap"><table class="table"><thead><tr>';
    foreach ($head as $h) $out .= '<th' . ($h === 'Изменено' ? ' class="c-date"' : '') . '>' . e($h) . '</th>';
    $out .= '<th></th></tr></thead><tbody>';
    foreach ($rows as $r) {
        $d = $r['data'];
        $edit = admin_url('edit', ['type' => $type, 'id' => $r['id']]);
        $name = $type === 'brand' ? (string) ($d['name'] ?? '') : tr_admin($d['name'] ?? ($d['title'] ?? ''));
        if ($name === '') $name = $r['slug'];
        $path = $type === 'product' ? 'product/' . rawurlencode($r['slug']) : ($type === 'post' ? 'blog/' . rawurlencode($r['slug']) : '');
        $sub = $path !== '' ? '/' . $path : $r['slug'];
        if ($type === 'product' && isset($brands[$d['brand'] ?? ''])) $sub .= ' · ' . $brands[$d['brand']];
        $cells = '<td><a class="strong" href="' . e($edit) . '">' . e($name) . '</a>' . ($r['active'] ? '' : ' <span class="st st-cancel">скрыт</span>') . '<small>' . e($sub) . '</small></td>';
        if ($type === 'product') {
            $cells = '<td class="pic">' . (!empty($d['img']) ? img_preview((string) $d['img']) : '<span class="nopic">рисунок</span>') . '</td>' . $cells
                . '<td><span class="pill">' . e($cats[$d['cat'] ?? ''] ?? '—') . '</span></td>'
                . '<td class="nowrap">' . e(fmt_money($d['price'] ?? null)) . (!empty($d['old']) ? '<small><s>' . e(fmt_money($d['old'])) . '</s></small>' : '') . '</td>';
        }
        if ($type === 'service') $cells .= '<td class="nowrap">' . (!empty($d['from']) ? 'от ' : '') . e(fmt_money($d['price'] ?? null)) . '</td>';
        if ($type === 'post') $cells .= '<td class="nowrap">' . e((string) ($d['date'] ?? '')) . '</td>';
        if ($hasPage) {
            // длина заголовка и описания страницы на основном языке: зелёная точка, когда оба укладываются в привычные для поиска рамки
            $l = LANGS[0];
            [$autoT, $autoD] = item_seo_auto($type, $d, $l, $catRows, $shop);
            $t = own_text($d['seoTitle'] ?? null, $l) ?: $autoT;
            $ds = own_text($d['seoDesc'] ?? null, $l) ?: $autoD;
            $tl = mb_strlen($t);
            $dl = mb_strlen($ds);
            $ok = $tl >= 15 && $tl <= 65 && $dl >= 50 && $dl <= 170;
            $cells .= '<td class="nowrap" title="Длина заголовка и описания страницы. Хорошо: заголовок 15–65 знаков, описание 50–170."><span class="dot ' . ($ok ? 'dot-ok' : 'dot-warn') . '"></span>' . $tl . ' / ' . $dl . '</td>';
        }
        $cells .= '<td class="nowrap c-date">' . e(substr(fmt_date((string) $r['updated_at']), 0, 10)) . '</td>';
        $acts = ($path !== '' && $r['active'] ? '<a class="btn btn-line btn-sm" href="' . e($base . $path) . '" target="_blank" rel="noopener" title="Открыть на сайте">' . icon('ext') . '<span class="lb">Открыть</span></a>' : '')
            . '<a class="btn btn-line btn-sm" href="' . e($edit) . '" title="Изменить">' . icon('edit') . '<span class="lb">Изменить</span></a>';
        if (empty($S['fixed'])) {
            $acts .= '<form method="post" action="' . e(admin_url('delete', ['type' => $type, 'id' => $r['id']])) . '" data-confirm="Удалить «' . e($name) . '»? Вернуть будет нельзя.">' . csrf_field()
                . '<button type="submit" class="btn btn-line btn-sm btn-del" title="Удалить">' . icon('trash') . '<span class="lb">Удалить</span></button></form>';
        }
        $out .= '<tr' . ($r['active'] ? '' : ' class="off"') . '>' . $cells . '<td class="acts">' . $acts . '</td></tr>';
    }
    admin_page($S['title'], $out . '</tbody></table></div></section>', 'list:' . $type, $actions);
}

/** Поля, которые задают устройство товара на сайте (рисунок, варианты, рецепт): берутся из образца для раздела. */
const PRODUCT_STRUCT = ['art', 'shape', 'metal', 'sw', 'sun', 'grad', 'tone', 'pack', 'opts', 'kind', 'rx', 'colorLabel', 'add'];

function product_template(string $cat): array
{
    $all = setting('templates', []);
    $t = is_array($all[$cat] ?? null) ? $all[$cat] : [];
    return array_intersect_key($t, array_flip(array_merge(PRODUCT_STRUCT, ['withLenses'])));
}

function admin_edit(): void
{
    [$type, $S] = admin_type();
    $id = (int) ($_GET['id'] ?? 0);
    $item = $id ? item_get($id) : null;
    if ($item && $item['type'] !== $type) $item = null;
    if (!$item && !empty($S['fixed'])) redirect(admin_url('list', ['type' => $type]));
    $listUrl = admin_url('list', ['type' => $type]);
    $data = $item ? $item['data'] : [];
    $slug = $item ? $item['slug'] : '';
    $position = $item ? $item['position'] : next_position($type);
    $active = $item ? $item['active'] : true;
    $copyOf = 0;
    if (!$item && !empty($_GET['copy'])) {   // новый товар на основе существующего
        $src = item_get((int) $_GET['copy']);
        if ($src && $src['type'] === $type) {
            $copyOf = $src['id'];
            $data = $src['data'];
            unset($data['img'], $data['home']);
            foreach ($data['colors'] ?? [] as $i => $c) unset($data['colors'][$i]['img']);
        }
    }
    // Новый товар начинается с выбора раздела: от него зависит, как товар выбирают на сайте
    if ($type === 'product' && !$item && !$copyOf) {
        $cats = opt_categories();
        $cat = (string) ($_GET['cat'] ?? '');
        if (!isset($cats[$cat])) {
            $out = '<section class="card">' . card_head('Новый товар', '<a href="' . e($listUrl) . '">← Все товары</a>') . '<div class="card-body card-pad">'
                . '<p class="note">Выберите раздел. От него зависит, как товар выбирают на сайте: оправу можно заказать с линзами, у контактных линз выбирают параметры для каждого глаза, у линз для очков вводят рецепт.</p><div class="choose">';
            foreach ($cats as $k => $l) $out .= '<a class="btn btn-line" href="' . e(admin_url('edit', ['type' => 'product', 'cat' => $k])) . '">' . e($l) . '</a>';
            $out .= '</div><p class="hint">Чтобы завести товар, похожий на уже существующий, откройте этот товар и нажмите «Создать копию товара» внизу страницы.</p></div></section>';
            admin_page($S['title'], $out, 'list:product', '', $S['add']);
        }
        $data = ['cat' => $cat] + product_template($cat);
    }
    $errors = [];
    if (is_post()) {
        if (isset($S['load'])) $data = $S['load']($data);
        $oldCat = (string) ($data['cat'] ?? '');
        $data = form_parse($S['fields'], $data, $_POST, $errors);
        if ($type === 'category' && !empty($data['banner']['demo'])) {
            // своё фото на слайде или просьба убрать временное: временное фото и его кадрирование больше не нужны
            $own = (string) ($data['banner']['img'] ?? '');
            if (!empty($_POST['nodemo']) || ($own !== '' && $own !== (string) ($item['data']['banner']['img'] ?? ''))) $data['banner'] = drop_demo($data['banner']);
        }
        if (isset($S['save'])) $data = $S['save']($data);
        if ($type === 'product') {
            $cat = (string) ($data['cat'] ?? '');
            if ($cat !== '' && $cat !== $oldCat) {   // раздел сменился — берём устройство товара из образца нового раздела
                foreach (PRODUCT_STRUCT as $k) unset($data[$k]);
                unset($data['withLenses']);
                $data = $data + product_template($cat);
            }
            if ($cat !== '' && empty(product_template($cat)['withLenses'])) unset($data['withLenses']);   // «с линзами» бывает только у оправ
            if (isset($data['old'], $data['price']) && $data['old'] <= $data['price']) unset($data['old']);
        }
        if (empty($S['fixed'])) {
            $slug = slugify((string) ($_POST['slug'] ?? ''));
            if ($slug === '') $slug = slugify($type === 'brand' ? (string) ($data['name'] ?? '') : (string) (($data['name'] ?? $data['title'] ?? [])['en'] ?? tr_admin($data['name'] ?? $data['title'] ?? '')));
            if ($slug === '') $slug = $type . '-' . substr(bin2hex(random_bytes(3)), 0, 5);
            $base = $slug;
            for ($i = 2; ($other = item_by_slug($type, $slug)) && $other['id'] !== ($item['id'] ?? 0); $i++) $slug = $base . '-' . $i;
        }
        $position = (int) ($_POST['position'] ?? $position);
        $active = !empty($_POST['active']);
        if (!$errors) {
            item_save($item['id'] ?? null, $type, $slug, $position, $active, $data);
            flash('Сохранено: ' . ($type === 'brand' ? (string) ($data['name'] ?? $slug) : tr_admin($data['name'] ?? $data['title'] ?? $slug)) . '.');
            redirect($listUrl);
        }
    }
    $view = isset($S['load']) ? $S['load']($data) : $data;
    $own = $type === 'brand' ? (string) ($data['name'] ?? '') : tr_admin($data['name'] ?? $data['title'] ?? '');
    $head = $item && $own !== '' ? $own : ($item ? $slug : ($copyOf ? 'Копия товара' : ($S['add'] ?? $S['one'])));
    $fields = $S['fields'];
    if ($type === 'product' || $type === 'post') {   // в пустых полях SEO серым показан текст, который сайт поставит сам
        $catRows = category_rows();
        $shop = (string) (setting('config', [])['shopName'] ?? 'Asioptik');
        foreach ($fields as $i => $f) {
            if (($f['key'] ?? '') !== 'seoTitle' && ($f['key'] ?? '') !== 'seoDesc') continue;
            foreach (LANGS as $l) $fields[$i]['ph'][$l] = item_seo_auto($type, $data, $l, $catRows, $shop)[$f['key'] === 'seoTitle' ? 0 : 1];
        }
    }
    $out = '';
    if ($errors) $out .= '<p class="flash flash-err" role="alert">Не сохранено: проверьте поля, отмеченные красным.</p>';
    if ($copyOf) $out .= '<p class="note">Это копия товара. Измените название, код и цену, загрузите фото и сохраните — появится новый товар.</p>';
    $out .= form_open($head, '<a href="' . e($listUrl) . '">← К списку</a>') . form_fields($fields, $view, $errors);
    if ($type === 'category' && !empty($data['banner']['demo'])) {
        $out .= '<div class="field"><label class="check"><input type="checkbox" name="nodemo" value="1"> <span>Убрать временное фото со слайда</span></label>'
            . '<p class="hint">Сейчас на слайде стоит временное фото с бесплатного фотостока. Загрузите своё, и временное уберётся само. Без фото на слайде показывается рисунок из товаров.</p></div>';
    }
    $out .= '<h3 class="block">' . (empty($S['fixed']) ? 'Адрес и показ на сайте' : 'Показ на сайте') . '</h3><div class="field-row">';
    if (empty($S['fixed'])) {
        $out .= '<div class="field"><label class="lbl" for="slug">' . e($S['slug']) . '</label><input id="slug" type="text" name="slug" value="' . e($copyOf ? '' : $slug) . '" class="mid" pattern="[a-z0-9\-]*"><p class="hint">' . e($S['slug_hint']) . '</p></div>';
    }
    $out .= '<div class="field"><label class="lbl" for="position">Порядок на сайте</label><input id="position" type="text" inputmode="numeric" name="position" value="' . e((string) $position) . '" class="short"><p class="hint">Чем меньше число, тем выше в списке.</p></div></div>'
        . '<div class="field"><label class="check"><input type="checkbox" name="active" value="1"' . ($active ? ' checked' : '') . '> <span>Показывать на сайте</span></label></div>'
        . form_close('<a href="' . e($listUrl) . '">Отмена</a>');
    if ($item && empty($S['fixed'])) {
        if ($type === 'product') $out .= '<p class="danger"><a class="btn btn-line btn-sm" href="' . e(admin_url('edit', ['type' => 'product', 'copy' => $item['id']])) . '">' . icon('copy') . 'Создать копию товара</a></p>';
        $out .= '<form method="post" action="' . e(admin_url('delete', ['type' => $type, 'id' => $item['id']])) . '" class="danger" data-confirm="Удалить «' . e($type === 'brand' ? (string) ($data['name'] ?? $slug) : tr_admin($data['name'] ?? $data['title'] ?? $slug)) . '»? Вернуть будет нельзя.">'
            . csrf_field() . '<button type="submit" class="link link-danger">Удалить</button></form>';
    }
    admin_page($S['title'], $out, 'list:' . $type, '', $item ? $S['one'] . ': ' . $head : ($S['add'] ?? $S['one']));
}

function admin_delete(): void
{
    [$type, $S] = admin_type();
    $item = item_get((int) ($_GET['id'] ?? 0));
    if (!is_post() || !$item || $item['type'] !== $type || !empty($S['fixed'])) redirect(admin_url('list', ['type' => $type]));
    delete_upload($item['data']['img'] ?? null);
    foreach ($item['data']['colors'] ?? [] as $c) delete_upload($c['img'] ?? null);
    item_delete($item['id']);
    flash('Удалено.');
    redirect(admin_url('list', ['type' => $type]));
}

/* ---------- настройки и «О нас» ---------- */
function admin_doc(): void
{
    $name = (string) ($_GET['name'] ?? '');
    $all = doc_schemas();
    if (!isset($all[$name])) redirect(admin_url());
    $S = $all[$name];
    $data = setting($name, []);
    if (!is_array($data)) $data = [];
    $errors = [];
    if (is_post()) {
        $data = form_parse($S['fields'], $data, $_POST, $errors);
        if ($name === 'config') {
            $data['whatsapp'] = preg_replace('/\D/', '', (string) ($data['whatsapp'] ?? ''));
            if (strlen($data['whatsapp']) < 9) $errors['whatsapp'] = 'Укажите номер полностью, с кодом страны: 994501234567.';
            $data['instagram'] = ltrim((string) ($data['instagram'] ?? ''), '@');
            foreach (['deliveryPrice', 'freeDeliveryFrom'] as $k) $data[$k] = $data[$k] ?? 0;
            if (!empty($data['siteUrl']) && !preg_match('~^https?://~i', (string) $data['siteUrl'])) $errors['siteUrl'] = 'Адрес должен начинаться с https://';
        }
        if (!$errors) {
            set_setting($name, $data);
            flash('Сохранено.');
            redirect(admin_url('doc', ['name' => $name]));
        }
    }
    $out = (!empty($S['note']) ? '<p class="note">' . e($S['note']) . '</p>' : '')
        . ($errors ? '<p class="flash flash-err" role="alert">Не сохранено: проверьте поля, отмеченные красным.</p>' : '')
        . form_open($S['head'] ?? $S['title'], isset($S['back']) ? '<a href="' . e(admin_url($S['back'][0], $S['back'][1])) . '">' . e($S['back'][2]) . '</a>' : '')
        . form_fields($S['fields'], $data, $errors) . form_close();
    admin_page($S['title'], $out, $name === 'about' ? 'pages' : 'doc:' . $name);
}

/* ---------- баннеры секций «Для взрослых», «Для мужчин», «Для женщин», «Для детей» ---------- */
function admin_banners(): void
{
    $aud = setting('audiences', []);
    if (!is_array($aud)) $aud = [];
    $fields = [];
    $demo = [];
    $wideHint = 'Широкое, примерно 2400×900. Слева стоит текст, поэтому главное на фото должно быть справа. Обычное фото тоже подойдёт: оно встанет в правой части баннера.';
    foreach ($aud as $i => $a) {
        $name = tr_admin($a['title'] ?? $a['name'] ?? (string) $i);
        $fields[] = ['key' => '_h' . $i, 'type' => 'head', 'label' => 'Баннер «' . $name . '»'];
        $fields[] = ['key' => $i . '.title', 'type' => 'i18n', 'label' => 'Название секции', 'req' => true,
            'hint' => !empty($a['parts']) ? 'На баннере это первая, светлая строка заголовка.' : 'Показывается на баннере, если не заполнен заголовок ниже.'];
        $fields[] = ['key' => $i . '.head', 'type' => 'i18n', 'label' => 'Заголовок на баннере', 'hint' => 'Крупная строка, например «Детская коллекция».'];
        if (!empty($a['parts'])) {
            // баннер с кнопками коллекций: строка под заголовком и несколько фото, которые сменяют друг друга
            $fields[] = ['key' => $i . '.feats', 'type' => 'i18n_lines', 'label' => 'Строка под заголовком', 'rows' => 3, 'hint' => 'Два-три коротких слова или фразы, каждая с новой строки. На баннере они стоят в одну строку через черту.'];
            foreach (array_values($a['slides'] ?? []) as $k => $slide) {
                $path = $i . '.slides.' . $k;
                $fields[] = ['key' => $path . '.img', 'type' => 'image', 'label' => 'Фото ' . ($k + 1) . ' на баннере', 'dir' => 'b', 'hint' => $wideHint];
                if (!empty($slide['demo'])) $demo[$path] = $name . ', фото ' . ($k + 1);
            }
            foreach ($a['parts'] as $j => $part) {
                $path = $i . '.parts.' . $j;
                $fields[] = ['key' => '_h' . $i . '_' . $j, 'type' => 'head', 'label' => 'Блок «' . tr_admin($part['title'] ?? $part['name'] ?? $path) . '» под баннером'];
                $fields[] = ['key' => $path . '.col', 'type' => 'i18n', 'label' => 'Кнопка на баннере', 'hint' => 'Например «Мужская коллекция». Кнопка открывает каталог с этими моделями.'];
                $fields[] = ['key' => $path . '.title', 'type' => 'i18n', 'label' => 'Заголовок блока', 'req' => true];
                $fields[] = ['key' => $path . '.text', 'type' => 'i18n', 'label' => 'Текст в блоке'];
                $fields[] = ['key' => $path . '.img', 'type' => 'image', 'label' => 'Фото в блоке', 'dir' => 'b',
                    'hint' => 'Вертикальное, примерно 800×1000. Снизу стоят заголовок и кнопка, поэтому лицо должно быть в верхней половине. Можно не загружать: тогда в блоке стоит рисунок оправы.'];
                if (!empty($part['demo'])) $demo[$path] = tr_admin($part['title'] ?? $path);
            }
        } else {
            $fields[] = ['key' => $i . '.text', 'type' => 'i18n', 'label' => 'Текст на тёмной плашке'];
            $fields[] = ['key' => $i . '.img', 'type' => 'image', 'label' => 'Фото на баннере', 'dir' => 'b', 'hint' => $wideHint];
            if (!empty($a['demo'])) $demo[(string) $i] = $name;
        }
    }
    $errors = [];
    if (is_post()) {
        $aud = form_parse($fields, $aud, $_POST, $errors);
        foreach (array_keys($demo) as $path) {
            // своё фото или просьба убрать временное: временное фото и его кадрирование больше не нужны
            $node = dget($aud, (string) $path);
            if (is_array($node) && (!empty($_POST['nodemo'][$path]) || !empty($node['img']))) dset($aud, (string) $path, drop_demo($node));
        }
        if (!$errors) {
            set_setting('audiences', $aud);
            flash('Сохранено.');
            redirect(admin_url('banners'));
        }
    }
    $out = '<p class="note">Баннеры секций «Для взрослых» и «Для детей» на главной странице: крупный заголовок слева, фото справа. Пока своего фото нет, показывается временное фото из интернета или рисунок. Фото для слайдов первого экрана загружаются в разделе «Разделы каталога», фото салона — в «Странице “О нас”».</p>'
        . ($errors ? '<p class="flash flash-err" role="alert">Не сохранено: проверьте поля, отмеченные красным.</p>' : '')
        . form_open('Баннеры секций на главной') . form_fields($fields, $aud, $errors);
    if ($demo) {
        $out .= '<h3 class="block">Временные фото из интернета</h3><div class="field"><div class="checks">';
        foreach ($demo as $path => $name) $out .= '<label class="check"><input type="checkbox" name="nodemo[' . e($path) . ']" value="1"> <span>Убрать временное фото у «' . e($name) . '»</span></label>';
        $out .= '</div><p class="hint">Временные фото взяты с бесплатного фотостока. Перед запуском сайта замените их своими.</p></div>';
    }
    $out .= form_close();
    admin_page('Баннеры и фото', $out, 'banners');
}

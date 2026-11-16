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
    header("Content-Security-Policy: default-src 'self'; img-src 'self' data: blob: https:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'");
    admin_session();
    $p = (string) ($_GET['p'] ?? '');
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
        case '':
        case 'orders': admin_orders(); break;
        case 'order': admin_order(); break;
        case 'list': admin_list(); break;
        case 'edit': admin_edit(); break;
        case 'delete': admin_delete(); break;
        case 'doc': admin_doc(); break;
        case 'banners': admin_banners(); break;
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
    if (is_post()) {
        csrf_check();
        $ip = client_ip_hash();
        q('DELETE FROM ao_logins WHERE created_at < ?', [date('Y-m-d H:i:s', time() - 86400)]);
        $tries = (int) q('SELECT COUNT(*) AS n FROM ao_logins WHERE ip_hash = ? AND created_at > ?', [$ip, date('Y-m-d H:i:s', time() - 900)])->fetch()['n'];
        $login = mb_substr(trim((string) ($_POST['login'] ?? '')), 0, 60);
        $pass = (string) ($_POST['password'] ?? '');
        if ($tries >= 5) {
            $error = 'Слишком много попыток входа. Подождите 15 минут и попробуйте снова.';
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
    $where = [];
    $args = [];
    if ($kind) { $where[] = 'kind = ?'; $args[] = $kind; }
    if ($status) { $where[] = 'status = ?'; $args[] = $status; }
    $w = $where ? ' WHERE ' . implode(' AND ', $where) : '';
    $total = (int) q('SELECT COUNT(*) AS n FROM ao_orders' . $w, $args)->fetch()['n'];
    $per = 40;
    $page = max(1, (int) ($_GET['pg'] ?? 1));
    $rows = q('SELECT id, number, kind, status, created_at, name, phone, total FROM ao_orders' . $w . ' ORDER BY created_at DESC, id DESC LIMIT ' . $per . ' OFFSET ' . (($page - 1) * $per), $args)->fetchAll();

    $tab = function (string $label, array $q) use ($kind, $status): string {
        $on = ($q['kind'] ?? '') === $kind && ($q['status'] ?? '') === $status;
        return '<a href="' . e(admin_url('orders', array_filter($q))) . '"' . ($on ? ' aria-current="true"' : '') . '>' . e($label) . '</a>';
    };
    $out = '<div class="tabs">' . $tab('Все', ['status' => $status]);
    foreach (ORDER_KINDS as $k => $l) $out .= $tab($l === 'Заказ' ? 'Заказы' : ($l === 'Ремонт' ? 'Ремонт' : 'Сообщения'), ['kind' => $k, 'status' => $status]);
    $out .= '</div><div class="tabs tabs-sub">' . $tab('Любой статус', ['kind' => $kind]);
    foreach (ORDER_STATUSES as $k => $l) $out .= $tab($l, ['kind' => $kind, 'status' => $k]);
    $out .= '</div>';
    if (!$rows) {
        $out .= '<p class="empty">' . ($kind || $status ? 'С такими условиями ничего нет.' : 'Заказов пока нет. Когда покупатель оформит заказ, оставит заявку на ремонт или напишет через форму на сайте, запись появится здесь.') . '</p>';
    } else {
        $out .= '<div class="table-wrap"><table class="table"><thead><tr><th>Дата</th><th>Номер</th><th>Тип</th><th>Имя</th><th>Телефон</th><th class="num">Сумма</th><th>Статус</th></tr></thead><tbody>';
        foreach ($rows as $r) {
            $url = admin_url('order', ['id' => $r['id']]);
            $out .= '<tr><td>' . e(fmt_date($r['created_at'])) . '</td><td><a href="' . e($url) . '">' . e($r['number']) . '</a></td><td>' . e(ORDER_KINDS[$r['kind']] ?? $r['kind']) . '</td><td>' . e($r['name']) . '</td><td>' . e($r['phone']) . '</td><td class="num">' . e(fmt_money($r['total'])) . '</td><td><span class="st st-' . e($r['status']) . '">' . e(ORDER_STATUSES[$r['status']] ?? $r['status']) . '</span></td></tr>';
        }
        $out .= '</tbody></table></div>';
        if ($total > $per) {
            $out .= '<p class="pager">';
            for ($i = 1; $i <= (int) ceil($total / $per); $i++) $out .= '<a href="' . e(admin_url('orders', array_filter(['kind' => $kind, 'status' => $status, 'pg' => $i]))) . '"' . ($i === $page ? ' aria-current="page"' : '') . '>' . $i . '</a>';
            $out .= '</p>';
        }
    }
    admin_page('Заказы и заявки', $out, 'orders');
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

function admin_list(): void
{
    [$type, $S] = admin_type();
    $rows = items($type);
    $cats = opt_categories();
    $brands = opt_brands();
    $out = '';
    if (!empty($S['note'])) $out .= '<p class="note">' . e($S['note']) . '</p>';
    $bar = '';
    if (empty($S['fixed'])) $bar .= '<a class="btn" href="' . e(admin_url('edit', ['type' => $type])) . '">' . e($S['add']) . '</a>';
    if ($type === 'product') {
        $fc = (string) ($_GET['cat'] ?? '');
        $fq = mb_strtolower(trim((string) ($_GET['q'] ?? '')));
        $bar .= '<form method="get" class="filter"><input type="hidden" name="p" value="list"><input type="hidden" name="type" value="product">'
            . '<select name="cat" aria-label="Раздел"><option value="">Все разделы</option>';
        foreach ($cats as $k => $l) $bar .= '<option value="' . e($k) . '"' . ($fc === $k ? ' selected' : '') . '>' . e($l) . '</option>';
        $bar .= '</select><input type="search" name="q" value="' . e($fq) . '" placeholder="Название или код" aria-label="Поиск по названию или коду"><button type="submit" class="btn btn-line">Показать</button></form>';
        $rows = array_values(array_filter($rows, function ($r) use ($fc, $fq) {
            if ($fc !== '' && ($r['data']['cat'] ?? '') !== $fc) return false;
            if ($fq === '') return true;
            return mb_strpos(mb_strtolower($r['slug'] . ' ' . implode(' ', (array) ($r['data']['name'] ?? []))), $fq) !== false;
        }));
    }
    $out .= '<div class="bar">' . $bar . '</div>';
    if (!$rows) {
        $out .= '<p class="empty">Здесь пока пусто.</p>';
        admin_page($S['title'], $out, 'list:' . $type);
    }
    $head = ['Название'];
    if ($type === 'product') $head = ['', 'Название', 'Раздел', 'Бренд', 'Цена'];
    if ($type === 'service') $head[] = 'Цена';
    if ($type === 'post') $head[] = 'Дата';
    $out .= '<div class="table-wrap"><table class="table"><thead><tr>';
    foreach ($head as $h) $out .= '<th>' . e($h) . '</th>';
    $out .= '<th>На сайте</th><th class="num">Порядок</th><th></th></tr></thead><tbody>';
    foreach ($rows as $r) {
        $d = $r['data'];
        $edit = admin_url('edit', ['type' => $type, 'id' => $r['id']]);
        $name = $type === 'brand' ? (string) ($d['name'] ?? '') : tr_admin($d['name'] ?? ($d['title'] ?? ''));
        $cells = '<td><a href="' . e($edit) . '"><b>' . e($name !== '' ? $name : $r['slug']) . '</b></a><small>' . e($r['slug']) . '</small></td>';
        if ($type === 'product') {
            $cells = '<td class="pic">' . (!empty($d['img']) ? img_preview((string) $d['img']) : '<span class="nopic">рисунок</span>') . '</td>' . $cells
                . '<td>' . e($cats[$d['cat'] ?? ''] ?? '—') . '</td><td>' . e($brands[$d['brand'] ?? ''] ?? '—') . '</td>'
                . '<td class="nowrap">' . e(fmt_money($d['price'] ?? null)) . (!empty($d['old']) ? ' <s>' . e(fmt_money($d['old'])) . '</s>' : '') . '</td>';
        }
        if ($type === 'service') $cells .= '<td class="nowrap">' . (!empty($d['from']) ? 'от ' : '') . e(fmt_money($d['price'] ?? null)) . '</td>';
        if ($type === 'post') $cells .= '<td class="nowrap">' . e((string) ($d['date'] ?? '')) . '</td>';
        $acts = '<a href="' . e($edit) . '">Изменить</a>';
        if ($type === 'product') $acts .= ' <a href="' . e(admin_url('edit', ['type' => $type, 'copy' => $r['id']])) . '">Дублировать</a>';
        $out .= '<tr' . ($r['active'] ? '' : ' class="off"') . '>' . $cells . '<td>' . ($r['active'] ? 'да' : '<b>скрыт</b>') . '</td><td class="num">' . $r['position'] . '</td><td class="acts">' . $acts . '</td></tr>';
    }
    $out .= '</tbody></table></div>';
    admin_page($S['title'], $out, 'list:' . $type);
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
            $out = '<p class="back"><a href="' . e($listUrl) . '">' . e($S['title']) . '</a></p>'
                . '<p class="note">Выберите раздел. От него зависит, как товар выбирают на сайте: оправу можно заказать с линзами, у контактных линз выбирают параметры для каждого глаза, у линз для очков вводят рецепт.</p><div class="choose">';
            foreach ($cats as $k => $l) $out .= '<a class="btn btn-line" href="' . e(admin_url('edit', ['type' => 'product', 'cat' => $k])) . '">' . e($l) . '</a>';
            $out .= '</div><p class="hint">Чтобы завести товар, похожий на уже существующий, откройте список товаров и нажмите «Дублировать».</p>';
            admin_page($S['add'], $out, 'list:product');
        }
        $data = ['cat' => $cat] + product_template($cat);
    }
    $errors = [];
    if (is_post()) {
        if (isset($S['load'])) $data = $S['load']($data);
        $oldCat = (string) ($data['cat'] ?? '');
        $data = form_parse($S['fields'], $data, $_POST, $errors);
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
    $out = '<p class="back"><a href="' . e($listUrl) . '">' . e($S['title']) . '</a></p>';
    if ($errors) $out .= '<p class="flash flash-err" role="alert">Не сохранено: проверьте поля, отмеченные красным.</p>';
    if ($copyOf) $out .= '<p class="note">Это копия товара. Измените название, код и цену, загрузите фото и сохраните — появится новый товар.</p>';
    $out .= '<form method="post" enctype="multipart/form-data" class="form">' . csrf_field() . form_fields($S['fields'], $view, $errors);
    $out .= '<div class="field-row">';
    if (empty($S['fixed'])) {
        $out .= '<div class="field"><label class="lbl" for="slug">' . e($S['slug']) . '</label><input id="slug" type="text" name="slug" value="' . e($copyOf ? '' : $slug) . '" class="mid" pattern="[a-z0-9\-]*"><p class="hint">' . e($S['slug_hint']) . '</p></div>';
    }
    $out .= '<div class="field"><label class="lbl" for="position">Порядок на сайте</label><input id="position" type="text" inputmode="numeric" name="position" value="' . e((string) $position) . '" class="short"><p class="hint">Чем меньше число, тем выше в списке.</p></div></div>'
        . '<div class="field"><label class="check"><input type="checkbox" name="active" value="1"' . ($active ? ' checked' : '') . '> <span>Показывать на сайте</span></label></div>'
        . '<div class="actions"><button type="submit" class="btn">Сохранить</button> <a href="' . e($listUrl) . '">Отмена</a></div></form>';
    if ($item && empty($S['fixed'])) {
        $out .= '<form method="post" action="' . e(admin_url('delete', ['type' => $type, 'id' => $item['id']])) . '" class="danger" data-confirm="Удалить «' . e($type === 'brand' ? (string) ($data['name'] ?? $slug) : tr_admin($data['name'] ?? $data['title'] ?? $slug)) . '»? Вернуть будет нельзя.">'
            . csrf_field() . '<button type="submit" class="link link-danger">Удалить</button></form>';
    }
    $title = $item ? $S['one'] . ': ' . ($type === 'brand' ? (string) ($data['name'] ?? '') : tr_admin($data['name'] ?? $data['title'] ?? $slug)) : ($S['add'] ?? $S['one']);
    admin_page($title, $out, 'list:' . $type);
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
        . '<form method="post" enctype="multipart/form-data" class="form">' . csrf_field() . form_fields($S['fields'], $data, $errors)
        . '<div class="actions"><button type="submit" class="btn">Сохранить</button></div></form>';
    admin_page($S['title'], $out, 'doc:' . $name);
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
        $q = '«' . $name . '»: ';
        $fields[] = ['key' => $i . '.title', 'type' => 'i18n', 'label' => $q . 'название секции', 'req' => true,
            'hint' => !empty($a['parts']) ? 'На баннере это первая, светлая строка заголовка.' : 'Показывается на баннере, если не заполнен заголовок ниже.'];
        $fields[] = ['key' => $i . '.head', 'type' => 'i18n', 'label' => $q . 'заголовок на баннере', 'hint' => 'Крупная строка, например «Детская коллекция».'];
        if (!empty($a['parts'])) {
            // баннер с кнопками коллекций: строка под заголовком и несколько фото, которые сменяют друг друга
            $fields[] = ['key' => $i . '.feats', 'type' => 'i18n_lines', 'label' => $q . 'строка под заголовком', 'rows' => 3, 'hint' => 'Два-три коротких слова или фразы, каждая с новой строки. На баннере они стоят в одну строку через черту.'];
            foreach (array_values($a['slides'] ?? []) as $k => $slide) {
                $path = $i . '.slides.' . $k;
                $fields[] = ['key' => $path . '.img', 'type' => 'image', 'label' => $q . 'фото ' . ($k + 1) . ' на баннере', 'dir' => 'b', 'hint' => $wideHint];
                if (!empty($slide['demo'])) $demo[$path] = $name . ', фото ' . ($k + 1);
            }
            foreach ($a['parts'] as $j => $part) {
                $path = $i . '.parts.' . $j;
                $pn = '«' . tr_admin($part['title'] ?? $part['name'] ?? $path) . '»: ';
                $fields[] = ['key' => $path . '.col', 'type' => 'i18n', 'label' => $pn . 'кнопка на баннере', 'hint' => 'Например «Мужская коллекция». Кнопка открывает каталог с этими моделями.'];
                $fields[] = ['key' => $path . '.title', 'type' => 'i18n', 'label' => $pn . 'заголовок блока под баннером', 'req' => true];
                $fields[] = ['key' => $path . '.text', 'type' => 'i18n', 'label' => $pn . 'текст в блоке'];
                $fields[] = ['key' => $path . '.img', 'type' => 'image', 'label' => $pn . 'фото в блоке', 'dir' => 'b',
                    'hint' => 'Вертикальное, примерно 800×1000. Снизу стоят заголовок и кнопка, поэтому лицо должно быть в верхней половине. Можно не загружать: тогда в блоке стоит рисунок оправы.'];
                if (!empty($part['demo'])) $demo[$path] = tr_admin($part['title'] ?? $path);
            }
        } else {
            $fields[] = ['key' => $i . '.text', 'type' => 'i18n', 'label' => $q . 'текст на тёмной плашке'];
            $fields[] = ['key' => $i . '.img', 'type' => 'image', 'label' => $q . 'фото на баннере', 'dir' => 'b', 'hint' => $wideHint];
            if (!empty($a['demo'])) $demo[(string) $i] = $name;
        }
    }
    $errors = [];
    if (is_post()) {
        $aud = form_parse($fields, $aud, $_POST, $errors);
        foreach (array_keys($demo) as $path) {
            if (!empty($_POST['nodemo'][$path])) dunset($aud, $path . '.demo');
        }
        if (!$errors) {
            set_setting('audiences', $aud);
            flash('Сохранено.');
            redirect(admin_url('banners'));
        }
    }
    $out = '<p class="note">Баннеры секций «Для взрослых» и «Для детей» на главной странице: крупный заголовок слева, фото справа. Пока своего фото нет, показывается временное фото из интернета или рисунок. Фото для слайдов первого экрана загружаются в разделе «Разделы каталога», фото салона — в «Странице “О нас”».</p>'
        . ($errors ? '<p class="flash flash-err" role="alert">Не сохранено: проверьте поля, отмеченные красным.</p>' : '')
        . '<form method="post" enctype="multipart/form-data" class="form">' . csrf_field() . form_fields($fields, $aud, $errors);
    if ($demo) {
        $out .= '<div class="field"><span class="lbl">Временные фото из интернета</span><div class="checks">';
        foreach ($demo as $path => $name) $out .= '<label class="check"><input type="checkbox" name="nodemo[' . e($path) . ']" value="1"> <span>Убрать временное фото у «' . e($name) . '»</span></label>';
        $out .= '</div><p class="hint">Временные фото взяты с бесплатного фотостока. Перед запуском сайта замените их своими.</p></div>';
    }
    $out .= '<div class="actions"><button type="submit" class="btn">Сохранить</button></div></form>';
    admin_page('Баннеры и фото', $out, 'banners');
}

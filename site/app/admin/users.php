<?php
/* Пользователи админ-панели: роли и права, раздел «Пользователи» и страница «Мой профиль». */
declare(strict_types=1);

/*
 * Что разрешено каждой роли:
 *   content  — содержимое сайта: страницы, блог, баннеры и фото, изображения, товары, разделы, бренды, услуги, филиалы;
 *   orders   — заказы и клиенты (имена и телефоны покупателей);
 *   settings — настройки сайта, почта, безопасность и пользователи.
 * Роль проверяется на сервере при каждом запросе (admin_run), а не только скрывает пункты меню.
 */
const ROLE_CAN = [
    'editor' => ['content'],
    'manager' => ['content', 'orders'],
    'admin' => ['content', 'orders', 'settings'],
];
const LOGIN_RULE = '~^[A-Za-z0-9._@-]{3,60}$~';

/** Названия ролей — от самой узкой к полной; первая стоит в форме нового пользователя по умолчанию. */
function role_names(): array
{
    return ['editor' => __('Редактор'), 'manager' => __('Менеджер'), 'admin' => __('Администратор')];
}

/** Вошедший пользователь (строка из ao_users); задаётся один раз в admin_run(). */
function me(?array $set = null): array
{
    static $u = [];
    if ($set !== null) $u = $set;
    return $u;
}

function can(string $what): bool
{
    return in_array($what, ROLE_CAN[me()['role'] ?? ''] ?? [], true);
}

/** Имя пользователя для показа: своё имя, а пока его нет — логин. */
function user_name(array $u): string
{
    $n = trim((string) ($u['name'] ?? ''));
    return $n !== '' ? $n : (string) ($u['login'] ?? '');
}

/**
 * Отметка пароля в сеансе входа. Когда пользователь меняет пароль или администратор задаёт ему новый,
 * отметка перестаёт совпадать — и все прежние сеансы этого пользователя заканчиваются.
 */
function pass_mark(string $hash): string
{
    return substr(hash_hmac('sha256', $hash, (string) (config()['secret'] ?? '')), 0, 24);
}

/* Неудачные попытки входа и подтверждения паролем считаются вместе, по отпечатку адреса: пять за 15 минут — пауза. */
function login_tries(): int
{
    return (int) q('SELECT COUNT(*) AS n FROM ao_logins WHERE ip_hash = ? AND created_at > ?', [client_ip_hash(), date('Y-m-d H:i:s', time() - 900)])->fetch()['n'];
}

function login_fail(): void
{
    q('INSERT INTO ao_logins (ip_hash, created_at) VALUES (?, ?)', [client_ip_hash(), now()]);
}

/**
 * Подтверждение важного действия своим паролем: добавить пользователя, сменить роль или пароль может только тот,
 * кто знает пароль администратора, а не всякий, кто сел за открытую админ-панель. Возвращает текст ошибки или ''.
 */
function confirm_password(): string
{
    if (login_tries() >= 5) return __('Слишком много неверных попыток. Подождите 15 минут и попробуйте снова.');
    $pass = is_string($_POST['confirm'] ?? null) ? $_POST['confirm'] : '';
    if ($pass !== '' && password_verify($pass, (string) (me()['pass_hash'] ?? ''))) return '';
    login_fail();
    return __('Ваш пароль указан неверно — ничего не изменено.');
}

function confirm_field(string $id): string
{
    return '<div class="field confirm"><label class="lbl" for="' . $id . '">' . e(__('Ваш пароль — для подтверждения')) . '</label>'
        . '<input id="' . $id . '" name="confirm" type="password" autocomplete="current-password" required></div>';
}

/** Почему пароль не годится; пустая строка — годится. */
function password_fault(string $pass, string $login): string
{
    if (mb_strlen($pass) < 8) return __('Пароль должен быть не короче 8 символов.');
    if (weak_password($pass, $login)) return __('Слишком простой пароль: такие подбирают первыми. Придумайте другой.');
    return '';
}

/** Раздел, закрытый для роли пользователя. */
function admin_denied(): void
{
    http_response_code(403);
    admin_page(__('Нет доступа'), '<section class="card"><p class="empty">'
        . e(__('У вашей роли нет доступа к этому разделу. Если он нужен для работы, попросите администратора сайта изменить роль.')) . '</p></section>');
}

/* ---------- раздел «Пользователи» ---------- */
function admin_users(): void
{
    $me = me();
    $roles = role_names();
    $errors = [];
    $add = ['name' => '', 'login' => '', 'role' => 'editor'];
    $posted = [];   // что ввели в таблице, если сохранить не получилось
    $clean = function ($v, int $max): string {
        $s = is_string($v) ? (string) preg_replace('/[\x00-\x1F\x7F]/u', '', $v) : '';
        return mb_substr(trim($s), 0, $max);
    };

    if (is_post() && ($_POST['act'] ?? '') === 'add') {
        $add = ['name' => $clean($_POST['name'] ?? '', 80), 'login' => $clean($_POST['login'] ?? '', 60), 'role' => is_string($_POST['role'] ?? null) ? $_POST['role'] : ''];
        $pass = is_string($_POST['password'] ?? null) ? $_POST['password'] : '';
        if (!preg_match(LOGIN_RULE, $add['login'])) $errors[] = __('Логин: от 3 до 60 знаков — латинские буквы, цифры, точка, дефис, знак @.');
        elseif (q('SELECT id FROM ao_users WHERE LOWER(login) = ?', [mb_strtolower($add['login'])])->fetch()) $errors[] = __('Пользователь с таким логином уже есть.');
        if (($w = password_fault($pass, $add['login'])) !== '') $errors[] = $w;
        if (!isset($roles[$add['role']])) $errors[] = __('Выберите роль.');
        if (!$errors && ($c = confirm_password()) !== '') $errors[] = $c;   // свой пароль проверяется последним: опечатка в поле не тратит попытку
        if (!$errors) {
            q('INSERT INTO ao_users (login, pass_hash, created_at, name, role, active) VALUES (?, ?, ?, ?, ?, 1)',
                [$add['login'], password_hash($pass, PASSWORD_DEFAULT), now(), $add['name'], $add['role']]);
            flash(__('Пользователь «{name}» добавлен. Передайте ему логин и пароль.', ['name' => $add['name'] !== '' ? $add['name'] : $add['login']]));
            redirect(admin_url('users'));
        }
    } elseif (is_post() && ($_POST['act'] ?? '') === 'save') {
        $in = is_array($_POST['u'] ?? null) ? $_POST['u'] : [];
        $changes = [];
        foreach (q('SELECT * FROM ao_users ORDER BY id')->fetchAll() as $u) {
            $row = $in[$u['id']] ?? null;
            if (!is_array($row)) continue;
            $self = (int) $u['id'] === (int) $me['id'];
            $set = ['name' => $clean($row['name'] ?? '', 80)];
            $posted[$u['id']] = $set;
            if (!$self) {   // свою роль и свой доступ администратор не меняет: так в панели всегда остаётся хотя бы один администратор
                $role = is_string($row['role'] ?? null) ? $row['role'] : '';
                if (!isset($roles[$role])) {
                    $errors[] = $u['login'] . ': ' . __('Выберите роль.');
                    continue;
                }
                $set['role'] = $role;
                $set['active'] = empty($row['active']) ? 0 : 1;
                $posted[$u['id']] = $set;
                $pass = is_string($row['password'] ?? null) ? $row['password'] : '';
                if ($pass !== '') {
                    if (($w = password_fault($pass, (string) $u['login'])) !== '') {
                        $errors[] = $u['login'] . ': ' . $w;
                        continue;
                    }
                    $set['pass_hash'] = password_hash($pass, PASSWORD_DEFAULT);
                }
            }
            $diff = [];
            foreach ($set as $k => $v) {
                if ((string) $u[$k] !== (string) $v) $diff[$k] = $v;
            }
            if ($diff) $changes[(int) $u['id']] = $diff;
        }
        if (!$errors && $changes && ($c = confirm_password()) !== '') $errors[] = $c;
        if (!$errors && $changes) {
            $pdo = db();
            $pdo->beginTransaction();
            foreach ($changes as $id => $diff) {   // имена столбцов — только из набора выше: name, role, active, pass_hash
                q('UPDATE ao_users SET ' . implode(' = ?, ', array_keys($diff)) . ' = ? WHERE id = ?', array_merge(array_values($diff), [$id]));
            }
            // на случай, когда два администратора одновременно отключают друг друга
            if ((int) q("SELECT COUNT(*) AS n FROM ao_users WHERE role = 'admin' AND active = 1")->fetch()['n'] < 1) {
                $pdo->rollBack();
                $errors[] = __('В панели должен остаться хотя бы один действующий администратор.');
            } else {
                $pdo->commit();
            }
        }
        if (!$errors) {
            flash($changes ? __('Изменения сохранены.') : __('Изменений нет.'));
            redirect(admin_url('users'));
        }
    }

    $select = function (string $name, string $cur, bool $off, string $label) use ($roles): string {
        $h = '<select name="' . e($name) . '" aria-label="' . e($label) . '"' . ($off ? ' disabled' : '') . '>';
        foreach ($roles as $k => $title) $h .= '<option value="' . $k . '"' . ($k === $cur ? ' selected' : '') . '>' . e($title) . '</option>';
        return $h . '</select>';
    };
    $out = '<div class="users">';
    if ($errors) $out .= '<div class="flash flash-err" role="alert">' . implode('<br>', array_map('e', $errors)) . '</div>';

    // --- новый пользователь
    $out .= '<section class="card form-card">' . card_head(__('Добавить пользователя'))
        . '<form method="post" class="card-body" autocomplete="off">' . csrf_field() . '<input type="hidden" name="act" value="add">'
        . '<p class="note">' . e(__('«Администратор» — полный доступ. «Менеджер» — заказы, клиенты и содержимое сайта. «Редактор» — только содержимое: товары, страницы, блог, фото и филиалы.')) . '</p>'
        . '<div class="field-row cols2">'
        . '<div class="field"><label class="lbl" for="nu-name">' . e(__('Имя')) . '</label><input id="nu-name" name="name" type="text" value="' . e($add['name']) . '" maxlength="80" autocomplete="off"></div>'
        . '<div class="field"><label class="lbl" for="nu-login">' . e(__('Логин')) . '</label><input id="nu-login" name="login" type="text" value="' . e($add['login']) . '" maxlength="60" autocomplete="off" autocapitalize="none" spellcheck="false" required>'
        . '<p class="hint">' . e(__('Латинскими буквами, например anar или anar@asioptik.az. С ним пользователь входит в админ-панель.')) . '</p></div>'
        . '</div><div class="field-row cols2">'
        . '<div class="field"><label class="lbl" for="nu-pass">' . e(__('Пароль (мин. 8 символов)')) . '</label><input id="nu-pass" name="password" type="password" autocomplete="new-password" minlength="8" required></div>'
        . '<div class="field"><label class="lbl" for="nu-role">' . e(__('Роль')) . '</label>' . str_replace('<select ', '<select id="nu-role" ', $select('role', isset($roles[$add['role']]) ? $add['role'] : 'editor', false, __('Роль'))) . '</div>'
        . '</div>' . confirm_field('nu-confirm')
        . '<div class="actions"><button type="submit" class="btn">' . icon('plus') . e(__('Добавить')) . '</button></div></form></section>';

    // --- все пользователи
    $rows = q('SELECT * FROM ao_users ORDER BY id')->fetchAll();
    $out .= '<section class="card">' . card_head(__('Все пользователи'), '<span class="muted">' . count($rows) . '</span>')
        . '<form method="post" autocomplete="off">' . csrf_field() . '<input type="hidden" name="act" value="save">'
        . '<p class="hint hint-card">' . e(__('Поле пароля оставьте пустым, если менять его не нужно. Отключённый пользователь войти не может, но его записи остаются.')) . '</p>'
        . '<div class="table-wrap"><table class="table utable"><thead><tr><th>' . e(__('Имя')) . '</th><th>' . e(__('Логин')) . '</th><th>' . e(__('Роль')) . '</th><th>' . e(__('Новый пароль'))
        . '</th><th>' . e(__('Активен')) . '</th><th>' . e(__('Вход')) . '</th></tr></thead><tbody>';
    foreach ($rows as $u) {
        $self = (int) $u['id'] === (int) $me['id'];
        $p = $posted[$u['id']] ?? [];
        $n = 'u[' . (int) $u['id'] . ']';
        $who = user_name($u);
        $out .= '<tr' . ((int) $u['active'] === 1 ? '' : ' class="off"') . '>'
            . '<td><input type="text" name="' . $n . '[name]" value="' . e($p['name'] ?? $u['name']) . '" maxlength="80" autocomplete="off" placeholder="' . e($u['login']) . '" aria-label="' . e(__('Имя')) . '"></td>'
            . '<td><span class="mono">' . e($u['login']) . '</span>' . ($self ? ' <span class="st st-done">' . e(__('это вы')) . '</span>' : '') . '</td>'
            . '<td>' . $select($n . '[role]', (string) ($p['role'] ?? $u['role']), $self, __('Роль: {name}', ['name' => $who])) . '</td>'
            . '<td>' . ($self
                ? '<a href="' . e(admin_url('profile')) . '">' . e(__('В «Моём профиле»')) . '</a>'
                : '<input type="password" name="' . $n . '[password]" autocomplete="new-password" placeholder="—" aria-label="' . e(__('Новый пароль: {name}', ['name' => $who])) . '">') . '</td>'
            . '<td><input type="checkbox" class="tick" name="' . $n . '[active]" value="1"' . ((int) ($p['active'] ?? $u['active']) === 1 ? ' checked' : '') . ($self ? ' disabled' : '')
            . ' aria-label="' . e(__('Активен: {name}', ['name' => $who])) . '"></td>'
            . '<td class="when">' . (!empty($u['last_login']) ? e(fmt_date((string) $u['last_login'])) : '<span class="muted">' . e(__('ещё не входил')) . '</span>') . '</td></tr>';
    }
    $out .= '</tbody></table></div><div class="card-body utable-foot">' . confirm_field('us-confirm')
        . '<div class="actions"><button type="submit" class="btn">' . e(__('Сохранить изменения')) . '</button></div></div></form></section></div>';

    admin_page(__('Пользователи'), $out, 'users');
}

/* ---------- «Мой профиль»: своё имя и пароль ---------- */
function admin_profile(): void
{
    $me = me();
    $error = '';
    if (is_post() && ($_POST['act'] ?? '') === 'name') {
        $name = mb_substr(trim((string) preg_replace('/[\x00-\x1F\x7F]/u', '', is_string($_POST['name'] ?? null) ? $_POST['name'] : '')), 0, 80);
        q('UPDATE ao_users SET name = ? WHERE id = ?', [$name, $me['id']]);
        flash(__('Сохранено.'));
        redirect(admin_url('profile'));
    }
    if (is_post()) {
        $old = is_string($_POST['old'] ?? null) ? $_POST['old'] : '';
        $new = is_string($_POST['new'] ?? null) ? $_POST['new'] : '';
        if (login_tries() >= 5) $error = __('Слишком много неверных попыток. Подождите 15 минут и попробуйте снова.');
        elseif (!password_verify($old, (string) $me['pass_hash'])) {
            login_fail();
            $error = __('Текущий пароль указан неверно.');
        } elseif (mb_strlen($new) < 8) $error = __('Новый пароль должен быть не короче 8 символов.');
        elseif (weak_password($new, (string) $me['login'])) $error = __('Слишком простой пароль: такие подбирают первыми. Придумайте другой.');
        elseif ($new !== (is_string($_POST['new2'] ?? null) ? $_POST['new2'] : '')) $error = __('Новый пароль и его повтор не совпадают.');
        else {
            $hash = password_hash($new, PASSWORD_DEFAULT);
            q('UPDATE ao_users SET pass_hash = ? WHERE id = ?', [$hash, $me['id']]);
            session_regenerate_id(true);
            $_SESSION['pm'] = pass_mark($hash);   // этот сеанс остаётся, остальные сеансы пользователя заканчиваются
            flash(__('Пароль изменён.'));
            redirect(admin_url('profile'));
        }
    }
    $role = role_names()[$me['role']] ?? (string) $me['role'];
    admin_page(__('Мой профиль'),
        ($error ? '<p class="flash flash-err" role="alert">' . e($error) . '</p>' : '')
        . '<form method="post" class="form narrow profile">' . csrf_field() . '<input type="hidden" name="act" value="name">'
        . '<h2 class="block">' . e(__('Профиль')) . '</h2>'
        . '<div class="field"><label class="lbl" for="pf-name">' . e(__('Имя')) . '</label><input id="pf-name" name="name" type="text" value="' . e((string) $me['name']) . '" maxlength="80" autocomplete="name" placeholder="' . e((string) $me['login']) . '">'
        . '<p class="hint">' . e(__('Показывается внизу меню и в списке пользователей.')) . '</p></div>'
        . '<dl class="facts"><div><dt>' . e(__('Логин')) . '</dt><dd class="mono">' . e((string) $me['login']) . '</dd></div><div><dt>' . e(__('Роль')) . '</dt><dd>' . e($role) . '</dd></div></dl>'
        . '<button type="submit" class="btn">' . e(__('Сохранить')) . '</button></form>'
        . '<form method="post" class="form narrow profile">' . csrf_field() . '<input type="hidden" name="act" value="pass">'
        . '<h2 class="block">' . e(__('Пароль')) . '</h2>'
        . '<div class="field"><label class="lbl" for="old">' . e(__('Текущий пароль')) . '</label><input id="old" name="old" type="password" autocomplete="current-password" required></div>'
        . '<div class="field"><label class="lbl" for="new">' . e(__('Новый пароль')) . '</label><input id="new" name="new" type="password" autocomplete="new-password" required minlength="8"><p class="hint">' . e(__('Не короче 8 символов.')) . '</p></div>'
        . '<div class="field"><label class="lbl" for="new2">' . e(__('Новый пароль ещё раз')) . '</label><input id="new2" name="new2" type="password" autocomplete="new-password" required></div>'
        . '<button type="submit" class="btn">' . e(__('Изменить пароль')) . '</button></form>', 'profile');
}

<?php
/* Оформление админ-панели: общий каркас страницы, поля форм и разбор отправленной формы. */
declare(strict_types=1);

function admin_url(string $p = '', array $q = []): string
{
    $q = ($p === '' ? [] : ['p' => $p]) + $q;
    return base_path() . 'admin/' . ($q ? '?' . http_build_query($q) : '');
}

function flash(?string $msg = null, string $kind = 'ok'): ?array
{
    if ($msg !== null) {
        $_SESSION['flash'] = [$kind, $msg];
        return null;
    }
    $f = $_SESSION['flash'] ?? null;
    unset($_SESSION['flash']);
    return $f;
}

/** Предупреждение, когда админ-панель открыта без шифрования: пароль и заказы видны по дороге. */
function https_note(): string
{
    if (is_https() || is_local()) return '';
    return '<p class="flash flash-warn" role="alert">Админ-панель открыта по http, без шифрования: пароль и данные покупателей передаются открыто. '
        . 'Включите сертификат SSL в панели хостинга и уберите решётки в трёх строках файла .htaccess — после этого сайт всегда открывается по https.</p>';
}

function csrf_field(): string
{
    return '<input type="hidden" name="csrf" value="' . e(csrf_token()) . '">';
}

/** Каркас страницы админ-панели. */
function admin_page(string $title, string $body, string $current = ''): void
{
    $nav = [
        'orders' => 'Заказы и заявки', 'list:product' => 'Товары', 'list:category' => 'Разделы каталога', 'list:brand' => 'Бренды',
        'list:post' => 'Блог', 'list:service' => 'Услуги мастерской', 'doc:about' => 'Страница «О нас»', 'banners' => 'Баннеры и фото',
        'doc:config' => 'Настройки', 'password' => 'Пароль',
    ];
    $new = (int) (q("SELECT COUNT(*) AS n FROM ao_orders WHERE status = 'new'")->fetch()['n'] ?? 0);
    $links = '';
    foreach ($nav as $key => $label) {
        $p = explode(':', $key);
        $url = $p[0] === 'list' ? admin_url('list', ['type' => $p[1]]) : ($p[0] === 'doc' ? admin_url('doc', ['name' => $p[1]]) : admin_url($p[0]));
        $badge = $key === 'orders' && $new ? ' <span class="n">' . $new . '</span>' : '';
        $links .= '<a href="' . e($url) . '"' . ($current === $key ? ' aria-current="page"' : '') . '>' . e($label) . $badge . '</a>';
    }
    $flash = flash();
    $base = base_path();
    $ver = substr(md5((string) @filemtime(ROOT . '/assets/css/admin.css')), 0, 8);
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow">'
        . '<title>' . e($title) . ' — админ-панель Asioptik</title><link rel="stylesheet" href="' . e($base) . 'assets/css/admin.css?v=' . $ver . '"></head><body>'
        . '<div class="adm"><aside class="side"><a class="brand" href="' . e(admin_url()) . '">asi<b>optik</b><small>админ-панель</small></a>'
        . '<button type="button" class="menu-btn" aria-expanded="false" aria-controls="adm-nav">Меню</button>'
        . '<nav id="adm-nav">' . $links . '</nav>'
        . '<div class="side-foot"><a href="' . e($base) . '" target="_blank" rel="noopener">Открыть сайт</a>'
        . '<form method="post" action="' . e(admin_url('logout')) . '">' . csrf_field() . '<button type="submit" class="link">Выйти</button></form></div></aside>'
        . '<main class="main"><h1>' . e($title) . '</h1>' . https_note()
        . ($flash ? '<p class="flash flash-' . e($flash[0]) . '" role="status">' . e($flash[1]) . '</p>' : '')
        . $body . '</main></div><script src="' . e($base) . 'assets/js/admin.js?v=' . $ver . '"></script></body></html>';
    exit;
}

/** Страница без меню: вход. */
function admin_bare(string $title, string $body): void
{
    $base = base_path();
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow">'
        . '<title>' . e($title) . ' — Asioptik</title><link rel="stylesheet" href="' . e($base) . 'assets/css/admin.css"></head><body class="bare">'
        . '<main class="card"><p class="brand">asi<b>optik</b></p><h1>' . e($title) . '</h1>' . https_note() . $body . '</main></body></html>';
    exit;
}

/* ---------- поля формы ---------- */
function field_options(array $f): array
{
    $o = $f['options'] ?? [];
    return is_string($o) ? $o() : $o;
}

function img_preview(?string $path): string
{
    if (!$path) return '';
    return '<img class="thumb" src="' . e(img_url($path)) . '" alt="">';
}

/** Все поля формы по описанию из schema.php. */
function form_fields(array $fields, array $data, array $errors = []): string
{
    $out = '';
    foreach ($fields as $f) {
        $k = $f['key'];
        $v = dget($data, $k);
        $name = 'f[' . $k . ']';
        $id = 'f-' . preg_replace('~[^a-z0-9]+~i', '-', $k);
        $err = $errors[$k] ?? '';
        $hint = isset($f['hint']) ? '<p class="hint">' . e($f['hint']) . '</p>' : '';
        $label = e($f['label']) . (!empty($f['req']) ? ' <span class="req" title="обязательно">*</span>' : '');
        $in = '';
        switch ($f['type']) {
            case 'text':
            case 'date':
            case 'number':
                $type = $f['type'] === 'date' ? 'date' : 'text';
                $extra = $f['type'] === 'number' ? ' inputmode="decimal" class="short"' : '';
                $in = '<label class="lbl" for="' . $id . '">' . $label . '</label><input id="' . $id . '" type="' . $type . '" name="' . e($name) . '" value="' . e(is_scalar($v) ? $v : '') . '"' . $extra . '>';
                break;
            case 'bool':
                $in = '<label class="check"><input type="checkbox" name="' . e($name) . '" value="1"' . ($v ? ' checked' : '') . '> <span>' . $label . '</span></label>';
                break;
            case 'select':
                $in = '<label class="lbl" for="' . $id . '">' . $label . '</label><select id="' . $id . '" name="' . e($name) . '">';
                if (isset($f['empty']) || empty($f['req'])) $in .= '<option value="">' . e($f['empty'] ?? '—') . '</option>';
                foreach (field_options($f) as $ov => $ol) $in .= '<option value="' . e($ov) . '"' . ((string) $v === (string) $ov ? ' selected' : '') . '>' . e($ol) . '</option>';
                $in .= '</select>';
                break;
            case 'checks':
                $in = '<span class="lbl">' . $label . '</span><div class="checks">';
                foreach (field_options($f) as $ov => $ol) $in .= '<label class="check"><input type="checkbox" name="' . e($name) . '[]" value="' . e($ov) . '"' . (is_array($v) && in_array($ov, $v, true) ? ' checked' : '') . '> <span>' . e($ol) . '</span></label>';
                $in .= '</div>';
                break;
            case 'i18n':
            case 'i18n_area':
            case 'i18n_lines':
            case 'specs':
                $in = '<span class="lbl">' . $label . '</span><div class="langs' . ($f['type'] === 'i18n' ? '' : ' langs-area') . '">';
                foreach (LANGS as $l) {
                    $val = is_array($v) ? ($v[$l] ?? '') : '';
                    if ($f['type'] === 'i18n_lines' && is_array($val)) $val = implode("\n", $val);
                    if ($f['type'] === 'specs' && is_array($val)) $val = implode("\n", array_map(function ($r) {
                        return is_array($r) ? ($r[0] ?? '') . ': ' . ($r[1] ?? '') : (string) $r;
                    }, $val));
                    $val = is_scalar($val) ? (string) $val : '';
                    $fid = $id . '-' . $l;
                    $in .= '<div class="lang"><label for="' . $fid . '">' . strtoupper($l) . '</label>';
                    $in .= $f['type'] === 'i18n'
                        ? '<input id="' . $fid . '" type="text" name="' . e($name) . '[' . $l . ']" value="' . e($val) . '" lang="' . $l . '">'
                        : '<textarea id="' . $fid . '" name="' . e($name) . '[' . $l . ']" rows="' . (int) ($f['rows'] ?? 5) . '" lang="' . $l . '">' . e($val) . '</textarea>';
                    $in .= '</div>';
                }
                $in .= '</div>';
                break;
            case 'image':
                $in = '<span class="lbl">' . $label . '</span><div class="imgf">' . img_preview(is_string($v) ? $v : null)
                    . '<div><input type="file" name="file[' . e($k) . ']" accept="image/jpeg,image/png,image/webp" data-max="' . upload_limit() . '" aria-label="' . e($f['label']) . '">'
                    . '<p class="file-note" aria-live="polite" hidden></p>'
                    . (is_string($v) && $v !== '' ? '<label class="check"><input type="checkbox" name="remove[' . e($k) . ']" value="1"> <span>Убрать фото</span></label>' : '')
                    . '</div></div>';
                break;
            case 'colors':
                $rows = is_array($v) ? array_values($v) : [];
                for ($i = 0; $i < 2; $i++) $rows[] = [];   // пустые строки для новых цветов
                $in = '<span class="lbl">' . $label . '</span><div class="colors" data-rows>';
                foreach ($rows as $i => $c) {
                    $extra = array_intersect_key(is_array($c) ? $c : [], ['a' => 1, 'c2' => 1, 'l' => 1, 'img' => 1]);
                    $n = "{$name}[$i]";
                    $in .= '<div class="color-row">';
                    foreach (LANGS as $l) $in .= '<input type="text" name="' . e($n) . '[n][' . $l . ']" value="' . e($c['n'][$l] ?? '') . '" placeholder="Название ' . strtoupper($l) . '" aria-label="Название цвета, ' . strtoupper($l) . '">';
                    $in .= '<input type="text" class="short" name="' . e($n) . '[c]" value="' . e($c['c'] ?? '') . '" placeholder="#1f1f22" aria-label="Код цвета">'
                        . '<span class="sw" style="background:' . e(preg_match('~^#[0-9a-f]{3,8}$~i', (string) ($c['c'] ?? '')) ? $c['c'] : 'transparent') . '"></span>'
                        . '<input type="hidden" name="' . e($n) . '[x]" value="' . e($extra ? to_json($extra) : '') . '"></div>';
                }
                $in .= '</div>';
                break;
        }
        $out .= '<div class="field' . ($err ? ' is-invalid' : '') . '">' . $in . ($err ? '<p class="err">' . e($err) . '</p>' : '') . $hint . '</div>';
    }
    return $out;
}

function upload_for(string $key): ?array
{
    if (!isset($_FILES['file']['name'][$key])) return null;
    $f = [];
    foreach (['name', 'type', 'tmp_name', 'error', 'size'] as $p) $f[$p] = $_FILES['file'][$p][$key] ?? null;
    return $f;
}

/**
 * Разбирает отправленную форму: возвращает обновлённые данные и список ошибок по полям.
 * Всё, чего нет в описании полей, в данных остаётся как было.
 */
function form_parse(array $fields, array $data, array $post, array &$errors): array
{
    $clean = function ($v, int $max = 2000): string {
        $s = is_scalar($v) ? (string) $v : '';
        return mb_substr(trim(str_replace(["\r\n", "\r"], "\n", $s)), 0, $max);
    };
    $in = isset($post['f']) && is_array($post['f']) ? $post['f'] : [];
    foreach ($fields as $f) {
        $k = $f['key'];
        $raw = $in[$k] ?? null;
        $req = !empty($f['req']);
        switch ($f['type']) {
            case 'text':
                $v = $clean($raw, 500);
                if ($v === '' && $req) $errors[$k] = 'Заполните это поле.';
                if ($v === '') dunset($data, $k); else dset($data, $k, $v);
                break;
            case 'date':
                $v = $clean($raw, 10);
                if (!preg_match('~^\d{4}-\d{2}-\d{2}$~', $v)) {
                    if ($req || $v !== '') $errors[$k] = 'Укажите дату.';
                    break;
                }
                dset($data, $k, $v);
                break;
            case 'number':
                $v = str_replace([',', ' '], ['.', ''], $clean($raw, 20));
                if ($v === '') {
                    if ($req) $errors[$k] = 'Укажите число.';
                    dunset($data, $k);
                    break;
                }
                if (!is_numeric($v) || (float) $v < 0 || (float) $v > 1000000) {
                    $errors[$k] = 'Здесь должно быть число, например 120 или 12.5.';
                    break;
                }
                dset($data, $k, (float) $v == (int) $v ? (int) $v : round((float) $v, 2));
                break;
            case 'bool':
                dset($data, $k, !empty($raw));
                break;
            case 'select':
                $v = $clean($raw, 120);
                if ($v !== '' && !array_key_exists($v, field_options($f))) $v = '';
                if ($v === '' && $req) $errors[$k] = 'Выберите значение.';
                if ($v === '') dunset($data, $k); else dset($data, $k, $v);
                break;
            case 'checks':
                $opts = array_map('strval', array_keys(field_options($f)));
                $v = array_values(array_intersect($opts, is_array($raw) ? array_map('strval', $raw) : []));
                if ($v) dset($data, $k, $v); else dunset($data, $k);
                break;
            case 'i18n':
            case 'i18n_area':
                $v = [];
                foreach (LANGS as $l) {
                    $s = $clean(is_array($raw) ? ($raw[$l] ?? '') : '', $f['type'] === 'i18n' ? 300 : 3000);
                    if ($s !== '') $v[$l] = $s;
                }
                if ($req && empty($v['az'])) $errors[$k] = 'Заполните хотя бы азербайджанский вариант (AZ): это основной язык сайта.';
                if ($v) dset($data, $k, $v); else dunset($data, $k);
                break;
            case 'i18n_lines':
            case 'specs':
                $v = [];
                foreach (LANGS as $l) {
                    $lines = array_values(array_filter(array_map('trim', explode("\n", $clean(is_array($raw) ? ($raw[$l] ?? '') : '', 20000))), 'strlen'));
                    if ($f['type'] === 'specs') {
                        $lines = array_map(function ($line) {
                            $p = explode(':', $line, 2);
                            return [trim($p[0]), trim($p[1] ?? '')];
                        }, $lines);
                    }
                    if ($lines) $v[$l] = $lines;
                }
                if ($req && empty($v['az'])) $errors[$k] = 'Заполните хотя бы азербайджанский вариант (AZ).';
                if ($v) dset($data, $k, $v); else dunset($data, $k);
                break;
            case 'colors':
                $v = [];
                foreach (is_array($raw) ? $raw : [] as $row) {
                    if (!is_array($row)) continue;
                    $n = [];
                    foreach (LANGS as $l) {
                        $s = $clean($row['n'][$l] ?? '', 80);
                        if ($s !== '') $n[$l] = $s;
                    }
                    $c = $clean($row['c'] ?? '', 20);
                    if (!$n) continue;
                    if (!preg_match('~^(#[0-9a-fA-F]{3,8}|[a-z]{3,20})$~', $c)) {
                        $errors[$k] = 'Код цвета должен выглядеть как #1f1f22.';
                        $c = '#888888';
                    }
                    $extra = json_decode((string) ($row['x'] ?? ''), true);
                    $extra = is_array($extra) ? array_intersect_key($extra, ['a' => 1, 'c2' => 1, 'l' => 1, 'img' => 1]) : [];
                    $v[] = ['n' => $n, 'c' => $c] + $extra;
                }
                if ($v) dset($data, $k, $v); else dunset($data, $k);
                break;
            case 'image':
                $old = dget($data, $k);
                $file = upload_for($k);
                $err = null;
                $new = $file ? save_upload($file, (string) ($f['dir'] ?? 'img'), $err) : null;
                if ($err) $errors[$k] = $err;
                if ($new) {
                    delete_upload(is_string($old) ? $old : null);
                    dset($data, $k, $new);
                } elseif (!empty($post['remove'][$k])) {
                    delete_upload(is_string($old) ? $old : null);
                    dunset($data, $k);
                }
                break;
        }
    }
    return $data;
}

function fmt_date(string $dt): string
{
    $t = strtotime($dt);
    return $t ? date('d.m.Y H:i', $t) : $dt;
}

function fmt_money($n): string
{
    if ($n === null || $n === '') return '';
    $f = (float) $n;
    return rtrim(rtrim(number_format($f, 2, '.', ' '), '0'), '.') . ' ₼';
}

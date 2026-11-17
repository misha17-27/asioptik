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
    return '<p class="flash flash-warn" role="alert">' . __('Админ-панель открыта по http, без шифрования: пароль и данные покупателей передаются открыто.') . ' '
        . __('Включите сертификат SSL в панели хостинга и уберите решётки в трёх строках файла .htaccess — после этого сайт всегда открывается по https.') . '</p>';
}

/**
 * Подсказка на «Обзоре», пока сайт открыт по временному адресу (подпапка на другом домене): объясняет,
 * почему сайта нет в поиске, и что после переезда на основной адрес ничего переключать не придётся.
 */
function preview_note(): string
{
    if (is_local() || !site_is_preview()) return '';
    $show = function (string $url): string {
        return '<b>' . e((string) preg_replace('~^https?://~i', '', $url)) . '</b>';
    };
    return '<p class="note note-top">' . strtr(e(__('Сайт открыт по временному адресу {here}. Поисковики его не показывают — так в поиске не окажется двух копий сайта. Когда сайт откроется на основном адресе {main}, поисковики увидят его сами: переключать ничего не нужно.')),
        ['{here}' => $show(site_here_url()), '{main}' => $show(site_main_url())])
        . ' <a href="' . e(admin_url('doc', ['name' => 'config'])) . '">' . e(__('Основной адрес задаётся в «Настройках сайта».')) . '</a></p>';
}

function csrf_field(): string
{
    return '<input type="hidden" name="csrf" value="' . e(csrf_token()) . '">';
}

/** Каркас страницы админ-панели. */
/** Контурные значки меню и кнопок (20×20). */
function icon(string $name): string
{
    static $paths = [
        'home' => '<path d="M3 9.5 10 3l7 6.5V17h-4.500v-5h-5v5H3z"/>',
        'orders' => '<path d="M5 3h10v14l-2.500-1.500L10 17l-2.500-1.500L5 17z"/><path d="M8 7.500h4M8 10.500h4"/>',
        'users' => '<circle cx="7.500" cy="7" r="3"/><path d="M2 17c.400-3 2.600-4.500 5.500-4.500s5.100 1.500 5.500 4.500"/><path d="M13.500 4.200a3 3 0 0 1 0 5.600M15.500 13c1.500.700 2.300 2 2.500 4"/>',
        'page' => '<path d="M5 2.500h7l3 3v12H5z"/><path d="M8 9.500h4M8 12.500h4"/>',
        'blog' => '<path d="M3 5h14M3 10h9M3 15h14"/>',
        'image' => '<rect x="3" y="4" width="14" height="12" rx="2"/><circle cx="7.500" cy="8.500" r="1.300"/><path d="m4 15 4.500-4.500 3 3 2-2L17 15"/>',
        'box' => '<path d="M3 6.500 10 3l7 3.500v7L10 17l-7-3.500z"/><path d="M3 6.500 10 10l7-3.500M10 10v7"/>',
        'grid' => '<rect x="3" y="3" width="6" height="6" rx="1"/><rect x="11" y="3" width="6" height="6" rx="1"/><rect x="3" y="11" width="6" height="6" rx="1"/><rect x="11" y="11" width="6" height="6" rx="1"/>',
        'tag' => '<path d="M3 3h7l7 7-7 7-7-7z"/><circle cx="7" cy="7" r="1.200"/>',
        'tool' => '<path d="M16.500 5.500 13.800 8.200l-2-2 2.700-2.700a4 4 0 0 0-5.100 5L3.500 14.400a1.500 1.500 0 0 0 2.100 2.100l5.900-5.900a4 4 0 0 0 5-5.100z"/>',
        'gear' => '<circle cx="10" cy="10" r="2.500"/><path d="M10 2.500v2.300M10 15.200v2.300M2.500 10h2.300M15.200 10h2.300M4.700 4.700l1.600 1.600M13.700 13.700l1.600 1.600M4.700 15.300l1.600-1.600M13.700 6.300l1.600-1.600"/>',
        'key' => '<circle cx="7" cy="13" r="3.500"/><path d="m9.500 10.500 7-7M13.500 6.500l2 2M11.500 8.500l1.500 1.500"/>',
        'shield' => '<path d="M10 2.500 16 5v4.500c0 3.700-2.500 6.600-6 8-3.500-1.400-6-4.300-6-8V5z"/><path d="m7.300 10 2 2 3.500-3.800"/>',
        'out' => '<path d="M8 3H4v14h4"/><path d="M12.500 6.500 16 10l-3.500 3.500M16 10H7.500"/>',
        'ext' => '<path d="M11.500 3H17v5.500M17 3l-8 8"/><path d="M14.500 11.500V17H3V5.500h5.500"/>',
        'edit' => '<path d="m3 17 .800-3.700 9.700-9.700a1.400 1.400 0 0 1 2 0l.900.900a1.400 1.400 0 0 1 0 2l-9.700 9.700z"/>',
        'trash' => '<path d="M4 6h12M8 6V3.500h4V6M5.500 6l.700 11h7.600l.700-11"/>',
        'plus' => '<path d="M10 4v12M4 10h12"/>',
        'globe' => '<circle cx="10" cy="10" r="7"/><path d="M3 10h14M10 3c2.200 2 3.300 4.300 3.300 7s-1.100 5-3.300 7c-2.200-2-3.300-4.300-3.300-7S7.800 5 10 3z"/>',
        'copy' => '<rect x="7" y="7" width="10" height="10" rx="1.500"/><path d="M13 7V4.500A1.500 1.500 0 0 0 11.500 3h-7A1.500 1.500 0 0 0 3 4.500v7A1.500 1.500 0 0 0 4.500 13H7"/>',
    ];
    return '<svg class="ic" viewBox="0 0 20 20" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.600" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' . ($paths[$name] ?? '') . '</svg>';
}

/** Переключатель языка админ-панели: ссылки на эту же страницу, выбор запоминается (см. admin_run). */
function ui_switch(): string
{
    $q = $_GET;
    $p = is_string($q['p'] ?? null) ? $q['p'] : '';
    unset($q['ui'], $q['p']);
    $out = '<div class="uis" role="group" aria-label="' . e(__('Язык админ-панели')) . '">' . icon('globe');
    foreach (UI_LANGS as $l => $name) {
        $out .= '<a href="' . e(admin_url($p, $q + ['ui' => $l])) . '" lang="' . $l . '" hreflang="' . $l . '" title="' . e($name) . '"' . ($l === ui_lang() ? ' aria-current="true"' : '') . '>' . strtoupper($l) . '</a>';
    }
    return $out . '</div>';
}

/** Надписи, которые показывает скрипт админ-панели (assets/js/admin.js), на языке интерфейса. */
function admin_js_texts(): array
{
    return [
        'fileBad' => __('Файл «{name}» не подходит: нужна картинка JPG, PNG или WebP.'),
        'filePrep' => __('Готовлю фото…'),
        'fileBig' => __('Файл {size} — больше, чем принимает хостинг ({max}). Уменьшите фото и выберите его снова.'),
        'fileSmall' => __('Фото уменьшено: {from} → {to}. Нажмите «Сохранить».'),
        'fileOk' => __('Фото выбрано: {size}. Нажмите «Сохранить».'),
        'count' => __('{n} из {max} знаков'),
        'countAuto' => __('{n} из {max} знаков — текст сайта'),
        'mb' => __('МБ'),
        'kb' => __('КБ'),
    ];
}

/** Переключатель языка для форм: показывает поля одного языка за раз. Без скриптов видны все три. */
function lang_switch(): string
{
    $out = '<div class="lgs" role="group" aria-label="' . e(__('Язык текстов')) . '">';
    foreach (['ru', 'az', 'en'] as $l) $out .= '<button type="button" class="lg-btn" data-lg-set="' . $l . '" aria-pressed="false">' . strtoupper($l) . '</button>';
    return $out . '</div>';
}

/** Заголовок карточки: название слева, справа ссылка или пояснение. */
function card_head(string $title, string $right = '', string $extra = ''): string
{
    return '<div class="card-head"><h2>' . e($title) . '</h2>' . $extra . ($right !== '' ? '<div class="card-side">' . $right . '</div>' : '') . '</div>';
}

/** Числа для меню: сколько чего в базе. Считаются один раз за запрос. */
function admin_counts(): array
{
    static $c = null;
    if ($c !== null) return $c;
    $c = ['new' => 0, 'orders' => 0, 'sales' => 0, 'clients' => 0];
    foreach (q('SELECT type, COUNT(*) AS n FROM ao_items GROUP BY type')->fetchAll() as $r) $c[$r['type']] = (int) $r['n'];
    $o = q("SELECT COUNT(*) AS n, SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) AS fresh, SUM(CASE WHEN kind = 'order' THEN 1 ELSE 0 END) AS sales, COUNT(DISTINCT phone) AS people FROM ao_orders")->fetch();
    $c['orders'] = (int) ($o['n'] ?? 0);
    $c['new'] = (int) ($o['fresh'] ?? 0);
    $c['sales'] = (int) ($o['sales'] ?? 0);
    $c['clients'] = (int) ($o['people'] ?? 0);
    return $c;
}

/**
 * Страница админ-панели: слева меню по группам, сверху заголовок и кнопки.
 * $actions — кнопки страницы рядом с «Сайт» и «Выйти» (например, «Добавить товар»).
 */
/** Начало формы в карточке: слева название и переключатель языка текстов, справа ссылка назад. */
function form_open(string $title, string $right = '', string $class = ''): string
{
    return '<form method="post" enctype="multipart/form-data" class="card form-card' . ($class !== '' ? ' ' . $class : '') . '">' . csrf_field()
        . card_head($title, $right, lang_switch()) . '<div class="card-body">';
}

/** Конец формы: кнопка «Сохранить» остаётся внизу экрана, пока листают поля. */
function form_close(string $after = ''): string
{
    return '</div><div class="actions actions-sticky"><button type="submit" class="btn">' . __('Сохранить') . '</button>' . $after . '</div></form>';
}

/** Страница админ-панели. $doc — название для вкладки браузера, если оно подробнее заголовка. */
function admin_page(string $title, string $body, string $current = '', string $actions = '', string $doc = ''): void
{
    $c = admin_counts();
    $groups = [
        __('Магазин') => [['home', __('Обзор'), 'home', null], ['orders', __('Заказы'), 'orders', $c['new'] ?: null], ['clients', __('Клиенты'), 'users', $c['clients'] ?: null]],
        __('Контент') => [['pages', __('Страницы'), 'page', null], ['list:post', __('Блог'), 'blog', $c['post'] ?? null], ['banners', __('Баннеры и фото'), 'image', null]],
        __('Каталог') => [['list:product', __('Товары'), 'box', $c['product'] ?? null], ['list:category', __('Разделы'), 'grid', $c['category'] ?? null],
            ['list:brand', __('Бренды'), 'tag', $c['brand'] ?? null], ['list:service', __('Услуги мастерской'), 'tool', $c['service'] ?? null]],
        __('Настройки') => [['doc:config', __('Настройки сайта'), 'gear', null], ['security', __('Безопасность'), 'shield', null], ['password', __('Пароль'), 'key', null]],
    ];
    $links = '';
    foreach ($groups as $group => $items) {
        $links .= '<p class="nav-group">' . e($group) . '</p>';
        foreach ($items as [$key, $label, $ic, $n]) {
            $p = explode(':', $key);
            $url = $p[0] === 'list' ? admin_url('list', ['type' => $p[1]]) : ($p[0] === 'doc' ? admin_url('doc', ['name' => $p[1]]) : admin_url($p[0] === 'home' ? '' : $p[0]));
            $badge = $n ? '<span class="n' . ($key === 'orders' ? ' n-new' : '') . '"' . ($key === 'orders' ? ' title="' . e(__('Новые')) . '"' : '') . '>' . (int) $n . '</span>' : '';
            $links .= '<a href="' . e($url) . '"' . ($current === $key ? ' aria-current="page"' : '') . '>' . icon($ic) . '<span>' . e($label) . '</span>' . $badge . '</a>';
        }
    }
    $flash = flash();
    $base = base_path();
    $ver = substr(md5((string) @filemtime(ROOT . '/assets/css/admin.css') . @filemtime(ROOT . '/assets/js/admin.js')), 0, 8);
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><html lang="' . ui_lang() . '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow">'
        . '<title>' . e($doc !== '' ? $doc : $title) . ' ' . __('— админ-панель Asioptik') . '</title><link rel="icon" href="' . e($base) . 'favicon.ico"><link rel="stylesheet" href="' . e($base) . 'assets/css/admin.css?v=' . $ver . '"></head><body>'
        . '<div class="adm"><aside class="side"><a class="brand" href="' . e(admin_url()) . '">asi<b>optik</b><small>Admin</small></a>'
        . '<button type="button" class="menu-btn" aria-expanded="false" aria-controls="adm-nav">' . __('Меню') . '</button>'
        . '<nav id="adm-nav" aria-label="' . e(__('Разделы админ-панели')) . '">' . $links . '</nav></aside>'
        . '<main class="main"><header class="top"><h1>' . e($title) . '</h1><div class="top-acts">' . $actions . ui_switch()
        . '<a class="btn btn-line" href="' . e($base) . '" target="_blank" rel="noopener">' . icon('ext') . __('Сайт') . '</a>'
        . '<form method="post" class="logout" action="' . e(admin_url('logout')) . '">' . csrf_field() . '<button type="submit" class="btn">' . icon('out') . __('Выйти') . '</button></form></div></header>'
        . https_note()
        . ($flash ? '<p class="flash flash-' . e($flash[0]) . '" role="status">' . e($flash[1]) . '</p>' : '')
        . $body . '</main></div><script type="application/json" id="ao-i18n">' . json_encode(admin_js_texts(), JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP) . '</script>'
        . '<script src="' . e($base) . 'assets/js/admin.js?v=' . $ver . '"></script></body></html>';
    exit;
}

function admin_bare(string $title, string $body): void
{
    $base = base_path();
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><html lang="' . ui_lang() . '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow">'
        . '<title>' . e($title) . ' — Asioptik</title><link rel="icon" href="' . e($base) . 'favicon.ico"><link rel="stylesheet" href="' . e($base) . 'assets/css/admin.css"></head><body class="bare">'
        . '<main class="card">' . ui_switch() . '<p class="brand">asi<b>optik</b></p><h1>' . e($title) . '</h1>' . https_note() . $body . '</main></body></html>';
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
        if ($f['type'] === 'head') {   // подзаголовок внутри формы
            $out .= '<h3 class="block">' . e($f['label']) . '</h3>' . (isset($f['hint']) ? '<p class="hint hint-block">' . e($f['hint']) . '</p>' : '');
            continue;
        }
        $k = $f['key'];
        $v = dget($data, $k);
        $name = 'f[' . $k . ']';
        $id = 'f-' . preg_replace('~[^a-z0-9]+~i', '-', $k);
        $err = $errors[$k] ?? '';
        $hint = isset($f['hint']) ? '<p class="hint">' . e($f['hint']) . '</p>' : '';
        $label = e($f['label']) . (!empty($f['req']) ? ' <span class="req" title="' . e(__('обязательно')) . '">*</span>' : '');
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
                    // ph — текст, который сайт поставит сам, пока поле пустое; count — сколько знаков обычно помещается в поиске
                    $more = (isset($f['ph'][$l]) && $f['ph'][$l] !== '' ? ' placeholder="' . e($f['ph'][$l]) . '"' : '') . (isset($f['count']) ? ' data-count="' . (int) $f['count'] . '"' : '');
                    $in .= '<div class="lang" data-lg="' . $l . '"><label for="' . $fid . '">' . strtoupper($l) . '</label>';
                    $in .= $f['type'] === 'i18n'
                        ? '<input id="' . $fid . '" type="text" name="' . e($name) . '[' . $l . ']" value="' . e($val) . '" lang="' . $l . '"' . $more . '>'
                        : '<textarea id="' . $fid . '" name="' . e($name) . '[' . $l . ']" rows="' . (int) ($f['rows'] ?? 5) . '" lang="' . $l . '"' . $more . '>' . e($val) . '</textarea>';
                    $in .= '</div>';
                }
                $in .= '</div>';
                break;
            case 'image':
                $in = '<span class="lbl">' . $label . '</span><div class="imgf">' . img_preview(is_string($v) ? $v : null)
                    . '<div><input type="file" name="file[' . e($k) . ']" accept="image/jpeg,image/png,image/webp" data-max="' . upload_limit() . '" aria-label="' . e($f['label']) . '">'
                    . '<p class="file-note" aria-live="polite" hidden></p>'
                    . (is_string($v) && $v !== '' ? '<label class="check"><input type="checkbox" name="remove[' . e($k) . ']" value="1"> <span>' . __('Убрать фото') . '</span></label>' : '')
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
                    foreach (LANGS as $l) $in .= '<input type="text" name="' . e($n) . '[n][' . $l . ']" value="' . e($c['n'][$l] ?? '') . '" placeholder="' . e(__('Название {lang}', ['lang' => strtoupper($l)])) . '" aria-label="' . e(__('Название цвета, {lang}', ['lang' => strtoupper($l)])) . '">';
                    $in .= '<input type="text" class="short" name="' . e($n) . '[c]" value="' . e($c['c'] ?? '') . '" placeholder="#1f1f22" aria-label="' . e(__('Код цвета')) . '">'
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
        if ($f['type'] === 'head') continue;
        $k = $f['key'];
        $raw = $in[$k] ?? null;
        $req = !empty($f['req']);
        switch ($f['type']) {
            case 'text':
                $v = $clean($raw, 500);
                if ($v === '' && $req) $errors[$k] = __('Заполните это поле.');
                if ($v === '') dunset($data, $k); else dset($data, $k, $v);
                break;
            case 'date':
                $v = $clean($raw, 10);
                if (!preg_match('~^\d{4}-\d{2}-\d{2}$~', $v)) {
                    if ($req || $v !== '') $errors[$k] = __('Укажите дату.');
                    break;
                }
                dset($data, $k, $v);
                break;
            case 'number':
                $v = str_replace([',', ' '], ['.', ''], $clean($raw, 20));
                if ($v === '') {
                    if ($req) $errors[$k] = __('Укажите число.');
                    dunset($data, $k);
                    break;
                }
                if (!is_numeric($v) || (float) $v < 0 || (float) $v > 1000000) {
                    $errors[$k] = __('Здесь должно быть число, например 120 или 12.5.');
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
                if ($v === '' && $req) $errors[$k] = __('Выберите значение.');
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
                if ($req && empty($v['az'])) $errors[$k] = __('Заполните хотя бы азербайджанский вариант (AZ): это основной язык сайта.');
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
                if ($req && empty($v['az'])) $errors[$k] = __('Заполните хотя бы азербайджанский вариант (AZ).');
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
                        $errors[$k] = __('Код цвета должен выглядеть как #1f1f22.');
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

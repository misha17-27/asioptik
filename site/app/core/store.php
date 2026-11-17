<?php
/* Данные сайта: настройки, товары, разделы, бренды, статьи, услуги, заказы — и выгрузка всего этого для страницы. */
declare(strict_types=1);

const LANGS = ['az', 'ru', 'en'];
const ITEM_TYPES = ['product', 'category', 'brand', 'service', 'post'];

/* ---------- настройки (по одному документу на имя) ---------- */
function setting(string $name, $default = null)
{
    $row = q('SELECT value FROM ao_settings WHERE name = ?', [$name])->fetch();
    if (!$row) return $default;
    $v = json_decode((string) $row['value'], true);
    return $v === null ? $default : $v;
}

function set_setting(string $name, $value): void
{
    $pdo = db();
    $pdo->beginTransaction();
    q('DELETE FROM ao_settings WHERE name = ?', [$name]);
    q('INSERT INTO ao_settings (name, value) VALUES (?, ?)', [$name, to_json($value)]);
    $pdo->commit();
    cache_clear();
}

/* ---------- записи: товары, разделы, бренды, услуги, статьи ---------- */
function item_row(array $r): array
{
    $data = json_decode((string) $r['data'], true);
    return [
        'id' => (int) $r['id'], 'type' => $r['type'], 'slug' => $r['slug'], 'position' => (int) $r['position'],
        'active' => (int) $r['active'] === 1, 'data' => is_array($data) ? $data : [], 'updated_at' => $r['updated_at'],
    ];
}

function items(string $type, bool $activeOnly = false): array
{
    $sql = 'SELECT * FROM ao_items WHERE type = ?' . ($activeOnly ? ' AND active = 1' : '') . ' ORDER BY position, id';
    return array_map('item_row', q($sql, [$type])->fetchAll());
}

function item_get(int $id): ?array
{
    $r = q('SELECT * FROM ao_items WHERE id = ?', [$id])->fetch();
    return $r ? item_row($r) : null;
}

function item_by_slug(string $type, string $slug): ?array
{
    $r = q('SELECT * FROM ao_items WHERE type = ? AND slug = ?', [$type, $slug])->fetch();
    return $r ? item_row($r) : null;
}

function item_save(?int $id, string $type, string $slug, int $position, bool $active, array $data): int
{
    if ($id) {
        q('UPDATE ao_items SET slug = ?, position = ?, active = ?, data = ?, updated_at = ? WHERE id = ? AND type = ?',
            [$slug, $position, $active ? 1 : 0, to_json($data), now(), $id, $type]);
    } else {
        q('INSERT INTO ao_items (type, slug, position, active, data, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
            [$type, $slug, $position, $active ? 1 : 0, to_json($data), now()]);
        $id = (int) db()->lastInsertId();
    }
    cache_clear();
    return $id;
}

function item_delete(int $id): void
{
    q('DELETE FROM ao_items WHERE id = ?', [$id]);
    cache_clear();
}

function next_position(string $type): int
{
    $r = q('SELECT MAX(position) AS m FROM ao_items WHERE type = ?', [$type])->fetch();
    return (int) ($r['m'] ?? 0) + 10;
}

/* ---------- выгрузка данных для страницы сайта ---------- */
function cache_file(): string
{
    return STORAGE . '/cache/site.json';
}

function cache_clear(): void
{
    if (is_file(cache_file())) @unlink(cache_file());
}

/* Версия первых данных. Когда в новых файлах сайта появляются данные, которых нет в уже установленном
   сайте (например, временные фото слайдов), число увеличивается, и data_upgrade() дополняет базу. */
const DATA_VERSION = 2;

/**
 * Дополняет уже установленный сайт тем, что появилось в первых данных позже. Своё не трогает:
 * временное фото получает только слайд раздела, у которого нет ни своего фото, ни временного.
 */
function data_upgrade(): void
{
    $have = (int) setting('data_version', 1);
    if ($have >= DATA_VERSION) return;
    $seed = json_decode((string) @file_get_contents(APP . '/data/seed.json'), true);
    if ($have < 2 && is_array($seed)) {
        $bySlug = [];
        foreach ($seed['items']['category'] ?? [] as $r) $bySlug[$r['slug']] = $r['data']['banner'] ?? [];
        foreach (items('category') as $it) {
            $b = $bySlug[$it['slug']] ?? [];
            $d = $it['data'];
            if (empty($b['demo']) || !empty($d['banner']['img']) || !empty($d['banner']['demo'])) continue;
            foreach (['demo', 'pos', 'flip'] as $k) {
                if (isset($b[$k])) $d['banner'][$k] = $b[$k];
            }
            item_save($it['id'], 'category', $it['slug'], $it['position'], $it['active'], $d);
        }
    }
    set_setting('data_version', DATA_VERSION);
}

/** Своё фото вместо временного: временное и его кадрирование больше не нужны. */
function drop_demo(array $node): array
{
    unset($node['demo'], $node['pos'], $node['flip']);
    return $node;
}

/** Все данные сайта в том виде, в каком их ждёт страница (CONFIG, PRODUCTS и так далее). */
function site_data(): array
{
    $f = cache_file();
    if (is_file($f)) {
        $d = json_decode((string) file_get_contents($f), true);
        if (is_array($d) && isset($d['PRODUCTS']) && ($d['_v'] ?? 0) === DATA_VERSION) return $d;
    }
    data_upgrade();
    $d = site_data_build();
    $d['_v'] = DATA_VERSION;
    if (!is_dir(dirname($f))) @mkdir(dirname($f), 0775, true);
    @file_put_contents($f, to_json($d), LOCK_EX);
    return $d;
}

function site_data_build(): array
{
    $withId = function (array $rows): array {
        return array_map(function ($r) {
            return ['id' => $r['slug']] + $r['data'];
        }, $rows);
    };
    $cats = $withId(items('category', true));
    $catIds = array_column($cats, 'id');
    $brands = array_map(function ($r) {
        return ['id' => $r['slug'], 'name' => (string) ($r['data']['name'] ?? $r['slug'])];
    }, items('brand', true));
    $brandIds = array_column($brands, 'id');

    $products = [];
    foreach ($withId(items('product', true)) as $p) {
        if (!in_array($p['cat'] ?? '', $catIds, true)) continue;
        if (isset($p['brand']) && !in_array($p['brand'], $brandIds, true)) unset($p['brand']);
        if (isset($p['old']) && (float) $p['old'] <= (float) ($p['price'] ?? 0)) unset($p['old']);
        foreach (['badge', 'img'] as $k) {
            if (isset($p[$k]) && ($p[$k] === '' || $p[$k] === [] || $p[$k] === null)) unset($p[$k]);
        }
        $products[] = $p;
    }
    $prodIds = array_column($products, 'id');

    // Секции «для кого» на главной: товары с отметкой «На главной», иначе прежний список
    $aud = setting('audiences', []);
    $pick = function (array $a, int $limit) use ($products, $prodIds): array {
        $ids = [];
        foreach ($products as $p) {
            if (!empty($p['home']) && in_array($a['id'], $p['for'] ?? [], true)) $ids[] = $p['id'];
        }
        if (!$ids) $ids = array_values(array_filter($a['pick'] ?? [], function ($id) use ($prodIds) {
            return in_array($id, $prodIds, true);
        }));
        return array_slice($ids, 0, $limit);
    };
    foreach ($aud as &$a) {
        if (!empty($a['parts'])) {
            foreach ($a['parts'] as &$part) $part['pick'] = $pick($part, 3);
            unset($part);
        } else {
            $a['pick'] = $pick($a, 4);
        }
    }
    unset($a);

    $posts = array_values(array_filter($withId(items('post', true)), function ($p) {
        return !empty($p['title']);
    }));

    return [
        'CONFIG' => setting('config', []),
        'CATEGORIES' => $cats,
        'RX' => setting('rx', new stdClass()),
        'AUDIENCES' => $aud,
        'PRODUCTS' => $products,
        'BRANDS' => $brands,
        'SERVICES' => $withId(items('service', true)),
        'ABOUT' => setting('about', new stdClass()),
        'POSTS' => $posts,
        // надписи и заголовки для поисковиков, изменённые в разделе «Страницы» (пусто — берутся встроенные)
        'TEXTS' => setting('texts', new stdClass()) ?: new stdClass(),
        'SEO' => setting('seo', new stdClass()) ?: new stdClass(),
    ];
}

/** Все надписи сайта на трёх языках, как они заданы в самом сайте: ключ => ['az' => …, 'ru' => …, 'en' => …]. */
function texts_default(): array
{
    static $t = null;
    if ($t === null) {
        $t = json_decode((string) @file_get_contents(APP . '/data/texts.json'), true);
        if (!is_array($t)) $t = [];
    }
    return $t;
}

/** Текст на одном языке без подстановки другого языка: для заголовков страниц, которые задаются отдельно. */
function own_text($v, string $lang): string
{
    return is_array($v) && isset($v[$lang]) && is_string($v[$lang]) ? trim($v[$lang]) : '';
}

/** Путь к картинке → адрес для страницы (картинки хранятся относительно корня сайта). */
function img_url(string $path): string
{
    if ($path === '' || preg_match('~^(https?:)?//|^/|^data:~i', $path)) return $path;
    return base_path() . $path;
}

/** Проставляет адреса картинок во всех данных сайта. */
function site_data_urls(array $d): array
{
    $fix = function (&$node) use (&$fix) {
        if (!is_array($node)) return;
        foreach ($node as $k => &$v) {
            if ($k === 'img' && is_string($v)) $v = img_url($v);
            elseif (is_array($v)) $fix($v);
        }
    };
    $fix($d);
    return $d;
}

/* ---------- заказы, заявки и сообщения с сайта ---------- */
const ORDER_KINDS = ['order' => 'Заказ', 'repair' => 'Ремонт', 'message' => 'Сообщение'];
const ORDER_STATUSES = ['new' => 'Новый', 'work' => 'В работе', 'done' => 'Выполнен', 'cancel' => 'Отменён'];

function api_token(int $dayShift = 0): string
{
    $c = config();
    return substr(hash_hmac('sha256', 'api|' . gmdate('Y-m-d', time() + $dayShift * 86400), (string) ($c['secret'] ?? '')), 0, 32);
}

/** Ключ с открытой страницы годится три дня: вкладку с корзиной могли оставить со вчера или позавчера. */
function api_token_valid(string $t): bool
{
    if ($t === '') return false;
    $ok = false;
    for ($day = 0; $day >= -3; $day--) $ok = hash_equals(api_token($day), $t) || $ok;
    return $ok;
}

/* ---------- загрузка картинок ---------- */
/**
 * Сохраняет загруженную картинку в uploads/<папка>/ и возвращает путь относительно корня сайта.
 * Принимаются только JPEG, PNG и WebP до 8 МБ; картинка пересохраняется и уменьшается до 2000 px по большей стороне.
 */
function save_upload(array $file, string $dir, ?string &$error = null): ?string
{
    $error = null;
    $code = $file['error'] ?? UPLOAD_ERR_NO_FILE;
    if ($code === UPLOAD_ERR_NO_FILE) return null;
    $limit = upload_limit();
    $mb = rtrim(rtrim(number_format($limit / 1048576, 1, ',', ''), '0'), ',') . ' МБ';
    if ($code === UPLOAD_ERR_INI_SIZE || $code === UPLOAD_ERR_FORM_SIZE || ($code === UPLOAD_ERR_OK && $file['size'] > $limit)) {
        $error = 'Файл больше ' . $mb . ': столько хостинг принимает за один раз. Уменьшите фото и загрузите снова.';
        return null;
    }
    if ($code !== UPLOAD_ERR_OK || !is_uploaded_file($file['tmp_name'])) {
        $error = 'Файл не загрузился. Попробуйте ещё раз.';
        return null;
    }
    $info = @getimagesize($file['tmp_name']);
    $types = [IMAGETYPE_JPEG => 'jpg', IMAGETYPE_PNG => 'png', IMAGETYPE_WEBP => 'webp'];
    if (!$info || !isset($types[$info[2]])) {
        $error = 'Подходят только картинки JPG, PNG или WebP.';
        return null;
    }
    $ext = $types[$info[2]];
    $w = (int) $info[0];
    $h = (int) $info[1];
    if ($w < 1 || $h < 1 || $w > 12000 || $h > 12000 || $w * $h > 50000000) {
        $error = 'Картинка слишком большая: ' . $w . '×' . $h . ' точек. Уменьшите её до 6000 точек по длинной стороне и загрузите снова.';
        return null;
    }
    if (function_exists('imagecreatetruecolor') && !upload_memory_ok($w, $h)) {
        $error = 'Серверу не хватает памяти для картинки ' . $w . '×' . $h . ' точек. Уменьшите её до 4000 точек по длинной стороне и загрузите снова.';
        return null;
    }
    $dir = preg_replace('~[^a-z0-9]~', '', $dir) ?: 'img';
    $target = UPLOADS . '/' . $dir;
    if (!is_dir($target) && !@mkdir($target, 0775, true)) {
        $error = 'Не удалось создать папку для картинок. Проверьте права на папку uploads.';
        return null;
    }
    $name = bin2hex(random_bytes(8));
    $saved = false;
    if (function_exists('imagecreatetruecolor')) {
        $src = null;
        if ($ext === 'jpg' && function_exists('imagecreatefromjpeg')) $src = @imagecreatefromjpeg($file['tmp_name']);
        if ($ext === 'png' && function_exists('imagecreatefrompng')) $src = @imagecreatefrompng($file['tmp_name']);
        if ($ext === 'webp' && function_exists('imagecreatefromwebp')) $src = @imagecreatefromwebp($file['tmp_name']);
        if (!$src) {
            $error = 'Не удалось прочитать картинку. Откройте её на компьютере, сохраните заново как JPG или PNG и загрузите снова.';
            return null;
        }
        if ($src) {
            if ($ext === 'jpg') $src = upload_orient($src, $file['tmp_name']);
            $w = imagesx($src);
            $h = imagesy($src);
            $k = min(1, 2000 / max($w, $h));
            $nw = max(1, (int) round($w * $k));
            $nh = max(1, (int) round($h * $k));
            $dst = imagecreatetruecolor($nw, $nh);
            if ($ext === 'png' || $ext === 'webp') {
                imagealphablending($dst, false);
                imagesavealpha($dst, true);
                imagefill($dst, 0, 0, imagecolorallocatealpha($dst, 255, 255, 255, 127));
            }
            imagecopyresampled($dst, $src, 0, 0, 0, 0, $nw, $nh, $w, $h);
            if ($ext === 'png') $saved = imagepng($dst, "$target/$name.png", 7);
            elseif ($ext === 'webp' && function_exists('imagewebp')) $saved = imagewebp($dst, "$target/$name.webp", 86);
            else {
                $ext = 'jpg';
                $saved = imagejpeg($dst, "$target/$name.jpg", 86);
            }
            imagedestroy($src);
            imagedestroy($dst);
        }
    }
    // без модуля GD картинку нечем пересохранить — кладём как есть (тип проверен, имя и расширение задаёт сайт)
    if (!$saved && !function_exists('imagecreatetruecolor')) $saved = move_uploaded_file($file['tmp_name'], "$target/$name.$ext");
    if (!$saved) {
        $error = 'Не удалось сохранить картинку. Проверьте права на папку uploads.';
        return null;
    }
    return "uploads/$dir/$name.$ext";
}

/** Значение из настроек PHP вида «8M» в байтах; пустое, 0 и -1 значат «без предела». */
function ini_bytes(string $name): int
{
    $v = trim((string) ini_get($name));
    $n = (int) $v;
    if ($v === '' || $n <= 0) return PHP_INT_MAX;
    $unit = strtolower(substr($v, -1));
    return $n * ($unit === 'g' ? 1073741824 : ($unit === 'm' ? 1048576 : ($unit === 'k' ? 1024 : 1)));
}

/** Сколько байт принимается в одном файле: предел хостинга, но не больше 8 МБ. */
function upload_limit(): int
{
    return (int) min(8 * 1048576, ini_bytes('upload_max_filesize'), ini_bytes('post_max_size'));
}

/** Хватит ли серверу памяти, чтобы раскрыть и уменьшить картинку; при нехватке пробуем поднять предел. */
function upload_memory_ok(int $w, int $h): bool
{
    $k = min(1, 2000 / max($w, $h));
    $need = (int) (($w * $h + $w * $k * $h * $k) * 5 * 1.3) + 24 * 1024 * 1024 + memory_get_usage();
    if ($need <= ini_bytes('memory_limit')) return true;
    @ini_set('memory_limit', (string) min($need, 768 * 1024 * 1024));
    return $need <= ini_bytes('memory_limit');
}

/** Снимки с телефона хранят поворот отдельной пометкой; при пересохранении она теряется, поэтому поворачиваем саму картинку. */
function upload_orient($img, string $path)
{
    if (!function_exists('exif_read_data') || !function_exists('imagerotate')) return $img;
    $exif = @exif_read_data($path);
    $o = is_array($exif) ? (int) ($exif['Orientation'] ?? 1) : 1;
    if (in_array($o, [2, 4, 5, 7], true) && function_exists('imageflip')) imageflip($img, $o === 4 ? IMG_FLIP_VERTICAL : IMG_FLIP_HORIZONTAL);
    $turn = [3 => 180, 4 => 0, 5 => 90, 6 => -90, 7 => -90, 8 => 90][$o] ?? 0;
    if ($turn) {
        $r = imagerotate($img, $turn, 0);
        if ($r) {
            imagedestroy($img);
            $img = $r;
        }
    }
    return $img;
}

/** Удаляет картинку, если она лежит в uploads (чужие и внешние адреса не трогаем). */
function delete_upload(?string $path): void
{
    if (!$path || !preg_match('~^uploads/[a-z0-9]+/[a-f0-9]{16}\.(jpg|png|webp)$~', $path)) return;
    $f = ROOT . '/' . $path;
    if (is_file($f)) @unlink($f);
}

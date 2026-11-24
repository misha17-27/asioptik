<?php
/* Раздел «Изображения»: все фото, загруженные на сайт. Загрузка в общую библиотеку, путь к фото для вставки
   в текст статьи, отметка «используется» и удаление того, что нигде не используется. */
declare(strict_types=1);

/* Путь к загруженному фото: uploads/папка/имя. Имя задаёт сайт (16 знаков), поэтому чужой путь сюда не подставить. */
const MEDIA_PATH = '~^uploads/[a-z0-9]+/[a-f0-9]{16}\.(?:jpg|png|webp)$~';

function fmt_size(int $bytes): string
{
    if ($bytes >= 1048576) return rtrim(rtrim(number_format($bytes / 1048576, 1, ',', ''), '0'), ',') . ' ' . __('МБ');
    return max(1, (int) round($bytes / 1024)) . ' ' . __('КБ');
}

/** Все картинки в папке uploads: путь, размер, время загрузки. Новые — первыми. */
function media_files(): array
{
    $out = [];
    foreach (glob(UPLOADS . '/*', GLOB_ONLYDIR) ?: [] as $dir) {
        $d = basename($dir);
        if (!preg_match('~^[a-z0-9]+$~', $d)) continue;
        foreach (scandir($dir) ?: [] as $f) {
            if (!preg_match('~^[a-f0-9]{16}\.(jpg|png|webp)$~', $f)) continue;
            $out[] = ['path' => "uploads/$d/$f", 'size' => (int) @filesize("$dir/$f"), 'time' => (int) @filemtime("$dir/$f")];
        }
    }
    usort($out, function ($a, $b) {
        return ($b['time'] <=> $a['time']) ?: strcmp($a['path'], $b['path']);
    });
    return $out;
}

/** Где используется каждое фото: путь → список мест («Товар: Milan», «Баннеры и фото»). Фото, которого здесь нет, не используется. */
function media_usage(): array
{
    $use = [];
    $find = function (string $json, string $label) use (&$use): void {
        // в базе данные лежат в JSON, где косая черта может быть записана как «\/»
        if (!preg_match_all('~uploads\\\\?/([a-z0-9]+)\\\\?/([a-f0-9]{16}\.(?:jpg|png|webp))~', $json, $m, PREG_SET_ORDER)) return;
        foreach ($m as $x) $use['uploads/' . $x[1] . '/' . $x[2]][$label] = true;
    };
    $S = schemas();
    foreach (q('SELECT type, slug, data FROM ao_items')->fetchAll() as $r) {
        $d = json_decode((string) $r['data'], true);
        $name = is_array($d) ? tr_admin($d['title'] ?? $d['name'] ?? '') : '';
        $find((string) $r['data'], ($S[$r['type']]['one'] ?? $r['type']) . ': ' . ($name !== '' ? $name : $r['slug']));
    }
    $docs = ['audiences' => __('Баннеры и фото'), 'about' => __('О нас'), 'config' => __('Настройки сайта')];
    foreach (q('SELECT name, value FROM ao_settings')->fetchAll() as $r) $find((string) $r['value'], $docs[$r['name']] ?? __('Страницы'));
    return array_map('array_keys', $use);
}

function admin_media(): void
{
    $errors = [];
    $many = max(1, min(20, (int) ini_get('max_file_uploads') ?: 20));
    if (is_post() && ($_POST['act'] ?? '') === 'delete') {
        $path = is_string($_POST['path'] ?? null) ? $_POST['path'] : '';
        if (!preg_match(MEDIA_PATH, $path) || !is_file(ROOT . '/' . $path)) flash(__('Такого фото уже нет.'), 'err');
        elseif (isset(media_usage()[$path])) flash(__('Это фото используется на сайте. Сначала уберите его оттуда, где оно стоит.'), 'err');
        elseif (@unlink(ROOT . '/' . $path)) flash(__('Фото удалено.'));
        else flash(__('Не удалось удалить файл. Проверьте права на папку uploads.'), 'err');
        redirect(admin_url('media'));
    }
    if (is_post()) {
        $f = $_FILES['files'] ?? null;
        $done = 0;
        if (is_array($f) && is_array($f['name'] ?? null)) {
            foreach (array_slice(array_keys($f['name']), 0, $many) as $i) {
                $one = ['name' => $f['name'][$i], 'tmp_name' => $f['tmp_name'][$i] ?? '', 'error' => $f['error'][$i] ?? UPLOAD_ERR_NO_FILE, 'size' => $f['size'][$i] ?? 0];
                if ($one['error'] === UPLOAD_ERR_NO_FILE) continue;
                $err = null;
                if (save_upload($one, 'media', $err)) $done++;
                elseif ($err) $errors[] = mb_substr(is_string($one['name']) ? $one['name'] : '', 0, 60) . ': ' . $err;
            }
        }
        if ($done) flash(__('Загружено фото: {n}.', ['n' => $done]));
        if (!$errors) {
            if (!$done) flash(__('Выберите хотя бы одно фото.'), 'err');
            redirect(admin_url('media'));
        }
    }

    $files = media_files();
    $use = media_usage();
    $total = array_sum(array_column($files, 'size'));
    $out = '<div class="lib">';
    if ($errors) $out .= '<div class="flash flash-err" role="alert">' . implode('<br>', array_map('e', $errors)) . '</div>';
    $out .= '<section class="card form-card">' . card_head(__('Загрузить фото'))
        . '<form method="post" enctype="multipart/form-data" class="card-body">' . csrf_field() . '<input type="hidden" name="act" value="upload">'
        . '<div class="field"><label class="lbl" for="lib-files">' . e(__('Фото с компьютера или телефона')) . '</label>'
        . '<input id="lib-files" type="file" name="files[]" multiple required accept="image/jpeg,image/png,image/webp" data-max="' . upload_limit() . '" data-max-total="' . (int) min(64 * 1048576, ini_bytes('post_max_size') * 0.9) . '" data-max-files="' . $many . '">'
        . '<p class="file-note" aria-live="polite" hidden></p>'
        . '<p class="hint">' . e(__('JPG, PNG или WebP, до {n} фото за один раз. Каждое фото пересохраняется и уменьшается до 2000 точек по длинной стороне — как во всех формах сайта.', ['n' => $many])) . '</p></div>'
        . '<div class="actions"><button type="submit" class="btn">' . icon('plus') . e(__('Загрузить')) . '</button></div></form></section>';

    $out .= '<section class="card">' . card_head(__('Медиа сайта ({n})', ['n' => count($files)]), $files ? '<span class="muted">' . e(fmt_size((int) $total)) . '</span>' : '');
    if (!$files) {
        $out .= '<p class="empty">' . e(__('Фото пока нет. Загрузите первое здесь — или добавьте фото в товар, бренд, статью или баннер: они тоже появятся в этом списке.')) . '</p>';
    } else {
        $out .= '<p class="hint hint-card">' . e(__('Нажмите на путь под фото — он скопируется. Чтобы поставить фото в статью блога, вставьте путь в текст статьи отдельной строкой; после пути через пробел можно написать подпись. Здесь же видны фото товаров, брендов и баннеров.')) . '</p><ul class="media">';
        foreach ($files as $f) {
            $where = $use[$f['path']] ?? [];
            $url = img_url($f['path']);
            $out .= '<li class="media-item' . ($where ? '' : ' is-free') . '">'
                . '<a class="media-pic" href="' . e($url) . '" target="_blank" rel="noopener" title="' . e(__('Открыть фото в новой вкладке')) . '"><img src="' . e($url) . '" alt="" loading="lazy" decoding="async"></a>'
                . '<button type="button" class="media-path" data-copy="' . e($f['path']) . '" title="' . e(__('Скопировать путь')) . '">' . icon('copy') . '<span data-copy-label>' . e($f['path']) . '</span></button>'
                . '<p class="media-meta">' . e(fmt_size($f['size'])) . ' · '
                . ($where ? e(implode(', ', array_slice($where, 0, 2)) . (count($where) > 2 ? ' …' : '')) : '<span class="media-free">' . e(__('не используется')) . '</span>') . '</p>'
                . ($where ? '' : '<form method="post" data-confirm="' . e(__('Удалить это фото? Вернуть его будет нельзя.')) . '">' . csrf_field()
                    . '<input type="hidden" name="act" value="delete"><input type="hidden" name="path" value="' . e($f['path']) . '">'
                    . '<button type="submit" class="btn btn-sm btn-line">' . icon('trash') . e(__('Удалить')) . '</button></form>')
                . '</li>';
        }
        $out .= '</ul>';
    }
    $out .= '</section></div>';
    admin_page(__('Изображения'), $out, 'media');
}

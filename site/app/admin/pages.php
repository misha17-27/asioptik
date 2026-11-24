<?php
declare(strict_types=1);

/* Обзор, клиенты и раздел «Страницы» админ-панели */

/**
 * Страницы сайта для раздела «Страницы»: название, адрес, блоки надписей и ссылки на связанные разделы.
 * В блоке перечислены группы надписей (часть ключа до точки) и отдельные ключи без точки.
 */
const SITE_PAGES = [
    'home' => ['title' => 'Главная', 'path' => '', 'seo' => true, 'blocks' => [
        'Первый экран' => ['hero', 'hs', 'kit', 'bn', 'fact1', 'fact2', 'fact3'],
        'Таблица для проверки зрения' => ['ch'],
        'Секции главной' => ['cats', 'rx', 'eye'],
        'Как сделать заказ' => ['how', 's1t', 's1p', 's2t', 's2p', 's3t', 's3p', 's4t', 's4p'],
        'Мастерская' => ['repair', 'rp'],
        'Контакты' => ['contacts', 'c'],
    ], 'more' => [['banners', 'Баннеры и фото'], ['list:category', 'Слайды первого экрана'], ['list:service', 'Услуги мастерской']]],
    'catalog' => ['title' => 'Каталог', 'path' => 'catalog', 'seo' => true, 'blocks' => [
        'Каталог' => ['cat', 'sort', 'brand', 'aud', 'all', 'toCart', 'choose', 'chooseFor', 'toCartFor', 'oldPrice', 'priceFrom', 'pcs'],
        'Описания разделов для поисковиков' => ['cseo'],
    ], 'more' => [['list:product', 'Товары'], ['list:category', 'Разделы'], ['list:brand', 'Бренды']]],
    'brands' => ['title' => 'Бренды', 'path' => 'brands', 'seo' => true, 'blocks' => ['Надписи страницы' => ['brs']], 'more' => [['list:brand', 'Список брендов']]],
    'product' => ['title' => 'Страница товара', 'path' => 'product/…', 'seo' => false, 'blocks' => [
        'Страница товара' => ['pp', 'pm', 'color', 'select', 'chooseMissing', 'optional', 'mm', 'forFrame', 'skip', 'seo'],
        'Параметры контактных линз' => ['rxc'],
    ], 'more' => [['list:product', 'Товары']]],
    'checkout' => ['title' => 'Корзина и оформление заказа', 'path' => 'checkout', 'seo' => true, 'blocks' => [
        'Корзина' => ['cart', 'qty', 'qtyOf', 'qtyDec', 'qtyInc', 'remove', 'free', 'pickupShort'],
        'Оформление заказа' => ['co', 'pay', 'dn', 'f'],
        'После заказа' => ['ok'],
    ], 'more' => [['doc:config', 'Доставка и контакты']]],
    'about' => ['title' => 'О нас', 'path' => 'about', 'seo' => true, 'blocks' => ['Надписи страницы' => ['ab']], 'more' => [['doc:about', 'Тексты и фото страницы']]],
    'blog' => ['title' => 'Блог', 'path' => 'blog', 'seo' => true, 'blocks' => ['Надписи страницы' => ['bl']], 'more' => [['list:post', 'Статьи блога']]],
    'contacts' => ['title' => 'Контакты', 'path' => 'contacts', 'seo' => true, 'blocks' => ['Надписи страницы и форма' => ['ct'], 'Филиалы и карта' => ['loc']], 'more' => [['list:branch', 'Филиалы: адреса, часы работы, карта'], ['doc:config', 'Телефон и WhatsApp']]],
    'common' => ['title' => 'Общие надписи', 'path' => null, 'seo' => false, 'blocks' => [
        'Меню и подвал' => ['nav', 'lang', 'pg', 'ft', 'footer', 'wa', 'toast', 'sb'],
        'Подсказки и ошибки в формах' => ['e', 'added', 'addedSvc', 'close', 'cap'],
        'Текст сообщения в WhatsApp' => ['m', 'ml', 'rxs'],
    ], 'more' => []],
];

/** Надписи страницы по блокам: [название блока => [ключ, …]]. Ключи, не попавшие ни в одну страницу, идут в «Общие надписи». */
function page_blocks(string $id): array
{
    static $all = null;
    if ($all === null) {
        $where = [];
        foreach (SITE_PAGES as $pid => $page) {
            foreach ($page['blocks'] as $block => $groups) {
                foreach ($groups as $g) $where[$g] = [$pid, $block];
            }
        }
        $all = [];
        foreach (array_keys(texts_default()) as $key) {
            $group = strpos($key, '.') !== false ? (string) strstr($key, '.', true) : $key;
            if ($group === 'meta') continue;   // заголовок и описание главной задаются в блоке SEO
            [$pid, $block] = $where[$group] ?? ['common', 'Прочее'];
            $all[$pid][$block][] = $key;
        }
    }
    $out = [];
    foreach (SITE_PAGES[$id]['blocks'] ?? [] as $block => $groups) {
        if (empty($all[$id][$block])) continue;
        $order = array_flip($groups);   // надписи идут в том порядке, в каком группы перечислены в блоке
        $keys = $all[$id][$block];
        $rank = [];
        foreach ($keys as $i => $key) $rank[$key] = [$order[strpos($key, '.') !== false ? (string) strstr($key, '.', true) : $key] ?? 99, $i];
        usort($keys, function ($a, $b) use ($rank) {
            return $rank[$a] <=> $rank[$b];
        });
        $out[$block] = $keys;
    }
    if (!empty($all[$id]['Прочее'])) $out['Прочее'] = $all[$id]['Прочее'];
    return $out;
}

/** Заголовок и описание страницы, которые сайт ставит сам, если свои не заданы (те же правила, что на сайте: seo_auto). */
function page_seo_default(string $id, string $lang): array
{
    $data = ['CONFIG' => setting('config', []), 'ABOUT' => setting('about', []), 'BRANCHES' => branches_public()];
    $auto = seo_auto($id, $lang, $data);
    return [$auto[0], $auto[1] !== '' ? $auto[1] : seo_auto('home', $lang, $data)[1]];
}

/** Что в записи: первая строка и пояснение для таблицы заказов. */
function order_summary(array $r): array
{
    $d = json_decode((string) ($r['data'] ?? ''), true);
    $d = is_array($d) && is_array($d['details'] ?? null) ? $d['details'] : [];
    $s = function ($v): string {
        return is_scalar($v) ? trim((string) $v) : '';
    };
    if ($r['kind'] === 'order') {
        $items = array_values(array_filter(is_array($d['items'] ?? null) ? $d['items'] : [], 'is_array'));
        if (!$items) return [__('Заказ'), ''];
        $more = count($items) - 1;
        $lines = array_filter(array_map($s, array_slice(is_array($items[0]['lines'] ?? null) ? $items[0]['lines'] : [], 0, 3)));
        return [$s($items[0]['name'] ?? '') . ($more > 0 ? ' ' . __('и ещё {n} {word}', ['n' => $more, 'word' => n__($more, 'товар', 'товара', 'товаров')]) : ''), implode(' · ', $lines)];
    }
    if ($r['kind'] === 'repair') {
        $sv = array_values(array_filter(array_map($s, is_array($d['services'] ?? null) ? $d['services'] : [])));
        return [__('Ремонт') . ($sv ? ': ' . $sv[0] : ''), implode(' · ', array_slice($sv, 1, 3))];
    }
    $text = $s($d['comment'] ?? '');
    return [__('Сообщение') . ($s($d['topic'] ?? '') !== '' ? ': ' . $s($d['topic']) : ''), mb_strlen($text) > 90 ? mb_substr($text, 0, 90) . '…' : $text];
}

/** Таблица заказов и заявок: номер и дата, клиент, что заказали, сумма, статус. */
function orders_table(array $rows): string
{
    $how = ['pickup' => __('самовывоз'), 'courier' => __('доставка курьером'), 'salon' => __('принесёт в салон')];
    $out = '<div class="table-wrap"><table class="table"><thead><tr><th>' . __('Заказ') . '</th><th>' . __('Клиент') . '</th><th>' . __('Что заказали') . '</th><th>' . __('Сумма') . '</th><th>' . __('Статус') . '</th></tr></thead><tbody>';
    foreach ($rows as $r) {
        [$what, $sub] = order_summary($r);
        $d = json_decode((string) ($r['data'] ?? ''), true);
        $way = is_array($d) ? (string) ($d['details']['delivery'] ?? ($d['details']['handover'] ?? '')) : '';
        $way = $way === 'courier' && $r['kind'] === 'repair' ? __('нужен курьер') : ($how[$way] ?? '');
        // филиал, который покупатель выбрал для самовывоза или куда принесёт очки
        $branch = is_array($d) && is_string($d['details']['branch'] ?? null) ? $d['details']['branch'] : '';
        if ($way !== '' && $branch !== '') $way .= ' · ' . $branch;
        $out .= '<tr><td><a class="strong" href="' . e(admin_url('order', ['id' => $r['id']])) . '">' . e($r['number']) . '</a><small>' . e(fmt_date($r['created_at'])) . '</small></td>'
            . '<td><span class="strong">' . e($r['name']) . '</span><small>' . e($r['phone']) . '</small></td>'
            . '<td>' . e($what) . ($sub !== '' ? '<small>' . e($sub) . '</small>' : '') . '</td>'
            . '<td class="nowrap">' . ($r['total'] !== null ? e(fmt_money($r['total'])) : '—') . ($way !== '' ? '<small>' . e($way) . '</small>' : '') . '</td>'
            . '<td><span class="st st-' . e($r['status']) . '">' . e(__(ORDER_STATUSES[$r['status']] ?? $r['status'])) . '</span></td></tr>';
    }
    return $out . '</tbody></table></div>';
}

/* ---------- обзор ---------- */
function admin_home(): void
{
    $c = admin_counts();
    $tiles = [
        [$c['new'], n__($c['new'], 'новое обращение', 'новых обращения', 'новых обращений'), admin_url('orders', ['status' => 'new']), true],
        [$c['sales'], n__($c['sales'], 'заказ всего', 'заказа всего', 'заказов всего'), admin_url('orders', ['kind' => 'order']), false],
        [$c['clients'], n__($c['clients'], 'клиент', 'клиента', 'клиентов'), admin_url('clients'), false],
        [$c['product'] ?? 0, n__($c['product'] ?? 0, 'товар', 'товара', 'товаров'), admin_url('list', ['type' => 'product']), false],
        [$c['category'] ?? 0, n__($c['category'] ?? 0, 'раздел', 'раздела', 'разделов'), admin_url('list', ['type' => 'category']), false],
        [$c['brand'] ?? 0, n__($c['brand'] ?? 0, 'бренд', 'бренда', 'брендов'), admin_url('list', ['type' => 'brand']), false],
    ];
    if (!can('orders')) $tiles = array_slice($tiles, 3);   // заказы и клиенты — не для всех ролей
    $out = preview_note() . '<div class="tiles">';
    foreach ($tiles as [$n, $label, $url, $hot]) {
        $out .= '<a class="tile' . ($hot && $n ? ' tile-hot' : '') . '" href="' . e($url) . '"><b>' . (int) $n . '</b><span>' . e($label) . '</span></a>';
    }
    $out .= '</div>';
    if (!can('orders')) admin_page(__('Обзор'), $out, 'home');
    $rows = q('SELECT id, number, kind, status, created_at, name, phone, total, data FROM ao_orders ORDER BY created_at DESC, id DESC LIMIT 8')->fetchAll();
    $out .= '<section class="card">' . card_head(__('Последние заказы'), '<a href="' . e(admin_url('orders')) . '">' . __('Все →') . '</a>')
        . ($rows ? orders_table($rows) : '<p class="empty">' . __('Заказов пока нет. Когда покупатель оформит заказ, оставит заявку на ремонт или напишет с сайта, запись появится здесь.') . '</p>')
        . '</section>';
    admin_page(__('Обзор'), $out, 'home');
}

/* ---------- клиенты: все, кто оставлял заказ, заявку или сообщение ---------- */
function admin_clients(): void
{
    $rows = q("SELECT phone, MAX(name) AS name, COUNT(*) AS n, SUM(CASE WHEN kind = 'order' AND status <> 'cancel' THEN total ELSE 0 END) AS spent, MAX(created_at) AS last
        FROM ao_orders GROUP BY phone ORDER BY last DESC LIMIT 500")->fetchAll();
    $out = '<section class="card">' . card_head(__('Клиенты'), '<span class="muted">' . __('все, кто оставлял заказ, заявку на ремонт или сообщение') . '</span>');
    if (!$rows) {
        $out .= '<p class="empty">' . __('Клиентов пока нет: список соберётся сам из заказов и заявок.') . '</p>';
    } else {
        $out .= '<div class="table-wrap"><table class="table"><thead><tr><th>' . __('Клиент') . '</th><th>' . __('Обращений') . '</th><th>' . __('Сумма заказов') . '</th><th>' . __('Последнее обращение') . '</th><th></th></tr></thead><tbody>';
        foreach ($rows as $r) {
            $tel = preg_replace('~[^0-9+]~', '', (string) $r['phone']);
            $out .= '<tr><td><span class="strong">' . e($r['name']) . '</span><small><a href="tel:' . e($tel) . '">' . e($r['phone']) . '</a></small></td>'
                . '<td>' . (int) $r['n'] . '</td><td class="nowrap">' . ((float) $r['spent'] > 0 ? e(fmt_money($r['spent'])) : '—') . '</td>'
                . '<td class="nowrap">' . e(fmt_date((string) $r['last'])) . '</td>'
                . '<td class="acts"><a class="btn btn-line btn-sm" href="' . e(admin_url('orders', ['q' => $r['phone']])) . '">' . __('Заказы') . '</a></td></tr>';
        }
        $out .= '</tbody></table></div>';
    }
    admin_page(__('Клиенты'), $out . '</section>', 'clients');
}

/* ---------- страницы: список ---------- */
function admin_pages(): void
{
    $tx = setting('texts', []);
    $seo = setting('seo', []);
    $base = base_path();
    $out = '<section class="card">' . card_head(__('Страницы сайта'), '<span class="muted">' . __('адрес, надписи и заголовки для поисковиков на трёх языках') . '</span>')
        . '<div class="table-wrap"><table class="table"><thead><tr><th>' . __('Страница') . '</th><th>' . __('Адрес') . '</th><th>' . __('Надписи') . '</th><th>SEO</th><th></th></tr></thead><tbody>';
    foreach (SITE_PAGES as $id => $page) {
        $keys = array_merge([], ...array_values(page_blocks($id)));
        $changed = 0;
        foreach ($keys as $k) {
            foreach (LANGS as $l) {
                if (isset($tx[$l][$k])) { $changed++; break; }
            }
        }
        $own = 0;
        foreach (LANGS as $l) {
            if (own_text($seo[$id]['title'] ?? null, $l) !== '' || own_text($seo[$id]['desc'] ?? null, $l) !== '') $own++;
        }
        $n = count($keys);
        $out .= '<tr><td><a class="strong" href="' . e(admin_url('page', ['id' => $id])) . '">' . e(__($page['title'])) . '</a><small>' . $n . ' ' . n__($n, 'надпись', 'надписи', 'надписей') . '</small></td>'
            . '<td class="nowrap">' . ($page['path'] === null ? '<span class="muted">' . __('на всех страницах') . '</span>' : '<code>' . e($base . $page['path']) . '</code>') . '</td>'
            . '<td class="nowrap"><span class="dot dot-ok"></span>' . ($changed ? __('изменено: {n}', ['n' => $changed]) : __('стандартные')) . '</td>'
            . '<td class="nowrap">' . (!$page['seo'] ? '<span class="muted">' . ($id === 'product' ? __('в карточке товара') : '—') . '</span>'
                : '<span class="dot ' . ($own === count(LANGS) ? 'dot-ok' : 'dot-auto') . '"></span>' . ($own === count(LANGS) ? __('заполнено') : ($own ? __('заполнено: {n} из 3 языков', ['n' => $own]) : __('автоматически')))) . '</td>'
            . '<td class="acts"><a class="btn btn-line btn-sm" href="' . e(admin_url('page', ['id' => $id])) . '" title="' . e(__('Редактировать')) . '">' . icon('edit') . '<span class="lb">' . __('Редактировать') . '</span></a>'
            . ($page['path'] !== null && strpos($page['path'], '…') === false ? '<a class="btn btn-line btn-sm" href="' . e($base . $page['path']) . '" target="_blank" rel="noopener" title="' . e(__('Открыть на сайте')) . '">' . icon('ext') . '<span class="lb">' . __('Открыть') . '</span></a>' : '')
            . '</td></tr>';
    }
    admin_page(__('Страницы'), $out . '</tbody></table></div></section>', 'pages');
}

/* ---------- страницы: надписи и заголовки одной страницы на трёх языках ---------- */
function admin_page_edit(): void
{
    $id = (string) ($_GET['id'] ?? '');
    if (!isset(SITE_PAGES[$id])) redirect(admin_url('pages'));
    $page = SITE_PAGES[$id];
    $blocks = page_blocks($id);
    $def = texts_default();
    $tx = setting('texts', []);
    $seo = setting('seo', []);
    if (!is_array($tx)) $tx = [];
    if (!is_array($seo)) $seo = [];
    $post = is_post() ? $_POST : null;
    $errors = [];

    if ($post !== null) {
        $clean = function ($v, int $max): string {
            $v = is_string($v) ? trim((string) preg_replace("~\r\n?~", "\n", $v)) : '';
            return mb_strlen($v) > $max ? mb_substr($v, 0, $max) : $v;
        };
        foreach ($blocks as $keys) {
            foreach ($keys as $key) {
                foreach (LANGS as $l) {
                    if (!isset($post['t'][$key][$l])) continue;
                    $val = $clean($post['t'][$key][$l], 600);
                    $base = (string) ($def[$key][$l] ?? '');
                    // слова в фигурных скобках сайт подставляет сам (имя, сумма, номер) — они должны остаться в тексте
                    preg_match_all('~\{\w+\}~', $base, $need);
                    foreach (array_unique($need[0]) as $ph) {
                        if ($val !== '' && strpos($val, $ph) === false) $errors[$key][$l] = __('В тексте должно остаться {word}: сайт подставит на это место нужное слово или число.', ['word' => $ph]);
                    }
                    if ($val === '' || $val === $base) unset($tx[$l][$key]);
                    else $tx[$l][$key] = $val;
                }
            }
        }
        if ($page['seo']) {
            foreach (['title' => 160, 'desc' => 400] as $part => $max) {
                foreach (LANGS as $l) {
                    $val = $clean($post['seo'][$part][$l] ?? '', $max);
                    if ($val === '') unset($seo[$id][$part][$l]);
                    else $seo[$id][$part][$l] = $val;
                }
                if (empty($seo[$id][$part])) unset($seo[$id][$part]);
            }
            if (empty($seo[$id])) unset($seo[$id]);
        }
        if (!$errors) {
            set_setting('texts', array_filter($tx) ?: new stdClass());
            set_setting('seo', $seo ?: new stdClass());
            flash(__('Сохранено. Изменения уже на сайте.'));
            redirect(admin_url('page', ['id' => $id]));
        }
    }

    $field = function (string $name, string $label, array $vals, array $hints, bool $area, array $errs = [], string $chip = '', int $count = 0) : string {
        $cnt = $count ? ' data-count="' . $count . '"' : '';
        $fid = 'f-' . preg_replace('~[^a-z0-9]+~i', '-', $name);
        $out = '<div class="field' . ($errs ? ' is-invalid' : '') . '"><span class="lbl">' . e($label) . ($chip !== '' ? ' <code class="key">' . e($chip) . '</code>' : '') . '</span><div class="langs">';
        foreach (LANGS as $l) {
            $v = (string) ($vals[$l] ?? '');
            $rows = max(2, min(8, (int) ceil(mb_strlen($v !== '' ? $v : (string) ($hints[$l] ?? '')) / 46) + 1));   // поле занимает половину ширины формы
            $out .= '<div class="lang" data-lg="' . $l . '"><label for="' . $fid . '-' . $l . '">' . strtoupper($l) . '</label>'
                . ($area
                    ? '<textarea id="' . $fid . '-' . $l . '" name="' . e($name) . '[' . $l . ']" rows="' . $rows . '" lang="' . $l . '" placeholder="' . e((string) ($hints[$l] ?? '')) . '"' . $cnt . '>' . e($v) . '</textarea>'
                    : '<input id="' . $fid . '-' . $l . '" type="text" name="' . e($name) . '[' . $l . ']" value="' . e($v) . '" lang="' . $l . '" placeholder="' . e((string) ($hints[$l] ?? '')) . '"' . $cnt . '>')
                . (isset($errs[$l]) ? '<p class="err">' . e($errs[$l]) . '</p>' : '') . '</div>';
        }
        return $out . '</div></div>';
    };

    $base = base_path();
    $out = form_open(__($page['title']), '<a href="' . e(admin_url('pages')) . '">' . __('← Все страницы') . '</a>', 'page-form');
    if ($page['path'] !== null) {
        $open = strpos($page['path'], '…') === false;
        $out .= '<div class="field"><span class="lbl">' . __('Адрес страницы') . '</span><div class="addr"><input type="text" value="/' . e($page['path']) . '" readonly aria-label="' . e(__('Адрес страницы')) . '">'
            . ($open ? '<a class="btn btn-line" href="' . e($base . $page['path']) . '" target="_blank" rel="noopener">' . __('Открыть') . icon('ext') . '</a>' : '') . '</div>'
            . '<p class="hint">' . ($open ? __('Адрес не меняется: на нём держатся позиции страницы в поиске.') : __('У каждого товара свой адрес: /product/ и код товара.')) . '</p></div>';
    }
    if ($page['seo']) {
        $cur = ['title' => [], 'desc' => []];
        $auto = ['title' => [], 'desc' => []];
        foreach (LANGS as $l) {
            [$auto['title'][$l], $auto['desc'][$l]] = page_seo_default($id, $l);
            foreach (['title', 'desc'] as $part) {
                $cur[$part][$l] = $post !== null ? (string) ($post['seo'][$part][$l] ?? '') : own_text($seo[$id][$part] ?? null, $l);
            }
        }
        $out .= '<h3 class="block">' . __('SEO — для поисковиков') . '</h3>'
            . $field('seo[title]', __('SEO-заголовок (title)'), $cur['title'], $auto['title'], false, [], '', 60)
            . $field('seo[desc]', __('SEO-описание (description)'), $cur['desc'], $auto['desc'], true, [], '', 160)
            . '<p class="hint hint-block">' . __('Заголовок виден на вкладке браузера и в результатах поиска, описание — под ним. Пока поле пустое, сайт ставит текст, который показан в нём серым.') . '</p>';
    }
    if ($page['more']) {
        $out .= '<p class="more">' . __('Ещё на этой странице:') . ' ';
        foreach ($page['more'] as $i => [$key, $label]) {
            $p = explode(':', $key);
            $url = $p[0] === 'list' ? admin_url('list', ['type' => $p[1]]) : ($p[0] === 'doc' ? admin_url('doc', ['name' => $p[1]]) : admin_url($p[0]));
            $out .= ($i ? ', ' : '') . '<a href="' . e($url) . '">' . e(__($label)) . '</a>';
        }
        $out .= '.</p>';
    }
    if ($blocks) $out .= '<p class="note note-in">' . __('Ниже — все надписи страницы. Слова в фигурных скобках, например {name}, сайт подставляет сам: их нужно оставить. Чтобы вернуть прежний текст, сотрите поле и сохраните.') . '</p>';
    foreach ($blocks as $block => $keys) {
        $out .= '<h3 class="block">' . e(__($block)) . '</h3>';
        foreach ($keys as $key) {
            $vals = [];
            $long = false;
            foreach (LANGS as $l) {
                $vals[$l] = $post !== null && isset($post['t'][$key][$l]) && is_string($post['t'][$key][$l]) ? $post['t'][$key][$l] : (string) ($tx[$l][$key] ?? ($def[$key][$l] ?? ''));
                $long = $long || mb_strlen((string) ($def[$key][$l] ?? '')) > 70 || mb_strlen($vals[$l]) > 70;
            }
            $name = (string) ($def[$key][ui_lang()] ?? $def[$key]['ru'] ?? $key);   // подпись поля — сама надпись на языке админ-панели
            $out .= $field('t[' . $key . ']', mb_strlen($name) > 64 ? mb_substr($name, 0, 64) . '…' : $name, $vals, $def[$key] ?? [], $long, $errors[$key] ?? [], $key);
        }
    }
    $out .= form_close('<a href="' . e(admin_url('pages')) . '">' . __('Отмена') . '</a>');
    if ($errors) $out = '<p class="flash flash-err" role="alert">' . __('Не сохранено: проверьте поля, отмеченные красным, на всех трёх языках.') . '</p>' . $out;
    admin_page(__('Страницы'), $out, 'pages');
}

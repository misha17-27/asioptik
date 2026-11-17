<?php
/* Публичная часть: адреса страниц, заголовки для поисковиков и мессенджеров, приём заказов с сайта. */
declare(strict_types=1);

/** Заголовки и описания страниц на трёх языках (то же, что показывает сама страница). */
const SITE_TEXT = [
    'az' => [
        'home' => ['{shop} — eynək, linza və eynək təmiri', 'Çərçivələr, günəş eynəkləri, kontakt linzaları və reseptlə eynək linzaları. Eynək təmiri. Saytda sifariş, WhatsApp-da təsdiq.'],
        'catalog' => ['Kataloq', 'Çərçivənin qiyməti linzasız göstərilib. Eynək linzaları cüt, kontakt linzaları isə qutu ilə satılır.'],
        'blog' => ['Bloq', 'Qısa və konkret: resepti necə oxumaq, eynəyi necə seçmək və ona necə qulluq etmək.'],
        'contacts' => ['Əlaqə', 'WhatsApp-a yazın, zəng edin və ya salona gəlin.'],
        'checkout' => ['Sifarişin rəsmiləşdirilməsi', ''],
    ],
    'ru' => [
        'home' => ['{shop} — очки, линзы и ремонт очков', 'Оправы, солнцезащитные очки, контактные линзы и линзы для очков по рецепту. Ремонт очков. Заказ на сайте, подтверждение в WhatsApp.'],
        'catalog' => ['Каталог', 'Цена оправы указана без линз. Линзы для очков продаются парой, контактные линзы — упаковками.'],
        'blog' => ['Блог', 'Коротко и по делу: как читать рецепт, как выбрать очки и как за ними ухаживать.'],
        'contacts' => ['Контакты', 'Напишите в WhatsApp, позвоните или приходите в салон.'],
        'checkout' => ['Оформление заказа', ''],
    ],
    'en' => [
        'home' => ['{shop} — glasses, lenses and repairs', 'Frames, sunglasses, contact lenses and prescription lenses. Eyewear repairs. Order on the site, confirm on WhatsApp.'],
        'catalog' => ['Catalog', 'Frame prices don’t include lenses. Spectacle lenses are sold in pairs, contact lenses by the box.'],
        'blog' => ['Blog', 'Short and practical: how to read a prescription, choose glasses and look after them.'],
        'contacts' => ['Contacts', 'Message us on WhatsApp, call or visit the shop.'],
        'checkout' => ['Checkout', ''],
    ],
];

function tr($v, string $lang): string
{
    if (is_array($v)) return (string) ($v[$lang] ?? $v['az'] ?? reset($v) ?: '');
    return (string) $v;
}

/** Надпись сайта на нужном языке: сначала изменённая в админ-панели, потом встроенная; слова в {скобках} подставляются. */
function site_text(string $key, string $lang, array $vars = []): string
{
    $own = setting('texts', []);
    $def = texts_default();
    $s = is_array($own) && isset($own[$lang][$key]) && is_string($own[$lang][$key]) && $own[$lang][$key] !== '' ? $own[$lang][$key] : (string) ($def[$key][$lang] ?? ($def[$key]['az'] ?? ''));
    foreach ($vars as $k => $v) $s = str_replace('{' . $k . '}', (string) $v, $s);
    return $s;
}

/** Описание страницы товара для поисковиков, когда своё не задано: название, короткое описание, раздел и салон. */
function product_desc(array $p, string $lang, array $data): string
{
    $cat = '';
    foreach ($data['CATEGORIES'] ?? [] as $c) {
        if (($c['id'] ?? '') === ($p['cat'] ?? null)) $cat = tr($c['name'] ?? '', $lang);
    }
    $s = site_text('seo.product', $lang, ['name' => tr($p['name'] ?? '', $lang), 'sub' => tr($p['sub'] ?? '', $lang), 'cat' => $cat, 'shop' => (string) ($data['CONFIG']['shopName'] ?? 'Asioptik')]);
    return (string) preg_replace('~\s*\.\s*\.~u', '.', $s);   // у товара без короткого описания не остаётся двух точек подряд
}

function site_run(): void
{
    if (!config()) redirect(base_path() . 'install.php');
    $base = base_path();
    $path = (string) (parse_url((string) ($_SERVER['REQUEST_URI'] ?? '/'), PHP_URL_PATH) ?: '/');
    $rel = strpos($path, $base) === 0 ? substr($path, strlen($base)) : ltrim($path, '/');
    $rel = trim(rawurldecode($rel), '/');
    if ($rel === 'index.php') $rel = '';
    $seg = $rel === '' ? [] : explode('/', $rel);

    if ($seg === ['api', 'order']) api_order();
    if ($rel === 'robots.txt') site_robots();
    if ($rel === 'sitemap.xml') site_sitemap();

    $lang = in_array($_GET['lang'] ?? '', LANGS, true) ? (string) $_GET['lang'] : 'az';
    $keep = [];
    foreach (['lang', 'cat', 'aud', 'brand'] as $k) {
        if (isset($_GET[$k]) && is_string($_GET[$k]) && $_GET[$k] !== '') $keep[$k] = $_GET[$k];
    }
    $query = function (array $q): string {
        return $q ? '?' . http_build_query($q) : '';
    };

    // Прежние адреса вида ?page=about и ?product=код ведут на обычные
    if (isset($_GET['product']) || isset($_GET['page'])) {
        $to = '';
        if (isset($_GET['product']) && is_string($_GET['product'])) $to = 'product/' . rawurlencode($_GET['product']);
        elseif (is_string($_GET['page'])) $to = rawurlencode($_GET['page']) . (isset($_GET['post']) && is_string($_GET['post']) ? '/' . rawurlencode($_GET['post']) : '');
        redirect($base . $to . $query($keep), 301);
    }

    $data = site_data();
    $cfg = $data['CONFIG'];
    $shop = (string) ($cfg['shopName'] ?? 'Asioptik');
    $T = SITE_TEXT[$lang];
    $title = str_replace('{shop}', $shop, $T['home'][0]);
    $desc = $T['home'][1];
    $route = '';
    $noindex = false;

    $first = $seg[0] ?? '';
    if ($first === '') {
        $route = '';
    } elseif ($first === 'product' && isset($seg[1]) && count($seg) === 2) {
        $p = null;
        foreach ($data['PRODUCTS'] as $x) {
            if ($x['id'] === $seg[1]) $p = $x;
        }
        if (!$p) redirect($base . 'catalog' . $query($keep));
        $route = 'product/' . rawurlencode($p['id']);
        $title = own_text($p['seoTitle'] ?? null, $lang) ?: tr($p['name'] ?? '', $lang) . ' — ' . $shop;
        $desc = own_text($p['seoDesc'] ?? null, $lang) ?: product_desc($p, $lang, $data);
    } elseif ($first === 'blog' && count($seg) <= 2) {
        $route = 'blog';
        $title = $T['blog'][0] . ' — ' . $shop;
        $desc = $T['blog'][1];
        if (isset($seg[1])) {
            $post = null;
            foreach ($data['POSTS'] as $x) {
                if ($x['id'] === $seg[1]) $post = $x;
            }
            if (!$post) redirect($base . 'blog' . $query($keep));
            $route = 'blog/' . rawurlencode($post['id']);
            $title = own_text($post['seoTitle'] ?? null, $lang) ?: tr($post['title'] ?? '', $lang) . ' — ' . $shop;
            $desc = own_text($post['seoDesc'] ?? null, $lang) ?: tr($post['lead'] ?? '', $lang);
        }
    } elseif ($first === 'about' && count($seg) === 1) {
        $route = 'about';
        $about = is_array($data['ABOUT']) ? $data['ABOUT'] : [];
        $title = (tr($about['title'] ?? 'About', $lang)) . ' — ' . $shop;
        $desc = tr($about['lead'] ?? '', $lang);
    } elseif (in_array($first, ['catalog', 'contacts', 'checkout'], true) && count($seg) === 1) {
        $route = $first;
        $title = $T[$first][0] . ' — ' . $shop;
        $desc = $T[$first][1] ?: $T['home'][1];
        $noindex = $first === 'checkout';
        if ($first === 'catalog' && isset($keep['cat'])) {
            foreach ($data['CATEGORIES'] as $c) {
                if ($c['id'] === $keep['cat']) $title = tr($c['name'] ?? '', $lang) . ' — ' . $title;
            }
        }
    } else {
        redirect($base . $query(array_intersect_key($keep, ['lang' => 1])));   // неизвестный адрес — на главную
    }
    // Свои заголовок и описание страницы из раздела «Страницы» админ-панели (у раздела каталога и у статьи остаются свои)
    $pageId = $route === '' ? 'home' : $route;
    $seo = is_array($data['SEO'] ?? null) ? ($data['SEO'][$pageId] ?? null) : null;
    if (is_array($seo) && !($route === 'catalog' && isset($keep['cat']))) {
        $title = own_text($seo['title'] ?? null, $lang) ?: $title;
        $desc = own_text($seo['desc'] ?? null, $lang) ?: $desc;
    }

    $site = rtrim((string) ($cfg['siteUrl'] ?? ''), '/');
    if ($site === '' || !preg_match('~^https?://~i', $site)) $site = origin() . rtrim($base, '/');
    $canonQ = array_intersect_key($keep, $route === 'catalog' ? ['cat' => 1, 'aud' => 1] : []);
    $url = function (string $l) use ($site, $route, $canonQ, $query): string {
        return $site . '/' . $route . $query(($l === 'az' ? [] : ['lang' => $l]) + $canonQ);
    };
    $hreflang = '';
    foreach (LANGS as $l) $hreflang .= '<link rel="alternate" hreflang="' . $l . '" href="' . e($url($l)) . '">' . "\n";

    // Данные для страницы: всё из базы плюс то, что зависит от сервера
    $data = site_data_urls($data);
    $data['CONFIG']['pathRoutes'] = true;
    $data['CONFIG']['basePath'] = $base;
    $data['CONFIG']['api'] = $base . 'api/order';
    $data['CONFIG']['apiToken'] = api_token();
    $data['CONFIG']['siteUrl'] = $site . '/';
    $flags = JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP;
    $js = '';
    // TEXTS и SEO — надписи и заголовки страниц, изменённые в админ-панели (раздел «Страницы»)
    foreach (['CONFIG', 'CATEGORIES', 'RX', 'AUDIENCES', 'PRODUCTS', 'BRANDS', 'SERVICES', 'ABOUT', 'POSTS', 'TEXTS', 'SEO'] as $k) {
        $v = $data[$k] ?? [];
        if (in_array($k, ['CONFIG', 'RX', 'ABOUT', 'TEXTS', 'SEO'], true) && ($v === [] || !is_array($v) && !is_object($v))) $v = new stdClass();
        $js .= "const $k = " . json_encode($v, $flags) . ";\n";
    }

    $ver = substr(md5((string) @filemtime(ROOT . '/assets/js/app.js') . (string) @filemtime(ROOT . '/assets/css/app.css')), 0, 8);
    $html = strtr((string) file_get_contents(APP . '/site/shell.html'), [
        '%%LANG%%' => $lang,
        '%%TITLE%%' => e($title),
        '%%DESC%%' => e($desc),
        '%%CANON%%' => e($url($lang)),
        '%%HREFLANG%%' => $hreflang,
        '%%SHOP%%' => e($shop),
        '%%ROBOTS%%' => $noindex ? '<meta name="robots" content="noindex">' . "\n" : '',
        '%%BASE%%' => e($base),
        '%%VER%%' => $ver,
        '%%DATA%%' => $js,
    ]);
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: no-cache');
    site_headers();
    echo $html;
    exit;
}

/** Заголовки безопасности для страниц сайта. */
function site_headers(): void
{
    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: SAMEORIGIN');
    header('Referrer-Policy: strict-origin-when-cross-origin');
    header('Permissions-Policy: geolocation=(), microphone=(), camera=()');
    // Скрипты и запросы — только со своего сайта; шрифты Google, карта Google и картинки по https разрешены
    header("Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        . "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https:; frame-src https://www.google.com https://maps.google.com; "
        . "connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'");
    if (is_https()) header('Strict-Transport-Security: max-age=15552000');
}

/* ---------- приём заказа, заявки на ремонт или сообщения с сайта ---------- */
function api_order(): void
{
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') json_out(['ok' => false, 'error' => 'method'], 405);
    // Запросы с чужих сайтов не принимаем
    $from = (string) ($_SERVER['HTTP_ORIGIN'] ?? '');
    if ($from !== '' && parse_url($from, PHP_URL_HOST) !== parse_url(origin(), PHP_URL_HOST)) json_out(['ok' => false, 'error' => 'origin'], 403);
    $raw = (string) file_get_contents('php://input', false, null, 0, 70000);
    if (strlen($raw) > 65000) json_out(['ok' => false, 'error' => 'size'], 413);
    $in = json_decode($raw, true);
    if (!is_array($in)) json_out(['ok' => false, 'error' => 'json'], 400);
    if (!api_token_valid((string) ($in['token'] ?? ''))) json_out(['ok' => false, 'error' => 'token'], 403);
    $kind = (string) ($in['kind'] ?? '');
    if (!isset(ORDER_KINDS[$kind])) json_out(['ok' => false, 'error' => 'kind'], 400);

    $clean = function ($v, int $max): string {
        $s = is_scalar($v) ? (string) $v : '';
        $s = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F]/u', '', $s) ?? '';
        return mb_substr(trim($s), 0, $max);
    };
    $name = $clean($in['name'] ?? '', 120);
    $phone = $clean($in['phone'] ?? '', 40);
    $text = $clean($in['text'] ?? '', 8000);
    $digits = strlen((string) preg_replace('/\D/', '', $phone));
    if (mb_strlen($name) < 2 || $digits < 7 || $digits > 15 || $text === '') json_out(['ok' => false, 'error' => 'fields'], 422);

    $ip = client_ip_hash();
    $recent = q('SELECT COUNT(*) AS n FROM ao_orders WHERE ip_hash = ? AND created_at > ?', [$ip, date('Y-m-d H:i:s', time() - 3600)])->fetch();
    if ((int) $recent['n'] >= 20) json_out(['ok' => false, 'error' => 'rate'], 429);

    $number = $clean($in['number'] ?? '', 24);
    if (!preg_match('/^[A-Z]{1,3}-\d{2,6}-\d{2,8}$/', $number)) $number = ($kind === 'message' ? 'M' : ($kind === 'repair' ? 'R' : 'OP')) . '-' . date('dm') . '-' . random_int(1000, 9999);
    $total = isset($in['total']) && is_numeric($in['total']) && $in['total'] >= 0 && $in['total'] < 1000000 ? round((float) $in['total'], 2) : null;
    $json = to_json(['text' => $text, 'details' => order_details($in['details'] ?? null, $clean)]);
    if (strlen($json) > 60000) $json = to_json(['text' => $text, 'details' => []]);
    $lang = in_array($in['lang'] ?? '', LANGS, true) ? $in['lang'] : '';

    q('INSERT INTO ao_orders (number, kind, status, created_at, name, phone, total, lang, data, ip_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [$number, $kind, 'new', now(), $name, $phone, $total, $lang, $json, $ip]);
    json_out(['ok' => true, 'number' => $number]);
}

/**
 * Подробности заказа с сайта: берём только известные поля, только простые значения и с ограничением длины.
 * Всё остальное, что пришло в запросе, отбрасывается.
 */
function order_details($d, callable $clean): array
{
    if (!is_array($d)) return [];
    $num = function ($v): ?float {
        return is_numeric($v) && $v >= 0 && $v < 1000000 ? round((float) $v, 2) : null;
    };
    $out = [];
    foreach (['delivery' => 20, 'payment' => 20, 'handover' => 20, 'date' => 20, 'topic' => 120, 'address' => 300, 'comment' => 1500] as $k => $max) {
        $v = $clean($d[$k] ?? '', $max);
        if ($v !== '') $out[$k] = $v;
    }
    foreach (['subtotal', 'deliveryCost'] as $k) {
        if (($n = $num($d[$k] ?? null)) !== null) $out[$k] = $n;
    }
    if (!empty($d['rxPhoto'])) $out['rxPhoto'] = true;
    foreach (array_slice(is_array($d['services'] ?? null) ? $d['services'] : [], 0, 30) as $s) {
        if (($s = $clean($s, 200)) !== '') $out['services'][] = $s;
    }
    foreach (array_slice(is_array($d['items'] ?? null) ? $d['items'] : [], 0, 60) as $it) {
        if (!is_array($it)) continue;
        $lines = [];
        foreach (array_slice(is_array($it['lines'] ?? null) ? $it['lines'] : [], 0, 30) as $l) {
            if (($l = $clean($l, 300)) !== '') $lines[] = $l;
        }
        $out['items'][] = [
            'id' => $clean($it['id'] ?? '', 80), 'name' => $clean($it['name'] ?? '', 200), 'lines' => $lines,
            'qty' => max(0, min(999, is_numeric($it['qty'] ?? null) ? (int) $it['qty'] : 0)),
            'price' => $num($it['price'] ?? null), 'sum' => $num($it['sum'] ?? null),
        ];
    }
    return $out;
}

function site_origin_url(): string
{
    $cfg = setting('config', []);
    $site = rtrim((string) ($cfg['siteUrl'] ?? ''), '/');
    return ($site !== '' && preg_match('~^https?://~i', $site)) ? $site : origin() . rtrim(base_path(), '/');
}

function site_robots(): void
{
    header('Content-Type: text/plain; charset=utf-8');
    echo "User-agent: *\nDisallow: " . base_path() . "admin/\nDisallow: " . base_path() . "api/\nDisallow: " . base_path() . "checkout\n\nSitemap: " . site_origin_url() . "/sitemap.xml\n";
    exit;
}

function site_sitemap(): void
{
    $data = site_data();
    $site = site_origin_url();
    $urls = ['', 'catalog', 'about', 'blog', 'contacts'];
    foreach ($data['CATEGORIES'] as $c) $urls[] = 'catalog?cat=' . rawurlencode($c['id']);
    foreach ($data['PRODUCTS'] as $p) $urls[] = 'product/' . rawurlencode($p['id']);
    foreach ($data['POSTS'] as $p) $urls[] = 'blog/' . rawurlencode($p['id']);
    header('Content-Type: application/xml; charset=utf-8');
    echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n" . '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . "\n";
    foreach ($urls as $u) echo '  <url><loc>' . e($site . '/' . $u) . '</loc></url>' . "\n";
    echo "</urlset>\n";
    exit;
}

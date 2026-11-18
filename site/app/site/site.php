<?php
/* Публичная часть: адреса страниц, заголовки для поисковиков и мессенджеров, приём заказов с сайта. */
declare(strict_types=1);

/** Значение на нужном языке; если перевода нет — на основном (az), иначе какое есть. */
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
    // слова подставляются за один проход, как в скрипте сайта: подставленное значение второй раз не разбирается
    return (string) preg_replace_callback('~\{(\w+)\}~', function (array $m) use ($vars): string {
        return isset($vars[$m[1]]) ? (string) $vars[$m[1]] : $m[0];
    }, $s);
}

/* ---------- заголовок и описание страницы для поисковиков (title и description) ----------
   Правила одни для сервера и для скрипта сайта (assets/js/app.js, функция pageMeta): страница, отданная сервером,
   и страница после перехода по сайту должны называться одинаково. Это проверяет test/php_seo.py.
   Свой текст из админ-панели ставится как есть; текст, который сайт собирает сам, укладывается в SEO_MAX знаков. */
const SEO_MAX = 160;

/** Две точки подряд и лишние пробелы (остаются, когда в шаблон подставлено пустое значение). */
function seo_clean(string $s): string
{
    $s = (string) preg_replace('~[ \t\r\n]*\.[ \t\r\n]*\.~u', '.', $s);
    return trim((string) preg_replace('~[ \t\r\n]+~u', ' ', $s), ' ');
}

/** Текст, который встаёт в середину описания, должен кончаться точкой. */
function seo_sentence(string $s): string
{
    $s = trim($s, " \t\r\n");
    return $s !== '' && !preg_match('~[.!?…]\z~u', $s) ? $s . '.' : $s;
}

/** Описание не длиннее SEO_MAX знаков: длинный текст обрезается по слову и кончается многоточием. */
function seo_clip(string $s): string
{
    $s = seo_clean($s);
    if (mb_strlen($s) <= SEO_MAX) return $s;
    $cut = mb_substr($s, 0, SEO_MAX - 3);
    $sp = mb_strrpos($cut, ' ');
    if ($sp !== false && $sp > 100) $cut = mb_substr($cut, 0, $sp);
    return (string) preg_replace('~[ ,;:.!?—–\-]+\z~u', '', $cut) . '…';
}

/** Товар относится к странице «для кого»: у раздела из частей («Взрослым») — к любой из частей. */
function in_audience(array $p, ?array $aud): bool
{
    if (!$aud) return true;
    $ids = array_column(is_array($aud['parts'] ?? null) ? $aud['parts'] : [], 'id') ?: [(string) ($aud['id'] ?? '')];
    return (bool) array_intersect($ids, is_array($p['for'] ?? null) ? $p['for'] : []);
}

/**
 * Заголовок и описание, которые сайт ставит сам, пока свои не заданы: [title, description].
 * $kind — страница сайта: home, catalog, brands, blog, about, contacts, checkout;
 *         или то, у чего своя страница: product (товар), post (статья), brand (бренд), category (раздел каталога) — тогда $item.
 * $aud  — открытая страница «для кого» (у каталога и у раздела каталога).
 */
function seo_auto(string $kind, string $lang, array $data, ?array $item = null, ?array $aud = null): array
{
    $shop = (string) ($data['CONFIG']['shopName'] ?? 'Asioptik');
    $T = function (string $key, array $vars = []) use ($lang, $shop): string {
        return site_text($key, $lang, $vars + ['shop' => $shop]);
    };
    $item = $item ?? [];
    $an = $aud ? (tr($aud['title'] ?? '', $lang) ?: tr($aud['name'] ?? '', $lang)) : '';
    $at = $aud ? seo_sentence(tr($aud['text'] ?? '', $lang)) : '';
    switch ($kind) {
        case 'product':
            $cat = '';
            foreach ($data['CATEGORIES'] ?? [] as $c) {
                if (($c['id'] ?? '') === ($item['cat'] ?? null)) $cat = tr($c['name'] ?? '', $lang);
            }
            $name = tr($item['name'] ?? '', $lang);
            return [$name . ' — ' . $shop, seo_clip($T('seo.product', ['name' => $name, 'sub' => tr($item['sub'] ?? '', $lang), 'cat' => $cat]))];
        case 'post':
            return [tr($item['title'] ?? '', $lang) . ' — ' . $shop, seo_clip(tr($item['lead'] ?? '', $lang)) ?: seo_clip($T('bl.lead'))];
        case 'brand':
            $name = (string) ($item['name'] ?? '');
            return [$name . ' — ' . $shop, seo_clip($T('brs.seo', ['name' => $name, 'text' => seo_sentence(tr($item['text'] ?? '', $lang))]))];
        case 'category':
            $name = tr($item['name'] ?? '', $lang);
            if ($aud) return [$name . ' — ' . $an . ' — ' . $shop, seo_clip($T('cseo.both', ['name' => $name, 'aud' => $an, 'text' => $at]))];
            return [$name . ' — ' . $T('cat.title') . ' — ' . $shop, seo_clip($T('cseo.cat', ['name' => $name]))];
        case 'catalog':
            if ($aud) return [$an . ' — ' . $shop, seo_clip($T('cseo.aud', ['name' => $an, 'text' => $at]))];
            return [$T('cat.title') . ' — ' . $shop, seo_clip($T('cat.lead'))];
        case 'brands':
            return [$T('brs.title') . ' — ' . $shop, seo_clip($T('brs.lead'))];
        case 'blog':
            return [$T('bl.title') . ' — ' . $shop, seo_clip($T('bl.lead'))];
        case 'about':
            $about = is_array($data['ABOUT'] ?? null) ? $data['ABOUT'] : [];
            return [tr($about['title'] ?? 'About', $lang) . ' — ' . $shop, seo_clip(tr($about['lead'] ?? '', $lang))];
        case 'contacts':   // в описании, кроме текста страницы, стоит адрес салона
            $addr = seo_sentence(tr($data['CONFIG']['address'] ?? '', $lang));
            return [$T('ct.title') . ' — ' . $shop, seo_clip($addr !== '' ? $T('ct.seo', ['lead' => seo_sentence($T('ct.lead')), 'address' => $addr]) : $T('ct.lead'))];
        case 'checkout':
            return [$T('co.title') . ' — ' . $shop, ''];
    }
    return [$T('meta.title'), seo_clip($T('meta.desc'))];
}

/** Итог: свои заголовок и описание ($own: ['title' => […], 'desc' => […]] или seoTitle/seoDesc записи), иначе собранные сайтом. */
function seo_meta(array $auto, $ownTitle, $ownDesc, string $lang, array $data): array
{
    $desc = own_text($ownDesc, $lang) ?: $auto[1];
    return [own_text($ownTitle, $lang) ?: $auto[0], $desc !== '' ? $desc : seo_auto('home', $lang, $data)[1]];
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
    // Сайт во временной папке другого домена поисковикам не показываем (см. site_is_preview)
    $preview = site_is_preview($cfg);
    if ($preview) header('X-Robots-Tag: noindex, nofollow');
    $shop = (string) ($cfg['shopName'] ?? 'Asioptik');
    $route = '';
    $noindex = false;
    // Что открыто: $kind и $item — для заголовка и описания (см. seo_auto), $page — страница из раздела «Страницы» админ-панели
    $kind = 'home';
    $page = 'home';
    $item = null;
    $aud = null;
    $find = function (array $rows, string $id): ?array {
        foreach ($rows as $x) {
            if (is_array($x) && (string) ($x['id'] ?? '') === $id) return $x;
        }
        return null;
    };
    $onlyLang = array_intersect_key($keep, ['lang' => 1]);

    $first = $seg[0] ?? '';
    if ($first === '') {
        $route = '';
    } elseif ($first === 'product' && isset($seg[1]) && count($seg) === 2) {
        $item = $find($data['PRODUCTS'], $seg[1]);
        if (!$item) redirect($base . 'catalog' . $query($keep));
        $route = 'product/' . rawurlencode($item['id']);
        $kind = 'product';
        $page = '';
    } elseif ($first === 'blog' && count($seg) <= 2) {
        $route = $kind = $page = 'blog';
        if (isset($seg[1])) {
            $item = $find($data['POSTS'], $seg[1]);
            if (!$item) redirect($base . 'blog' . $query($keep));
            $route = 'blog/' . rawurlencode($item['id']);
            $kind = 'post';
            $page = '';
        }
    } elseif ($first === 'brands' && count($seg) <= 2) {
        // Все бренды и страница бренда с его товарами. Бренд без товаров на сайте не показывается, поэтому поисковикам его страница не нужна
        $route = $kind = $page = 'brands';
        $filled = array_flip(array_filter(array_column($data['PRODUCTS'], 'brand'), 'is_string'));
        $noindex = !$filled;
        if (isset($seg[1])) {
            $item = $find($data['BRANDS'], $seg[1]);
            if (!$item) redirect($base . 'brands' . $query($onlyLang));
            $route = 'brands/' . rawurlencode($item['id']);
            $kind = 'brand';
            $page = '';
            $noindex = !isset($filled[$item['id']]);
        }
    } elseif (in_array($first, ['about', 'catalog', 'contacts', 'checkout'], true) && count($seg) === 1) {
        $route = $kind = $page = $first;
        $noindex = $first === 'checkout';
        if ($first === 'catalog') {
            // Страница «для кого» (?aud=adults, men, women, kids): свой заголовок и текст, как на самой странице
            foreach ($data['AUDIENCES'] as $a) {
                foreach (array_merge([$a], is_array($a['parts'] ?? null) ? $a['parts'] : []) as $x) {
                    if (isset($keep['aud']) && ($x['id'] ?? '') === $keep['aud']) $aud = $x;
                }
            }
            if (!$aud) unset($keep['aud']);   // незнакомое значение в адрес страницы не попадает
            // Раздел каталога (?cat=frames) открывается, когда в нём есть товары для выбранных «для кого»: так же решает страница
            $cat = isset($keep['cat']) ? $find($data['CATEGORIES'], $keep['cat']) : null;
            if ($cat) {
                $has = false;
                foreach ($data['PRODUCTS'] as $x) $has = $has || (($x['cat'] ?? '') === $cat['id'] && in_audience($x, $aud));
                if (!$has) $cat = null;
            }
            if (!$cat) unset($keep['cat']);
            if ($cat) {
                $kind = 'category';
                $item = $cat;
            }
            if ($cat || $aud) $page = '';
        }
    } else {
        redirect($base . $query($onlyLang));   // неизвестный адрес — на главную
    }
    // Свои заголовок и описание: у товара, статьи, бренда и раздела каталога — из их карточки (на странице «для кого» у раздела своих нет),
    // у страниц сайта — из раздела «Страницы» админ-панели
    $own = $page !== '' && is_array($data['SEO'] ?? null) && is_array($data['SEO'][$page] ?? null) ? $data['SEO'][$page] : [];
    if ($item && !($kind === 'category' && $aud)) $own = ['title' => $item['seoTitle'] ?? null, 'desc' => $item['seoDesc'] ?? null];
    [$title, $desc] = seo_meta(seo_auto($kind, $lang, $data, $item, $aud), $own['title'] ?? null, $own['desc'] ?? null, $lang, $data);

    $site = site_origin_url($cfg);
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
    // проверка «не робот» для форм: страница получает только публичный ключ
    $cap = captcha_allowed() && is_string($data['_cap'] ?? null) ? $data['_cap'] : '';
    if ($cap !== '') $data['CONFIG']['captchaKey'] = $cap;
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
        '%%ROBOTS%%' => $preview ? '<meta name="robots" content="noindex, nofollow">' . "\n" : ($noindex ? '<meta name="robots" content="noindex">' . "\n" : ''),
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
    // (политика целиком — в app/core/bootstrap.php, её же повторяет .htaccess)
    header('Content-Security-Policy: ' . CSP_SITE);
    // Это правило браузер запоминает для всего домена, поэтому сайт задаёт его, только когда домен целиком его:
    // в подпапке чужого сайта (временный адрес) решать за основной сайт нельзя
    if (is_https() && base_path() === '/') header('Strict-Transport-Security: max-age=15552000');
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
    // Проверка «не робот»: без неё запись не сохраняется (в WhatsApp заказ покупателя уходит в любом случае)
    if (captcha_on('forms') && !captcha_pass(is_string($in['captcha'] ?? null) ? $in['captcha'] : '')) json_out(['ok' => false, 'error' => 'captcha'], 403);

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

/** Основной адрес сайта из «Настроек сайта», без косой черты на конце; пустая строка — адрес не задан. */
function site_main_url(?array $cfg = null): string
{
    $cfg = $cfg ?? setting('config', []);
    $site = rtrim(trim((string) ($cfg['siteUrl'] ?? '')), '/');
    return preg_match('~^https?://[^/\s]+~i', $site) ? $site : '';
}

/** Адрес, по которому сайт открыт сейчас, без косой черты на конце. */
function site_here_url(): string
{
    return origin() . rtrim(base_path(), '/');
}

function site_origin_url(?array $cfg = null): string
{
    $main = site_main_url($cfg);
    return $main !== '' ? $main : site_here_url();
}

/**
 * Сайт открыт по временному адресу: лежит в подпапке, а домен не тот, что указан в «Адресе сайта»
 * (например mguliyev.com/asioptik, пока основной домен ещё не подключён). Такую копию поисковикам не показываем:
 * иначе в поиске окажутся два одинаковых сайта. На основном домене сайт виден поисковикам сам, без переключателей.
 * Строка 'preview' => true или false в storage/config.php задаёт это вручную — для особых случаев.
 */
function site_is_preview(?array $cfg = null): bool
{
    $c = config();
    if (is_array($c) && isset($c['preview']) && is_bool($c['preview'])) return $c['preview'];
    $main = site_main_url($cfg);
    if ($main === '' || base_path() === '/') return false;
    return host_key((string) parse_url($main, PHP_URL_HOST)) !== host_key((string) ($_SERVER['HTTP_HOST'] ?? ''));
}

function site_robots(): void
{
    header('Content-Type: text/plain; charset=utf-8');
    $b = base_path();
    $preview = site_is_preview();
    if ($preview) header('X-Robots-Tag: noindex, nofollow');
    // Запрет на обход здесь не ставится и для временного адреса: чтобы страница не попала в поиск,
    // поисковик должен её открыть и увидеть «noindex»
    echo "User-agent: *\nDisallow: {$b}admin/\nDisallow: {$b}api/\nDisallow: {$b}checkout\n" . ($preview ? '' : "\nSitemap: " . site_origin_url() . "/sitemap.xml\n");
    exit;
}

function site_sitemap(): void
{
    $data = site_data();
    $site = site_origin_url($data['CONFIG']);
    if (site_is_preview($data['CONFIG'])) header('X-Robots-Tag: noindex, nofollow');
    $urls = ['', 'catalog'];
    // разделы каталога и бренды попадают в карту, когда в них есть товары
    $inCat = array_flip(array_column($data['PRODUCTS'], 'cat'));
    foreach ($data['CATEGORIES'] as $c) {
        if (isset($inCat[$c['id']])) $urls[] = 'catalog?cat=' . rawurlencode($c['id']);
    }
    // страницы «для кого»: взрослым, мужчинам, женщинам, детям — если для них есть товары
    $for = [];
    foreach ($data['PRODUCTS'] as $p) foreach ((array) ($p['for'] ?? []) as $f) $for[$f] = true;
    foreach ($data['AUDIENCES'] as $a) {
        $parts = array_column(is_array($a['parts'] ?? null) ? $a['parts'] : [], 'id');
        if (array_intersect_key($for, array_flip($parts ?: [$a['id']]))) $urls[] = 'catalog?aud=' . rawurlencode($a['id']);
        foreach ($parts as $id) if (isset($for[$id])) $urls[] = 'catalog?aud=' . rawurlencode($id);
    }
    $inBrand = array_flip(array_filter(array_column($data['PRODUCTS'], 'brand'), 'is_string'));
    $brands = array_values(array_filter($data['BRANDS'], function ($x) use ($inBrand) {
        return isset($inBrand[$x['id']]);
    }));
    if ($brands) $urls[] = 'brands';
    foreach ($brands as $x) $urls[] = 'brands/' . rawurlencode($x['id']);
    array_push($urls, 'about', 'blog', 'contacts');
    foreach ($data['PRODUCTS'] as $p) $urls[] = 'product/' . rawurlencode($p['id']);
    foreach ($data['POSTS'] as $p) $urls[] = 'blog/' . rawurlencode($p['id']);
    header('Content-Type: application/xml; charset=utf-8');
    echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n" . '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . "\n";
    foreach ($urls as $u) echo '  <url><loc>' . e($site . '/' . $u) . '</loc></url>' . "\n";
    echo "</urlset>\n";
    exit;
}

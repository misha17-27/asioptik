<?php
/* Описание того, что редактируется в админ-панели: какие поля есть у товара, раздела, бренда, статьи и так далее. */
declare(strict_types=1);

function opt_categories(): array
{
    $o = [];
    foreach (items('category') as $c) $o[$c['slug']] = tr_admin($c['data']['name'] ?? $c['slug']);
    return $o;
}

function opt_brands(): array
{
    $o = [];
    foreach (items('brand') as $b) $o[$b['slug']] = (string) ($b['data']['name'] ?? $b['slug']);
    return $o;
}

function opt_products(): array
{
    $o = [];
    foreach (items('product') as $p) $o[$p['slug']] = tr_admin($p['data']['name'] ?? $p['slug']);
    return $o;
}

/** Куда может вести кнопка в конце статьи. */
function opt_post_links(): array
{
    $o = ['catalog:all' => 'Каталог: все товары', 'catalog:all:kids' => 'Каталог: детские модели'];
    foreach (opt_categories() as $id => $name) $o['catalog:' . $id] = 'Каталог: ' . $name;
    $o['repair'] = 'Мастерская (заявка на ремонт)';
    return $o;
}

/** Текст на русском для списков админ-панели (с запасным вариантом на других языках). */
function tr_admin($v): string
{
    if (is_array($v)) return (string) ($v['ru'] ?? $v['az'] ?? $v['en'] ?? '');
    return (string) $v;
}

function schemas(): array
{
    return [
        'product' => [
            'title' => 'Товары', 'add' => 'Добавить товар', 'one' => 'Товар', 'slug' => 'Код товара',
            'slug_hint' => 'Латиницей, без пробелов: f-milan. Попадает в адрес страницы товара. Можно оставить пустым — подставится сам.',
            'fields' => [
                ['key' => 'name', 'type' => 'i18n', 'label' => 'Название', 'req' => true],
                ['key' => 'sub', 'type' => 'i18n', 'label' => 'Короткое описание', 'hint' => 'Одна строка под названием: материал, форма, количество в упаковке.'],
                ['key' => 'cat', 'type' => 'select', 'label' => 'Раздел каталога', 'options' => 'opt_categories', 'req' => true],
                ['key' => 'brand', 'type' => 'select', 'label' => 'Бренд', 'options' => 'opt_brands', 'empty' => 'Без бренда'],
                ['key' => 'for', 'type' => 'checks', 'label' => 'Для кого', 'options' => ['men' => 'Мужчинам', 'women' => 'Женщинам', 'kids' => 'Детям'], 'hint' => 'Отмечается у очков. У линз и аксессуаров оставьте пустым.'],
                ['key' => 'price', 'type' => 'number', 'label' => 'Цена, ₼', 'req' => true],
                ['key' => 'old', 'type' => 'number', 'label' => 'Старая цена, ₼', 'hint' => 'Заполните, если товар со скидкой: на карточке появится метка со скидкой.'],
                ['key' => 'badge', 'type' => 'i18n', 'label' => 'Метка на фото', 'hint' => 'Например: Хит, Новинка. Можно не заполнять.'],
                ['key' => 'img', 'type' => 'image', 'label' => 'Фото товара', 'dir' => 'p', 'hint' => 'Лучше на белом фоне, товар по центру. Пока фото нет, на сайте показывается рисунок.'],
                ['key' => 'colors', 'type' => 'colors', 'label' => 'Цвета', 'hint' => 'Цвет — код вида #1f1f22. Строку без названия сайт не покажет.'],
                ['key' => 'info', 'type' => 'specs', 'label' => 'Характеристики', 'hint' => 'Каждая с новой строки, через двоеточие: «Материал: Ацетат».'],
                ['key' => 'withLenses', 'type' => 'bool', 'label' => 'Можно заказать вместе с линзами по рецепту', 'hint' => 'Для оправ.'],
                ['key' => 'home', 'type' => 'bool', 'label' => 'Показывать на главной странице', 'hint' => 'В секциях «Для мужчин» и «Для женщин» помещается по 3 товара, в «Для детей» — 4.'],
                ['key' => '_seo', 'type' => 'head', 'label' => 'SEO — для поисковиков', 'hint' => 'Заголовок страницы товара виден на вкладке браузера и в результатах поиска, описание — под ним. Пока поле пустое, сайт ставит текст сам (он показан в поле серым): название товара и салона; в описании — название, короткое описание, раздел и салон.'],
                ['key' => 'seoTitle', 'type' => 'i18n', 'label' => 'SEO-заголовок (title)', 'count' => 60],
                ['key' => 'seoDesc', 'type' => 'i18n_area', 'label' => 'SEO-описание (description)', 'rows' => 2, 'count' => 160],
            ],
        ],
        'category' => [
            'title' => 'Разделы каталога', 'one' => 'Раздел', 'fixed' => true,
            'note' => 'Список разделов постоянный: от раздела зависит, как товар оформляется на сайте (оправа, линзы по рецепту, контактные линзы). Здесь меняются названия и слайд на первом экране.',
            'fields' => [
                ['key' => 'name', 'type' => 'i18n', 'label' => 'Название', 'req' => true],
                ['key' => 'short', 'type' => 'i18n', 'label' => 'Короткое название', 'hint' => 'Для списка разделов в каталоге. Можно не заполнять.'],
                ['key' => 'banner.text', 'type' => 'i18n', 'label' => 'Текст на слайде первого экрана'],
                ['key' => 'banner.img', 'type' => 'image', 'label' => 'Фото на слайде', 'dir' => 'b', 'hint' => 'Примерно 1200×1000. Текст стоит слева сверху, поэтому главное на фото должно быть справа.'],
            ],
        ],
        'brand' => [
            'title' => 'Бренды', 'add' => 'Добавить бренд', 'one' => 'Бренд', 'slug' => 'Код бренда',
            'slug_hint' => 'Латиницей. Можно оставить пустым — подставится из названия.',
            'fields' => [
                ['key' => 'name', 'type' => 'text', 'label' => 'Название', 'req' => true],
            ],
        ],
        'service' => [
            'title' => 'Услуги мастерской', 'add' => 'Добавить услугу', 'one' => 'Услуга', 'slug' => 'Код услуги',
            'slug_hint' => 'Латиницей. Можно оставить пустым.',
            'fields' => [
                ['key' => 'name', 'type' => 'i18n', 'label' => 'Название', 'req' => true],
                ['key' => 'price', 'type' => 'number', 'label' => 'Цена, ₼', 'req' => true],
                ['key' => 'from', 'type' => 'bool', 'label' => 'Показывать цену как «от …»'],
                ['key' => 'time', 'type' => 'i18n', 'label' => 'Срок', 'hint' => 'Например: 15 минут, 1–2 дня.'],
            ],
        ],
        'post' => [
            'title' => 'Блог', 'add' => 'Добавить статью', 'one' => 'Статья', 'slug' => 'Код статьи',
            'slug_hint' => 'Латиницей: попадает в адрес статьи. Можно оставить пустым.',
            'fields' => [
                ['key' => 'date', 'type' => 'date', 'label' => 'Дата', 'req' => true],
                ['key' => 'title', 'type' => 'i18n', 'label' => 'Заголовок', 'req' => true],
                ['key' => 'lead', 'type' => 'i18n_area', 'label' => 'Вступление', 'rows' => 3, 'hint' => 'Одно-два предложения: показываются в списке статей и под заголовком.'],
                ['key' => 'body', 'type' => 'i18n_lines', 'label' => 'Текст', 'rows' => 14, 'hint' => 'Каждый абзац с новой строки. Строка с «## » в начале — подзаголовок, с «- » в начале — пункт списка.'],
                ['key' => 'img', 'type' => 'image', 'label' => 'Фото к статье', 'dir' => 'blog', 'hint' => 'Горизонтальное, примерно 1600×700. Если фото нет, показывается рисунок товара.'],
                ['key' => 'art.id', 'type' => 'select', 'label' => 'Рисунок товара вместо фото', 'options' => 'opt_products', 'empty' => 'Нет'],
                ['key' => 'cta.text', 'type' => 'i18n', 'label' => 'Кнопка в конце статьи: надпись', 'hint' => 'Если кнопка не нужна, оставьте пустым.'],
                ['key' => '_link', 'type' => 'select', 'label' => 'Кнопка в конце статьи: куда ведёт', 'options' => 'opt_post_links', 'empty' => 'Никуда'],
                ['key' => '_seo', 'type' => 'head', 'label' => 'SEO — для поисковиков', 'hint' => 'Заголовок страницы статьи виден на вкладке браузера и в результатах поиска, описание — под ним. Пока поле пустое, сайт ставит текст сам (он показан в поле серым): заголовок статьи и название салона; в описании — вступление статьи.'],
                ['key' => 'seoTitle', 'type' => 'i18n', 'label' => 'SEO-заголовок (title)', 'count' => 60],
                ['key' => 'seoDesc', 'type' => 'i18n_area', 'label' => 'SEO-описание (description)', 'rows' => 2, 'count' => 160],
            ],
            // «Куда ведёт кнопка» хранится как cta.hash / cta.goto / cta.aud
            'load' => function (array $d): array {
                $c = $d['cta'] ?? [];
                if (($c['hash'] ?? '') === '#repair') $d['_link'] = 'repair';
                elseif (($c['hash'] ?? '') === '#catalog') $d['_link'] = 'catalog:' . ($c['goto'] ?? 'all') . (!empty($c['aud']) ? ':' . $c['aud'] : '');
                return $d;
            },
            'save' => function (array $d): array {
                $link = (string) ($d['_link'] ?? '');
                unset($d['_link']);
                $text = $d['cta']['text'] ?? null;
                unset($d['cta']);
                if ($link !== '' && $text) {
                    $p = explode(':', $link);
                    $d['cta'] = $p[0] === 'repair' ? ['hash' => '#repair'] : ['hash' => '#catalog', 'goto' => $p[1] ?? 'all'] + (isset($p[2]) ? ['aud' => $p[2]] : []);
                    $d['cta']['text'] = $text;
                }
                if (isset($d['art']) && empty($d['art']['id'])) unset($d['art']);
                return $d;
            },
        ],
    ];
}

/** Страницы с одним набором полей: настройки сайта и «О нас». */
function doc_schemas(): array
{
    return [
        'config' => [
            'title' => 'Настройки сайта', 'head' => 'Контакты и доставка', 'note' => 'Контакты и доставка. После сохранения изменения сразу видны на сайте.',
            'fields' => [
                ['key' => 'shopName', 'type' => 'text', 'label' => 'Название магазина', 'req' => true],
                ['key' => 'phone', 'type' => 'text', 'label' => 'Телефон', 'hint' => 'Как показывать на сайте: +994 50 123 45 67'],
                ['key' => 'whatsapp', 'type' => 'text', 'label' => 'Номер WhatsApp для заказов', 'req' => true, 'hint' => 'Только цифры с кодом страны, без плюса: 994501234567. На этот номер приходят заказы.'],
                ['key' => 'address', 'type' => 'i18n', 'label' => 'Адрес'],
                ['key' => 'hours', 'type' => 'i18n_lines', 'label' => 'Часы работы', 'rows' => 3, 'hint' => 'Каждая строка отдельно: «Пн–Сб: 10:00–20:00».'],
                ['key' => 'instagram', 'type' => 'text', 'label' => 'Instagram', 'hint' => 'Имя без @. Если пусто, ссылка на сайте не показывается.'],
                ['key' => 'mapQuery', 'type' => 'text', 'label' => 'Адрес для карты', 'hint' => 'Заполните, если карта показывает не то место: точный адрес или название на Google Картах.'],
                ['key' => 'deliveryPrice', 'type' => 'number', 'label' => 'Доставка курьером, ₼'],
                ['key' => 'freeDeliveryFrom', 'type' => 'number', 'label' => 'Бесплатная доставка от суммы, ₼', 'hint' => '0 — бесплатной доставки нет.'],
                ['key' => 'siteUrl', 'type' => 'text', 'label' => 'Адрес сайта', 'hint' => 'Например: https://asioptik.az/'],
            ],
        ],
        'about' => [
            'title' => 'Страница «О нас»', 'head' => 'Тексты и фото', 'back' => ['page', ['id' => 'about'], 'Надписи и SEO страницы'],
            'fields' => [
                ['key' => 'title', 'type' => 'i18n', 'label' => 'Заголовок', 'req' => true],
                ['key' => 'lead', 'type' => 'i18n_area', 'label' => 'Вступление', 'rows' => 3],
                ['key' => 'text', 'type' => 'i18n_lines', 'label' => 'Текст', 'rows' => 10, 'hint' => 'Каждый абзац с новой строки.'],
                ['key' => 'img', 'type' => 'image', 'label' => 'Фото салона', 'dir' => 'about', 'hint' => 'Горизонтальное, примерно 1200×960.'],
            ],
        ],
    ];
}

/** Латиница для кодов: «Оправа Милан» → «oprava-milan». */
function slugify(string $s): string
{
    $map = [
        'а' => 'a', 'б' => 'b', 'в' => 'v', 'г' => 'g', 'д' => 'd', 'е' => 'e', 'ё' => 'e', 'ж' => 'zh', 'з' => 'z', 'и' => 'i', 'й' => 'y', 'к' => 'k', 'л' => 'l', 'м' => 'm',
        'н' => 'n', 'о' => 'o', 'п' => 'p', 'р' => 'r', 'с' => 's', 'т' => 't', 'у' => 'u', 'ф' => 'f', 'х' => 'h', 'ц' => 'c', 'ч' => 'ch', 'ш' => 'sh', 'щ' => 'sch', 'ъ' => '',
        'ы' => 'y', 'ь' => '', 'э' => 'e', 'ю' => 'yu', 'я' => 'ya', 'ə' => 'e', 'ı' => 'i', 'ö' => 'o', 'ü' => 'u', 'ç' => 'c', 'ş' => 's', 'ğ' => 'g',
    ];
    $s = strtr(mb_strtolower($s), $map);
    $s = trim((string) preg_replace('~[^a-z0-9]+~', '-', $s), '-');
    return substr($s, 0, 60);
}

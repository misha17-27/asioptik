/* ======================================================================
   НАСТРОЙКИ МАГАЗИНА
   Всё, что нужно поменять под себя, находится в этом блоке:
   контакты, номер WhatsApp для заказов, доставка, товары и цены.
   Тексты на трёх языках записаны так: { az: '…', ru: '…', en: '…' }.
   ====================================================================== */

const CONFIG = {
  shopName: 'Asioptik',             // название в текстах и сообщениях; логотип в шапке — картинка
  siteUrl: 'https://asioptik.az/',     // адрес сайта в интернете: нужен поисковикам и для ссылок, которыми делятся


  // Номер WhatsApp, на который приходят заказы и заявки на ремонт.
  // Только цифры: код страны и номер, без «+», пробелов и скобок. Пример: 994501234567
  whatsapp: '994000000000',

  phone: '+994 00 000 00 00',          // телефон, который видят покупатели
  phonePrefix: '+994 ',                // подставляется в поле «Телефон» в формах
  address: { az: 'Bakı ş., Nümunə küç., 1', ru: 'г. Баку, ул. Примерная, 1', en: '1 Example St, Baku' },
  mapQuery: 'Baku',                    // адрес или название салона для карты Google
  hours: {
    az: ['Bazar ertəsi – Şənbə: 10:00–20:00', 'Bazar: 11:00–18:00'],
    ru: ['Пн–Сб: 10:00–20:00', 'Вс: 11:00–18:00'],
    en: ['Mon–Sat: 10:00–20:00', 'Sun: 11:00–18:00'],
  },
  instagram: 'your_instagram',         // имя аккаунта без @; оставьте '' чтобы скрыть

  currency: '₼',
  deliveryPrice: 5,                    // доставка курьером по городу
  freeDeliveryFrom: 150,               // бесплатная доставка от этой суммы; 0 — выключить

  languages: ['az', 'ru', 'en'],       // языки сайта; первый — основной
  messageLang: '',                     // язык сообщений в WhatsApp: '' — как на сайте у покупателя, или 'az' / 'ru' / 'en'
};

/* ---------- Разделы каталога ----------
   banner — баннер раздела в слайдах на первом экране:
     img  — фото для баннера. Положите файл с таким именем в папку images рядом с сайтом,
            и он появится сам. Пока файла нет, показывается рисунок из товаров.
     show — до трёх товаров для рисунка: [код товара, номер цвета]
     text — подпись под названием раздела */
const CATEGORIES = [
  { id: 'frames',   name: { az: 'Çərçivələr', ru: 'Оправы', en: 'Frames' },
    banner: { img: 'images/slide-frames.jpg', show: [['f-florence', 0], ['f-milan', 0], ['f-oslo', 0]],
      text: { az: 'Asetat, titan və metal. Linzaları reseptinizə uyğun taxırıq.', ru: 'Ацетат, титан и металл. Линзы поставим по вашему рецепту.', en: 'Acetate, titanium and metal. We fit lenses to your prescription.' } } },
  { id: 'sun',      name: { az: 'Günəş eynəkləri', ru: 'Солнцезащитные очки', en: 'Sunglasses' },
                    short: { az: 'Günəş eynəkləri', ru: 'Солнцезащитные', en: 'Sunglasses' },
    banner: { img: 'images/slide-sun.jpg', show: [['s-tropez', 1], ['s-riviera', 0], ['s-capri', 0]],
      text: { az: 'Polyarizasiya və UV400 qoruması, böyüklər və uşaqlar üçün.', ru: 'Поляризация и защита UV400, для взрослых и детей.', en: 'Polarized lenses and UV400 protection, for adults and kids.' } } },
  { id: 'contacts', name: { az: 'Kontakt linzaları', ru: 'Контактные линзы', en: 'Contact lenses' },
    banner: { img: 'images/slide-contacts.jpg', show: [['c-2week', 0], ['c-daily', 0], ['c-month', 0]],
      text: { az: 'Birgünlük, ikihəftəlik və aylıq. Hər göz üçün ayrıca seçilir.', ru: 'Однодневные, двухнедельные и месячные. Подбираются отдельно для каждого глаза.', en: 'Daily, two-weekly and monthly. Chosen separately for each eye.' } } },
  { id: 'lenses',   name: { az: 'Eynək linzaları', ru: 'Линзы для очков', en: 'Spectacle lenses' },
    banner: { img: 'images/slide-lenses.jpg', show: [['l-ar', 0], ['l-photo', 0], ['l-blue', 0]],
      text: { az: 'Antirefleks, mavi işıq filtri, fotoxrom və proqressiv.', ru: 'Антиблик, фильтр синего света, фотохромные и прогрессивные.', en: 'Anti-reflective, blue light filter, photochromic and progressive.' } } },
  { id: 'care',     name: { az: 'Qulluq və aksesuarlar', ru: 'Уход и аксессуары', en: 'Care & accessories' },
                    short: { az: 'Qulluq', ru: 'Уход', en: 'Care' },
    banner: { img: 'images/slide-care.jpg', show: [['a-solution', 0], ['a-case', 0], ['a-cloth', 0]],
      text: { az: 'Məhlul, damcılar, qablar və salfetlər.', ru: 'Раствор, капли, футляры и салфетки.', en: 'Solution, drops, cases and cloths.' } } },
];

/* ---------- Повторяющиеся названия: цвета и метки ---------- */
const C = {
  black:    { az: 'Qara', ru: 'Чёрный', en: 'Black' },
  tortoise: { az: 'Tısbağa naxışı', ru: 'Черепаховый', en: 'Tortoiseshell' },
  clear:    { az: 'Şəffaf', ru: 'Прозрачный', en: 'Clear' },
  navy:     { az: 'Tünd göy', ru: 'Тёмно-синий', en: 'Navy' },
  burgundy: { az: 'Bordo', ru: 'Бордовый', en: 'Burgundy' },
  powder:   { az: 'Pudra rəngi', ru: 'Пудровый', en: 'Powder pink' },
  gold:     { az: 'Qızılı', ru: 'Золото', en: 'Gold' },
  silver:   { az: 'Gümüşü', ru: 'Серебро', en: 'Silver' },
  graphite: { az: 'Qrafit', ru: 'Графит', en: 'Graphite' },
  smoke:    { az: 'Tüstü rəngi', ru: 'Дымчатый', en: 'Smoke' },
  honey:    { az: 'Bal rəngi', ru: 'Медовый', en: 'Honey' },
  blue:     { az: 'Göy', ru: 'Синий', en: 'Blue' },
  pink:     { az: 'Çəhrayı', ru: 'Розовый', en: 'Pink' },
  mint:     { az: 'Nanə rəngi', ru: 'Мятный', en: 'Mint' },
  milk:     { az: 'Süd rəngi', ru: 'Молочный', en: 'Milky white' },
  sky:      { az: 'Mavi', ru: 'Голубой', en: 'Light blue' },
  green:    { az: 'Yaşıl', ru: 'Зелёный', en: 'Green' },
  brown:    { az: 'Qəhvəyi', ru: 'Карий', en: 'Brown' },
  grey:     { az: 'Boz', ru: 'Серый', en: 'Grey' },
  beige:    { az: 'Bej', ru: 'Бежевый', en: 'Beige' },
};
const B = {
  hit:   { az: 'Populyar', ru: 'Хит', en: 'Bestseller' },
  new:   { az: 'Yeni', ru: 'Новинка', en: 'New' },
  kids:  { az: 'Uşaq üçün', ru: 'Детские', en: 'Kids' },
  polar: { az: 'Polyarizasiya', ru: 'Поляризация', en: 'Polarized' },
};

/* ---------- Параметры, которые покупатель выбирает перед покупкой ---------- */

// Оптическая сила (SPH): шаг 0.25 до ±6.00, дальше шаг 0.50
function sph(min = -12, max = 8, withZero = false) {
  const f = x => (x > 0 ? '+' : x < 0 ? '-' : '') + (Math.abs(x) / 100).toFixed(2);
  const step = x => (Math.abs(x) < 600 ? 25 : 50);
  const minus = [], plus = [];
  for (let x = -50; x >= min * 100; x -= step(x)) minus.push(f(x));
  for (let x = 50; x <= max * 100; x += step(x)) plus.push(f(x));
  const groups = [];
  if (withZero) groups.push({ label: { az: 'Dioptrisiz', ru: 'Без диоптрий', en: 'Plano (no power)' }, values: ['0.00'] });
  if (minus.length) groups.push({ label: { az: 'Mənfi (yaxındangörmə)', ru: 'Минус (близорукость)', en: 'Minus (short-sighted)' }, values: minus });
  if (plus.length) groups.push({ label: { az: 'Müsbət (uzaqdangörmə)', ru: 'Плюс (дальнозоркость)', en: 'Plus (long-sighted)' }, values: plus });
  return {
    k: 'sph', short: 'SPH', groups, eye: true,   // eye: true — значение выбирают отдельно для каждого глаза
    label: { az: 'Optik güc (SPH)', ru: 'Оптическая сила (SPH)', en: 'Power (SPH)' },
  };
}
// Радиус кривизны (BC). Если значение одно, оно подставится само
function bc(...values) { return { k: 'bc', short: 'BC', label: { az: 'Əyrilik radiusu (BC)', ru: 'Радиус кривизны (BC)', en: 'Base curve (BC)' }, values }; }
// Цилиндр и ось — для торических линз (при астигматизме)
function cyl() { return { k: 'cyl', short: 'CYL', eye: true, label: { az: 'Silindr (CYL)', ru: 'Цилиндр (CYL)', en: 'Cylinder (CYL)' }, values: ['-0.75', '-1.25', '-1.75', '-2.25', '-2.75'] }; }
function ax() {
  const values = [];
  for (let a = 10; a <= 180; a += 10) values.push(String(a));
  return { k: 'ax', short: 'AX', eye: true, label: { az: 'Ox (AX)', ru: 'Ось (AX)', en: 'Axis (AX)' }, values };
}
// Толщина линз для очков. d — доплата к цене товара
const IDX = {
  std:   { az: '1.56 (standart)', ru: '1.56 (стандартные)', en: '1.56 (standard)' },
  thin:  { az: '1.60 (nazik)', ru: '1.60 (тонкие)', en: '1.60 (thin)' },
  ultra: { az: '1.67 (ultranazik)', ru: '1.67 (ультратонкие)', en: '1.67 (ultra-thin)' },
  max:   { az: '1.74 (ən nazik)', ru: '1.74 (самые тонкие)', en: '1.74 (thinnest)' },
};
function lensIndex(prices) {
  const keys = ['std', 'thin', 'ultra', 'max'];
  return {
    k: 'index', preselect: true,
    short: { az: 'İndeks', ru: 'Индекс', en: 'Index' },
    label: { az: 'İndeks (nə qədər yüksəkdirsə, linza o qədər nazik olur)', ru: 'Индекс (чем выше, тем тоньше линза)', en: 'Index (higher means thinner lenses)' },
    values: prices.map((d, i) => ({ v: IDX[keys[i]].en.slice(0, 4), label: IDX[keys[i]], d })),
  };
}

/* ---------- Показатели зрения на странице товара (линзы для очков) ----------
   Из этих значений покупатель выбирает показатели для каждого глаза. */
const RX = {
  sph: sph(-12, 8, true),                                                     // сила линзы (SPH)
  cyl: Array.from({ length: 16 }, (_, i) => (-(i + 1) * 0.25).toFixed(2)),    // цилиндр (CYL): от -0.25 до -4.00
  add: Array.from({ length: 12 }, (_, i) => '+' + (0.75 + i * 0.25).toFixed(2)), // аддидация (ADD) для прогрессивных линз
  pd: [50, 76],                                                               // расстояние между зрачками (PD), мм: от и до
};

/* ---------- Для кого: секции на главной и фильтр в каталоге ----------
   Две секции: «Для взрослых» (внутри мужчины и женщины) и «Для детей».
   name  — короткое название в меню и в фильтре каталога
   title, text — заголовок и подпись секции (у мужчин и женщин — заголовок и подпись их блока)
   panel — заголовок блока, если внутри секции нет частей (у детей)
   all   — надпись на кнопке «все модели»
   img   — фото для баннера секции или блока. Положите файл с таким именем в папку images рядом с сайтом,
           и он появится сам. Пока файла нет, показывается временное фото (demo) или рисунок.
   demo  — временное фото с бесплатного фотостока Pexels, грузится по ссылке из интернета.
           Его заменит ваш файл из папки images; чтобы убрать совсем, удалите строку demo.
   pos   — какая часть кадра остаётся видна при обрезке: по горизонтали и по вертикали (0% — левый/верхний край)
   show  — до трёх товаров для рисунка на баннере секции: [код товара, номер цвета]
   art   — товар (и номер его цвета), который нарисован в блоке крупно
   pick  — какие товары показать в блоке; если убрать, покажутся первые четыре
   У товара раздел задаётся так: for: ['men', 'women'] или for: ['kids'] */
const AUDIENCES = [
  { id: 'adults',
    name: { az: 'Böyüklər', ru: 'Взрослым', en: 'Adults' },
    title: { az: 'Böyüklər üçün', ru: 'Для взрослых', en: 'For adults' },
    text: { az: 'Kişilər və qadınlar üçün çərçivələr və günəş eynəkləri.', ru: 'Оправы и солнцезащитные очки для мужчин и женщин.', en: 'Frames and sunglasses for men and women.' },
    all: { az: 'Böyüklər üçün bütün modellər', ru: 'Все модели для взрослых', en: 'All adult styles' },
    img: 'images/banner-adults.jpg', show: [['f-florence', 2], ['f-berlin', 0], ['s-riviera', 0]],
    // временное фото: полки с оправами, автор Ksenia Chernaya (Pexels)
    demo: 'https://images.pexels.com/photos/5766609/pexels-photo-5766609.jpeg?auto=compress&cs=tinysrgb&w=1920', pos: '50% 45%',
    parts: [
      { id: 'men',
        name: { az: 'Kişilər', ru: 'Мужчинам', en: 'Men' },
        title: { az: 'Kişilər üçün', ru: 'Для мужчин', en: 'For men' },
        text: { az: 'Düzbucaqlı və browline çərçivələr, günəşdən qoruyan aviatorlar.', ru: 'Прямоугольные оправы и браулайнеры, авиаторы от солнца.', en: 'Rectangular and browline frames, aviators for the sun.' },
        all: { az: 'Kişi modellərinin hamısı', ru: 'Все мужские модели', en: 'All men’s styles' },
        // временное фото: автор cottonbro studio (Pexels)
        demo: 'https://images.pexels.com/photos/5990258/pexels-photo-5990258.jpeg?auto=compress&cs=tinysrgb&w=900', pos: '50% 30%',
        img: 'images/banner-men.jpg', art: { id: 'f-berlin', color: 0 }, pick: ['f-verona', 'f-berlin', 's-riviera', 'f-london'] },
      { id: 'women',
        name: { az: 'Qadınlar', ru: 'Женщинам', en: 'Women' },
        title: { az: 'Qadınlar üçün', ru: 'Для женщин', en: 'For women' },
        text: { az: '«Pişik gözü», nazik metal və iri oval formalar.', ru: '«Кошачий глаз», тонкий металл и крупные овалы.', en: 'Cat-eye, fine metal and oversized ovals.' },
        all: { az: 'Qadın modellərinin hamısı', ru: 'Все женские модели', en: 'All women’s styles' },
        // временное фото: автор Andrea Piacquadio (Pexels)
        demo: 'https://images.pexels.com/photos/5046193/pexels-photo-5046193.jpeg?auto=compress&cs=tinysrgb&w=1400', pos: '10% 30%',
        img: 'images/banner-women.jpg', art: { id: 'f-florence', color: 2 }, pick: ['f-florence', 'f-tokyo', 's-capri', 's-tropez'] },
    ] },
  { id: 'kids',
    name: { az: 'Uşaqlar', ru: 'Детям', en: 'Kids' },
    title: { az: 'Uşaqlar üçün', ru: 'Для детей', en: 'For kids' },
    text: { az: 'Elastik və yüngül çərçivələr, UV400 günəş eynəkləri.', ru: 'Гибкие лёгкие оправы и солнцезащитные очки UV400.', en: 'Flexible, lightweight frames and UV400 sunglasses.' },
    panel: { az: '3 yaşdan 14 yaşadək', ru: 'От 3 до 14 лет', en: 'Ages 3 to 14' },
    all: { az: 'Uşaq modellərinin hamısı', ru: 'Все детские модели', en: 'All kids’ styles' },
    img: 'images/banner-kids.jpg', demo: 'https://images.pexels.com/photos/6193647/pexels-photo-6193647.jpeg?auto=compress&cs=tinysrgb&w=1920', pos: '50% 12%', flip: true, show: [['f-bubble', 0], ['f-kids', 0], ['s-kids', 0]],
    art: { id: 'f-kids', color: 0 }, pick: ['f-kids', 'f-bubble', 'f-junior', 's-kids'] },
];

/* ---------- Товары ----------
   id      — уникальный код товара (латиницей)
   cat     — раздел из списка CATEGORIES
   price   — цена; old — старая цена (если есть скидка)
   badge   — короткая метка на карточке
   colors  — варианты цвета: n — название, c — цвет (#hex или 'tortoise' — черепаховый)
   opts    — параметры, которые нужно выбрать (сила, радиус, индекс…)
   info    — характеристики на странице товара, отдельно для каждого языка
   img     — путь к фото товара, например 'images/milan.jpg' (если пусто — рисуется иллюстрация)
   for     — для кого: 'men', 'women' (взрослые) или 'kids' (секции на главной и фильтр в каталоге)
   withLenses: true — к оправе на её странице можно сразу заказать линзы по рецепту
   rx: true — линзы для очков: на странице товара выбирают показатели зрения или прикладывают фото рецепта
   add: true — для этих линз нужна ещё аддидация (ADD), как у прогрессивных
   У каждого товара свой адрес: имя-файла.html?product=id
*/
const PRODUCTS = [
  // ----- Оправы -----
  { id: 'f-milan', cat: 'frames', brand: 'asi-classic', price: 140, old: 170, badge: B.hit, art: 'glasses', shape: 'round', withLenses: true, for: ['men', 'women'],
    name: { az: '«Milan» çərçivəsi', ru: 'Оправа «Милан»', en: 'Milan frame' },
    sub: { az: 'Asetat, dəyirmi forma', ru: 'Ацетат, круглая форма', en: 'Acetate, round' },
    colors: [{ n: C.tortoise, c: 'tortoise' }, { n: C.black, c: '#1f1f22' }, { n: C.clear, c: '#bdb2a1', a: 0.6 }],
    info: {
      az: [['Material', 'Asetat'], ['Ölçü, mm', '48□21 145'], ['Çəki', '24 q']],
      ru: [['Материал', 'Ацетат'], ['Размер, мм', '48□21 145'], ['Вес', '24 г']],
      en: [['Material', 'Acetate'], ['Size, mm', '48□21 145'], ['Weight', '24 g']],
    } },
  { id: 'f-verona', cat: 'frames', brand: 'asi-classic', price: 120, art: 'glasses', shape: 'rect', withLenses: true, for: ['men'],
    name: { az: '«Verona» çərçivəsi', ru: 'Оправа «Верона»', en: 'Verona frame' },
    sub: { az: 'Asetat, düzbucaqlı', ru: 'Ацетат, прямоугольная', en: 'Acetate, rectangular' },
    colors: [{ n: C.black, c: '#1f1f22' }, { n: C.navy, c: '#23305a' }, { n: C.burgundy, c: '#5c1f2b' }],
    info: {
      az: [['Material', 'Asetat'], ['Ölçü, mm', '52□18 145']],
      ru: [['Материал', 'Ацетат'], ['Размер, мм', '52□18 145']],
      en: [['Material', 'Acetate'], ['Size, mm', '52□18 145']],
    } },
  { id: 'f-florence', cat: 'frames', brand: 'asi-classic', price: 155, badge: B.new, art: 'glasses', shape: 'cateye', withLenses: true, for: ['women'],
    name: { az: '«Florensiya» çərçivəsi', ru: 'Оправа «Флоренция»', en: 'Florence frame' },
    sub: { az: 'Asetat, «pişik gözü»', ru: 'Ацетат, «кошачий глаз»', en: 'Acetate, cat-eye' },
    colors: [{ n: C.black, c: '#1f1f22' }, { n: C.powder, c: '#d39d94' }, { n: C.tortoise, c: 'tortoise' }],
    info: {
      az: [['Material', 'Asetat'], ['Ölçü, mm', '51□18 140']],
      ru: [['Материал', 'Ацетат'], ['Размер, мм', '51□18 140']],
      en: [['Material', 'Acetate'], ['Size, mm', '51□18 140']],
    } },
  { id: 'f-oslo', cat: 'frames', brand: 'asi-metal', price: 95, art: 'glasses', shape: 'round', metal: true, withLenses: true, for: ['men', 'women'],
    name: { az: '«Oslo» çərçivəsi', ru: 'Оправа «Осло»', en: 'Oslo frame' },
    sub: { az: 'Titan, nazik dəyirmi', ru: 'Титан, тонкая круглая', en: 'Titanium, slim round' },
    colors: [{ n: C.gold, c: '#b8955a' }, { n: C.silver, c: '#9fa4ab' }, { n: C.graphite, c: '#4a4e55' }],
    info: {
      az: [['Material', 'Titan'], ['Ölçü, mm', '47□20 140'], ['Çəki', '12 q']],
      ru: [['Материал', 'Титан'], ['Размер, мм', '47□20 140'], ['Вес', '12 г']],
      en: [['Material', 'Titanium'], ['Size, mm', '47□20 140'], ['Weight', '12 g']],
    } },
  { id: 'f-tokyo', cat: 'frames', brand: 'asi-metal', price: 110, art: 'glasses', shape: 'hex', metal: true, withLenses: true, for: ['women'],
    name: { az: '«Tokio» çərçivəsi', ru: 'Оправа «Токио»', en: 'Tokyo frame' },
    sub: { az: 'Metal, altıbucaqlı', ru: 'Металл, шестигранная', en: 'Metal, hexagonal' },
    colors: [{ n: C.gold, c: '#b8955a' }, { n: C.silver, c: '#9fa4ab' }],
    info: {
      az: [['Material', 'Paslanmayan polad'], ['Ölçü, mm', '50□20 145']],
      ru: [['Материал', 'Нержавеющая сталь'], ['Размер, мм', '50□20 145']],
      en: [['Material', 'Stainless steel'], ['Size, mm', '50□20 145']],
    } },
  { id: 'f-berlin', cat: 'frames', brand: 'asi-metal', price: 130, art: 'glasses', shape: 'browline', withLenses: true, for: ['men'],
    name: { az: '«Berlin» çərçivəsi', ru: 'Оправа «Берлин»', en: 'Berlin frame' },
    sub: { az: 'Asetat və metal, browline', ru: 'Ацетат и металл, браулайн', en: 'Acetate and metal, browline' },
    colors: [
      { n: { az: 'Qara, qızılı ilə', ru: 'Чёрный с золотом', en: 'Black with gold' }, c: '#1f1f22', c2: '#b8955a' },
      { n: { az: 'Tısbağa naxışı, gümüşü ilə', ru: 'Черепаховый с серебром', en: 'Tortoiseshell with silver' }, c: 'tortoise', c2: '#9fa4ab' },
    ],
    info: {
      az: [['Material', 'Asetat və metal'], ['Ölçü, mm', '51□20 145']],
      ru: [['Материал', 'Ацетат и металл'], ['Размер, мм', '51□20 145']],
      en: [['Material', 'Acetate and metal'], ['Size, mm', '51□20 145']],
    } },
  { id: 'f-london', cat: 'frames', brand: 'asi-classic', price: 125, art: 'glasses', shape: 'square', withLenses: true, for: ['men', 'women'],
    name: { az: '«London» çərçivəsi', ru: 'Оправа «Лондон»', en: 'London frame' },
    sub: { az: 'Asetat, iri kvadrat', ru: 'Ацетат, крупная квадратная', en: 'Acetate, oversized square' },
    colors: [{ n: C.black, c: '#1f1f22' }, { n: C.smoke, c: '#7d8087', a: 0.7 }, { n: C.honey, c: '#cf8f35', a: 0.85 }],
    info: {
      az: [['Material', 'Asetat'], ['Ölçü, mm', '53□19 145']],
      ru: [['Материал', 'Ацетат'], ['Размер, мм', '53□19 145']],
      en: [['Material', 'Acetate'], ['Size, mm', '53□19 145']],
    } },
  { id: 'f-kids', cat: 'frames', brand: 'asi-kids', price: 65, badge: B.kids, art: 'glasses', shape: 'oval', sw: 5.5, withLenses: true, for: ['kids'],
    name: { az: '«Mini» uşaq çərçivəsi', ru: 'Детская оправа «Мини»', en: 'Mini kids’ frame' },
    sub: { az: 'Elastik, 4–8 yaşlı uşaqlar üçün', ru: 'Гибкая, для детей 4–8 лет', en: 'Flexible, for ages 4–8' },
    colors: [{ n: C.blue, c: '#2f67c9' }, { n: C.pink, c: '#e06a98' }, { n: C.mint, c: '#4fb393' }],
    info: {
      az: [['Material', 'Elastik plastik TR-90'], ['Ölçü, mm', '44□16 125'], ['Yaş', '4–8 yaş']],
      ru: [['Материал', 'Гибкий пластик TR-90'], ['Размер, мм', '44□16 125'], ['Возраст', '4–8 лет']],
      en: [['Material', 'Flexible TR-90 plastic'], ['Size, mm', '44□16 125'], ['Age', '4–8 years']],
    } },

  { id: 'f-bubble', cat: 'frames', brand: 'asi-kids', price: 58, badge: B.kids, art: 'glasses', shape: 'round', sw: 6, withLenses: true, for: ['kids'],
    name: { az: '«Bubble» uşaq çərçivəsi', ru: 'Детская оправа «Бабл»', en: 'Bubble kids’ frame' },
    sub: { az: 'Silikon, 3–6 yaş, kəmərlə', ru: 'Силикон, 3–6 лет, с ремешком', en: 'Silicone, ages 3–6, with strap' },
    colors: [{ n: C.mint, c: '#4fb393' }, { n: C.sky, c: '#4a9ad8' }, { n: C.honey, c: '#e0a13c' }],
    info: {
      az: [['Material', 'Silikon'], ['Ölçü, mm', '40□15 115'], ['Dəstdə', 'Tənzimlənən kəmər']],
      ru: [['Материал', 'Силикон'], ['Размер, мм', '40□15 115'], ['В комплекте', 'Регулируемый ремешок']],
      en: [['Material', 'Silicone'], ['Size, mm', '40□15 115'], ['Included', 'Adjustable strap']],
    } },
  { id: 'f-junior', cat: 'frames', brand: 'asi-kids', price: 78, badge: B.kids, art: 'glasses', shape: 'rect', sw: 5.5, withLenses: true, for: ['kids'],
    name: { az: '«Junior» yeniyetmə çərçivəsi', ru: 'Подростковая оправа «Джуниор»', en: 'Junior teen frame' },
    sub: { az: 'Asetat, 9–14 yaş üçün', ru: 'Ацетат, для 9–14 лет', en: 'Acetate, for ages 9–14' },
    colors: [{ n: C.navy, c: '#23305a' }, { n: C.black, c: '#1f1f22' }, { n: C.burgundy, c: '#5c1f2b' }],
    info: {
      az: [['Material', 'Asetat'], ['Ölçü, mm', '46□17 130'], ['Çəki', '18 q']],
      ru: [['Материал', 'Ацетат'], ['Размер, мм', '46□17 130'], ['Вес', '18 г']],
      en: [['Material', 'Acetate'], ['Size, mm', '46□17 130'], ['Weight', '18 g']],
    } },

  // ----- Солнцезащитные очки -----
  { id: 's-riviera', cat: 'sun', brand: 'asi-sun', price: 145, badge: B.polar, art: 'glasses', shape: 'aviator', metal: true, sun: true, for: ['men', 'women'],
    name: { az: '«Riviera» eynəyi', ru: 'Очки «Ривьера»', en: 'Riviera sunglasses' },
    sub: { az: 'Aviator, polyarizasiyalı', ru: 'Авиаторы, поляризация', en: 'Aviators, polarized' },
    colors: [
      { n: { az: 'Qızılı, yaşıl linzalar', ru: 'Золото, зелёные линзы', en: 'Gold, green lenses' }, c: '#b8955a', l: '#33503c' },
      { n: { az: 'Gümüşü, boz linzalar', ru: 'Серебро, серые линзы', en: 'Silver, grey lenses' }, c: '#9fa4ab', l: '#3a3e46' },
    ],
    info: {
      az: [['Linzalar', 'Polyarizasiyalı, UV400'], ['Çərçivə', 'Metal'], ['Ölçü, mm', '58□14 140']],
      ru: [['Линзы', 'Поляризационные, UV400'], ['Оправа', 'Металл'], ['Размер, мм', '58□14 140']],
      en: [['Lenses', 'Polarized, UV400'], ['Frame', 'Metal'], ['Size, mm', '58□14 140']],
    } },
  { id: 's-tropez', cat: 'sun', brand: 'asi-sun', price: 120, art: 'glasses', shape: 'cateye', sun: true, for: ['women'],
    name: { az: '«Sen-Trope» eynəyi', ru: 'Очки «Сен-Тропе»', en: 'Saint-Tropez sunglasses' },
    sub: { az: '«Pişik gözü», UV400', ru: '«Кошачий глаз», UV400', en: 'Cat-eye, UV400' },
    colors: [{ n: C.black, c: '#1f1f22', l: '#2b2b30' }, { n: C.tortoise, c: 'tortoise', l: '#5a3a22' }],
    info: {
      az: [['Linzalar', 'UV400'], ['Çərçivə', 'Asetat'], ['Ölçü, mm', '53□19 145']],
      ru: [['Линзы', 'UV400'], ['Оправа', 'Ацетат'], ['Размер, мм', '53□19 145']],
      en: [['Lenses', 'UV400'], ['Frame', 'Acetate'], ['Size, mm', '53□19 145']],
    } },
  { id: 's-miami', cat: 'sun', brand: 'asi-sun', price: 135, art: 'glasses', shape: 'trapeze', sun: true, for: ['men'],
    name: { az: '«Mayami» eynəyi', ru: 'Очки «Майами»', en: 'Miami sunglasses' },
    sub: { az: 'Klassik forma, polyarizasiyalı', ru: 'Классическая форма, поляризация', en: 'Classic shape, polarized' },
    colors: [{ n: C.black, c: '#1f1f22', l: '#26282d' }, { n: C.tortoise, c: 'tortoise', l: '#4b3424' }, { n: C.blue, c: '#24407a', l: '#2a3550' }],
    info: {
      az: [['Linzalar', 'Polyarizasiyalı, UV400'], ['Çərçivə', 'Asetat'], ['Ölçü, mm', '52□18 145']],
      ru: [['Линзы', 'Поляризационные, UV400'], ['Оправа', 'Ацетат'], ['Размер, мм', '52□18 145']],
      en: [['Lenses', 'Polarized, UV400'], ['Frame', 'Acetate'], ['Size, mm', '52□18 145']],
    } },
  { id: 's-capri', cat: 'sun', brand: 'asi-sun', price: 99, old: 120, art: 'glasses', shape: 'round', metal: true, sun: true, grad: true, for: ['women'],
    name: { az: '«Kapri» eynəyi', ru: 'Очки «Капри»', en: 'Capri sunglasses' },
    sub: { az: 'Dəyirmi, qradiyentli linzalar', ru: 'Круглые, градиентные линзы', en: 'Round, gradient lenses' },
    colors: [
      { n: { az: 'Qızılı, qəhvəyi linzalar', ru: 'Золото, коричневые линзы', en: 'Gold, brown lenses' }, c: '#b8955a', l: '#6b4a2e' },
      { n: { az: 'Gümüşü, boz linzalar', ru: 'Серебро, серые линзы', en: 'Silver, grey lenses' }, c: '#9fa4ab', l: '#4a4e57' },
    ],
    info: {
      az: [['Linzalar', 'Qradiyentli, UV400'], ['Çərçivə', 'Metal'], ['Ölçü, mm', '50□21 145']],
      ru: [['Линзы', 'Градиентные, UV400'], ['Оправа', 'Металл'], ['Размер, мм', '50□21 145']],
      en: [['Lenses', 'Gradient, UV400'], ['Frame', 'Metal'], ['Size, mm', '50□21 145']],
    } },
  { id: 's-dubai', cat: 'sun', brand: 'asi-sun', price: 110, art: 'glasses', shape: 'oval', sun: true, for: ['women'],
    name: { az: '«Dubay» eynəyi', ru: 'Очки «Дубай»', en: 'Dubai sunglasses' },
    sub: { az: 'İri oval, UV400', ru: 'Крупные овальные, UV400', en: 'Oversized oval, UV400' },
    colors: [{ n: C.milk, c: '#e6ddcf', l: '#5a4c40' }, { n: C.black, c: '#1f1f22', l: '#2b2b30' }],
    info: {
      az: [['Linzalar', 'UV400'], ['Çərçivə', 'Asetat'], ['Ölçü, mm', '56□17 140']],
      ru: [['Линзы', 'UV400'], ['Оправа', 'Ацетат'], ['Размер, мм', '56□17 140']],
      en: [['Lenses', 'UV400'], ['Frame', 'Acetate'], ['Size, mm', '56□17 140']],
    } },
  { id: 's-kids', cat: 'sun', brand: 'asi-kids', price: 45, badge: B.kids, art: 'glasses', shape: 'oval', sw: 5.5, sun: true, for: ['kids'],
    name: { az: 'Uşaq günəş eynəyi', ru: 'Детские солнцезащитные', en: 'Kids’ sunglasses' },
    sub: { az: 'Elastik çərçivə, UV400', ru: 'Гибкая оправа, UV400', en: 'Flexible frame, UV400' },
    colors: [{ n: C.sky, c: '#4a9ad8', l: '#2d3a4a' }, { n: C.pink, c: '#e77aa4', l: '#43303a' }],
    info: {
      az: [['Linzalar', 'UV400, zərbəyədavamlı'], ['Yaş', '3–7 yaş']],
      ru: [['Линзы', 'UV400, ударопрочные'], ['Возраст', '3–7 лет']],
      en: [['Lenses', 'UV400, impact-resistant'], ['Age', '3–7 years']],
    } },

  // ----- Контактные линзы (цена за упаковку) -----
  { id: 'c-daily', cat: 'contacts', price: 38, art: 'cbox', tone: '#2a9fc4', pack: '30', opts: [sph(), bc('8.5', '9.0')],
    name: { az: 'Birgünlük linzalar', ru: 'Однодневные линзы', en: 'Daily lenses' },
    sub: { az: 'Qutuda 30 linza', ru: '30 линз в упаковке', en: '30 lenses per box' },
    info: {
      az: [['Dəyişmə', 'Hər gün'], ['Qutuda', '30 linza'], ['Material', 'Hidrogel'], ['Nəmlik', '58%']],
      ru: [['Замена', 'Каждый день'], ['В упаковке', '30 линз'], ['Материал', 'Гидрогель'], ['Влагосодержание', '58%']],
      en: [['Replace', 'Every day'], ['Per box', '30 lenses'], ['Material', 'Hydrogel'], ['Water content', '58%']],
    } },
  { id: 'c-daily-si', cat: 'contacts', price: 55, badge: B.hit, art: 'cbox', tone: '#3567c9', pack: '30', opts: [sph(), bc('8.5')],
    name: { az: 'Birgünlük silikon-hidrogel linzalar', ru: 'Однодневные силикон-гидрогелевые', en: 'Daily silicone hydrogel lenses' },
    sub: { az: '30 linza, uzunmüddətli taxmaq üçün', ru: '30 линз, для долгого ношения', en: '30 lenses, for all-day wear' },
    info: {
      az: [['Dəyişmə', 'Hər gün'], ['Qutuda', '30 linza'], ['Material', 'Silikon-hidrogel'], ['Nəmlik', '46%']],
      ru: [['Замена', 'Каждый день'], ['В упаковке', '30 линз'], ['Материал', 'Силикон-гидрогель'], ['Влагосодержание', '46%']],
      en: [['Replace', 'Every day'], ['Per box', '30 lenses'], ['Material', 'Silicone hydrogel'], ['Water content', '46%']],
    } },
  { id: 'c-2week', cat: 'contacts', price: 28, art: 'cbox', tone: '#23a174', pack: '6', opts: [sph(), bc('8.3', '8.7')],
    name: { az: 'İkihəftəlik linzalar', ru: 'Двухнедельные линзы', en: 'Two-week lenses' },
    sub: { az: 'Qutuda 6 linza', ru: '6 линз в упаковке', en: '6 lenses per box' },
    info: {
      az: [['Dəyişmə', '2 həftədən bir'], ['Qutuda', '6 linza'], ['Material', 'Hidrogel']],
      ru: [['Замена', 'Раз в 2 недели'], ['В упаковке', '6 линз'], ['Материал', 'Гидрогель']],
      en: [['Replace', 'Every 2 weeks'], ['Per box', '6 lenses'], ['Material', 'Hydrogel']],
    } },
  { id: 'c-month', cat: 'contacts', price: 45, art: 'cbox', tone: '#7656cc', pack: '6', opts: [sph(), bc('8.6')],
    name: { az: 'Aylıq silikon-hidrogel linzalar', ru: 'Месячные силикон-гидрогелевые', en: 'Monthly silicone hydrogel lenses' },
    sub: { az: 'Qutuda 6 linza', ru: '6 линз в упаковке', en: '6 lenses per box' },
    info: {
      az: [['Dəyişmə', 'Ayda bir'], ['Qutuda', '6 linza'], ['Material', 'Silikon-hidrogel']],
      ru: [['Замена', 'Раз в месяц'], ['В упаковке', '6 линз'], ['Материал', 'Силикон-гидрогель']],
      en: [['Replace', 'Monthly'], ['Per box', '6 lenses'], ['Material', 'Silicone hydrogel']],
    } },
  { id: 'c-toric', cat: 'contacts', price: 65, art: 'cbox', tone: '#c9702a', pack: '6', opts: [sph(-10, 6), cyl(), ax(), bc('8.6')],
    name: { az: 'Astiqmatizm üçün torik linzalar', ru: 'Торические линзы при астигматизме', en: 'Toric lenses for astigmatism' },
    sub: { az: 'Aylıq, 6 linza', ru: 'Месячные, 6 линз', en: 'Monthly, 6 lenses' },
    info: {
      az: [['Dəyişmə', 'Ayda bir'], ['Qutuda', '6 linza'], ['Kimlər üçün', 'Astiqmatizm zamanı']],
      ru: [['Замена', 'Раз в месяц'], ['В упаковке', '6 линз'], ['Для кого', 'При астигматизме']],
      en: [['Replace', 'Monthly'], ['Per box', '6 lenses'], ['For', 'Astigmatism']],
    } },
  { id: 'c-color', cat: 'contacts', price: 32, badge: B.new, art: 'iris', opts: [sph(-8, 0, true), bc('8.6')],
    name: { az: 'Rəngli linzalar', ru: 'Цветные линзы', en: 'Coloured lenses' },
    sub: { az: '3 aydan bir dəyişdirilir, 2 linza', ru: 'Замена раз в 3 месяца, 2 линзы', en: 'Replace every 3 months, 2 lenses' },
    colors: [{ n: { az: 'Mavi', ru: 'Голубой', en: 'Blue' }, c: '#5f9fd6' }, { n: C.green, c: '#5ea56c' }, { n: C.brown, c: '#8f5f34' }, { n: C.grey, c: '#97a0aa' }],
    info: {
      az: [['Dəyişmə', '3 aydan bir'], ['Qutuda', '2 linza']],
      ru: [['Замена', 'Раз в 3 месяца'], ['В упаковке', '2 линзы']],
      en: [['Replace', 'Every 3 months'], ['Per box', '2 lenses']],
    } },

  // ----- Линзы для очков (цена за пару) -----
  { id: 'l-ar', cat: 'lenses', price: 40, art: 'slens', kind: 'ar', opts: [lensIndex([0, 25, 60, 120])], rx: true,
    name: { az: 'Antirefleks örtüklü linzalar', ru: 'Линзы с антибликовым покрытием', en: 'Anti-reflective lenses' },
    sub: { az: 'Qiymət bir cüt üçündür', ru: 'Цена за пару', en: 'Price per pair' },
    info: {
      az: [['Örtük', 'Antirefleks və möhkəmləndirici'], ['Hazırlanma müddəti', '1–3 gün']],
      ru: [['Покрытие', 'Антибликовое и упрочняющее'], ['Изготовление', '1–3 дня']],
      en: [['Coating', 'Anti-reflective and hard coat'], ['Made in', '1–3 days']],
    } },
  { id: 'l-blue', cat: 'lenses', price: 60, badge: B.hit, art: 'slens', kind: 'blue', opts: [lensIndex([0, 25, 60, 120])], rx: true,
    name: { az: 'Mavi işıq filtrli linzalar', ru: 'Линзы с фильтром синего света', en: 'Blue light filter lenses' },
    sub: { az: 'Ekranla iş üçün, qiymət bir cüt üçündür', ru: 'Для работы за экраном, цена за пару', en: 'For screen work, price per pair' },
    info: {
      az: [['Örtük', 'Mavi işıq filtri və antirefleks'], ['Hazırlanma müddəti', '1–3 gün']],
      ru: [['Покрытие', 'Фильтр синего света и антибликовое'], ['Изготовление', '1–3 дня']],
      en: [['Coating', 'Blue light filter and anti-reflective'], ['Made in', '1–3 days']],
    } },
  { id: 'l-photo', cat: 'lenses', price: 110, art: 'slens', kind: 'photo', opts: [lensIndex([0, 25, 60, 120])], rx: true,
    name: { az: 'Fotoxrom linzalar «buqələmun»', ru: 'Фотохромные линзы «хамелеон»', en: 'Photochromic lenses' },
    sub: { az: 'Günəşdə tündləşir, qiymət bir cüt üçündür', ru: 'Темнеют на солнце, цена за пару', en: 'Darken in sunlight, price per pair' },
    colorLabel: { az: 'Tündləşmə rəngi', ru: 'Цвет затемнения', en: 'Tint colour' },
    colors: [{ n: C.grey, c: '#4a4f57' }, { n: { az: 'Qəhvəyi', ru: 'Коричневый', en: 'Brown' }, c: '#6a4a32' }],
    info: {
      az: [['Necə işləyir', 'Günəşdə tündləşir, qapalı məkanda açılır'], ['Hazırlanma müddəti', '3–5 gün']],
      ru: [['Как работают', 'Темнеют на солнце, светлеют в помещении'], ['Изготовление', '3–5 дней']],
      en: [['How they work', 'Darken outdoors, clear indoors'], ['Made in', '3–5 days']],
    } },
  { id: 'l-prog', cat: 'lenses', price: 220, art: 'slens', kind: 'prog', opts: [lensIndex([0, 40, 90])], rx: true, add: true,
    name: { az: 'Proqressiv linzalar', ru: 'Прогрессивные линзы', en: 'Progressive lenses' },
    sub: { az: 'Uzaq və yaxın üçün bir linzada, qiymət bir cüt üçündür', ru: 'Для дали и близи в одной линзе, цена за пару', en: 'Distance and near in one lens, price per pair' },
    info: {
      az: [['Uyğundur', 'Uzaq məsafə, kompüter və oxumaq üçün'], ['Hazırlanma müddəti', '5–7 gün']],
      ru: [['Подходят', 'Для дали, компьютера и чтения'], ['Изготовление', '5–7 дней']],
      en: [['Good for', 'Distance, computer and reading'], ['Made in', '5–7 days']],
    } },

  // ----- Уход и аксессуары -----
  { id: 'a-solution', cat: 'care', price: 12, art: 'bottle', tone: '#2a9fc4',
    name: { az: 'Kontakt linzaları üçün məhlul', ru: 'Раствор для контактных линз', en: 'Contact lens solution' },
    sub: { az: '360 ml, konteyner daxildir', ru: '360 мл, контейнер в комплекте', en: '360 ml, lens case included' },
    info: {
      az: [['Həcm', '360 ml'], ['Dəstdə', 'Linza konteyneri']],
      ru: [['Объём', '360 мл'], ['В комплекте', 'Контейнер для линз']],
      en: [['Volume', '360 ml'], ['Included', 'Lens case']],
    } },
  { id: 'a-drops', cat: 'care', price: 9, art: 'drops', tone: '#23a174',
    name: { az: 'Nəmləndirici damcılar', ru: 'Увлажняющие капли', en: 'Moisturising eye drops' },
    sub: { az: '10 ml, linza ilə istifadə etmək olar', ru: '10 мл, можно капать с линзами', en: '10 ml, safe with lenses' },
    info: { az: [['Həcm', '10 ml']], ru: [['Объём', '10 мл']], en: [['Volume', '10 ml']] } },
  { id: 'a-case', cat: 'care', price: 12, art: 'case',
    name: { az: 'Eynək qabı', ru: 'Футляр для очков', en: 'Glasses case' },
    sub: { az: 'Bərk, maqnitli', ru: 'Жёсткий, на магните', en: 'Hard shell, magnetic' },
    colors: [{ n: C.graphite, c: '#3d4048' }, { n: C.beige, c: '#c9b293' }, { n: C.blue, c: '#2c4a86' }],
    info: {
      az: [['Növ', 'Bərk, maqnit qapaqlı']],
      ru: [['Тип', 'Жёсткий, на магнитной застёжке']],
      en: [['Type', 'Hard shell, magnetic clasp']],
    } },
  { id: 'a-lenscase', cat: 'care', price: 3, art: 'lenscase', tone: '#3a86d4',
    name: { az: 'Linza konteyneri', ru: 'Контейнер для линз', en: 'Lens case' },
    sub: { az: 'L və R işarəli', ru: 'С маркировкой L и R', en: 'Marked L and R' } },
  { id: 'a-cloth', cat: 'care', price: 2, art: 'cloth', tone: '#8e7cc3',
    name: { az: 'Mikrofibra salfet', ru: 'Салфетка из микрофибры', en: 'Microfibre cloth' },
    sub: { az: '15 × 18 sm', ru: '15 × 18 см', en: '15 × 18 cm' },
    info: { az: [['Ölçü', '15 × 18 sm']], ru: [['Размер', '15 × 18 см']], en: [['Size', '15 × 18 cm']] } },
];

/* ---------- Бренды очков ----------
   Названия ниже условные — замените своими брендами. У товара бренд задаётся полем brand: 'код бренда'.
   Бренд показывается на карточке и странице товара, а в каталоге по брендам можно фильтровать. */
const BRANDS = [
  { id: 'asi-classic', name: 'Asi Classic' },
  { id: 'asi-metal',   name: 'Asi Metal' },
  { id: 'asi-sun',     name: 'Asi Sun' },
  { id: 'asi-kids',    name: 'Asi Kids' },
];

/* ---------- Услуги мастерской (from: true — цена «от») ---------- */
const MIN = { az: 'dəqiqə', ru: 'минут', en: 'min' };
const mins = n => ({ az: `${n} ${MIN.az}`, ru: `${n} ${MIN.ru}`, en: `${n} ${MIN.en}` });
const SERVICES = [
  { id: 'screw',  price: 2,  from: true, time: mins(10),
    name: { az: 'Vintin dəyişdirilməsi', ru: 'Замена винта', en: 'Screw replacement' } },
  { id: 'pads',   price: 5,  from: true, time: mins(15),
    name: { az: 'Burun yastıqcıqlarının dəyişdirilməsi', ru: 'Замена носоупоров', en: 'Nose pad replacement' } },
  { id: 'fit',    price: 3,  from: true, time: mins(15),
    name: { az: 'Çərçivənin tənzimlənməsi və uyğunlaşdırılması', ru: 'Регулировка и подгонка оправы', en: 'Frame adjustment and fitting' } },
  { id: 'line',   price: 6,  from: true, time: mins(30),
    name: { az: 'Yarımçərçivədə neylon sapın dəyişdirilməsi', ru: 'Замена лески в полуободковой оправе', en: 'Nylon line replacement (semi-rimless)' } },
  { id: 'temple', price: 10, from: true, time: { az: '1–2 gün', ru: '1–2 дня', en: '1–2 days' },
    name: { az: 'Eynək qolunun dəyişdirilməsi', ru: 'Замена заушника', en: 'Temple arm replacement' } },
  { id: 'solder', price: 20, from: true, time: { az: '1–3 gün', ru: '1–3 дня', en: '1–3 days' },
    name: { az: 'Metal çərçivənin lehimlənməsi', ru: 'Пайка металлической оправы', en: 'Metal frame soldering' } },
  { id: 'lens',   price: 25, from: true, time: { az: '1 gündən', ru: 'от 1 дня', en: 'from 1 day' },
    name: { az: 'Sizin çərçivənizdə linzaların dəyişdirilməsi', ru: 'Замена линз в вашей оправе', en: 'New lenses in your own frame' } },
  { id: 'clean',  price: 3, time: mins(5),
    name: { az: 'Ultrasəs təmizləmə', ru: 'Ультразвуковая чистка', en: 'Ultrasonic cleaning' } },
  { id: 'exam',   price: 10, time: mins(20),
    name: { az: 'Görmə yoxlaması', ru: 'Проверка зрения', en: 'Eye test' } },
];

/* ---------- Страница «О нас» ----------
   Это черновик: замените текст своим рассказом о салоне (с какого года работаете, кто мастер).
   img  — фото салона; пока файла нет, показывается рисунок
   text — абзацы; can — список «Чем можем помочь» со ссылками на разделы сайта */
const ABOUT = {
  img: 'images/about.jpg',
  title: { az: 'Haqqımızda', ru: 'О нас', en: 'About us' },
  lead: {
    az: 'Asioptik — Bakıda optika salonu və eynək təmiri emalatxanasıdır. Reseptə uyğun çərçivə və linza seçirik, kontakt linzaları satırıq və eynəkləri yerindəcə təmir edirik.',
    ru: 'Asioptik — салон оптики и мастерская по ремонту очков в Баку. Подбираем оправы и линзы по рецепту, продаём контактные линзы и чиним очки на месте.',
    en: 'Asioptik is an optical shop and eyewear repair workshop in Baku. We fit frames and prescription lenses, sell contact lenses and repair glasses on site.',
  },
  text: {
    az: [
      'Bizdə böyüklər və uşaqlar üçün çərçivələr, günəş eynəkləri, eynək linzaları və kontakt linzaları var. Kataloqdakı hər şeyi saytda sifariş edə bilərsiniz: sifariş WhatsApp-ımıza gəlir, biz mövcudluğu və müddəti təsdiqləyirik və yalnız bundan sonra sifarişi hazırlayırıq.',
      'Salonun öz emalatxanası var. Vint və burun yastıqcıqlarını yanınızda dəyişirik, metal çərçivələri lehimləyirik və çərçivənizə yeni linzalar qoyuruq. Reseptiniz yoxdursa və ya köhnədirsə, görmənizi salonda yoxlayırıq.',
      'Sifarişi salondan götürə və ya şəhər daxilində kuryerlə ala bilərsiniz.',
    ],
    ru: [
      'У нас есть оправы для взрослых и детей, солнцезащитные очки, линзы для очков и контактные линзы. Всё из каталога можно заказать на сайте: заявка приходит нам в WhatsApp, мы подтверждаем наличие и срок и только после этого готовим заказ.',
      'При салоне работает своя мастерская. Винты и носоупоры меняем при вас, паяем металлические оправы и ставим новые линзы в вашу оправу. Если рецепта нет или он давно не обновлялся, проверим зрение в салоне.',
      'Заказ можно забрать в салоне или получить с курьером по городу.',
    ],
    en: [
      'We stock frames for adults and kids, sunglasses, spectacle lenses and contact lenses. Everything in the catalog can be ordered on the site: your order reaches us on WhatsApp, we confirm stock and timing, and only then prepare it.',
      'The shop has its own workshop. We replace screws and nose pads while you wait, solder metal frames and fit new lenses into your own frame. If you have no prescription, or it is an old one, we can test your eyesight in the shop.',
      'Collect your order in the shop or have it delivered by courier within the city.',
    ],
  },
  can: [
    { hash: '#catalog', goto: 'frames',
      title: { az: 'Çərçivə seçmək', ru: 'Подобрать оправу', en: 'Choose a frame' },
      text: { az: 'Böyüklər və uşaqlar üçün, reseptli linzalarla və ya linzasız.', ru: 'Для взрослых и детей, с линзами по рецепту или без них.', en: 'For adults and kids, with or without prescription lenses.' } },
    { hash: '#catalog', goto: 'lenses',
      title: { az: 'Reseptlə linza sifariş etmək', ru: 'Заказать линзы по рецепту', en: 'Order prescription lenses' },
      text: { az: 'Göstəricilər məhsulun səhifəsində seçilir, reseptin şəklini də əlavə etmək olar.', ru: 'Показатели выбираются на странице товара, можно приложить фото рецепта.', en: 'Pick your values on the product page or attach a photo of the prescription.' } },
    { hash: '#catalog', goto: 'contacts',
      title: { az: 'Kontakt linzaları almaq', ru: 'Купить контактные линзы', en: 'Buy contact lenses' },
      text: { az: 'Birgünlük, ikihəftəlik, aylıq və torik linzalar.', ru: 'Однодневные, двухнедельные, месячные и торические.', en: 'Daily, two-week, monthly and toric lenses.' } },
    { hash: '#repair',
      title: { az: 'Eynəyi təmir etdirmək', ru: 'Починить очки', en: 'Get glasses repaired' },
      text: { az: 'Xırda təmir yanınızda, mürəkkəb iş 1–3 günə.', ru: 'Мелкий ремонт при вас, сложный — за 1–3 дня.', en: 'Small repairs while you wait, bigger jobs in 1–3 days.' } },
  ],
};

/* ---------- Блог ----------
   Каждая статья: id (латиницей, попадает в адрес), date (ГГГГ-ММ-ДД), art — товар, рисунок которого стоит в карточке,
   title — заголовок, lead — короткое вступление, body — текст по строкам:
     обычная строка — абзац;  строка с «## » в начале — подзаголовок;  строка с «- » в начале — пункт списка.
   cta — кнопка в конце статьи: hash — раздел сайта, goto — раздел каталога, aud — для кого (необязательно). */
const POSTS = [
  { id: 'prescription', date: '2026-11-16', art: { id: 'l-ar', color: 0 },
    title: { az: 'Eynək reseptini necə oxumaq olar', ru: 'Как читать рецепт на очки', en: 'How to read your glasses prescription' },
    lead: {
      az: 'OD, OS, SPH, CYL, AX, PD — demək olar ki, hər reseptdə rast gəlinən altı qısaltma. Hər birinin nə demək olduğunu izah edirik.',
      ru: 'OD, OS, SPH, CYL, AX, PD — шесть сокращений, из которых состоит почти любой рецепт. Разбираем, что значит каждое.',
      en: 'OD, OS, SPH, CYL, AX, PD: six abbreviations that make up almost any prescription. Here is what each one means.',
    },
    body: {
      az: [
        '## Sağ və sol göz',
        'OD — sağ göz, OS — sol gözdür. Bəzən OU yazılır — hər iki göz. Gözlərin göstəriciləri çox vaxt fərqli olur, ona görə saytda onlar ayrıca seçilir.',
        '## Sfera, silindr və ox',
        '- SPH (sfera) — linzanın dioptriya ilə gücü. Yaxıngörmədə mənfi, uzaqgörmədə müsbət yazılır.',
        '- CYL (silindr) — astiqmatizm üçün düzəliş. Astiqmatizm yoxdursa, xana boş qalır.',
        '- AX (ox) — silindrin yerləşdiyi 0-dan 180°-dək bucaq. Silindr yoxdursa, ox göstərilmir.',
        '## PD və ADD',
        'PD — bəbəklər arasındakı məsafədir, millimetrlə ölçülür. Linzalar çərçivədə ona görə mərkəzləşdirilir. ADD (addisiya) — oxumaq üçün əlavədir; proqressiv və yaxın üçün eynək reseptlərində yazılır.',
        '## Nəyi yadda saxlamaq lazımdır',
        '- Eynək resepti kontakt linzaları üçün yaramır: onların öz parametrləri var, məsələn, BC əyrilik radiusu.',
        '- Görmə dəyişir. Reseptin bir-iki ildən çox yaşı varsa, görməni yenidən yoxlatmaq yaxşıdır.',
        '- Rəqəmlərə əmin deyilsinizsə, sifarişə reseptin şəklini əlavə edin — göstəriciləri özümüz köçürərik.',
      ],
      ru: [
        '## Правый и левый глаз',
        'OD — правый глаз, OS — левый. Иногда встречается OU — оба глаза. Значения для глаз часто разные, поэтому на сайте они выбираются отдельно.',
        '## Сфера, цилиндр и ось',
        '- SPH (сфера) — сила линзы в диоптриях. Минус ставят при близорукости, плюс — при дальнозоркости.',
        '- CYL (цилиндр) — поправка на астигматизм. Если астигматизма нет, графа пустая.',
        '- AX (ось) — угол от 0 до 180°, под которым стоит цилиндр. Без цилиндра ось не указывают.',
        '## PD и ADD',
        'PD — расстояние между зрачками в миллиметрах. По нему линзы центрируют в оправе. ADD (аддидация) — добавка для чтения, её пишут в рецептах на прогрессивные очки и очки для близи.',
        '## Что важно помнить',
        '- Рецепт на очки не подходит для контактных линз: у них свои параметры, например радиус кривизны BC.',
        '- Зрение меняется. Если рецепту больше года-двух, лучше проверить зрение заново.',
        '- Не уверены в цифрах — приложите фото рецепта к заказу, мы перенесём значения сами.',
      ],
      en: [
        '## Right and left eye',
        'OD is the right eye and OS is the left. You may also see OU, meaning both eyes. The values often differ between eyes, which is why the site asks for each eye separately.',
        '## Sphere, cylinder and axis',
        '- SPH (sphere) is the lens power in dioptres: minus for short-sightedness, plus for long-sightedness.',
        '- CYL (cylinder) corrects astigmatism. If you have none, the box is left empty.',
        '- AX (axis) is the angle, from 0 to 180°, at which the cylinder sits. No cylinder means no axis.',
        '## PD and ADD',
        'PD is the distance between your pupils in millimetres; lenses are centred in the frame by it. ADD (addition) is extra power for reading, written on prescriptions for progressive and reading glasses.',
        '## Worth remembering',
        '- A glasses prescription does not work for contact lenses: they have their own parameters, such as the base curve (BC).',
        '- Eyesight changes. If your prescription is more than a year or two old, have your eyes tested again.',
        '- Not sure about the numbers? Attach a photo of the prescription to your order and we will copy the values ourselves.',
      ],
    },
    cta: { hash: '#catalog', goto: 'lenses', text: { az: 'Eynək linzalarını seçin', ru: 'Выбрать линзы для очков', en: 'Choose spectacle lenses' } } },

  { id: 'kids-glasses', date: '2026-11-09', art: { id: 'f-kids', color: 0 },
    title: { az: 'Uşağa eynək necə seçilir', ru: 'Как выбрать очки ребёнку', en: 'How to choose glasses for a child' },
    lead: {
      az: 'Uşaq eynəyi yüngül olmalı, düz oturmalı və uşağın özünün xoşuna gəlməlidir — yoxsa onu taxmayacaq.',
      ru: 'Детские очки должны быть лёгкими, сидеть ровно и нравиться самому ребёнку — иначе их не будут носить.',
      en: 'Children’s glasses should be light, sit straight and appeal to the child, otherwise they will not be worn.',
    },
    body: {
      az: [
        '## Əvvəlcə resept',
        'Uşağa resepti həkim-oftalmoloq yazır. Reseptlə biz çərçivə seçir və linzaları hazırlayırıq.',
        '## Oturuş',
        '- Uşaq başını əyəndə çərçivə burnundan sürüşmür.',
        '- Eynək qolları qulaq arxasını sıxmır və iz qoymur.',
        '- Gözlər təxminən linzaların mərkəzində olur.',
        '## Material',
        'Kiçik yaşlı uşaqlara kəmərli elastik silikon çərçivələr uyğundur: yıxılmağa və oyunlara davam gətirir. Məktəblilərə yüngül asetat yaraşır. Uşaq eynəkləri üçün adətən zərbəyə davamlı linzalar seçilir.',
        '## Qoy özü seçsin',
        'Rəngi və formanı uşaqla birlikdə seçmək daha yaxşıdır. Xoşa gələn eynəyi xatırlatmadan taxırlar.',
        '## Nə vaxt dəyişməli',
        'Uşaqlar tez böyüyür. Çərçivə kiçik gəlirsə və ya görmə dəyişibsə, eynəyi dəyişmək vaxtıdır. Xırda nasazlıqları — vint, burun yastıqcığı — emalatxanada yanınızda düzəldirik.',
      ],
      ru: [
        '## Сначала рецепт',
        'Рецепт ребёнку выписывает врач-офтальмолог. С рецептом мы подберём оправу и изготовим линзы.',
        '## Посадка',
        '- Оправа не съезжает с носа, когда ребёнок наклоняет голову.',
        '- Заушники не давят за ушами и не оставляют следов.',
        '- Глаза находятся примерно по центру линз.',
        '## Материал',
        'Малышам подходят гибкие силиконовые оправы с ремешком: они переживают падения и игры. Школьникам — лёгкий ацетат. Для детских очков обычно выбирают ударопрочные линзы.',
        '## Пусть выбирает сам',
        'Цвет и форму лучше выбирать вместе с ребёнком. Очки, которые нравятся, носят без напоминаний.',
        '## Когда менять',
        'Дети растут быстро. Если оправа стала мала или зрение изменилось, очки пора менять. Мелкие поломки — винт, носоупор — чиним в мастерской при вас.',
      ],
      en: [
        '## Start with the prescription',
        'A child’s prescription is written by an eye doctor. With it, we fit the frame and make the lenses.',
        '## Fit',
        '- The frame stays put when the child looks down.',
        '- The temples do not press behind the ears or leave marks.',
        '- The eyes sit roughly in the centre of the lenses.',
        '## Material',
        'Flexible silicone frames with a strap suit younger children: they survive falls and play. Lightweight acetate works for schoolchildren. Impact-resistant lenses are the usual choice for children’s glasses.',
        '## Let them choose',
        'Pick the colour and shape together. Glasses a child likes get worn without reminders.',
        '## When to replace',
        'Children grow fast. If the frame has become too small or their eyesight has changed, it is time for a new pair. Small breakages such as a screw or a nose pad are fixed in the workshop while you wait.',
      ],
    },
    cta: { hash: '#catalog', goto: 'all', aud: 'kids', text: { az: 'Uşaq modellərinə baxın', ru: 'Смотреть детские модели', en: 'See kids’ styles' } } },

  { id: 'care', date: '2026-11-02', art: { id: 'a-cloth', color: 0 },
    title: { az: 'Eynəyə necə qulluq etməli', ru: 'Как ухаживать за очками', en: 'How to look after your glasses' },
    lead: {
      az: 'Linzaların daha uzun müddət təmiz və cızıqsız, çərçivənin isə düz qalması üçün bir neçə vərdiş.',
      ru: 'Несколько привычек, с которыми линзы дольше остаются чистыми и без царапин, а оправа — ровной.',
      en: 'A few habits that keep lenses clean and scratch-free and the frame straight for longer.',
    },
    body: {
      az: [
        '## Təmizləmə',
        '- Əvvəlcə linzaları su ilə yaxalayın — beləcə örtüyü cızan tozu yuyub aparırsınız.',
        '- Paltarın ucu və ya kağız salfetlə yox, mikrofibra salfetlə silin.',
        '- Yağlı izlər üçün linza spreyi yarayır.',
        '## Saxlama',
        'Eynəyi qabında gəzdirin və linzaları üzüaşağı qoymayın. Eynəyi günəş altında maşında saxlamayın: istidən linza örtükləri və çərçivənin forması korlanır.',
        '## Taxmaq və çıxarmaq',
        'Eynəyi iki əllə çıxarın. Bir əllə çəkib çıxaranda eynək qolları zamanla aralanır və çərçivə əyri oturmağa başlayır.',
        '## Emalatxanaya nə vaxt gətirməli',
        '- Vint boşalıb və ya çərçivə əyri oturur.',
        '- Burun yastıqcıqları saralıb və ya bərkiyib.',
        '- Salfetin çatmadığı yerlərə çirk yığılıb — ultrasəs təmizləmə kömək edər.',
      ],
      ru: [
        '## Чистка',
        '- Сначала сполосните линзы водой — так вы смоете пыль, которая царапает покрытие.',
        '- Протирайте салфеткой из микрофибры, а не краем одежды или бумажной салфеткой.',
        '- Для жирных следов подойдёт спрей для линз.',
        '## Хранение',
        'Носите очки в футляре и не кладите их линзами вниз. Не оставляйте очки в машине на солнце: от жары страдают покрытия линз и форма оправы.',
        '## Как надевать и снимать',
        'Снимайте очки двумя руками. Если стягивать их одной рукой, заушники со временем расходятся и оправа начинает сидеть криво.',
        '## Когда нести в мастерскую',
        '- Разболтался винт или оправа сидит неровно.',
        '- Пожелтели или затвердели носоупоры.',
        '- Грязь набилась в местах, куда не достаёт салфетка, — поможет ультразвуковая чистка.',
      ],
      en: [
        '## Cleaning',
        '- Rinse the lenses with water first: it washes off the dust that scratches the coating.',
        '- Wipe with a microfibre cloth, not the edge of your shirt or a paper tissue.',
        '- A lens spray deals with greasy marks.',
        '## Storage',
        'Carry your glasses in a case and never lay them lens-down. Do not leave them in a car in the sun: heat damages lens coatings and warps the frame.',
        '## Putting on and taking off',
        'Take your glasses off with both hands. Pulling them off with one hand gradually spreads the temples and the frame starts to sit crooked.',
        '## When to bring them to the workshop',
        '- A screw has come loose or the frame sits unevenly.',
        '- The nose pads have yellowed or hardened.',
        '- Dirt has built up where a cloth cannot reach; ultrasonic cleaning will help.',
      ],
    },
    cta: { hash: '#repair', text: { az: 'Emalatxanaya yazılın', ru: 'Записаться в мастерскую', en: 'Book the workshop' } } },
];

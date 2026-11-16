/* ======================================================================
   Логика сайта: каталог, корзина, оформление заказа, отправка в WhatsApp
   и переключение языков (AZ / RU / EN).
   Обычно здесь ничего менять не нужно — товары и контакты задаются
   в блоке «НАСТРОЙКИ МАГАЗИНА» в начале файла. Тексты интерфейса
   корзины и форм — в словаре UI ниже.
   ====================================================================== */
(function () {
  'use strict';

  const TH = (typeof THEME !== 'undefined' && THEME) || {};
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.prototype.slice.call((r || document).querySelectorAll(s));
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const cssEsc = s => (window.CSS && CSS.escape ? CSS.escape(String(s)) : String(s).replace(/["\\]/g, '\\$&'));
  const reduced = () => !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  const NB = '\u00A0';
  const p2 = n => String(n).padStart(2, '0');

  /* ---------- тексты интерфейса ---------- */
  const UI = {
    az: {
      added: 'Səbətə əlavə olundu: {name}', addedSvc: 'Müraciətə əlavə olundu: {name}',
      color: 'Rəng', select: 'Seçin', chooseMissing: 'Seçin: {list}', all: 'Bütün məhsullar',
      toCart: 'Səbətə əlavə edin', choose: 'Seçin', chooseFor: 'Parametrləri seçin: {name}', toCartFor: 'Səbətə əlavə edin: {name}',
      oldPrice: 'Köhnə qiymət', priceFrom: '{price}-dan', pcs: '{n} əd.', free: 'pulsuz', pickupShort: 'mağazadan götürmək',
      'cart.title': 'Səbət', 'cart.close': 'Səbəti bağlayın',
      'cart.empty': 'Səbət hələ boşdur. Kataloqda çərçivələr, günəş eynəkləri və linzalar var.',
      'cart.toCatalog': 'Kataloqa keçin', 'cart.sum': 'Məbləğ', 'cart.checkout': 'Sifarişi rəsmiləşdirin',
      'cart.freeLeft': 'Pulsuz çatdırılmaya {left} qalıb', 'cart.freeYes': 'Şəhərdaxili çatdırılma pulsuz olacaq',
      qty: 'Say', qtyOf: 'Say: {name}', qtyDec: 'Sayı azaldın', qtyInc: 'Sayı artırın', remove: 'Səbətdən silin: {name}',
      close: 'Bağlayın', 'pm.add': 'Səbətə əlavə edin',
      'co.title': 'Sifarişin rəsmiləşdirilməsi', 'co.close': 'Rəsmiləşdirməni bağlayın', 'co.contacts': 'Əlaqə məlumatları',
      'f.name': 'Ad', 'f.phone': 'Telefon', 'co.delivery': 'Çatdırılma', 'co.pickup': 'Mağazadan götürmək', 'co.courier': 'Kuryerlə çatdırılma',
      'co.address': 'Çatdırılma ünvanı', 'co.addressPh': 'Küçə, ev, mənzil, nişangah', 'co.payment': 'Ödəniş',
      'pay.cash': 'Nağd', 'pay.onDelivery': 'Təhvil zamanı', 'pay.card': 'Kartla', 'pay.transfer': 'Köçürmə', 'pay.transferNote': 'Rekvizitləri WhatsApp-da göndərəcəyik',
      'co.comment': 'Şərh', optional: '(istəyə görə)', 'co.commentPh': 'Çatdırılma üçün uyğun vaxt, sifarişlə bağlı suallar',
      'co.summary': 'Sifarişiniz', 'co.items': 'Məhsullar', 'co.deliveryRow': 'Çatdırılma', 'co.total': 'Cəmi',
      'co.submit': 'Sifarişi WhatsApp-a göndərin', 'co.note': 'Sifarişin hazır mətni ilə WhatsApp açılacaq. Orada «Göndər» düyməsini basın, sifariş bizə çatacaq.',
      'dn.free': 'Şəhər daxilində pulsuz', 'dn.price': 'Şəhər daxilində {price}', 'dn.priceFree': 'Şəhər daxilində {price}. {lim}-dan pulsuz',
      'e.name': 'Adınızı yazın', 'e.phone': 'Telefon nömrəsini tam yazın', 'e.phoneLong': 'Nömrədə artıq rəqəmlər var, yoxlayın', 'sb.photos': 'Banner şəkilləri', 'sb.photo': 'Şəkil {n}', 'e.address': 'Çatdırılma ünvanını yazın',
      'e.svc': 'Ən azı bir xidmət seçin', 'e.pickupAddr': 'Eynəyin götürüləcəyi ünvanı yazın',
      'ok.orderTitle': 'Sifarişi göndərmək qalıb',
      'ok.orderText': '{id} sifarişinin mətni ilə WhatsApp-ı açdıq. Çatda «Göndər» düyməsini basın, menecer sifarişi və çatdırılma vaxtını təsdiqləyəcək.',
      'ok.repairTitle': 'Müraciəti göndərmək qalıb',
      'ok.repairText': '{id} müraciətinin mətni ilə WhatsApp-ı açdıq. Çatda «Göndər» düyməsini basın, usta təmirin müddəti və qiyməti ilə cavab verəcək.',
      'ok.again': 'WhatsApp-ı yenidən açın', 'ok.back': 'Sayta qayıdın', 'toast.cart': 'Səbəti açın', 'wa.fab': 'Bizə WhatsApp-da yazın',
      'rp.title': 'Təmir üçün müraciət', 'rp.what': 'Nə etmək lazımdır', 'rp.desc': 'Nasazlığı təsvir edin', 'rp.descPh': 'Məsələn: metal çərçivənin qolu qırılıb',
      'rp.how': 'Eynəyi necə təhvil verəcəksiniz', 'rp.salon': 'Salona gətirəcəyəm', 'rp.courier': 'Kuryer götürsün',
      'rp.address': 'Eynəyi haradan götürək', 'rp.addressPh': 'Küçə, ev, mənzil', 'rp.date': 'Uyğun tarix',
      'rp.submit': 'Müraciəti WhatsApp-a göndərin', 'rp.note': 'Nasazlığın şəklini çat açılanda WhatsApp-da əlavə edə bilərsiniz.',
      'm.helloOrder': 'Salam! Sifariş vermək istəyirəm.', 'm.order': '*Sifariş {id}*', 'm.items': '*Məhsullar:*', 'm.itemsSum': 'Məhsullar: {v}',
      'm.delivery': 'Çatdırılma: {v}', 'm.total': '*Ödəniləcək məbləğ: {v}*', 'm.customer': '*Alıcı:*', 'm.name': 'Ad: {v}', 'm.phone': 'Telefon: {v}',
      'm.receive': 'Alınma üsulu: {v}', 'm.address': 'Ünvan: {v}', 'm.payment': 'Ödəniş: {v}',
      'm.od': 'OD (sağ): {v}', 'm.os': 'OS (sol): {v}', 'm.pd': 'PD: {v} mm', 'm.comment': 'Şərh: {v}',
      'm.helloRepair': 'Salam! Eynək təmiri üçün müraciət etmək istəyirəm.', 'm.request': '*Müraciət {id}*', 'm.services': 'Nə etmək lazımdır: {v}',
      'm.desc': 'Təsvir: {v}', 'm.handover': 'Eynəyin təhvili: {v}', 'm.date': 'Uyğun tarix: {v}', 'm.client': '*Müştəri:*', 'm.question': 'Salam! Sualım var.',
      'ml.pickup': 'Mağazadan götürmək', 'ml.courier': 'Kuryerlə çatdırılma', 'ml.cash': 'Təhvil zamanı nağd', 'ml.card': 'Təhvil zamanı kartla',
      'ml.transfer': 'Karta köçürmə',
      'ml.salon': 'Eynəyi salona gətirəcəyəm', 'ml.courierPick': 'Eynəyi götürmək üçün kuryer lazımdır',
      'pp.crumbs': 'Kataloqda yeriniz', 'pp.catalog': 'Kataloq', 'pp.details': 'Xüsusiyyətlər', 'pp.related': 'Oxşar məhsullar',
      'pp.lenses': 'Linzalar', 'pp.frameOnly': 'Yalnız çərçivə', 'pp.frameOnlyNote': 'Linzasız', 'pp.withLenses': 'Reseptə uyğun linzalarla',
      'pp.pair': '{price}, bir cüt üçün', 'pp.lensType': 'Linza növü',
      'pp.rx': 'Göz göstəriciləriniz', 'pp.mode.enter': 'Göstəriciləri seçəcəyəm', 'pp.mode.photo': 'Reseptin şəklini əlavə edəcəyəm',
      'pp.mode.exam': 'Reseptim yoxdur, görmə yoxlaması lazımdır',
      'pp.examNote': 'Sifarişdən sonra sizi salonda görmə yoxlamasına yazacağıq, bu 20 dəqiqə çəkir. Linzaları yoxlamanın nəticəsinə görə hazırlayacağıq.',
      'pp.od': 'Sağ göz', 'pp.os': 'Sol göz', 'pp.both': 'Hər iki göz', 'pp.same': 'Hər iki göz üçün eynidir', 'pp.boxes': 'Qutu sayı',
      'pp.none': 'yoxdur', 'pp.pd': 'Bəbəklərarası məsafə (PD)', 'pp.pdUnknown': 'Bilmirəm, salonda ölçərik', 'pp.add': 'Addisiya (ADD)', mm: 'mm',
      'pp.hint': 'Dəyərlər reseptinizdə yazılıb. CYL və AX-ı yalnız reseptdə varsa doldurun.',
      'pp.hintContacts': 'Dəyərlər reseptinizdə və ya linza qutusunda yazılıb.',
      'pp.unknown': 'Göstəricilərinizi bilmirsiniz?', 'pp.bookExam': 'Görmə yoxlamasına yazılın',
      'pp.photoPick': 'Reseptin şəklini seçin', 'pp.photoFormats': 'Foto və ya PDF', 'pp.photoChange': 'Dəyişin', 'pp.photoRemove': 'Silin',
      'pp.photoNote': 'Fayl cihazınızda qalır. Sifarişi göndərəndən sonra onu WhatsApp çatına əlavə etməyi xatırladacağıq.',
      'pp.total': 'Cəmi', 'pp.sumParts': 'çərçivə {a} + linzalar {b}',
      'eye.od': 'Sağ göz (OD)', 'eye.os': 'Sol göz (OS)', 'eye.both': 'Hər iki göz', forFrame: 'Çərçivə: {name}',
      'rxs.photo': 'Resept: şəkil ({name})', 'm.rxPhoto': 'Resept: şəklini bu çata göndərəcəyəm', 'm.rxExam': 'Resept yoxdur, salonda görmə yoxlaması lazımdır',
      'e.eyeNone': 'Ən azı bir göz üçün qutu sayını göstərin', 'e.eyeMissing': '{eye}: {list} seçin', 'e.sphOne': 'Ən azı bir göz üçün SPH seçin',
      'e.ax': '{eye}: CYL seçilibsə, oxu (AX) 0-dan 180-dək yazın', 'e.addReq': 'Addisiyanı (ADD) seçin', 'e.photo': 'Reseptin şəklini seçin',
      'ok.photo': 'Sonra reseptin şəklini də həmin çata göndərin.', 'ok.photoHow': 'Çatda sancaq işarəsini basın və faylı seçin: {names}.', 'ok.share': 'Reseptin şəklini göndərin',
      'aud.label': 'Kimin üçün', 'aud.all': 'Hamısı',
      'lang.label': 'Dil', itemsForms: ['məhsul', 'məhsul', 'məhsul'],
    },
    ru: {
      added: 'Добавлено в корзину: {name}', addedSvc: 'Добавлено в заявку: {name}',
      color: 'Цвет', select: 'Выберите', chooseMissing: 'Выберите: {list}', all: 'Все товары',
      toCart: 'В корзину', choose: 'Выбрать', chooseFor: 'Выбрать параметры: {name}', toCartFor: 'В корзину: {name}',
      oldPrice: 'Старая цена', priceFrom: 'от {price}', pcs: '{n} шт.', free: 'бесплатно', pickupShort: 'самовывоз',
      'cart.title': 'Корзина', 'cart.close': 'Закрыть корзину',
      'cart.empty': 'В корзине пока пусто. В каталоге есть оправы, солнцезащитные очки и линзы.',
      'cart.toCatalog': 'Перейти в каталог', 'cart.sum': 'Сумма', 'cart.checkout': 'Оформить заказ',
      'cart.freeLeft': 'До бесплатной доставки осталось {left}', 'cart.freeYes': 'Доставка по городу будет бесплатной',
      qty: 'Количество', qtyOf: 'Количество: {name}', qtyDec: 'Уменьшить количество', qtyInc: 'Увеличить количество', remove: 'Удалить из корзины: {name}',
      close: 'Закрыть', 'pm.add': 'Добавить в корзину',
      'co.title': 'Оформление заказа', 'co.close': 'Закрыть оформление', 'co.contacts': 'Контакты',
      'f.name': 'Имя', 'f.phone': 'Телефон', 'co.delivery': 'Получение', 'co.pickup': 'Самовывоз из салона', 'co.courier': 'Доставка курьером',
      'co.address': 'Адрес доставки', 'co.addressPh': 'Улица, дом, квартира, ориентир', 'co.payment': 'Оплата',
      'pay.cash': 'Наличными', 'pay.onDelivery': 'При получении', 'pay.card': 'Картой', 'pay.transfer': 'Переводом', 'pay.transferNote': 'Реквизиты пришлём в WhatsApp',
      'co.comment': 'Комментарий', optional: '(необязательно)', 'co.commentPh': 'Удобное время доставки, вопросы по заказу',
      'co.summary': 'Ваш заказ', 'co.items': 'Товары', 'co.deliveryRow': 'Доставка', 'co.total': 'Итого',
      'co.submit': 'Отправить заказ в WhatsApp', 'co.note': 'Откроется WhatsApp с готовым текстом заказа. Нажмите в нём «Отправить», и заказ придёт к нам.',
      'dn.free': 'По городу, бесплатно', 'dn.price': 'По городу, {price}', 'dn.priceFree': 'По городу, {price}. Бесплатно от {lim}',
      'e.name': 'Укажите имя', 'e.phone': 'Укажите номер телефона полностью', 'e.phoneLong': 'В номере лишние цифры, проверьте его', 'sb.photos': 'Фото баннера', 'sb.photo': 'Фото {n}', 'e.address': 'Укажите адрес доставки',
      'e.svc': 'Выберите хотя бы одну услугу', 'e.pickupAddr': 'Укажите адрес, откуда забрать очки',
      'ok.orderTitle': 'Осталось отправить заказ',
      'ok.orderText': 'Мы открыли WhatsApp с текстом заказа {id}. Нажмите в чате «Отправить», и менеджер подтвердит заказ и время доставки.',
      'ok.repairTitle': 'Осталось отправить заявку',
      'ok.repairText': 'Мы открыли WhatsApp с текстом заявки {id}. Нажмите в чате «Отправить», и мастер ответит со сроком и стоимостью ремонта.',
      'ok.again': 'Открыть WhatsApp ещё раз', 'ok.back': 'Вернуться на сайт', 'toast.cart': 'Открыть корзину', 'wa.fab': 'Написать нам в WhatsApp',
      'rp.title': 'Заявка на ремонт', 'rp.what': 'Что нужно сделать', 'rp.desc': 'Опишите поломку', 'rp.descPh': 'Например: отломился заушник у металлической оправы',
      'rp.how': 'Как передадите очки', 'rp.salon': 'Принесу в салон', 'rp.courier': 'Заберите курьером',
      'rp.address': 'Откуда забрать очки', 'rp.addressPh': 'Улица, дом, квартира', 'rp.date': 'Удобная дата',
      'rp.submit': 'Отправить заявку в WhatsApp', 'rp.note': 'Фото поломки можно прикрепить в WhatsApp, когда откроется чат.',
      'm.helloOrder': 'Здравствуйте! Хочу оформить заказ.', 'm.order': '*Заказ {id}*', 'm.items': '*Товары:*', 'm.itemsSum': 'Товары: {v}',
      'm.delivery': 'Доставка: {v}', 'm.total': '*Итого к оплате: {v}*', 'm.customer': '*Покупатель:*', 'm.name': 'Имя: {v}', 'm.phone': 'Телефон: {v}',
      'm.receive': 'Получение: {v}', 'm.address': 'Адрес: {v}', 'm.payment': 'Оплата: {v}',
      'm.od': 'OD (правый): {v}', 'm.os': 'OS (левый): {v}', 'm.pd': 'PD: {v} мм', 'm.comment': 'Комментарий: {v}',
      'm.helloRepair': 'Здравствуйте! Хочу оставить заявку на ремонт очков.', 'm.request': '*Заявка {id}*', 'm.services': 'Что сделать: {v}',
      'm.desc': 'Описание: {v}', 'm.handover': 'Передача очков: {v}', 'm.date': 'Удобная дата: {v}', 'm.client': '*Клиент:*', 'm.question': 'Здравствуйте! У меня вопрос.',
      'ml.pickup': 'Самовывоз из салона', 'ml.courier': 'Доставка курьером', 'ml.cash': 'Наличными при получении', 'ml.card': 'Картой при получении',
      'ml.transfer': 'Переводом на карту',
      'ml.salon': 'Принесу очки в салон', 'ml.courierPick': 'Нужен курьер, чтобы забрать очки',
      'pp.crumbs': 'Вы находитесь здесь', 'pp.catalog': 'Каталог', 'pp.details': 'Характеристики', 'pp.related': 'Похожие товары',
      'pp.lenses': 'Линзы', 'pp.frameOnly': 'Только оправа', 'pp.frameOnlyNote': 'Без линз', 'pp.withLenses': 'С линзами по рецепту',
      'pp.pair': '{price} за пару', 'pp.lensType': 'Тип линз',
      'pp.rx': 'Ваши показатели зрения', 'pp.mode.enter': 'Выберу показатели', 'pp.mode.photo': 'Приложу фото рецепта',
      'pp.mode.exam': 'Рецепта нет, нужна проверка зрения',
      'pp.examNote': 'После заказа запишем вас на проверку зрения в салоне, она занимает 20 минут. Линзы изготовим по её результатам.',
      'pp.od': 'Правый глаз', 'pp.os': 'Левый глаз', 'pp.both': 'Оба глаза', 'pp.same': 'Одинаково для обоих глаз', 'pp.boxes': 'Упаковок',
      'pp.none': 'нет', 'pp.pd': 'Межзрачковое расстояние (PD)', 'pp.pdUnknown': 'Не знаю, измерим в салоне', 'pp.add': 'Аддидация (ADD)', mm: 'мм',
      'pp.hint': 'Значения указаны в вашем рецепте. CYL и AX заполняйте, только если они есть в рецепте.',
      'pp.hintContacts': 'Значения указаны в рецепте или на упаковке ваших линз.',
      'pp.unknown': 'Не знаете свои показатели?', 'pp.bookExam': 'Запишитесь на проверку зрения',
      'pp.photoPick': 'Выбрать фото рецепта', 'pp.photoFormats': 'Фото или PDF', 'pp.photoChange': 'Заменить', 'pp.photoRemove': 'Убрать',
      'pp.photoNote': 'Файл остаётся на вашем устройстве. После отправки заказа напомним приложить его в чате WhatsApp.',
      'pp.total': 'Итого', 'pp.sumParts': 'оправа {a} + линзы {b}',
      'eye.od': 'Правый глаз (OD)', 'eye.os': 'Левый глаз (OS)', 'eye.both': 'Оба глаза', forFrame: 'Для оправы: {name}',
      'rxs.photo': 'Рецепт: фото ({name})', 'm.rxPhoto': 'Рецепт: пришлю фото в этот чат', 'm.rxExam': 'Рецепта нет, нужна проверка зрения в салоне',
      'e.eyeNone': 'Укажите количество упаковок хотя бы для одного глаза', 'e.eyeMissing': '{eye}: выберите {list}', 'e.sphOne': 'Выберите SPH хотя бы для одного глаза',
      'e.ax': '{eye}: для CYL укажите ось (AX) от 0 до 180', 'e.addReq': 'Выберите аддидацию (ADD)', 'e.photo': 'Выберите фото рецепта',
      'ok.photo': 'Затем отправьте в тот же чат фото рецепта.', 'ok.photoHow': 'В чате нажмите на скрепку и выберите файл: {names}.', 'ok.share': 'Отправить фото рецепта',
      'aud.label': 'Для кого', 'aud.all': 'Всем',
      'lang.label': 'Язык', itemsForms: ['товар', 'товара', 'товаров'],
    },
    en: {
      added: 'Added to cart: {name}', addedSvc: 'Added to your request: {name}',
      color: 'Colour', select: 'Select', chooseMissing: 'Please choose: {list}', all: 'All products',
      toCart: 'Add to cart', choose: 'Choose', chooseFor: 'Choose options: {name}', toCartFor: 'Add to cart: {name}',
      oldPrice: 'Was', priceFrom: 'from {price}', pcs: '× {n}', free: 'free', pickupShort: 'pickup',
      'cart.title': 'Cart', 'cart.close': 'Close cart',
      'cart.empty': 'Your cart is empty. Browse frames, sunglasses and lenses in the catalog.',
      'cart.toCatalog': 'Go to catalog', 'cart.sum': 'Subtotal', 'cart.checkout': 'Check out',
      'cart.freeLeft': '{left} more for free delivery', 'cart.freeYes': 'City delivery will be free',
      qty: 'Quantity', qtyOf: 'Quantity: {name}', qtyDec: 'Decrease quantity', qtyInc: 'Increase quantity', remove: 'Remove from cart: {name}',
      close: 'Close', 'pm.add': 'Add to cart',
      'co.title': 'Checkout', 'co.close': 'Close checkout', 'co.contacts': 'Your details',
      'f.name': 'Name', 'f.phone': 'Phone', 'co.delivery': 'Delivery', 'co.pickup': 'Pick up in store', 'co.courier': 'Courier delivery',
      'co.address': 'Delivery address', 'co.addressPh': 'Street, building, flat, landmark', 'co.payment': 'Payment',
      'pay.cash': 'Cash', 'pay.onDelivery': 'On delivery', 'pay.card': 'Card', 'pay.transfer': 'Bank transfer', 'pay.transferNote': 'We’ll send the details on WhatsApp',
      'co.comment': 'Comment', optional: '(optional)', 'co.commentPh': 'Preferred delivery time, questions about your order',
      'co.summary': 'Your order', 'co.items': 'Items', 'co.deliveryRow': 'Delivery', 'co.total': 'Total',
      'co.submit': 'Send order via WhatsApp', 'co.note': 'WhatsApp will open with your order already written. Press Send there and the order reaches us.',
      'dn.free': 'Within the city, free', 'dn.price': 'Within the city, {price}', 'dn.priceFree': 'Within the city, {price}. Free from {lim}',
      'e.name': 'Enter your name', 'e.phone': 'Enter your full phone number', 'e.phoneLong': 'The number has too many digits, please check it', 'sb.photos': 'Banner photos', 'sb.photo': 'Photo {n}', 'e.address': 'Enter the delivery address',
      'e.svc': 'Choose at least one service', 'e.pickupAddr': 'Enter the address to collect your glasses from',
      'ok.orderTitle': 'Now send the order',
      'ok.orderText': 'We’ve opened WhatsApp with order {id}. Press Send in the chat and our manager will confirm the order and delivery time.',
      'ok.repairTitle': 'Now send the request',
      'ok.repairText': 'We’ve opened WhatsApp with request {id}. Press Send in the chat and the technician will reply with the timing and price.',
      'ok.again': 'Open WhatsApp again', 'ok.back': 'Back to the site', 'toast.cart': 'Open cart', 'wa.fab': 'Message us on WhatsApp',
      'rp.title': 'Repair request', 'rp.what': 'What needs doing', 'rp.desc': 'Describe the problem', 'rp.descPh': 'For example: the arm broke off a metal frame',
      'rp.how': 'How will you hand over your glasses', 'rp.salon': 'I’ll bring them in', 'rp.courier': 'Collect by courier',
      'rp.address': 'Where to collect the glasses', 'rp.addressPh': 'Street, building, flat', 'rp.date': 'Preferred date',
      'rp.submit': 'Send request via WhatsApp', 'rp.note': 'You can attach a photo of the damage in WhatsApp once the chat opens.',
      'm.helloOrder': 'Hello! I’d like to place an order.', 'm.order': '*Order {id}*', 'm.items': '*Items:*', 'm.itemsSum': 'Items: {v}',
      'm.delivery': 'Delivery: {v}', 'm.total': '*Total to pay: {v}*', 'm.customer': '*Customer:*', 'm.name': 'Name: {v}', 'm.phone': 'Phone: {v}',
      'm.receive': 'Delivery method: {v}', 'm.address': 'Address: {v}', 'm.payment': 'Payment: {v}',
      'm.od': 'OD (right): {v}', 'm.os': 'OS (left): {v}', 'm.pd': 'PD: {v} mm', 'm.comment': 'Comment: {v}',
      'm.helloRepair': 'Hello! I’d like to request a glasses repair.', 'm.request': '*Request {id}*', 'm.services': 'Services: {v}',
      'm.desc': 'Description: {v}', 'm.handover': 'Handover: {v}', 'm.date': 'Preferred date: {v}', 'm.client': '*Customer:*', 'm.question': 'Hello! I have a question.',
      'ml.pickup': 'Pick up in store', 'ml.courier': 'Courier delivery', 'ml.cash': 'Cash on delivery', 'ml.card': 'Card on delivery',
      'ml.transfer': 'Bank transfer to card',
      'ml.salon': 'I’ll bring the glasses to the store', 'ml.courierPick': 'I need a courier to collect the glasses',
      'pp.crumbs': 'Breadcrumb', 'pp.catalog': 'Catalog', 'pp.details': 'Details', 'pp.related': 'Similar products',
      'pp.lenses': 'Lenses', 'pp.frameOnly': 'Frame only', 'pp.frameOnlyNote': 'No lenses', 'pp.withLenses': 'With prescription lenses',
      'pp.pair': '{price} a pair', 'pp.lensType': 'Lens type',
      'pp.rx': 'Your prescription', 'pp.mode.enter': 'I’ll enter my values', 'pp.mode.photo': 'I’ll add a photo of my prescription',
      'pp.mode.exam': 'I have no prescription and need an eye test',
      'pp.examNote': 'After you order, we’ll book you in for an eye test in store, which takes 20 minutes. We’ll make the lenses to the result.',
      'pp.od': 'Right eye', 'pp.os': 'Left eye', 'pp.both': 'Both eyes', 'pp.same': 'Same for both eyes', 'pp.boxes': 'Boxes',
      'pp.none': 'none', 'pp.pd': 'Pupillary distance (PD)', 'pp.pdUnknown': 'Not sure, measure it in store', 'pp.add': 'Addition (ADD)', mm: 'mm',
      'pp.hint': 'You’ll find these values on your prescription. Fill in CYL and AX only if they’re listed.',
      'pp.hintContacts': 'You’ll find these values on your prescription or lens box.',
      'pp.unknown': 'Don’t know your values?', 'pp.bookExam': 'Book an eye test',
      'pp.photoPick': 'Choose a photo of your prescription', 'pp.photoFormats': 'Photo or PDF', 'pp.photoChange': 'Replace', 'pp.photoRemove': 'Remove',
      'pp.photoNote': 'The file stays on your device. After you send the order, we’ll remind you to attach it in the WhatsApp chat.',
      'pp.total': 'Total', 'pp.sumParts': 'frame {a} + lenses {b}',
      'eye.od': 'Right eye (OD)', 'eye.os': 'Left eye (OS)', 'eye.both': 'Both eyes', forFrame: 'For frame: {name}',
      'rxs.photo': 'Prescription: photo ({name})', 'm.rxPhoto': 'Prescription: I’ll send a photo in this chat', 'm.rxExam': 'No prescription, eye test in store needed',
      'e.eyeNone': 'Set the number of boxes for at least one eye', 'e.eyeMissing': '{eye}: choose {list}', 'e.sphOne': 'Choose SPH for at least one eye',
      'e.ax': '{eye}: enter the axis (AX) from 0 to 180 for the CYL', 'e.addReq': 'Choose the addition (ADD)', 'e.photo': 'Choose a photo of your prescription',
      'ok.photo': 'Then send the photo of your prescription in the same chat.', 'ok.photoHow': 'In the chat, tap the paperclip and choose the file: {names}.', 'ok.share': 'Send the prescription photo',
      'aud.label': 'Who it’s for', 'aud.all': 'All',
      'lang.label': 'Language', itemsForms: ['item', 'items', 'items'],
    },
  };
  const LANG_NAMES = { az: 'Azərbaycanca', ru: 'Русский', en: 'English' };
  const LOCALES = { az: 'az-Latn-AZ', ru: 'ru-RU', en: 'en-GB' };

  /* ---------- хранилище браузера ---------- */
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* хранилище недоступно */ } },
  };
  const CART_KEY = 'optika4-cart';
  const CUSTOMER_KEY = 'optika-customer';
  const LANG_KEY = 'optika-lang';

  /* ---------- язык ---------- */
  const LANGS = ((Array.isArray(CONFIG.languages) && CONFIG.languages.length) ? CONFIG.languages : [document.documentElement.lang || 'ru'])
    .filter(l => UI[l]);
  if (!LANGS.length) LANGS.push('ru');
  let lang = LANGS[0];
  (function pickLang() {
    let q = '';
    try { q = new URLSearchParams(window.location.search).get('lang') || ''; } catch (e) { /* ничего */ }
    const saved = store.get(LANG_KEY, '');
    if (LANGS.indexOf(q) !== -1) { lang = q; if (q !== saved) store.set(LANG_KEY, q); }
    else if (LANGS.indexOf(saved) !== -1) lang = saved;
  })();
  const msgLang = () => (LANGS.indexOf(CONFIG.messageLang) !== -1 ? CONFIG.messageLang : lang);

  function L(v, lng) {
    if (v == null) return '';
    if (typeof v === 'object' && !Array.isArray(v)) {
      const l = lng || lang;
      if (v[l] != null) return v[l];
      if (v[LANGS[0]] != null) return v[LANGS[0]];
      return v.az != null ? v.az : v.ru != null ? v.ru : v.en != null ? v.en : '';
    }
    return v;
  }
  const allText = v => (v && typeof v === 'object' && !Array.isArray(v) ? Object.keys(v).map(k => v[k]).join(' ') : String(v || ''));

  function money(n, lng) {
    const v = Math.round((+n || 0) * 100) / 100;
    let s;
    try { s = v.toLocaleString(LOCALES[lng || lang] || 'ru-RU', { minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 }); }
    catch (e) { s = String(v); }
    return s + NB + CONFIG.currency;
  }
  function t(key, vars, lng) {
    const l = lng || lang;
    const P = TH.i18n || {};
    let s = (P[l] && P[l][key] != null) ? P[l][key]
      : (UI[l] && UI[l][key] != null) ? UI[l][key]
      : (P[LANGS[0]] && P[LANGS[0]][key] != null) ? P[LANGS[0]][key]
      : (UI.ru[key] != null ? UI.ru[key] : key);
    const v = Object.assign({
      freeFrom: money(CONFIG.freeDeliveryFrom || 0, l), deliveryPrice: money(CONFIG.deliveryPrice || 0, l), shop: CONFIG.shopName,
    }, vars || {});
    return String(s).replace(/\{(\w+)\}/g, (m, k) => (v[k] != null ? v[k] : m));
  }
  function itemsCount(n, lng) {
    const l = lng || lang, f = (UI[l] || UI.ru).itemsForms;
    let i = 2;
    if (l === 'ru') { const a = Math.abs(n) % 100, b = a % 10; i = a > 10 && a < 20 ? 2 : b > 1 && b < 5 ? 1 : b === 1 ? 0 : 2; }
    else if (l === 'en') i = n === 1 ? 0 : 1;
    else i = 0;
    return n + ' ' + f[i];
  }
  const priceFrom = (price, lng) => t('priceFrom', { price: money(price, lng) }, lng);

  /* ---------- форматирование ---------- */
  function nowStr() {
    const d = new Date();
    return `${p2(d.getDate())}.${p2(d.getMonth() + 1)}.${d.getFullYear()}, ${p2(d.getHours())}:${p2(d.getMinutes())}`;
  }
  function makeId(prefix) {
    const d = new Date();
    return `${prefix}-${p2(d.getDate())}${p2(d.getMonth() + 1)}-${Math.floor(1000 + Math.random() * 9000)}`;
  }
  const digitsCount = s => String(s || '').replace(/\D/g, '').length;

  /* ---------- товары и параметры ---------- */
  const byId = {};
  PRODUCTS.forEach(p => { byId[p.id] = p; });
  const catById = {};
  CATEGORIES.forEach(c => { catById[c.id] = c; });
  const catName = (id, lng) => (catById[id] ? L(catById[id].name, lng) : '');

  function normVal(x) {
    if (x && typeof x === 'object') return { v: String(x.v), d: +x.d || 0, label: x.label || null };
    return { v: String(x), d: 0, label: null };
  }
  // Значения параметров хранятся без привязки к языку (цвет — номер варианта, индекс — «1.60»)
  function defsOf(p) {
    if (p._defs) return p._defs;
    const out = [];
    if (p.colors && p.colors.length) {
      out.push({
        k: 'color', label: p.colorLabel || null, type: 'swatch', required: true, def: '0',
        values: p.colors.map((c, i) => ({ v: String(i), d: +c.d || 0, label: c.n, color: c })),
      });
    }
    (p.opts || []).forEach(o => out.push(mkDef(o)));
    Object.defineProperty(p, '_defs', { value: out, enumerable: false });
    return out;
  }
  // eye: true — параметр выбирают отдельно для правого и левого глаза
  function mkDef(o) {
    const groups = o.groups ? o.groups.map(g => ({ label: g.label, values: g.values.map(normVal) })) : null;
    const values = groups ? [].concat.apply([], groups.map(g => g.values)) : (o.values || []).map(normVal);
    let def = '';
    if (o.default != null) def = String(o.default);
    else if ((o.preselect || values.length === 1) && values.length) def = values[0].v;
    return { k: o.k, label: o.label, short: o.short, hint: o.hint, type: 'select', groups, values, required: o.required !== false, def, eye: !!o.eye };
  }
  const labelOf = (d, lng) => (d.k === 'color' ? (d.label ? L(d.label, lng) : t('color', null, lng)) : L(d.label, lng));
  function valLabel(d, v, lng) {
    const it = d.values.find(x => x.v === v);
    return it ? (it.label ? L(it.label, lng) : it.v) : v;
  }
  const needsOptions = p => !!((p.opts && p.opts.length) || p.rx);   // такой товар настраивают на его странице
  function colorIdx(p, sel) {
    if (!p.colors || !p.colors.length) return -1;
    const n = typeof sel === 'number' ? sel : (/^\d+$/.test(String(sel)) ? +sel : 0);
    return n >= 0 && n < p.colors.length ? n : 0;
  }
  const colorOf = (p, sel) => { const i = colorIdx(p, sel); return i < 0 ? null : p.colors[i]; };
  function deltaOf(p, sel) {
    let s = 0;
    defsOf(p).forEach(d => { const v = d.values.find(x => x.v === sel[d.k]); if (v) s += v.d; });
    return s;
  }
  const unitPrice = (p, sel) => p.price + deltaOf(p, sel);
  const hasDeltas = p => defsOf(p).some(d => d.values.some(v => v.d > 0));
  const priceLabel = p => (hasDeltas(p) ? priceFrom(p.price) : money(p.price));
  const optsText = (p, sel, lng) => defsOf(p).filter(d => sel[d.k] != null && sel[d.k] !== '')
    .map(d => (d.short ? L(d.short, lng) + ' ' : '') + valLabel(d, sel[d.k], lng)).join(', ');
  const optsLong = (p, sel, lng) => defsOf(p).filter(d => sel[d.k] != null && sel[d.k] !== '')
    .map(d => (d.short ? L(d.short, lng) : labelOf(d, lng)) + ': ' + valLabel(d, sel[d.k], lng)).join(', ');
  // Строка корзины — товар с выбранными параметрами; у линз к ним добавляются глаз, оправа и показатели зрения
  const sigOf = it => [it.id].concat(defsOf(byId[it.id]).map(d => it.sel[d.k] || ''), it.eye || '',
    it.frame ? it.frame.id + ':' + (it.frame.color || '') : '', it.rx ? JSON.stringify(it.rx) : '').join('|');
  const eyeText = e => (e ? [['SPH', e.sph], ['CYL', e.cyl], ['AX', e.ax]].filter(x => x[1]).map(x => x[0] + ' ' + x[1]).join(', ') : '');
  // Пояснения к строке корзины: параметры, для какой оправы линзы, показатели зрения. long — вариант для сообщения
  function itemLines(it, lng, long) {
    const p = byId[it.id], out = [];
    const o = long && !it.eye ? optsLong(p, it.sel, lng) : optsText(p, it.sel, lng);
    if (it.eye) out.push(t('eye.' + it.eye, null, lng) + (o ? ': ' + o : ''));
    else if (o) out.push(o);
    const f = it.frame ? byId[it.frame.id] : null;
    if (f) { const c = colorOf(f, it.frame.color); out.push(t('forFrame', { name: L(f.name, lng) + (c ? ' (' + L(c.n, lng) + ')' : '') }, lng)); }
    const rx = it.rx;
    if (rx && rx.mode === 'enter') {
      ['od', 'os'].forEach(e => { const v = eyeText(rx[e]); if (v) out.push(t('m.' + e, { v }, lng)); });
      if (rx.add) out.push('ADD: ' + rx.add);
      if (rx.pd) out.push(t('m.pd', { v: rx.pd }, lng));
    } else if (rx && rx.mode === 'photo') out.push(long ? t('m.rxPhoto', null, lng) : t('rxs.photo', { name: rx.photo.name }, lng));
    else if (rx && rx.mode === 'exam') out.push(t('m.rxExam', null, lng));
    return out;
  }
  function badges(p) {
    const out = [];
    if (p.badge) out.push({ t: L(p.badge) });
    if (p.old && p.old > p.price) out.push({ t: '−' + Math.round((1 - p.price / p.old) * 100) + '%', sale: true });
    return out;
  }

  /* ---------- иконки ---------- */
  const ic = d => `<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${d}</svg>`;
  const ICON = {
    bag: ic('<path d="M5 8h14l-1.2 11.2a2 2 0 0 1-2 1.8H8.2a2 2 0 0 1-2-1.8L5 8Z"/><path d="M9 8V6.5a3 3 0 0 1 6 0V8"/>'),
    x: ic('<path d="M6 6l12 12M18 6 6 18"/>'),
    menu: ic('<path d="M4 7h16M4 12h16M4 17h16"/>'),
    chat: ic('<path d="M5 4.5h14a2 2 0 0 1 2 2V15a2 2 0 0 1-2 2h-7.5L7 20.5V17H5a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2Z"/><path d="M8.3 10.8h.01M12 10.8h.01M15.7 10.8h.01" stroke-width="2.6"/>'),
    phone: ic('<path d="M6.5 3.5h2.8l1.6 4.4-2 1.4a11.5 11.5 0 0 0 5.8 5.8l1.4-2 4.4 1.6v2.8a2 2 0 0 1-2.1 2A16.5 16.5 0 0 1 4.5 5.6a2 2 0 0 1 2-2.1Z"/>'),
    pin: ic('<path d="M12 21s-6.5-5.8-6.5-11a6.5 6.5 0 0 1 13 0c0 5.2-6.5 11-6.5 11Z"/><circle cx="12" cy="10" r="2.3"/>'),
    clock: ic('<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>'),
    search: ic('<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>'),
    at: ic('<circle cx="12" cy="12" r="3.6"/><path d="M15.6 8.4v4.6a2.4 2.4 0 0 0 4.8 0V12a8.4 8.4 0 1 0-3.3 6.7"/>'),
    check: ic('<path d="m5 12.5 4.5 4.5L19 7.5"/>'),
    tool: ic('<path d="M14.6 6.4a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.1-3.1a5.6 5.6 0 0 1-7.4 7.4l-6.4 6.4a2 2 0 0 1-2.9-2.9l6.4-6.4a5.6 5.6 0 0 1 7.4-7.4l-3.2 3Z"/>'),
    truck: ic('<path d="M3 6.5h11V16H3zM14 9.5h3.8L21 13v3h-7"/><circle cx="7" cy="17.5" r="1.7"/><circle cx="17" cy="17.5" r="1.7"/>'),
    eye: ic('<path d="M2.5 12s3.5-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.5 6.5-9.5 6.5S2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="2.8"/>'),
    minus: ic('<path d="M6 12h12"/>'),
    plus: ic('<path d="M12 6v12M6 12h12"/>'),
    camera: ic('<path d="M4 8.5h3l1.5-2.5h7L17 8.5h3a1 1 0 0 1 1 1V18a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5a1 1 0 0 1 1-1Z"/><circle cx="12" cy="13.5" r="3.4"/>'),
    doc: ic('<path d="M7.5 3.5H14l4 4V20a.5.5 0 0 1-.5.5h-10A.5.5 0 0 1 7 20V4a.5.5 0 0 1 .5-.5Z"/><path d="M14 3.5v4h4M10 12.5h5M10 16h5"/>'),
  };

  /* ---------- иллюстрации товаров ---------- */
  const svgOpen = () => '<svg class="art" viewBox="0 0 240 120" aria-hidden="true" focusable="false">';
  const SHAPES = {
    round:    { d: 'M-30,0a30,30 0 1,0 60,0a30,30 0 1,0 -60,0Z', b: [28.2, -10.3], h: [-28.5, -9.5] },
    oval:     { d: 'M-34,0a34,25 0 1,0 68,0a34,25 0 1,0 -68,0Z', b: [32.2, -8], h: [-32.5, -7.5] },
    rect:     { d: 'M-25,-22H25Q35,-22 35,-12V12Q35,22 25,22H-25Q-35,22 -35,12V-12Q-35,-22 -25,-22Z', b: [35, -9], h: [-35, -13] },
    square:   { d: 'M-18,-29H18Q34,-29 34,-13V13Q34,29 18,29H-18Q-34,29 -34,13V-13Q-34,-29 -18,-29Z', b: [34, -10], h: [-34, -15] },
    cateye:   { d: 'M-42,-24C-20,-24 12,-20 30,-14C36,-6 34,10 22,18C8,26 -20,24 -32,12C-40,2 -42,-12 -42,-24Z', b: [31.5, -11], h: [-41, -22] },
    aviator:  { d: 'M30,-19C12,-22 -22,-23 -36,-15C-44,-8 -40,10 -28,20C-14,31 8,32 20,20C28,11 32,-2 32,-12C32,-16 31,-18 30,-19Z', b: [31.5, -14], h: [-38, -12], bar: [16, -21.5] },
    hex:      { d: 'M-18,-26H18L34,0L18,26H-18L-34,0Z', b: [29, -8], h: [-27, -12] },
    trapeze:  { d: 'M-38,-23H33Q38,-23 37,-16L32,12Q30,21 20,21H-20Q-30,21 -32,13L-38,-15Q-40,-23 -38,-23Z', b: [35.5, -11], h: [-39, -19] },
    browline: { d: 'M-34,-16Q-34,-22 -26,-22H26Q34,-22 34,-16V2Q34,24 4,24H-6Q-34,24 -34,2Z', b: [34, -12], h: [-35, -17], brow: 'M-37,-16Q-37,-24 -28,-24H28Q37,-24 37,-16' },
  };
  function glasses(o) {
    const S = SHAPES[o.shape] || SHAPES.round;
    const Lx = 76, Rx = 164, Y = 60;
    const brow = !!S.brow;
    const sw = o.sw || (o.metal ? 2.6 : 6.5);
    const paint = o.c === 'tortoise' ? 'url(#opt-tortoise)' : (o.c || '#222');
    const metalPaint = o.c2 || '#9fa4ab';
    const tL = `translate(${Lx} ${Y})`, tR = `translate(${Rx} ${Y}) scale(-1 1)`;
    const lens = `<path d="${S.d}" transform="${tL}"/><path d="${S.d}" transform="${tR}"/>`;
    const bx1 = Lx + S.b[0], bx2 = Rx - S.b[0], by = Y + S.b[1];
    const hx1 = Lx + S.h[0], hx2 = Rx - S.h[0], hy = Y + S.h[1];
    const bridge = `<path d="M${bx1} ${by}Q120 ${by - 9} ${bx2} ${by}"/>`;
    const temples = `<path d="M${hx1} ${hy}l-15 -3.5M${hx2} ${hy}l15 -3.5"/>`;
    const bar = S.bar ? `<path d="M${Lx + S.bar[0]} ${Y + S.bar[1]}H${Rx - S.bar[0]}"/>` : '';
    const browPath = brow ? `<path d="${S.brow}" transform="${tL}"/><path d="${S.brow}" transform="${tR}"/>` : '';
    let s = svgOpen();
    s += `<ellipse cx="120" cy="108" rx="80" ry="4.5" fill="#000" opacity="${o.shadow != null ? o.shadow : 0.07}"/>`;
    if (o.sun) {
      s += `<g fill="${o.l || '#2b2b30'}" fill-opacity=".9">${lens}</g>`;
      if (o.grad) s += `<g fill="url(#opt-fade)">${lens}</g>`;
      s += `<g fill="url(#opt-glare)">${lens}</g>`;
    } else {
      s += `<g fill="${o.glass || 'url(#opt-glass)'}">${lens}</g>`;
    }
    s += `<path d="M${Lx - 17} ${Y - 4}l9 -10M${Rx - 17} ${Y - 4}l9 -10" stroke="#fff" stroke-opacity="${o.sun ? 0.32 : 0.8}" stroke-width="2.6" stroke-linecap="round" fill="none"/>`;
    if (o.rim) s += `<g fill="none" stroke="${o.rim}" stroke-width="${(brow ? 8 : sw) + 2.2}" stroke-linejoin="round" stroke-linecap="round">${brow ? browPath + lens : lens}${bridge}${bar}${temples}</g>`;
    const op = o.a != null ? ` opacity="${o.a}"` : '';
    if (brow) {
      s += `<g fill="none" stroke="${metalPaint}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round">${lens}${bridge}</g>`;
      s += `<g fill="none" stroke="${paint}" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"${op}>${browPath}${temples}</g>`;
    } else {
      s += `<g fill="none" stroke="${paint}" stroke-width="${sw}" stroke-linejoin="round" stroke-linecap="round"${op}>${lens}${bridge}${bar}${temples}</g>`;
    }
    if (o.metal || brow) s += `<g fill="${o.pad || 'rgba(255,255,255,.8)'}" stroke="rgba(0,0,0,.25)" stroke-width=".8"><ellipse cx="${bx1 - 6}" cy="${Y + 9}" rx="2.6" ry="5"/><ellipse cx="${bx2 + 6}" cy="${Y + 9}" rx="2.6" ry="5"/></g>`;
    return s + '</svg>';
  }
  const glassFill = () => (TH.art && TH.art.glass) || 'url(#opt-glass)';
  function cbox(p) {
    const c = p.tone || '#2a9fc4';
    return svgOpen() + '<ellipse cx="128" cy="108" rx="60" ry="5" fill="#000" opacity=".08"/>' +
      `<path d="M74 28 88 19h94l-14 9Z" fill="${c}" opacity=".45"/><path d="M168 28l14-9v76l-14 9Z" fill="${c}" opacity=".7"/>` +
      '<rect x="74" y="28" width="94" height="76" rx="3" fill="#fff"/>' +
      `<path d="M74 31a3 3 0 0 1 3-3h88a3 3 0 0 1 3 3v24H74Z" fill="${c}"/>` +
      '<rect x="84" y="37" width="40" height="5" rx="2.5" fill="#fff"/><rect x="84" y="46" width="24" height="3.5" rx="1.75" fill="#fff" opacity=".7"/>' +
      '<circle cx="151" cy="41.5" r="8" fill="none" stroke="#fff" stroke-width="2"/><path d="M146.5 40q4.5-4 9 0" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" opacity=".85"/>' +
      `<text x="84" y="84" font-size="23" font-weight="700" fill="${c}">${esc(p.pack || '')}</text>` +
      '<rect x="118" y="70" width="38" height="3.5" rx="1.75" fill="#1c2430" opacity=".16"/><rect x="118" y="78" width="28" height="3.5" rx="1.75" fill="#1c2430" opacity=".1"/>' +
      `<rect x="84" y="93" width="72" height="2.5" rx="1.25" fill="${c}" opacity=".35"/>` +
      '<rect x="74.5" y="28.5" width="93" height="75" rx="3" fill="none" stroke="#1c2430" stroke-opacity=".1"/></svg>';
  }
  function iris(p, col) {
    const c = (col && col.c) || '#5f9fd6';
    let fib = '';
    for (let i = 0; i < 30; i++) {
      const a = (i / 30) * Math.PI * 2, r1 = 11, r2 = i % 2 ? 22 : 24.5;
      fib += `M${(Math.cos(a) * r1).toFixed(1)} ${(Math.sin(a) * r1).toFixed(1)}L${(Math.cos(a) * r2).toFixed(1)} ${(Math.sin(a) * r2).toFixed(1)}`;
    }
    const lens = (x, y, s) => `<g transform="translate(${x} ${y}) scale(${s})"><circle r="34" fill="${glassFill()}"/><circle r="25.5" fill="${c}"/>` +
      `<path d="${fib}" stroke="#fff" stroke-opacity=".38" stroke-width="1.3" fill="none"/><circle r="25.5" fill="none" stroke="#14181f" stroke-opacity=".3" stroke-width="2.6"/>` +
      '<circle r="9.5" fill="#14181f" fill-opacity=".85"/><circle r="34" fill="none" stroke="#7f8c95" stroke-opacity=".4" stroke-width="1.2"/>' +
      '<path d="M-22 -14q9-13 26-12" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="3" stroke-linecap="round"/></g>';
    return svgOpen() + '<ellipse cx="124" cy="108" rx="66" ry="4.5" fill="#000" opacity=".07"/>' + lens(152, 64, 0.84) + lens(98, 58, 1) + '</svg>';
  }
  function slens(p, col) {
    const k = p.kind || 'ar';
    const refl = k === 'blue' ? '#7b84ff' : '#3fcf8e';
    const disc = (x, y, tint) => `<g transform="translate(${x} ${y})"><circle r="36" fill="${tint || glassFill()}"${tint ? ' fill-opacity=".88"' : ''}/><circle r="36" fill="url(#opt-glare)"/>` +
      (k === 'prog' ? '<path d="M-5 -6c-2 12 1 22-3 34M5 -6c2 12-1 22 3 34" fill="none" stroke="#7f8c95" stroke-opacity=".6" stroke-width="1.2" stroke-dasharray="2 3"/><path d="M-30 -8h60" stroke="#7f8c95" stroke-opacity=".35" stroke-width="1" stroke-dasharray="2 3"/>' : '') +
      `<path d="M-27 -16a31 31 0 0 1 22-17" fill="none" stroke="${refl}" stroke-opacity=".8" stroke-width="4" stroke-linecap="round"/>` +
      '<circle r="36" fill="none" stroke="#7f8c95" stroke-opacity=".5" stroke-width="1.3"/><circle r="33.5" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1"/></g>';
    const dark = k === 'photo' ? ((col && col.c) || '#4a4f57') : null;
    return svgOpen() + '<ellipse cx="122" cy="108" rx="70" ry="4.5" fill="#000" opacity=".07"/>' + disc(146, 62, dark) + disc(98, 58, null) + '</svg>';
  }
  function bottle(p) {
    const c = p.tone || '#2a9fc4';
    const body = 'M104 26h32c8 3 11 9 11 17v59a8 8 0 0 1-8 8H101a8 8 0 0 1-8-8V43c0-8 3-14 11-17Z';
    return svgOpen() + '<ellipse cx="120" cy="113" rx="32" ry="4" fill="#000" opacity=".08"/>' +
      `<rect x="109" y="5" width="22" height="15" rx="3" fill="${c}"/><rect x="106" y="18" width="28" height="8" rx="2" fill="${c}" opacity=".78"/>` +
      `<path d="${body}" fill="#fff"/><path d="M93 54h54v34H93Z" fill="${c}"/>` +
      '<rect x="101" y="62" width="26" height="4" rx="2" fill="#fff"/><rect x="101" y="70" width="17" height="3" rx="1.5" fill="#fff" opacity=".7"/>' +
      `<path d="M100 34v66" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".55"/><path d="${body}" fill="none" stroke="#1c2430" stroke-opacity=".12"/></svg>`;
  }
  function drops(p) {
    const c = p.tone || '#23a174';
    return svgOpen() + '<ellipse cx="120" cy="113" rx="24" ry="3.5" fill="#000" opacity=".08"/>' +
      '<path d="M114 22l6-15 6 15Z" fill="#fff" stroke="#1c2430" stroke-opacity=".15"/>' +
      `<rect x="109" y="20" width="22" height="24" rx="4" fill="${c}"/><rect x="104" y="42" width="32" height="68" rx="9" fill="#fff"/>` +
      `<rect x="104" y="58" width="32" height="30" fill="${c}" opacity=".9"/><rect x="110" y="65" width="16" height="3.5" rx="1.75" fill="#fff"/>` +
      '<path d="M110 50v54" stroke="#fff" stroke-width="2.6" stroke-linecap="round" opacity=".55"/>' +
      '<rect x="104" y="42" width="32" height="68" rx="9" fill="none" stroke="#1c2430" stroke-opacity=".12"/></svg>';
  }
  function lenscase(p) {
    const c = p.tone || '#3a86d4';
    return svgOpen() + '<ellipse cx="120" cy="96" rx="70" ry="4.5" fill="#000" opacity=".08"/>' +
      `<rect x="88" y="52" width="64" height="18" rx="6" fill="${c}" opacity=".8"/>` +
      `<circle cx="84" cy="61" r="27" fill="${c}"/><circle cx="84" cy="61" r="19" fill="#fff" opacity=".92"/>` +
      `<circle cx="156" cy="61" r="27" fill="#fff"/><circle cx="156" cy="61" r="24" fill="none" stroke="${c}" stroke-width="6"/><circle cx="156" cy="61" r="19" fill="${c}" opacity=".14"/>` +
      `<text x="84" y="68" text-anchor="middle" font-size="19" font-weight="700" fill="${c}">L</text><text x="156" y="68" text-anchor="middle" font-size="19" font-weight="700" fill="${c}">R</text></svg>`;
  }
  function glassCase(p, col) {
    const c = (col && col.c) || p.tone || '#3d4048';
    return svgOpen() + '<ellipse cx="120" cy="100" rx="84" ry="5" fill="#000" opacity=".09"/>' +
      `<rect x="36" y="34" width="168" height="58" rx="29" fill="${c}"/><path d="M40 63h160" stroke="#000" stroke-opacity=".22" stroke-width="1.5"/>` +
      '<path d="M58 42q62-12 124 0" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="3" stroke-linecap="round"/>' +
      '<rect x="110" y="59" width="20" height="8" rx="4" fill="#fff" opacity=".4"/></svg>';
  }
  function cloth(p) {
    const c = p.tone || '#8e7cc3';
    return svgOpen() + '<ellipse cx="120" cy="104" rx="64" ry="4.5" fill="#000" opacity=".08"/>' +
      `<path d="M74 24h92l8 76H66Z" fill="${c}"/><path d="M120 24l2 76M70 62h100" stroke="#fff" stroke-opacity=".28" stroke-width="1.5"/>` +
      '<path d="M140 86h22" stroke="#fff" stroke-opacity=".6" stroke-width="2" stroke-linecap="round"/><path d="M74 24h92l8 76H66Z" fill="none" stroke="#000" stroke-opacity=".08"/></svg>';
  }
  function art(p, sel) {
    const col = colorOf(p, sel);
    const img = (col && col.img) || p.img;
    if (img) return `<img class="art-img" src="${esc(img)}" alt="" loading="lazy">`;
    const A = TH.art || {};
    switch (p.art) {
      case 'glasses':
        return glasses({
          shape: p.shape, c: col ? col.c : '#222', a: col ? col.a : null, c2: col ? col.c2 : null, l: col ? col.l : null,
          metal: p.metal, sun: p.sun, grad: p.grad, sw: p.sw, rim: A.rim, glass: A.glass, pad: A.pad,
        });
      case 'cbox': return cbox(p);
      case 'iris': return iris(p, col);
      case 'slens': return slens(p, col);
      case 'bottle': return bottle(p);
      case 'drops': return drops(p);
      case 'lenscase': return lenscase(p);
      case 'case': return glassCase(p, col);
      case 'cloth': return cloth(p);
      default: return svgOpen() + '</svg>';
    }
  }
  function hexA(h, a) {
    const m = /^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(h);
    return m ? `rgba(${parseInt(m[1], 16)},${parseInt(m[2], 16)},${parseInt(m[3], 16)},${a})` : h;
  }
  function swAttr(c) {
    if (!c) return '';
    if (c.c === 'tortoise') return 'data-tortoise';
    const base = c.a != null && c.a < 1 ? hexA(c.c, c.a) : c.c;
    let bg = base;
    if (c.c2) bg = `linear-gradient(135deg, ${base} 0 55%, ${c.c2} 55% 100%)`;
    else if (c.l) bg = `radial-gradient(circle, ${c.l} 0 44%, ${base} 46%)`;
    return `style="--c:${esc(bg)}"`;
  }
  function swatches(p) {
    if (!p.colors || p.colors.length < 2) return '';
    const cur = state.sel[p.id] || 0;
    return `<div class="swatches" role="group" aria-label="${esc(p.colorLabel ? L(p.colorLabel) : t('color'))}">` + p.colors.map((c, i) =>
      `<button type="button" class="sw${i === cur ? ' is-active' : ''}" data-swatch="${i}" aria-pressed="${i === cur}" aria-label="${esc(L(c.n))}" title="${esc(L(c.n))}" ${swAttr(c)}></button>`
    ).join('') + '</div>';
  }
  function injectDefs() {
    const d = document.createElement('div');
    d.setAttribute('aria-hidden', 'true');
    d.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
    d.innerHTML = '<svg width="0" height="0" focusable="false"><defs>' +
      '<linearGradient id="opt-glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".55" stop-color="#e4edf1" stop-opacity=".55"/><stop offset="1" stop-color="#d3dfe6" stop-opacity=".5"/></linearGradient>' +
      '<linearGradient id="opt-sheen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8ee6c8" stop-opacity=".32"/><stop offset=".5" stop-color="#5b6a9a" stop-opacity=".06"/><stop offset="1" stop-color="#9c8bff" stop-opacity=".34"/></linearGradient>' +
      '<linearGradient id="opt-glare" x1="0" y1="0" x2=".7" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".42"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/></linearGradient>' +
      '<linearGradient id="opt-fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".25" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".6"/></linearGradient>' +
      '<filter id="opt-tt" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">' +
      '<feTurbulence type="fractalNoise" baseFrequency="0.045 0.075" numOctaves="3" seed="8" stitchTiles="stitch" result="n"/>' +
      '<feColorMatrix in="n" type="matrix" values="0 0 0 0 .17  0 0 0 0 .085  0 0 0 0 .03  4.2 0 0 0 -2.05" result="dk"/>' +
      '<feColorMatrix in="n" type="matrix" values="0 0 0 0 .47  0 0 0 0 .23  0 0 0 0 .07  0 3.2 0 0 -1.35" result="md"/>' +
      '<feFlood flood-color="#c98b3a" result="bs"/><feMerge><feMergeNode in="bs"/><feMergeNode in="md"/><feMergeNode in="dk"/></feMerge></filter>' +
      '<pattern id="opt-tortoise" width="120" height="120" patternUnits="userSpaceOnUse"><rect width="120" height="120" filter="url(#opt-tt)"/></pattern>' +
      '</defs></svg>';
    document.body.insertBefore(d, document.body.firstChild);
  }

  /* ---------- состояние ---------- */
  const state = { cat: 'all', aud: '', brands: [], q: '', sort: 'default', sel: {}, cart: [], ok: null, page: '', view: '', post: '', viewInfo: null, pps: {} };
  // Разделы «для кого»: взрослым (внутри мужчины и женщины) и детям
  const AUDS = (typeof AUDIENCES !== 'undefined' && Array.isArray(AUDIENCES)) ? AUDIENCES : [];
  const audById = {}, audParent = {};
  AUDS.forEach(a => { audById[a.id] = a; (a.parts || []).forEach(x => { audById[x.id] = x; audParent[x.id] = a.id; }); });
  // Раздел с частями («Взрослым») объединяет товары всех своих частей
  const audIds = a => (audById[a] ? (audById[a].parts ? audById[a].parts.map(x => x.id) : [a]) : []);
  const inAud = (p, a) => !a || !!(p.for && audIds(a).some(id => p.for.indexOf(id) !== -1));

  /* ---------- бренды очков: список BRANDS в настройках, у товара поле brand ---------- */
  const BRAND_LIST = typeof BRANDS !== 'undefined' && Array.isArray(BRANDS) ? BRANDS : [];
  const brandById = {};
  BRAND_LIST.forEach(b => { brandById[b.id] = b; });
  const brandName = p => (p && p.brand && brandById[p.brand] ? brandById[p.brand].name : '');

  /* ---------- каталог ---------- */
  const norm = s => String(s || '').toLowerCase().replace(/ё/g, 'е');
  function filtered() {
    let list = PRODUCTS.filter(p => inAud(p, state.aud) && (state.cat === 'all' || p.cat === state.cat));
    if (state.brands.length) list = list.filter(p => state.brands.indexOf(p.brand) !== -1);
    if (state.q) {
      const q = norm(state.q);
      list = list.filter(p => norm([allText(p.name), allText(p.sub), brandName(p), allText(catById[p.cat] && catById[p.cat].name)]
        .concat((p.colors || []).map(c => allText(c.n))).join(' ')).indexOf(q) !== -1);
      list.forEach(p => {
        if (!p.colors) return;
        const i = p.colors.findIndex(c => norm(allText(c.n)).indexOf(q) !== -1);
        if (i >= 0) state.sel[p.id] = i;
      });
    }
    if (state.sort === 'asc') list = list.slice().sort((a, b) => a.price - b.price);
    if (state.sort === 'desc') list = list.slice().sort((a, b) => b.price - a.price);
    return list;
  }
  function renderTabs() {
    const box = $('#catTabs');
    if (!box) return;
    const pool = PRODUCTS.filter(p => inAud(p, state.aud));
    const all = [{ id: 'all', name: t('all') }].concat(CATEGORIES);
    box.innerHTML = all.map(c => {
      const n = c.id === 'all' ? pool.length : pool.filter(p => p.cat === c.id).length;
      if (!n && c.id !== 'all') return '';
      const on = state.cat === c.id;
      const cc = { id: c.id, name: L(c.name), short: L(c.short || c.name) };
      return TH.tab ? TH.tab(cc, n, on)
        : `<button type="button" class="tab${on ? ' is-active' : ''}" data-cat="${c.id}" aria-pressed="${on}">${esc(cc.short)}<span class="tab-n">${n}</span></button>`;
    }).join('');
  }
  function renderProducts() {
    const grid = $('#productsGrid');
    if (!grid) return;
    const list = filtered();
    grid.innerHTML = list.map(p => (TH.card ? TH.card(p) : `<article data-pid="${p.id}">${esc(L(p.name))}</article>`)).join('');
    const empty = $('#catalogEmpty');
    if (empty) empty.hidden = list.length > 0;
    const cnt = $('#resultCount');
    if (cnt) cnt.textContent = itemsCount(list.length);
    const now = $('#catNow');
    if (now) now.textContent = state.cat !== 'all' && catById[state.cat] ? catName(state.cat) : t('all');
    $$('[data-sort]').forEach(b => {
      const on = b.dataset.sort === state.sort;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-pressed', on);
    });
    $$('#catTabs [data-cat]').forEach(b => {
      const on = b.dataset.cat === state.cat;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-pressed', on);
    });
    if (TH.onRender) TH.onRender();
    syncCatalogURL();
  }
  // Фильтр «для кого» в каталоге и названия разделов в меню
  function renderAudSwitch() {
    const top = state.aud ? (audParent[state.aud] || state.aud) : '', cur = audById[top];
    const btn = (key, target, name, on) => `<button type="button" data-aud="${target}" data-key="${key}" aria-pressed="${on}" class="${on ? 'is-active' : ''}">${esc(name)}</button>`;
    $$('[data-aud-switch]').forEach(box => {
      box.hidden = !AUDS.length;
      box.innerHTML = '<div class="aud-row">' + btn('', '', t('aud.all'), !top) + AUDS.map(a => btn(a.id, a.id, L(a.name), top === a.id)).join('') + '</div>' +
        // Второй ряд — части выбранного раздела; повторное нажатие на выбранную часть возвращает ко всему разделу
        (cur && cur.parts ? '<div class="aud-row aud-sub">' + cur.parts.map(x => btn(x.id, state.aud === x.id ? cur.id : x.id, L(x.name), state.aud === x.id)).join('') + '</div>' : '');
    });
    $$('[data-aud-name]').forEach(el => { const x = audById[el.dataset.audName]; if (x) el.textContent = L(x.name); });
  }
  // Фильтр по брендам: показываются бренды, которые есть в выбранном разделе; можно отметить несколько
  function renderBrands() {
    const box = $('#brandBox'), list = $('#brandList');
    const pool = PRODUCTS.filter(p => inAud(p, state.aud) && (state.cat === 'all' || p.cat === state.cat) && brandById[p.brand]);
    const shown = BRAND_LIST.filter(b => pool.some(p => p.brand === b.id));
    state.brands = state.brands.filter(id => shown.some(b => b.id === id));
    if (!box || !list) return;
    box.hidden = !shown.length;
    list.innerHTML = shown.map(b => {
      const on = state.brands.indexOf(b.id) !== -1, n = pool.filter(p => p.brand === b.id).length;
      return `<button type="button" class="${on ? 'is-active' : ''}" data-brand="${esc(b.id)}" aria-pressed="${on}">${esc(b.name)}<span class="tab-n">${n}</span></button>`;
    }).join('');
  }
  function renderCatalog() {
    if (state.cat !== 'all' && !PRODUCTS.some(p => inAud(p, state.aud) && p.cat === state.cat)) state.cat = 'all';
    renderTabs();
    renderAudSwitch();
    renderBrands();
    renderProducts();
  }
  // Секции на главной: «Для взрослых» (мужчины и женщины) и «Для детей»
  function audView(a) {
    const pool = PRODUCTS.filter(p => inAud(p, a.id));
    let list = (a.pick || []).map(id => byId[id]).filter(p => p && inAud(p, a.id));
    if (!list.length && !a.parts) list = pool.slice(0, 4);
    const ap = a.art ? byId[a.art.id] : null;
    return {
      id: a.id, name: L(a.name), title: L(a.title), text: L(a.text), panel: L(a.panel), all: L(a.all), count: pool.length,
      art: ap ? art(ap, a.art.color || 0) : '', img: a.img || '', demo: a.demo || '', pos: a.pos || '', flip: !!a.flip, show: a.show || null, list,
      head: L(a.head), col: L(a.col), feats: [].concat(L(a.feats) || []), slides: Array.isArray(a.slides) ? a.slides.filter(x => x && (x.img || x.demo)) : [],
      parts: a.parts ? a.parts.map(audView).filter(v => v.count) : null,
    };
  }
  function renderAudiences() {
    const box = $('[data-audiences]');
    if (!box) return;
    box.innerHTML = AUDS.map(audView).filter(v => v.count).map(v => (TH.audience ? TH.audience(v)
      : `<section id="${v.id}"><h2>${esc(v.title)}</h2><p>${esc(v.text)}</p><a href="#catalog" data-goto="all" data-aud="${v.id}">${esc(v.all)}</a></section>`)).join('');
  }
  function onGridClick(e) {
    const card = e.target.closest('[data-pid]');
    if (!card) return;
    const pid = card.dataset.pid;
    const sw = e.target.closest('[data-swatch]');
    if (sw) { state.sel[pid] = +sw.dataset.swatch; syncCard(pid); return; }
    if (e.target.closest('[data-add]')) quickAdd(pid);
  }
  function updateCardColor(card, p, idx) {
    const a = card.querySelector('.js-art');
    if (a) a.innerHTML = art(p, idx);
    $$('[data-swatch]', card).forEach(b => {
      const on = +b.dataset.swatch === idx;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-pressed', on);
    });
    const cn = card.querySelector('.js-color-name');
    if (cn && p.colors) cn.textContent = L(p.colors[idx].n);
    if (TH.onSwatch) TH.onSwatch(card, p, idx);
  }
  // Один товар может стоять сразу в нескольких местах: в каталоге, в секции на главной, в «похожих»
  function syncCard(pid) {
    $$(`[data-pid="${cssEsc(pid)}"]`).forEach(card => updateCardColor(card, byId[pid], state.sel[pid] || 0));
  }
  function quickAdd(pid) {
    const p = byId[pid];
    if (needsOptions(p)) { navigate(pid); return; }
    const sel = {};
    if (p.colors && p.colors.length) sel.color = String(state.sel[pid] || 0);
    addItem({ id: pid, sel, qty: 1 });
    toast(t('added', { name: L(p.name) }));
  }

  /* ---------- страница товара ---------- */
  // У каждого товара свой адрес: имя-файла.html?product=код-товара. На странице выбирают цвет и параметры,
  // а для линз — показатели зрения отдельно для каждого глаза или прикладывают фото рецепта.
  const RXC = (typeof RX !== 'undefined' && RX) || {};
  const rxDef = k => mkDef(Array.isArray(RXC[k]) ? { k, values: RXC[k] } : Object.assign({ values: [] }, RXC[k] || {}, { k }));
  const RXD = { sph: rxDef('sph'), cyl: rxDef('cyl'), add: rxDef('add') };
  const PDR = Array.isArray(RXC.pd) && RXC.pd.length === 2 ? RXC.pd : [50, 76];
  const eyeDefs = p => defsOf(p).filter(d => d.eye);
  const sharedDefs = p => defsOf(p).filter(d => !d.eye);
  const isContacts = p => eyeDefs(p).length > 0;
  const isLens = p => !!p.rx && !isContacts(p);
  const lensList = () => PRODUCTS.filter(isLens);
  const kindOf = p => (isContacts(p) ? 'contacts' : isLens(p) ? 'lens' : (p.withLenses && lensList().length ? 'frame' : 'plain'));
  const nice = v => String(v).replace(/^-/, '−');
  const clamp = (n, a, b) => Math.min(b, Math.max(a, n));
  const photoFiles = {};   // выбранные файлы рецептов хранятся только в памяти этой вкладки
  let photoSeq = 0;

  function ppState(id) {
    if (state.pps[id]) return state.pps[id];
    const p = byId[id], sel = {};
    sharedDefs(p).forEach(d => { if (d.def) sel[d.k] = d.def; });
    const eye = () => { const o = { qty: 1 }; eyeDefs(p).forEach(d => { o[d.k] = d.def || ''; }); return o; };
    const pp = {
      id, sel, qty: 1, lens: '', lastLens: '', lensSel: {}, mode: 'enter', same: false, bothQty: 2,
      eyes: isContacts(p) ? { od: eye(), os: eye() } : { od: { sph: '', cyl: '', ax: '' }, os: { sph: '', cyl: '', ax: '' } },
      pd: '', add: '', photo: null,
    };
    state.pps[id] = pp;
    return pp;
  }
  function setLens(pp, id) {
    pp.lens = id && byId[id] && isLens(byId[id]) ? id : '';
    if (!pp.lens) return;
    const keep = pp.lensSel, sel = {};
    defsOf(byId[pp.lens]).forEach(d => {
      const v = keep[d.k] != null && d.values.some(x => x.v === keep[d.k]) ? keep[d.k] : d.def;
      if (v) sel[d.k] = v;
    });
    pp.lensSel = sel;
    pp.lastLens = pp.lens;
  }
  function setPhoto(pp, file) {
    const id = 'ph' + Date.now().toString(36) + (++photoSeq);
    let url = '';
    if (/^image\//.test(file.type || '')) { try { url = URL.createObjectURL(file); } catch (e) { url = ''; } }
    photoFiles[id] = file;
    pp.photo = { id, name: String(file.name || 'photo').slice(0, 80), url };
  }

  function defOptions(d, cur, withPrice) {
    const tag = v => `<option value="${esc(v.v)}"${cur === v.v ? ' selected' : ''}>${esc(v.label ? L(v.label) : nice(v.v))}${withPrice && v.d ? ' (+' + money(v.d) + ')' : ''}</option>`;
    return d.groups
      ? d.groups.map(g => `<optgroup label="${esc(L(g.label))}">${g.values.map(tag).join('')}</optgroup>`).join('')
      : d.values.map(tag).join('');
  }
  // scope: 'p' — параметры самого товара, 'l' — параметры линз, которые заказывают вместе с оправой
  function optHTML(d, sel, scope) {
    const id = `pp-${scope}-${d.k}`;
    if (d.type === 'swatch') {
      return `<fieldset class="opt opt-sw"><legend>${esc(labelOf(d))}: <span class="js-sw-current">${esc(valLabel(d, sel.color))}</span></legend><div class="swatches">` +
        d.values.map((v, i) => `<label class="sw-pick"><input type="radio" id="${id}-${i}" name="${id}" data-opt="color" data-scope="${scope}" value="${esc(v.v)}"${sel.color === v.v ? ' checked' : ''}><span class="sw" ${swAttr(v.color)} title="${esc(L(v.label))}"></span><span class="vh">${esc(L(v.label))}</span></label>`).join('') +
        '</div></fieldset>';
    }
    if (d.values.length === 1) {
      return `<div class="opt opt-fixed"><span class="opt-label">${esc(labelOf(d))}</span><span class="opt-value">${esc(valLabel(d, d.values[0].v))}</span></div>`;
    }
    return `<div class="opt opt-sel"><label class="opt-label" for="${id}">${esc(labelOf(d))}</label>` +
      `<select id="${id}" data-opt="${d.k}" data-scope="${scope}">${d.def ? '' : `<option value="">${esc(t('select'))}</option>`}${defOptions(d, sel[d.k], true)}</select>` +
      (d.hint ? `<p class="opt-hint">${esc(L(d.hint))}</p>` : '') + '</div>';
  }
  const stepper = (attr, id, n, labelKey) => `<div class="qty" role="group" aria-label="${esc(t(labelKey))}">` +
    `<button type="button" id="${id}-dec" ${attr} data-dir="-1" aria-label="${esc(t('qtyDec'))}">${ICON.minus}</button><output>${n}</output>` +
    `<button type="button" id="${id}-inc" ${attr} data-dir="1" aria-label="${esc(t('qtyInc'))}">${ICON.plus}</button></div>`;
  const eyeCell = e => `<span class="rxb-eye"><b>${e === 'both' ? 'OD + OS' : e.toUpperCase()}</b><small>${esc(t('pp.' + e))}</small></span>`;

  // Контактные линзы: сила (и цилиндр с осью у торических) и число упаковок для каждого глаза
  function contactsRx(p, pp) {
    const defs = eyeDefs(p), rows = pp.same ? ['both'] : ['od', 'os'];
    const body = rows.map(e => {
      const st = pp.eyes[e === 'both' ? 'od' : e], n = e === 'both' ? pp.bothQty : st.qty, off = n === 0;
      return `<div class="rxb-row${off ? ' is-off' : ''}">${eyeCell(e)}` +
        defs.map(d => {
          const lab = d.short ? L(d.short) : labelOf(d);
          return `<label class="rxb-cell"><span>${esc(lab)}</span><select id="pp-${e}-${d.k}" data-eye="${e}" data-opt="${d.k}" aria-label="${esc(t('pp.' + e) + ', ' + lab)}"${off ? ' disabled' : ''}>${d.def ? '' : '<option value="">—</option>'}${defOptions(d, st[d.k])}</select></label>`;
        }).join('') +
        `<div class="rxb-cell rxb-qty"><span>${esc(t('pp.boxes'))}</span>${stepper(`data-eye-qty="${e}"`, 'pp-q-' + e, n, 'pp.boxes')}</div></div>`;
    }).join('');
    const rest = sharedDefs(p).filter(d => d.type !== 'swatch');
    const extra = rest.length ? '<div class="rxb-extra">' + rest.map(d => (d.values.length === 1
      ? `<p class="rxb-cell rxb-fixed"><span>${esc(labelOf(d))}</span><b>${esc(valLabel(d, d.values[0].v))}</b></p>`
      : `<label class="rxb-cell"><span>${esc(labelOf(d))}</span><select id="pp-p-${d.k}" data-opt="${d.k}" data-scope="p">${d.def ? '' : `<option value="">${esc(t('select'))}</option>`}${defOptions(d, pp.sel[d.k])}</select></label>`)).join('') + '</div>' : '';
    return `<label class="pp-check"><input type="checkbox" id="pp-same"${pp.same ? ' checked' : ''}><span>${esc(t('pp.same'))}</span></label>` +
      `<div class="rxb has-qty" style="--n:${defs.length}" role="group" aria-label="${esc(t('pp.rx'))}">${body}${extra}</div>` +
      `<p class="hint">${esc(t('pp.hintContacts'))} ${esc(t('pp.unknown'))} <a href="#repair" data-pick-svc="exam">${esc(t('pp.bookExam'))}</a></p>`;
  }
  // Линзы для очков: SPH, CYL и AX для каждого глаза, расстояние между зрачками, для прогрессивных — аддидация
  function glassesRx(rp, pp) {
    const body = ['od', 'os'].map(e => {
      const st = pp.eyes[e], who = t('pp.' + e);
      return `<div class="rxb-row">${eyeCell(e)}` +
        `<label class="rxb-cell"><span>SPH</span><select id="pp-${e}-sph" data-eye="${e}" data-rx="sph" aria-label="${esc(who)}, SPH"><option value="">—</option>${defOptions(RXD.sph, st.sph)}</select></label>` +
        `<label class="rxb-cell"><span>CYL</span><select id="pp-${e}-cyl" data-eye="${e}" data-rx="cyl" aria-label="${esc(who)}, CYL"><option value="">${esc(t('pp.none'))}</option>${defOptions(RXD.cyl, st.cyl)}</select></label>` +
        `<label class="rxb-cell"><span>AX</span><input id="pp-${e}-ax" data-eye="${e}" data-rx="ax" type="text" inputmode="numeric" maxlength="3" autocomplete="off" placeholder="0–180" value="${esc(st.ax)}" aria-label="${esc(who)}, AX"${st.cyl ? '' : ' disabled'}></label></div>`;
    }).join('');
    let pd = '';
    for (let v = PDR[0]; v <= PDR[1]; v++) pd += `<option value="${v}"${pp.pd === String(v) ? ' selected' : ''}>${v} ${esc(t('mm'))}</option>`;
    const extra = '<div class="rxb-extra">' +
      (rp.add ? `<label class="rxb-cell"><span>${esc(t('pp.add'))}</span><select id="pp-add"><option value="">${esc(t('select'))}</option>${defOptions(RXD.add, pp.add)}</select></label>` : '') +
      `<label class="rxb-cell"><span>${esc(t('pp.pd'))}</span><select id="pp-pd"><option value="">${esc(t('pp.pdUnknown'))}</option>${pd}</select></label></div>`;
    return `<div class="rxb" style="--n:3" role="group" aria-label="${esc(t('pp.rx'))}">${body}${extra}</div><p class="hint">${esc(t('pp.hint'))}</p>`;
  }
  function photoBlock(pp) {
    const ph = pp.photo;
    const input = '<input class="vh" type="file" id="pp-photo" accept="image/*,application/pdf">';
    const note = `<p class="hint">${esc(t('pp.photoNote'))}</p>`;
    if (!ph) {
      return `<div class="rx-photo">${input}<label class="rx-drop" for="pp-photo"><span class="rx-drop-icon">${ICON.camera}</span><span><b>${esc(t('pp.photoPick'))}</b><small>${esc(t('pp.photoFormats'))}</small></span></label>${note}</div>`;
    }
    const thumb = ph.url ? `<img class="rx-thumb" src="${esc(ph.url)}" alt="">` : `<span class="rx-thumb">${ICON.doc}</span>`;
    return `<div class="rx-photo">${input}<div class="rx-file">${thumb}<p class="rx-file-name">${esc(ph.name)}</p>` +
      `<p class="rx-file-acts"><label class="btn-text" for="pp-photo">${esc(t('pp.photoChange'))}</label><button type="button" class="btn-text" data-photo-remove>${esc(t('pp.photoRemove'))}</button></p></div>${note}</div>`;
  }
  // Оправа: только оправа или сразу с линзами по рецепту (тип линз, индекс, показатели)
  function lensBlock(pp) {
    const list = lensList(), min = Math.min.apply(null, list.map(x => x.price));
    const pick = (id, name, value, on, title, note) => `<label class="choice"><input type="radio" id="${id}" name="${name}" value="${esc(value)}"${on ? ' checked' : ''}><span><b>${esc(title)}</b><small>${note}</small></span></label>`;
    let h = '<div class="choices choices-2">' +
      pick('pp-lens-off', 'pp-lens-on', '', !pp.lens, t('pp.frameOnly'), esc(t('pp.frameOnlyNote'))) +
      pick('pp-lens-yes', 'pp-lens-on', '1', !!pp.lens, t('pp.withLenses'), esc(t('pp.pair', { price: priceFrom(min) }))) + '</div>';
    if (pp.lens) {
      const lp = byId[pp.lens];
      h += `<div class="opt"><span class="opt-label" id="pp-lt">${esc(t('pp.lensType'))}</span><div class="choices choices-2" role="radiogroup" aria-labelledby="pp-lt">` +
        list.map(x => pick('pp-lt-' + x.id, 'pp-lens', x.id, x.id === pp.lens, L(x.name), priceLabel(x))).join('') + '</div></div>' +
        defsOf(lp).map(d => optHTML(d, pp.lensSel, 'l')).join('');
    }
    return `<fieldset class="pp-block"><legend>${esc(t('pp.lenses'))}</legend>${h}</fieldset>`;
  }
  function rxBlock(p, pp, kind) {
    const modes = kind === 'contacts' ? ['enter', 'photo'] : ['enter', 'photo', 'exam'];
    if (modes.indexOf(pp.mode) === -1) pp.mode = 'enter';
    const cards = modes.map(m => `<label class="choice"><input type="radio" id="pp-mode-${m}" name="pp-mode" value="${m}"${pp.mode === m ? ' checked' : ''}><span><b>${esc(t('pp.mode.' + m))}</b></span></label>`).join('');
    let body;
    if (pp.mode === 'photo') body = photoBlock(pp);
    else if (pp.mode === 'exam') body = `<p class="pp-note">${esc(t('pp.examNote'))}</p>`;
    else body = kind === 'contacts' ? contactsRx(p, pp) : glassesRx(kind === 'frame' ? byId[pp.lens] : p, pp);
    return `<fieldset class="pp-block"><legend>${esc(t('pp.rx'))}</legend><div class="choices choices-modes">${cards}</div>${body}</fieldset>`;
  }
  function formHTML(p, pp, kind) {
    const contacts = kind === 'contacts', perEye = contacts && pp.mode === 'enter';
    let h = sharedDefs(p).filter(d => !contacts || d.type === 'swatch').map(d => optHTML(d, pp.sel, 'p')).join('');
    if (kind === 'frame') h += lensBlock(pp);
    if (contacts || kind === 'lens' || (kind === 'frame' && pp.lens)) h += rxBlock(p, pp, kind);
    return h + '<div class="pp-buy">' +
      (perEye ? '' : (contacts ? `<span class="pp-qty-label">${esc(t('pp.boxes'))}</span>` : '') + stepper('data-pp-qty', 'pp-q', pp.qty, contacts ? 'pp.boxes' : 'qty')) +
      `<p class="pp-total"><span>${esc(t('pp.total'))}</span><b id="ppTotal"></b><small id="ppSumNote" hidden></small></p></div>` +
      '<p class="form-error" id="ppError" role="alert" hidden></p>' +
      `<button type="submit" class="btn btn-primary btn-block" id="ppAdd">${esc(t('pm.add'))}</button>`;
  }
  function related(p) {
    const same = PRODUCTS.filter(x => x.cat === p.cat), i = same.indexOf(p), out = [];
    for (let k = 1; k < same.length && out.length < 3; k++) out.push(same[(i + k) % same.length]);
    return out;
  }
  function ppSum(p, pp) {
    const kind = kindOf(p), unit = unitPrice(p, pp.sel);
    if (kind === 'contacts' && pp.mode === 'enter') return { total: unit * (pp.same ? pp.bothQty : pp.eyes.od.qty + pp.eyes.os.qty) };
    if (kind === 'frame' && pp.lens) {
      const lu = unitPrice(byId[pp.lens], pp.lensSel);
      return { total: (unit + lu) * pp.qty, a: unit * pp.qty, b: lu * pp.qty };
    }
    return { total: unit * pp.qty };
  }
  function ppUpdate() {
    const pp = state.page ? state.pps[state.page] : null, tot = $('#ppTotal');
    if (!pp || !tot) return;
    const p = byId[pp.id], s = ppSum(p, pp), note = $('#ppSumNote');
    tot.textContent = money(s.total);
    note.hidden = s.b == null;
    note.textContent = s.b == null ? '' : t('pp.sumParts', { a: money(s.a), b: money(s.b) });
    $$('#productPage .js-pp-art').forEach(el => { el.innerHTML = art(p, pp.sel.color); });
  }
  function renderPPForm() {
    const f = $('#ppForm'), pp = state.page ? state.pps[state.page] : null;
    if (!f || !pp) return;
    const p = byId[pp.id];
    f.innerHTML = formHTML(p, pp, kindOf(p));
    ppUpdate();
  }
  function renderPP() {
    const box = $('#productPage');
    if (!box || !state.page) return;
    const p = byId[state.page], pp = ppState(p.id), rows = L(p.info) || [], rel = related(p);
    const bd = badges(p).map(x => `<span class="badge${x.sale ? ' is-sale' : ''}">${esc(x.t)}</span>`).join('');
    box.innerHTML = `<div class="wrap">
      <nav class="pp-crumbs" aria-label="${esc(t('pp.crumbs'))}"><a href="#catalog" data-goto="all">${esc(t('pp.catalog'))}</a><span aria-hidden="true">/</span><a href="#catalog" data-goto="${p.cat}">${esc(catName(p.cat))}</a></nav>
      <div class="pp-grid">
        <div class="pp-media"><div class="pp-stage"><div class="js-pp-art"></div>${bd ? `<div class="card-badges">${bd}</div>` : ''}</div></div>
        <div class="pp-main">
          ${brandName(p) ? `<p class="pp-brand">${esc(brandName(p))}</p>` : ''}
          <h1 class="pp-name" id="ppName" tabindex="-1">${esc(L(p.name))}</h1>
          <p class="pp-sub">${esc(L(p.sub))}</p>
          <p class="pp-price">${priceLabel(p)}${p.old ? `<s><span class="vh">${esc(t('oldPrice'))} </span>${money(p.old)}</s>` : ''}</p>
          <form class="pp-form" id="ppForm" novalidate></form>
          ${rows.length ? `<h2 class="pp-h">${esc(t('pp.details'))}</h2><dl class="pm-info">${rows.map(r => `<div><dt>${esc(r[0])}</dt><dd>${esc(r[1])}</dd></div>`).join('')}</dl>` : ''}
        </div>
      </div>
      ${rel.length && TH.card ? `<div class="pp-related"><h2>${esc(t('pp.related'))}</h2><div class="grid">${rel.map(x => TH.card(x)).join('')}</div></div>` : ''}
    </div>`;
    renderPPForm();
  }
  function ppValidate(p, pp) {
    const kind = kindOf(p), errs = [], photo = pp.mode === 'photo';
    const need = (defs, sel) => defs.filter(d => d.required && !sel[d.k]);
    const short = d => (d.short ? L(d.short) : labelOf(d));
    if (!(kind === 'contacts' && photo)) {
      const m = need(sharedDefs(p), pp.sel);
      if (m.length) errs.push({ msg: t('chooseMissing', { list: m.map(d => labelOf(d)).join(', ') }), ids: m.map(d => 'pp-p-' + d.k) });
    }
    if (kind === 'contacts') {
      if (photo) { if (!pp.photo) errs.push({ msg: t('e.photo'), ids: ['pp-photo'] }); return errs; }
      const rows = pp.same ? [['both', pp.eyes.od, pp.bothQty]] : [['od', pp.eyes.od, pp.eyes.od.qty], ['os', pp.eyes.os, pp.eyes.os.qty]];
      const active = rows.filter(r => r[2] > 0);
      if (!active.length) errs.push({ msg: t('e.eyeNone'), ids: ['pp-q-od-inc'] });
      active.forEach(r => {
        const m = need(eyeDefs(p), r[1]);
        if (m.length) errs.push({ msg: t('e.eyeMissing', { eye: t('pp.' + r[0]), list: m.map(short).join(', ') }), ids: m.map(d => `pp-${r[0]}-${d.k}`) });
      });
      return errs;
    }
    if (kind === 'lens' || (kind === 'frame' && pp.lens)) {
      const rp = kind === 'lens' ? p : byId[pp.lens];
      if (kind === 'frame') {
        const m = need(defsOf(rp), pp.lensSel);
        if (m.length) errs.push({ msg: t('chooseMissing', { list: m.map(d => labelOf(d)).join(', ') }), ids: m.map(d => 'pp-l-' + d.k) });
      }
      if (photo) { if (!pp.photo) errs.push({ msg: t('e.photo'), ids: ['pp-photo'] }); }
      else if (pp.mode === 'enter') {
        if (!pp.eyes.od.sph && !pp.eyes.os.sph) errs.push({ msg: t('e.sphOne'), ids: ['pp-od-sph', 'pp-os-sph'] });
        ['od', 'os'].forEach(e => {
          const s = pp.eyes[e];
          if (!s.cyl) return;
          if (!s.sph && (pp.eyes.od.sph || pp.eyes.os.sph)) errs.push({ msg: t('e.eyeMissing', { eye: t('pp.' + e), list: 'SPH' }), ids: [`pp-${e}-sph`] });
          if (!/^\d{1,3}$/.test(s.ax) || +s.ax > 180) errs.push({ msg: t('e.ax', { eye: t('pp.' + e) }), ids: [`pp-${e}-ax`] });
        });
        if (rp.add && !pp.add) errs.push({ msg: t('e.addReq'), ids: ['pp-add'] });
      }
    }
    return errs;
  }
  // Что именно попадёт в корзину со страницы товара
  function ppItems(p, pp) {
    const kind = kindOf(p), items = [], copy = o => Object.assign({}, o);
    const photoRx = () => ({ mode: 'photo', photo: { id: pp.photo.id, name: pp.photo.name } });
    if (kind === 'contacts') {
      if (pp.mode === 'photo') { items.push({ id: p.id, sel: copy(pp.sel), rx: photoRx(), qty: pp.qty }); return items; }
      const rows = pp.same ? [['both', pp.eyes.od, pp.bothQty]] : [['od', pp.eyes.od, pp.eyes.od.qty], ['os', pp.eyes.os, pp.eyes.os.qty]];
      rows.filter(r => r[2] > 0).forEach(r => {
        const sel = copy(pp.sel);
        eyeDefs(p).forEach(d => { sel[d.k] = r[1][d.k]; });
        items.push({ id: p.id, sel, eye: r[0], qty: r[2] });
      });
      return items;
    }
    if (kind === 'plain' || (kind === 'frame' && !pp.lens)) { items.push({ id: p.id, sel: copy(pp.sel), qty: pp.qty }); return items; }
    const rp = kind === 'lens' ? p : byId[pp.lens];
    const eye = s => ({ sph: s.sph, cyl: s.cyl, ax: s.cyl ? String(+s.ax) : '' });
    const rx = pp.mode === 'photo' ? photoRx() : pp.mode === 'exam' ? { mode: 'exam' }
      : { mode: 'enter', od: eye(pp.eyes.od), os: eye(pp.eyes.os), pd: pp.pd, add: rp.add ? pp.add : '' };
    if (kind === 'lens') items.push({ id: p.id, sel: copy(pp.sel), rx, qty: pp.qty });
    else {
      items.push({ id: p.id, sel: copy(pp.sel), qty: pp.qty });
      items.push({ id: rp.id, sel: copy(pp.lensSel), rx, frame: { id: p.id, color: pp.sel.color || '' }, qty: pp.qty });
    }
    return items;
  }
  function ppAdd() {
    const pp = state.page ? state.pps[state.page] : null;
    if (!pp) return;
    const p = byId[pp.id], errs = ppValidate(p, pp), er = $('#ppError');
    $$('#ppForm .is-invalid').forEach(el => el.classList.remove('is-invalid'));
    if (errs.length) {
      er.innerHTML = errs.map(x => esc(x.msg)).join('<br>');
      er.hidden = false;
      let first = null;
      errs.forEach(x => x.ids.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        const w = el.closest('.rxb-cell, .opt, .rx-photo');
        if (w) w.classList.add('is-invalid');
        if (!first) first = el;
      }));
      if (first) first.focus();
      return;
    }
    er.hidden = true;
    const items = ppItems(p, pp);
    items.forEach(addItem);
    const extra = items.filter(it => it.id !== p.id).map(it => L(byId[it.id].name));
    toast(t('added', { name: [L(p.name)].concat(extra).join(' + ') }));
  }
  function bindPP() {
    const box = $('#productPage');
    if (!box) return;
    const cur = () => (state.page ? state.pps[state.page] : null);
    const rerender = focusId => {
      const a = document.activeElement, id = focusId || (a && box.contains(a) ? a.id : '');
      renderPPForm();
      const el = id ? document.getElementById(id) : null;
      if (el) el.focus({ preventScroll: true });
    };
    const unmark = el => { const w = el.closest('.is-invalid'); if (w) w.classList.remove('is-invalid'); };
    const clearErr = () => { const er = $('#ppError'); if (er) { er.hidden = true; er.textContent = ''; } };
    box.addEventListener('change', e => {
      const tg = e.target, pp = cur();
      if (!pp || !tg.closest('#ppForm')) return;
      const p = byId[pp.id], ds = tg.dataset;
      if (tg.id === 'pp-photo') { if (tg.files && tg.files[0]) { setPhoto(pp, tg.files[0]); rerender('pp-photo'); } return; }
      if (tg.name === 'pp-mode') { pp.mode = tg.value; rerender(); return; }
      if (tg.name === 'pp-lens-on') { setLens(pp, tg.value ? (pp.lastLens || (lensList()[0] || {}).id) : ''); rerender(); return; }
      if (tg.name === 'pp-lens') { setLens(pp, tg.value); rerender(); return; }
      if (tg.id === 'pp-same') {
        pp.same = tg.checked;
        if (!pp.same) eyeDefs(p).forEach(d => { if (!pp.eyes.os[d.k]) pp.eyes.os[d.k] = pp.eyes.od[d.k]; });
        rerender();
        return;
      }
      if (tg.id === 'pp-pd') { pp.pd = tg.value; return; }
      if (tg.id === 'pp-add') { pp.add = tg.value; unmark(tg); return; }
      if (ds.eye && ds.opt) { pp.eyes[ds.eye === 'both' ? 'od' : ds.eye][ds.opt] = tg.value; unmark(tg); return; }
      if (ds.eye && ds.rx) {
        const st = pp.eyes[ds.eye];
        st[ds.rx] = tg.value;
        if (ds.rx === 'cyl') {
          const ax = document.getElementById(`pp-${ds.eye}-ax`);
          if (ax) { ax.disabled = !tg.value; if (!tg.value) { ax.value = ''; st.ax = ''; unmark(ax); } }
        }
        unmark(tg);
        return;
      }
      if (ds.opt) {
        const forLens = ds.scope === 'l', sel = forLens ? pp.lensSel : pp.sel, owner = forLens ? byId[pp.lens] : p;
        if (tg.value) sel[ds.opt] = tg.value; else delete sel[ds.opt];
        if (ds.opt === 'color') {
          const lab = tg.closest('.opt').querySelector('.js-sw-current');
          if (lab) lab.textContent = valLabel(defsOf(owner)[0], tg.value);
          if (!forLens) { state.sel[p.id] = colorIdx(p, tg.value); syncCard(p.id); }
        }
        unmark(tg);
        ppUpdate();
      }
    });
    // Сообщение об ошибке убираем, когда покупатель что-то меняет. Именно по событию input: событие change
    // у текстового поля приходит в момент нажатия на кнопку, кнопка сдвинулась бы под курсором, и клик пропал бы
    box.addEventListener('input', e => {
      const tg = e.target, pp = cur();
      if (!pp || !tg.closest('#ppForm')) return;
      clearErr();
      if (tg.dataset.rx !== 'ax') return;
      const v = tg.value.replace(/\D/g, '').slice(0, 3);
      if (v !== tg.value) tg.value = v;
      pp.eyes[tg.dataset.eye].ax = v;
      unmark(tg);
    });
    box.addEventListener('click', e => {
      const pp = cur();
      if (!pp) return;
      const q = e.target.closest('[data-pp-qty]');
      if (q) { pp.qty = clamp(pp.qty + (+q.dataset.dir), 1, 99); q.parentNode.querySelector('output').textContent = pp.qty; ppUpdate(); return; }
      const eq = e.target.closest('[data-eye-qty]');
      if (eq) {
        const eye = eq.dataset.eyeQty, dir = +eq.dataset.dir;
        clearErr();
        if (eye === 'both') { pp.bothQty = clamp(pp.bothQty + dir, 1, 99); eq.parentNode.querySelector('output').textContent = pp.bothQty; }
        else {
          const st = pp.eyes[eye], was = st.qty;
          st.qty = clamp(was + dir, 0, 99);
          if ((was === 0) !== (st.qty === 0)) rerender(eq.id); else eq.parentNode.querySelector('output').textContent = st.qty;
        }
        ppUpdate();
        return;
      }
      if (e.target.closest('[data-photo-remove]')) { pp.photo = null; clearErr(); rerender('pp-photo'); }
    });
    box.addEventListener('submit', e => { if (e.target.id === 'ppForm') { e.preventDefault(); ppAdd(); } });
  }

  /* ---------- адреса страниц: главная, страницы товаров и страницы сайта («Каталог», «О нас», «Блог», «Контакты») ----------
     ?product=код — страница товара;  ?page=catalog|about|blog|contacts — страница сайта;
     ?page=catalog&cat=раздел&aud=для-кого — раздел каталога;  ?page=blog&post=код — статья блога */
  const ROUTE_KEYS = ['product', 'page', 'post', 'cat', 'aud', 'brand'];
  let homeScroll = 0;
  const VIEWS = (TH.views || []).concat(TH.view ? ['checkout'] : []);
  // Когда сайт работает на сервере (PHP), адреса обычные: /catalog, /product/f-milan, /blog/care.
  // Когда страница открыта как файл — прежние: ?page=catalog, ?product=f-milan.
  const PATHS = !!CONFIG.pathRoutes;
  const BASE = PATHS ? String(CONFIG.basePath || '/').replace(/\/*$/, '/') : '';
  function locRoute() {
    const out = { product: '', view: '', post: '' };
    try {
      if (PATHS) {
        let path = decodeURIComponent(window.location.pathname);
        if (path.indexOf(BASE) === 0) path = path.slice(BASE.length);
        const seg = path.replace(/^\/+|\/+$/g, '').split('/');
        if (seg[0] === 'product' && byId[seg[1]]) out.product = seg[1];
        else if (VIEWS.indexOf(seg[0]) !== -1) { out.view = seg[0]; out.post = seg[0] === 'blog' ? (seg[1] || '') : ''; }
      } else {
        const sp = new URLSearchParams(window.location.search), id = sp.get('product'), v = sp.get('page');
        if (id && byId[id]) out.product = id;
        else if (v && VIEWS.indexOf(v) !== -1) { out.view = v; out.post = sp.get('post') || ''; }
      }
    } catch (e) { /* ничего */ }
    return out;
  }
  function pageFromURL() { return locRoute().product; }
  function viewFromURL() { const r = locRoute(); return { view: r.view, post: r.post }; }
  // Адрес с нужными параметрами; язык и прочие параметры сохраняются
  function urlWith(set) {
    const sp = new URLSearchParams(window.location.search);
    ROUTE_KEYS.forEach(k => sp.delete(k));
    if (PATHS) {
      let path = BASE;
      if (set.product) path += 'product/' + encodeURIComponent(set.product);
      else if (set.page) path += encodeURIComponent(set.page) + (set.post ? '/' + encodeURIComponent(set.post) : '');
      ['cat', 'aud', 'brand'].forEach(k => { if (set[k]) sp.set(k, set[k]); });
      const q = sp.toString();
      return path + (q ? '?' + q : '');
    }
    Object.keys(set).forEach(k => { if (set[k]) sp.set(k, set[k]); });
    return '?' + sp.toString();
  }
  // Адрес раздела каталога, например ?page=catalog&cat=frames
  function hrefCatalog(cat, aud) {
    try { return urlWith({ page: 'catalog', cat: cat && cat !== 'all' ? cat : '', aud: aud || '' }); }
    catch (e) { return '?page=catalog' + (cat && cat !== 'all' ? '&cat=' + encodeURIComponent(cat) : ''); }
  }
  // Раздел каталога из адреса (при открытии страницы и по кнопкам «Назад» и «Вперёд»)
  function catalogFromURL() {
    try {
      const sp = new URLSearchParams(window.location.search), c = sp.get('cat'), a = sp.get('aud'), br = sp.get('brand');
      state.cat = c && catById[c] ? c : 'all';
      state.aud = a && audById[a] ? a : '';
      state.brands = br ? br.split(',').filter(id => brandById[id]) : [];
      if (c !== null || a !== null || br !== null) { state.q = ''; const si = $('#searchInput'); if (si) si.value = ''; }
      renderCatalog();
    } catch (e) { /* ничего */ }
  }
  // Выбранный раздел записываем в адрес, чтобы ссылкой на него можно было поделиться
  function syncCatalogURL() {
    if (state.view !== 'catalog') return;
    try {
      const u = new URL(window.location.href), had = u.search;
      if (state.cat && state.cat !== 'all') u.searchParams.set('cat', state.cat); else u.searchParams.delete('cat');
      if (state.aud) u.searchParams.set('aud', state.aud); else u.searchParams.delete('aud');
      if (state.brands.length) u.searchParams.set('brand', state.brands.join(',')); else u.searchParams.delete('brand');
      if (u.search !== had) { window.history.replaceState(null, '', u.toString()); setMeta(); syncNav(); }
    } catch (e) { /* ничего */ }
  }
  function hrefFor(id) {
    try { return urlWith({ product: id }); } catch (e) { return '?product=' + encodeURIComponent(id); }
  }
  function hrefView(view, post) {
    try { return urlWith({ page: view, post: post || '' }); }
    catch (e) { return '?page=' + encodeURIComponent(view) + (post ? '&post=' + encodeURIComponent(post) : ''); }
  }
  // Страница сайта: её текст и разметку даёт оформление (THEME.view)
  function renderView() {
    const box = $('#pageView');
    if (!box || !state.view || !TH.view || state.view === 'checkout') return;
    const old = $('#contactForm', box), keep = old ? CT_KEEP.map(k => (old.elements[k] ? old.elements[k].value : '')) : null;
    const v = TH.view(state.view, state.post) || {};
    state.post = v.post || '';
    state.viewInfo = v;
    box.innerHTML = v.html || '';
    $$('[data-icon]', box).forEach(el => { el.innerHTML = ICON[el.dataset.icon] || ''; });
    fillConfig();
    const f = $('#contactForm', box);
    if (f) {
      prefill(f);
      if (keep) CT_KEEP.forEach((k, i) => { if (f.elements[k] && keep[i]) f.elements[k].value = keep[i]; });
      $$('input[type="tel"]', f).forEach(bindPhone);
      renderContactPhoto();
    }
  }
  // Ссылки на страницы сайта: адрес с текущим языком и отметка открытой страницы в меню
  function syncNav() {
    $$('a[data-view]').forEach(a => {
      a.setAttribute('href', hrefView(a.dataset.view, a.dataset.post || ''));
      if (!a.closest('.nav, .ft-nav')) return;
      if (a.dataset.view === state.view) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
  }
  // Мгновенный переход к месту на странице (без плавной прокрутки через весь сайт)
  function jump(target) {
    const root = document.documentElement, prev = root.style.scrollBehavior;
    root.style.scrollBehavior = 'auto';
    if (typeof target === 'number') window.scrollTo(0, target);
    else if (target) target.scrollIntoView({ block: 'start' });
    root.style.scrollBehavior = prev;
  }
  function setMeta() {
    const p = state.page ? byId[state.page] : null, v = !p && state.view && state.viewInfo && state.viewInfo.title ? state.viewInfo : null;
    const inCat = v && state.view === 'catalog' && state.cat !== 'all' && catById[state.cat] ? state.cat : '';
    const title = p ? L(p.name) + ' — ' + CONFIG.shopName : v ? (inCat ? catName(inCat) + ' — ' : '') + v.title + ' — ' + CONFIG.shopName : t('meta.title');
    if (title !== 'meta.title') document.title = title;
    const md = $('meta[name="description"]'), desc = p ? L(p.name) + '. ' + L(p.sub) + '.' : v && v.desc ? v.desc : t('meta.desc');
    if (md && desc !== 'meta.desc') md.setAttribute('content', desc);
    // Адрес страницы для поисковиков и для ссылок, которыми делятся в мессенджерах
    const put = (sel, attr, v) => { const el = $(sel); if (el && v) el.setAttribute(attr, v); };
    if (CONFIG.siteUrl) {
      const q = [];
      let path = '';
      if (lang !== LANGS[0]) q.push('lang=' + lang);
      if (PATHS) path = p ? 'product/' + encodeURIComponent(p.id) : v ? encodeURIComponent(state.view) + (state.post ? '/' + encodeURIComponent(state.post) : '') : '';
      else {
        if (p) q.push('product=' + encodeURIComponent(p.id));
        if (v) { q.push('page=' + encodeURIComponent(state.view)); if (state.post) q.push('post=' + encodeURIComponent(state.post)); }
      }
      if (inCat) q.push('cat=' + encodeURIComponent(inCat));
      if (v && state.view === 'catalog' && state.aud) q.push('aud=' + encodeURIComponent(state.aud));
      const url = String(CONFIG.siteUrl).replace(/\/+$/, '') + '/' + path + (q.length ? '?' + q.join('&') : '');
      put('link[rel="canonical"]', 'href', url);
      put('meta[property="og:url"]', 'content', url);
    }
    put('meta[property="og:title"]', 'content', title !== 'meta.title' ? title : '');
    put('meta[property="og:description"]', 'content', desc !== 'meta.desc' ? desc : '');
    put('meta[property="og:site_name"]', 'content', CONFIG.shopName);
  }
  function showPage(o) {
    o = o || {};
    const box = $('#productPage'), id = box ? pageFromURL() : '';
    const vbox = $('#pageView');
    let vw = !id && vbox && TH.view ? viewFromURL() : { view: '', post: '' };
    // Ссылка на блок, который живёт на отдельной странице (например #catalog), открывает эту страницу
    if (!id && !vw.view && vbox && TH.view && o.hash && o.hash.length > 1) {
      const el = document.getElementById(o.hash.slice(1)), part = el ? el.closest('[data-in-view]') : null;
      if (part && VIEWS.indexOf(part.dataset.inView) !== -1) {
        vw = { view: part.dataset.inView, post: '' };
        try {
          if (PATHS) window.history.replaceState(null, '', urlWith({ page: vw.view }) + o.hash);
          else { const u = new URL(window.location.href); u.searchParams.set('page', vw.view); window.history.replaceState(null, '', u.toString()); }
        } catch (e) { /* ничего */ }
      }
    }
    state.page = id;
    state.view = vw.view;
    state.post = vw.post;
    state.viewInfo = null;
    document.body.classList.toggle('is-product', !!id);
    document.body.classList.toggle('is-view', !!vw.view);
    VIEWS.forEach(v => document.body.classList.toggle('is-view-' + v, v === vw.view));
    if (box) box.hidden = !id;
    const isCo = vw.view === 'checkout', cpage = $('#checkoutPage');
    if (vbox) { vbox.hidden = !vw.view || isCo; if (!vw.view || isCo) vbox.innerHTML = ''; }
    if (cpage) cpage.hidden = !isCo;
    closeMenu();
    if (vw.view === 'catalog' && (o.restore || o.init)) catalogFromURL();
    if (isCo) renderCheckoutPage(); else if (vw.view) renderView();
    setMeta();
    syncNav();
    if (id) {
      const pp = ppState(id);
      if (byId[id].colors && state.sel[id] != null) pp.sel.color = String(state.sel[id]);
      renderPP();
      jump(0);
      if (o.focus) { const h = $('#ppName'); if (h) h.focus({ preventScroll: true }); }
    }
    if (vw.view) {
      const at = o.hash && o.hash.length > 1 ? document.getElementById(o.hash.slice(1)) : null;
      if (o.restore && typeof o.y === 'number') jump(o.y);
      else if (at && at.getClientRects().length) jump(at);
      else jump(0);
      if (o.focus && !at) { const h = isCo ? $('#coTitle') : $('#pgTitle'); if (h) h.focus({ preventScroll: true }); }
    }
    if (TH.onRoute) TH.onRoute(id || vw.view);
    if (id || vw.view) return;
    const target = o.hash && o.hash.length > 1 ? document.getElementById(o.hash.slice(1)) : null;
    if (target) jump(target);
    else if (o.restore) jump(typeof o.y === 'number' ? o.y : homeScroll);
    else if (o.top) jump(0);
  }
  // to: код товара, { view, post } для страницы сайта или пустая строка для главной
  function navigate(to, o) {
    o = o || {};
    const r = typeof to === 'string' ? { product: to } : (to || {});
    const id = r.product || '', view = !id && r.view ? r.view : '', post = view && r.post ? r.post : '';
    let url;
    const inCatalog = view === 'catalog';
    const extra = { cat: inCatalog && state.cat !== 'all' ? state.cat : '', aud: inCatalog ? state.aud : '', brand: inCatalog ? state.brands.join(',') : '' };
    try {
      if (PATHS) url = urlWith(Object.assign({ product: id, page: view, post }, extra)) + (o.hash || '');
      else {
        const u = new URL(window.location.href);
        ROUTE_KEYS.forEach(k => u.searchParams.delete(k));
        if (id) u.searchParams.set('product', id);
        if (view) u.searchParams.set('page', view);
        if (post) u.searchParams.set('post', post);
        Object.keys(extra).forEach(k => { if (extra[k]) u.searchParams.set(k, extra[k]); });
        u.hash = o.hash || '';
        url = u.toString();
      }
    } catch (e) { url = (id ? hrefFor(id) : view ? hrefView(view, post) : window.location.pathname) + (o.hash || ''); }
    if (!state.page && !state.view) homeScroll = window.scrollY;
    // Запоминаем место на текущей странице, чтобы кнопка «Назад» вернула туда же
    if (!o.replace) { try { window.history.replaceState({ y: window.scrollY }, ''); } catch (e) { /* ничего */ } }
    // Если браузер не даёт сменить адрес без перезагрузки, открываем страницу обычным переходом
    try { if (o.replace) window.history.replaceState(null, '', url); else window.history.pushState(null, '', url); } catch (e) { window.location.href = url; return; }
    showPage({ hash: o.hash, focus: !!(id || view), top: !id && !view });
  }

  /* ---------- страница «Контакты»: сообщение в WhatsApp (имя, телефон, услуга, текст, фото рецепта) ---------- */
  const CT_KEEP = ['name', 'phone', 'topic', 'message'];
  const ctState = { photo: null };   // фото рецепта, выбранное в форме «Напишите нам»
  function renderContactPhoto() {
    const box = $('#ctPhotoBox');
    if (!box) return;
    const ph = ctState.photo, input = '<input class="vh" type="file" id="ct-photo" accept="image/*,application/pdf">';
    const note = `<p class="hint">${esc(t('ct.photoNote'))}</p>`;
    if (!ph) {
      box.innerHTML = `<div class="rx-photo">${input}<label class="rx-drop" for="ct-photo"><span class="rx-drop-icon">${ICON.camera}</span><span><b>${esc(t('pp.photoPick'))}</b><small>${esc(t('pp.photoFormats'))}</small></span></label>${note}</div>`;
      return;
    }
    const thumb = ph.url ? `<img class="rx-thumb" src="${esc(ph.url)}" alt="">` : `<span class="rx-thumb">${ICON.doc}</span>`;
    box.innerHTML = `<div class="rx-photo">${input}<div class="rx-file">${thumb}<p class="rx-file-name">${esc(ph.name)}</p>` +
      `<p class="rx-file-acts"><label class="btn-text" for="ct-photo">${esc(t('pp.photoChange'))}</label><button type="button" class="btn-text" data-ct-photo-remove>${esc(t('pp.photoRemove'))}</button></p></div>${note}</div>`;
  }
  function submitContact(f) {
    clearErrors(f);
    const errs = [];
    if (val(f, 'name').length < 2) errs.push([f.elements.name, 'e.name']);
    { const n = digitsCount(val(f, 'phone')); if (n < 9) errs.push([f.elements.phone, 'e.phone']); else if (n > 15) errs.push([f.elements.phone, 'e.phoneLong']); }
    if (!val(f, 'topic')) errs.push([f.elements.topic, 'e.topic']);
    if (errs.length) { errs.forEach(x => setError(x[0], x[1])); errs[0][0].focus(); return; }
    const ml = msgLang(), M = (k, v) => t(k, v, ml);
    const out = [M('m.helloSite'), '', M('m.topic', { v: M('ct.t.' + val(f, 'topic')) })];
    if (val(f, 'message')) out.push(val(f, 'message'));
    if (ctState.photo) out.push(M('m.rxPhoto'));
    out.push('', M('m.client'), M('m.name', { v: val(f, 'name') }), M('m.phone', { v: val(f, 'phone') }));
    const url = waUrl(out.join('\n'));
    sendToServer('message', { name: val(f, 'name'), phone: val(f, 'phone'), text: out.join('\n'), details: { topic: M('ct.t.' + val(f, 'topic')), comment: val(f, 'message'), rxPhoto: !!ctState.photo } });
    saveCustomer(f);
    openWA(url);
    const photos = ctState.photo ? [ctState.photo] : [];
    f.elements.message.value = '';
    f.elements.topic.value = '';
    ctState.photo = null;
    renderContactPhoto();
    // Фото нельзя вложить в ссылку WhatsApp, поэтому напоминаем отправить его в чат
    if (photos.length) showSuccess('contact', '', url, photos); else toast(t('ct.sent'));
  }

  /* ---------- корзина ---------- */
  function loadCart() {
    const raw = store.get(CART_KEY, []);
    state.cart = (Array.isArray(raw) ? raw : []).map(cleanItem).filter(Boolean);
  }
  // Сохранённую корзину проверяем заново: товар или значение параметра могли убрать из каталога
  function cleanItem(it) {
    if (!it || !byId[it.id] || !(it.qty > 0)) return null;
    const p = byId[it.id], str = v => String(v == null ? '' : v).slice(0, 80);
    const out = { id: it.id, sel: {}, qty: clamp(it.qty | 0, 1, 99) };
    defsOf(p).forEach(d => { const v = it.sel ? it.sel[d.k] : null; if (v != null && d.values.some(x => x.v === String(v))) out.sel[d.k] = String(v); });
    if (it.eye === 'od' || it.eye === 'os' || it.eye === 'both') out.eye = it.eye;
    if (it.frame && byId[it.frame.id]) out.frame = { id: it.frame.id, color: str(it.frame.color) };
    const rx = it.rx, eye = o => ({ sph: str(o && o.sph), cyl: str(o && o.cyl), ax: str(o && o.ax) });
    if (rx && rx.mode === 'enter') out.rx = { mode: 'enter', od: eye(rx.od), os: eye(rx.os), pd: str(rx.pd), add: str(rx.add) };
    else if (rx && rx.mode === 'photo') out.rx = { mode: 'photo', photo: { id: str(rx.photo && rx.photo.id), name: str(rx.photo && rx.photo.name) } };
    else if (rx && rx.mode === 'exam') out.rx = { mode: 'exam' };
    const photo = !!out.rx && out.rx.mode === 'photo';
    return defsOf(p).every(d => !d.required || out.sel[d.k] != null || (photo && d.type !== 'swatch')) ? out : null;
  }
  const saveCart = () => store.set(CART_KEY, state.cart);
  function addItem(item) {
    const k = sigOf(item);
    const ex = state.cart.find(it => sigOf(it) === k);
    if (ex) ex.qty = Math.min(99, ex.qty + item.qty);
    else state.cart.push(JSON.parse(JSON.stringify(item)));
    saveCart();
    renderCart();
    bump();
  }
  function setQty(k, q) {
    const it = state.cart.find(x => sigOf(x) === k);
    if (!it) return;
    if (q <= 0) state.cart = state.cart.filter(x => x !== it);
    else it.qty = Math.min(99, q);
    saveCart();
    renderCart();
  }
  const cartCount = () => state.cart.reduce((s, it) => s + it.qty, 0);
  const cartSubtotal = () => state.cart.reduce((s, it) => s + unitPrice(byId[it.id], it.sel) * it.qty, 0);
  function deliveryCost(sub, method) {
    if (method !== 'courier') return 0;
    const lim = +CONFIG.freeDeliveryFrom || 0;
    return lim && sub >= lim ? 0 : (+CONFIG.deliveryPrice || 0);
  }
  function deliveryNote() {
    const price = +CONFIG.deliveryPrice || 0, lim = +CONFIG.freeDeliveryFrom || 0;
    if (!price) return t('dn.free');
    return lim ? t('dn.priceFree', { price: money(price), lim: money(lim) }) : t('dn.price', { price: money(price) });
  }
  function cartItemHTML(it) {
    const p = byId[it.id], k = sigOf(it), u = unitPrice(p, it.sel), lines = itemLines(it), name = L(p.name);
    if (TH.cartItem) return TH.cartItem({ p, it, k, u, o: lines.join('; '), lines });
    return `<li class="ci" data-key="${esc(k)}">
      <div class="ci-art">${art(p, it.sel.color)}</div>
      <div class="ci-body">
        <p class="ci-name">${esc(name)}</p>
        ${lines.map(x => `<p class="ci-opts">${esc(x)}</p>`).join('')}
        <div class="ci-row">
          <div class="qty qty-sm" role="group" aria-label="${esc(t('qtyOf', { name }))}">
            <button type="button" data-qty="-1" aria-label="${esc(t('qtyDec'))}">${ICON.minus}</button>
            <output>${it.qty}</output>
            <button type="button" data-qty="1" aria-label="${esc(t('qtyInc'))}">${ICON.plus}</button>
          </div>
          <p class="ci-price">${money(u * it.qty)}</p>
        </div>
      </div>
      <button type="button" class="ci-remove" data-remove aria-label="${esc(t('remove', { name }))}">${ICON.x}</button>
    </li>`;
  }
  function renderCart() {
    const n = cartCount();
    $$('.js-cart-count').forEach(el => { el.textContent = n; el.classList.toggle('is-zero', n === 0); });
    const list = $('#cartList');
    if (list) list.innerHTML = state.cart.map(cartItemHTML).join('');
    const empty = $('#cartEmpty');
    if (empty) empty.hidden = n > 0;
    const foot = $('#cartFoot');
    if (foot) foot.hidden = n === 0;
    const sub = cartSubtotal();
    $$('.js-cart-subtotal').forEach(el => { el.textContent = money(sub); });
    const fs = $('#freeShip');
    if (fs) {
      const lim = +CONFIG.freeDeliveryFrom || 0;
      fs.hidden = !lim;
      if (lim) {
        const left = Math.max(0, lim - sub);
        $('.js-fs-text', fs).textContent = left > 0 ? t('cart.freeLeft', { left: money(left) }) : t('cart.freeYes');
        $('.js-fs-bar', fs).style.width = Math.min(100, (sub / lim) * 100) + '%';
      }
    }
    if (state.view === 'checkout') renderCheckoutPage();
  }
  function bindCart() {
    $('#cartList').addEventListener('click', e => {
      const li = e.target.closest('[data-key]');
      if (!li) return;
      const k = li.dataset.key;
      const q = e.target.closest('[data-qty]');
      if (q) {
        const it = state.cart.find(x => sigOf(x) === k);
        if (!it) return;
        const dir = q.dataset.qty;
        setQty(k, it.qty + (+dir));
        const again = $(`#cartList [data-key="${cssEsc(k)}"] [data-qty="${dir}"]`);
        if (again) again.focus();
        else { const first = $('#cartList [data-qty]') || $('#cartDrawer .icon-btn[data-close]'); if (first) first.focus(); }
        return;
      }
      if (e.target.closest('[data-remove]')) {
        setQty(k, 0);
        const next = $('#cartList [data-remove]') || $('#cartDrawer .icon-btn[data-close]');
        if (next) next.focus();
      }
    });
  }
  let bumpT;
  function bump() {
    $$('.js-cart-count').forEach(el => { el.classList.remove('bump'); void el.offsetWidth; el.classList.add('bump'); });
    clearTimeout(bumpT);
    bumpT = setTimeout(() => $$('.js-cart-count').forEach(el => el.classList.remove('bump')), 600);
  }
  let toastT;
  function toast(msg, withCart) {
    const tEl = $('#toast');
    if (!tEl) return;
    $('#toastText').textContent = msg;
    const b = tEl.querySelector('[data-open-cart]');
    if (b) b.hidden = withCart === false;
    tEl.classList.add('is-on');
    clearTimeout(toastT);
    toastT = setTimeout(hideToast, 4000);
  }
  function hideToast() { const tEl = $('#toast'); if (tEl) tEl.classList.remove('is-on'); }

  /* ---------- слои: корзина и окна ---------- */
  const layers = [];
  const isOpen = sel => { const el = $(sel); return !!(el && el.classList.contains('is-open')); };
  function focusables(root) {
    return $$('a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])', root)
      .filter(x => x.getClientRects().length && !x.closest('[hidden]'));
  }
  function openLayer(el) {
    if (!el || el.classList.contains('is-open')) return;
    if (!layers.length) document.documentElement.style.setProperty('--sbw', (window.innerWidth - document.documentElement.clientWidth) + 'px');
    let ret = document.activeElement;
    const host = ret && ret.closest ? ret.closest('.layer') : null;
    if (host && host !== el && !host.classList.contains('is-open') && host._ret) ret = host._ret;
    layers.push({ el, ret });
    el.removeAttribute('inert');
    el.setAttribute('aria-hidden', 'false');
    el.classList.add('is-open');
    document.documentElement.classList.add('is-locked');
    setTimeout(() => { const f = el.querySelector('[data-autofocus]') || focusables(el)[0]; if (f) f.focus({ preventScroll: true }); }, 60);
  }
  function closeLayer(el, keepFocus) {
    const i = layers.findIndex(x => x.el === el);
    if (i < 0) return;
    const ret = layers.splice(i, 1)[0].ret;
    el._ret = ret;
    el.classList.remove('is-open');
    el.setAttribute('aria-hidden', 'true');
    el.setAttribute('inert', '');
    if (!layers.length) document.documentElement.classList.remove('is-locked');
    if (!keepFocus && ret && ret.focus && document.contains(ret)) ret.focus({ preventScroll: true });
  }

  // Подписи с data-i18n переводятся на лету, поэтому введённые данные при смене языка не теряются
  const T = k => `<span data-i18n="${k}">${esc(t(k))}</span>`;
  const A = (attr, k) => `${attr}="${esc(t(k))}" data-i18n-attr="${attr}:${k}"`;
  function layersHTML() {
    const I = ICON;
    const choice = (name, value, msg, titleKey, smallHTML, checked, extra) =>
      `<label class="choice"${extra || ''}><input type="radio" name="${name}" value="${value}" data-msg="${msg}"${checked ? ' checked' : ''}><span><b data-i18n="${titleKey}">${esc(t(titleKey))}</b>${smallHTML || ''}</span></label>`;
    return `
<aside class="layer drawer" id="cartDrawer" role="dialog" aria-modal="true" aria-labelledby="cartTitle" aria-hidden="true" inert>
  <div class="drawer-backdrop" data-close></div>
  <div class="drawer-box">
    <header class="drawer-head"><h2 id="cartTitle" data-i18n="cart.title">${esc(t('cart.title'))}</h2><button type="button" class="icon-btn" data-close ${A('aria-label', 'cart.close')}>${I.x}</button></header>
    <div class="drawer-body">
      <ul class="cart-list" id="cartList"></ul>
      <div class="cart-empty" id="cartEmpty">
        <span class="cart-empty-icon">${I.bag}</span>
        <p data-i18n="cart.empty">${esc(t('cart.empty'))}</p>
        <a class="btn btn-line" href="#catalog" data-close data-i18n="cart.toCatalog">${esc(t('cart.toCatalog'))}</a>
      </div>
    </div>
    <footer class="drawer-foot" id="cartFoot" hidden>
      <div class="free-ship" id="freeShip"><p class="js-fs-text"></p><div class="bar"><i class="js-fs-bar"></i></div></div>
      <div class="cart-sum"><span data-i18n="cart.sum">${esc(t('cart.sum'))}</span><b class="js-cart-subtotal"></b></div>
      <button type="button" class="btn btn-primary btn-block" data-checkout data-i18n="cart.checkout">${esc(t('cart.checkout'))}</button>
    </footer>
  </div>
</aside>

<section class="pg co-page" id="checkoutPage" aria-labelledby="coTitle" hidden>
  <div class="wrap">
  <nav class="pp-crumbs" ${A('aria-label', 'pp.crumbs')}><a href="#top" data-i18n="pg.home">${esc(t('pg.home'))}</a><span aria-hidden="true">/</span><a href="?page=catalog" data-view="catalog" data-i18n="pp.catalog">${esc(t('pp.catalog'))}</a></nav>
  <header class="pg-head"><h1 id="coTitle" tabindex="-1" data-i18n="co.title">${esc(t('co.title'))}</h1></header>
  <div class="co-empty" id="coEmpty" hidden>
    <p data-i18n="cart.empty">${esc(t('cart.empty'))}</p>
    <a class="btn btn-primary" href="?page=catalog" data-view="catalog" data-goto="all" data-i18n="cart.toCatalog">${esc(t('cart.toCatalog'))}</a>
  </div>
  <form class="co" id="checkoutForm" novalidate>
    <div class="co-grid">
      <div class="co-fields">
        <fieldset class="co-set">
          <legend data-i18n="co.contacts">${esc(t('co.contacts'))}</legend>
          <div class="row2">
            <div class="field"><label for="coName" data-i18n="f.name">${esc(t('f.name'))}</label><input id="coName" name="name" type="text" autocomplete="name" required><p class="field-error"></p></div>
            <div class="field"><label for="coPhone" data-i18n="f.phone">${esc(t('f.phone'))}</label><input id="coPhone" name="phone" type="tel" autocomplete="tel" inputmode="tel" placeholder="+994 50 000 00 00" required><p class="field-error"></p></div>
          </div>
        </fieldset>
        <fieldset class="co-set">
          <legend data-i18n="co.delivery">${esc(t('co.delivery'))}</legend>
          <div class="choices">
            ${choice('delivery', 'pickup', 'ml.pickup', 'co.pickup', '<small data-cfg="address"></small>', true)}
            ${choice('delivery', 'courier', 'ml.courier', 'co.courier', '<small class="js-delivery-note"></small>')}
          </div>
          <div class="field" id="coAddressField" hidden><label for="coAddress" data-i18n="co.address">${esc(t('co.address'))}</label><textarea id="coAddress" name="address" rows="2" autocomplete="street-address" ${A('placeholder', 'co.addressPh')}></textarea><p class="field-error"></p></div>
        </fieldset>
        <fieldset class="co-set">
          <legend data-i18n="co.payment">${esc(t('co.payment'))}</legend>
          <div class="choices choices-3">
            ${choice('payment', 'cash', 'ml.cash', 'pay.cash', T('pay.onDelivery').replace('<span', '<small').replace('</span>', '</small>'), true)}
            ${choice('payment', 'card', 'ml.card', 'pay.card', T('pay.onDelivery').replace('<span', '<small').replace('</span>', '</small>'))}
            ${choice('payment', 'transfer', 'ml.transfer', 'pay.transfer', T('pay.transferNote').replace('<span', '<small').replace('</span>', '</small>'))}
          </div>
        </fieldset>
        <div class="field"><label for="coComment">${T('co.comment')} <span class="opt-note" data-i18n="optional">${esc(t('optional'))}</span></label><textarea id="coComment" name="comment" rows="2" ${A('placeholder', 'co.commentPh')}></textarea></div>
      </div>
      <aside class="co-summary">
        <h3 data-i18n="co.summary">${esc(t('co.summary'))}</h3>
        <ul class="co-items" id="coItems"></ul>
        <dl class="co-totals">
          <div><dt data-i18n="co.items">${esc(t('co.items'))}</dt><dd id="coSubtotal"></dd></div>
          <div><dt data-i18n="co.deliveryRow">${esc(t('co.deliveryRow'))}</dt><dd id="coDelivery"></dd></div>
          <div class="co-total"><dt data-i18n="co.total">${esc(t('co.total'))}</dt><dd id="coTotal"></dd></div>
        </dl>
        <button type="submit" class="btn btn-primary btn-block btn-wa">${I.chat}${T('co.submit')}</button>
        <p class="co-note" data-i18n="co.note">${esc(t('co.note'))}</p>
      </aside>
    </div>
  </form>
  </div>
</section>

<div class="layer modal modal-ok" id="successModal" role="dialog" aria-modal="true" aria-labelledby="okTitle" aria-hidden="true" inert>
  <div class="modal-backdrop" data-close></div>
  <div class="modal-box ok">
    <span class="ok-icon">${I.check}</span>
    <h2 id="okTitle"></h2>
    <p id="okText"></p>
    <div class="ok-photo" id="okPhoto" hidden><p id="okPhotoText"></p><button type="button" class="btn btn-accent btn-block" id="okShare" hidden>${T('ok.share')}</button></div>
    <a class="btn btn-primary btn-block" id="okWa" href="#" target="_blank" rel="noopener">${I.chat}${T('ok.again')}</a>
    <button type="button" class="btn btn-line btn-block" data-close data-i18n="ok.back">${esc(t('ok.back'))}</button>
  </div>
</div>

<div class="toast" id="toast" role="status" aria-live="polite"><span id="toastText"></span><button type="button" data-open-cart data-i18n="toast.cart">${esc(t('toast.cart'))}</button></div>
<a class="wa-float" data-cfg-href="wa" href="#" target="_blank" rel="noopener" ${A('aria-label', 'wa.fab')}>${I.chat}</a>`;
  }
  function repairFormHTML(titleKey) {
    const k = titleKey || 'rp.title';
    return `<h3 class="rf-title" data-i18n="${k}">${esc(t(k))}</h3>
      <div class="row2">
        <div class="field"><label for="rpName" data-i18n="f.name">${esc(t('f.name'))}</label><input id="rpName" name="name" type="text" autocomplete="name" required><p class="field-error"></p></div>
        <div class="field"><label for="rpPhone" data-i18n="f.phone">${esc(t('f.phone'))}</label><input id="rpPhone" name="phone" type="tel" autocomplete="tel" inputmode="tel" placeholder="+994 50 000 00 00" required><p class="field-error"></p></div>
      </div>
      <fieldset class="field"><legend data-i18n="rp.what">${esc(t('rp.what'))}</legend><div class="chips" id="rpServices"></div><p class="field-error"></p></fieldset>
      <div class="field"><label for="rpDesc">${T('rp.desc')} <span class="opt-note" data-i18n="optional">${esc(t('optional'))}</span></label><textarea id="rpDesc" name="desc" rows="3" ${A('placeholder', 'rp.descPh')}></textarea></div>
      <fieldset class="field"><legend data-i18n="rp.how">${esc(t('rp.how'))}</legend>
        <div class="choices choices-2">
          <label class="choice"><input type="radio" name="handover" value="salon" data-msg="ml.salon" checked><span><b data-i18n="rp.salon">${esc(t('rp.salon'))}</b></span></label>
          <label class="choice"><input type="radio" name="handover" value="courier" data-msg="ml.courierPick"><span><b data-i18n="rp.courier">${esc(t('rp.courier'))}</b></span></label>
        </div>
      </fieldset>
      <div class="field" id="rpAddressField" hidden><label for="rpAddress" data-i18n="rp.address">${esc(t('rp.address'))}</label><textarea id="rpAddress" name="address" rows="2" autocomplete="street-address" ${A('placeholder', 'rp.addressPh')}></textarea><p class="field-error"></p></div>
      <div class="field"><label for="rpDate">${T('rp.date')} <span class="opt-note" data-i18n="optional">${esc(t('optional'))}</span></label><input id="rpDate" name="date" type="date"></div>
      <button type="submit" class="btn btn-primary btn-block btn-wa">${ICON.chat}${T('rp.submit')}</button>
      <p class="form-note" data-i18n="rp.note">${esc(t('rp.note'))}</p>`;
  }

  /* ---------- формы: ошибки и помощники ---------- */
  let errSeq = 0;
  function setError(el, key) {
    const fld = el.closest('.field') || el.parentElement;
    fld.classList.add('is-invalid');
    let p = $('.field-error', fld);
    if (!p) { p = document.createElement('p'); p.className = 'field-error'; fld.appendChild(p); }
    if (!p.id) p.id = 'err-' + (++errSeq);
    p.textContent = t(key);
    p.dataset.errKey = key;
    el.setAttribute('aria-invalid', 'true');
    el.setAttribute('aria-describedby', p.id);
  }
  function clearFieldError(fld) {
    fld.classList.remove('is-invalid');
    const p = $('.field-error', fld);
    if (p) { p.textContent = ''; delete p.dataset.errKey; }
    $$('[aria-invalid]', fld).forEach(x => x.removeAttribute('aria-invalid'));
  }
  const clearErrors = f => $$('.field.is-invalid', f).forEach(clearFieldError);
  const val = (f, n) => (f.elements[n] && f.elements[n].value != null ? String(f.elements[n].value).trim() : '');
  const radioVal = (f, n) => { const r = f.querySelector(`input[name="${n}"]:checked`); return r ? r.value : ''; };
  const radioMsg = (f, n, ml) => { const r = f.querySelector(`input[name="${n}"]:checked`); return r ? t(r.dataset.msg, null, ml) : ''; };

  function toggleField(f, name, value, sel) { const el = $(sel); if (el) el.hidden = radioVal(f, name) !== value; }

  function bindPhone(inp) {
    const pre = CONFIG.phonePrefix || '';
    const cc = pre.replace(/\D/g, '');
    inp.addEventListener('focus', () => {
      if (!inp.value && pre) {
        inp.value = pre;
        setTimeout(() => { try { inp.setSelectionRange(inp.value.length, inp.value.length); } catch (e) { /* ничего */ } }, 0);
      }
    });
    inp.addEventListener('blur', () => {
      if (pre && inp.value.trim() === pre.trim()) { inp.value = ''; return; }
      if (cc && inp.value.replace(/\D/g, '').indexOf(cc + cc) === 0) inp.value = inp.value.replace(cc, '').replace(/^\+\s*/, '+');
      // «+994 050…» → «+994 50…»: в международном формате ноль после кода страны не набирают
      const head = pre.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      if (head) inp.value = inp.value.replace(new RegExp('^(' + head + '\\s*)0(?=\\d)'), '$1');
      // Азербайджанский номер показываем группами: +994 50 123 45 67 (в том числе из «050 123 45 67»)
      if (cc === '994') {
        const raw = inp.value.trim(), d = raw.replace(/\D/g, '');
        let n = '';
        if (d.length === 12 && d.indexOf('994') === 0) n = d.slice(3);
        else if (raw.charAt(0) !== '+' && d.length === 10 && d.charAt(0) === '0') n = d.slice(1);
        else if (raw.charAt(0) !== '+' && d.length === 9) n = d;
        if (n) inp.value = `+994 ${n.slice(0, 2)} ${n.slice(2, 5)} ${n.slice(5, 7)} ${n.slice(7)}`;
      }
    });
    inp.addEventListener('input', () => {
      let v = inp.value.replace(/[^\d+()\-\s]/g, '');
      const i = v.lastIndexOf('+');
      if (i > 0) v = v.slice(i);
      if (v !== inp.value) inp.value = v;
    });
  }
  function prefill(f) {
    const c = store.get(CUSTOMER_KEY, null);
    if (!c || !f) return;
    ['name', 'phone', 'address'].forEach(k => { if (f.elements[k] && !f.elements[k].value && c[k]) f.elements[k].value = c[k]; });
  }
  function saveCustomer(f) {
    const c = store.get(CUSTOMER_KEY, {}) || {};
    ['name', 'phone', 'address'].forEach(k => { const v = val(f, k); if (v) c[k] = v; });
    store.set(CUSTOMER_KEY, c);
  }
  // Если сайт работает на сервере (PHP), заказ, заявка и сообщение сохраняются ещё и там: список виден в админ-панели.
  // Отправка идёт в фоне и не мешает открыть WhatsApp.
  function sendToServer(kind, data) {
    if (!CONFIG.api || typeof fetch !== 'function') return;
    try {
      const body = JSON.stringify(Object.assign({ kind, lang, token: CONFIG.apiToken || '' }, data));
      fetch(CONFIG.api, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body, keepalive: true, credentials: 'same-origin' }).catch(() => { /* сеть недоступна: заказ всё равно уйдёт в WhatsApp */ });
    } catch (e) { /* ничего */ }
  }
  function waUrl(text) {
    const num = String(CONFIG.whatsapp || '').replace(/\D/g, '');
    return 'https://wa.me/' + num + (text ? '?text=' + encodeURIComponent(text) : '');
  }
  function openWA(url) {
    const w = window.open(url, '_blank');
    if (w) { try { w.opener = null; } catch (e) { /* ничего */ } } else { window.location.href = url; }
  }
  function renderSuccess() {
    const ok = state.ok;
    if (!ok) return;
    const order = ok.kind === 'order';
    const contact = ok.kind === 'contact';
    $('#okTitle').textContent = t(order ? 'ok.orderTitle' : contact ? 'ok.contactTitle' : 'ok.repairTitle');
    $('#okText').innerHTML = contact ? esc(t('ok.contactText'))
      : esc(t(order ? 'ok.orderText' : 'ok.repairText', { id: '\u0000' })).replace('\u0000', `<b>${esc(ok.id)}</b>`);
    $('#okWa').href = ok.url;
    // Фото рецепта нельзя вложить в ссылку WhatsApp, поэтому напоминаем отправить его в чат
    const photos = ok.photos || [], box = $('#okPhoto');
    box.hidden = !photos.length;
    if (photos.length) {
      const share = canShare(ok.files);
      $('#okPhotoText').textContent = t('ok.photo') + (share ? '' : ' ' + t('ok.photoHow', { names: photos.map(x => x.name).join(', ') }));
      $('#okShare').hidden = !share;
    }
  }
  function canShare(files) {
    try { return !!(files && files.length && navigator.canShare && navigator.canShare({ files })); } catch (e) { return false; }
  }
  function sharePhotos() {
    const files = (state.ok && state.ok.files) || [];
    if (canShare(files)) navigator.share({ files }).catch(() => { /* покупатель закрыл окно «Поделиться» */ });
  }
  function showSuccess(kind, id, url, photos) {
    state.ok = { kind, id, url, photos: photos || [], files: (photos || []).map(x => photoFiles[x.id]).filter(Boolean) };
    renderSuccess();
    openLayer($('#successModal'));
  }

  /* ---------- оформление заказа ---------- */
  // Оформление заказа — отдельная страница сайта (?page=checkout)
  function openCheckout() {
    if (!state.cart.length) return;
    const dr = $('#cartDrawer');
    if (dr && dr.classList.contains('is-open')) closeLayer(dr, true);
    hideToast();
    if (state.view === 'checkout') { renderCheckoutPage(); jump(0); return; }
    navigate({ view: 'checkout' });
  }
  function renderCheckoutPage() {
    const f = $('#checkoutForm'), none = !state.cart.length, em = $('#coEmpty');
    state.viewInfo = { title: t('co.title'), desc: '' };
    if (em) em.hidden = !none;
    if (!f) return;
    f.hidden = none;
    prefill(f);
    toggleField(f, 'delivery', 'courier', '#coAddressField');
    renderCheckoutSummary();
  }
  function renderCheckoutSummary() {
    const f = $('#checkoutForm');
    if (!f) return;
    const sub = cartSubtotal(), method = radioVal(f, 'delivery') || 'pickup', del = deliveryCost(sub, method);
    $('#coItems').innerHTML = state.cart.map(it => {
      const p = byId[it.id], u = unitPrice(p, it.sel);
      return `<li><span class="co-i-name">${esc(L(p.name))}${itemLines(it).map(x => `<small>${esc(x)}</small>`).join('')}</span><span class="co-i-qty">${esc(t('pcs', { n: it.qty })).replace(' ', NB)}</span><span class="co-i-sum">${money(u * it.qty)}</span></li>`;
    }).join('');
    $('#coSubtotal').textContent = money(sub);
    $('#coDelivery').textContent = method === 'courier' ? (del ? money(del) : t('free')) : t('pickupShort');
    $('#coTotal').textContent = money(sub + del);
  }
  function submitOrder(e) {
    e.preventDefault();
    const f = e.currentTarget;
    if (!state.cart.length) { renderCheckoutPage(); return; }
    clearErrors(f);
    const errs = [];
    if (val(f, 'name').length < 2) errs.push([f.elements.name, 'e.name']);
    { const n = digitsCount(val(f, 'phone')); if (n < 9) errs.push([f.elements.phone, 'e.phone']); else if (n > 15) errs.push([f.elements.phone, 'e.phoneLong']); }
    const method = radioVal(f, 'delivery');
    if (method === 'courier' && val(f, 'address').length < 5) errs.push([f.elements.address, 'e.address']);
    if (errs.length) { errs.forEach(x => setError(x[0], x[1])); errs[0][0].focus(); return; }

    const ml = msgLang(), M = (k, v) => t(k, v, ml), $m = n => money(n, ml);
    const sub = cartSubtotal(), del = deliveryCost(sub, method), id = makeId('OP');
    const out = [M('m.helloOrder'), '', M('m.order', { id }), nowStr(), '', M('m.items')];
    state.cart.forEach((it, i) => {
      const p = byId[it.id], u = unitPrice(p, it.sel);
      out.push(`${i + 1}. ${L(p.name, ml)}`);
      itemLines(it, ml, true).forEach(x => out.push(`    ${x}`));
      out.push(`    ${it.qty} × ${$m(u)} = ${$m(u * it.qty)}`);
    });
    out.push('', M('m.itemsSum', { v: $m(sub) }));
    out.push(M('m.delivery', { v: method === 'courier' ? (del ? $m(del) : M('free')) : M('pickupShort') }));
    out.push(M('m.total', { v: $m(sub + del) }), '', M('m.customer'));
    out.push(M('m.name', { v: val(f, 'name') }), M('m.phone', { v: val(f, 'phone') }), M('m.receive', { v: radioMsg(f, 'delivery', ml) }));
    if (method === 'courier') out.push(M('m.address', { v: val(f, 'address') }));
    out.push(M('m.payment', { v: radioMsg(f, 'payment', ml) }));
    if (val(f, 'comment')) out.push('', M('m.comment', { v: val(f, 'comment') }));

    const url = waUrl(out.join('\n'));
    sendToServer('order', {
      number: id, name: val(f, 'name'), phone: val(f, 'phone'), total: sub + del, text: out.join('\n'),
      details: {
        delivery: method, address: method === 'courier' ? val(f, 'address') : '', payment: radioVal(f, 'payment'), comment: val(f, 'comment'), subtotal: sub, deliveryCost: del,
        items: state.cart.map(it => { const p = byId[it.id], u = unitPrice(p, it.sel); return { id: it.id, name: L(p.name, ml), lines: itemLines(it, ml, true), qty: it.qty, price: u, sum: u * it.qty }; }),
      },
    });
    saveCustomer(f);
    prefill($('#repairForm'));
    openWA(url);
    const photos = [];
    state.cart.forEach(it => { if (it.rx && it.rx.mode === 'photo' && !photos.some(x => x.id === it.rx.photo.id)) photos.push(it.rx.photo); });
    state.cart = [];
    saveCart();
    renderCart();
    if (f.elements.comment) f.elements.comment.value = '';
    // Заказ отправлен: возвращаем на главную (без лишней записи в истории) и показываем подсказку
    navigate('', { replace: true });
    showSuccess('order', id, url, photos);
  }

  /* ---------- заявка на ремонт ---------- */
  const svcPrice = s => (s.from ? priceFrom(s.price) : money(s.price));
  function renderServiceList() {
    const list = $('#servicesList');
    if (!list) return;
    list.innerHTML = SERVICES.map(s => {
      const ss = { id: s.id, name: L(s.name), time: L(s.time) };
      return TH.service ? TH.service(ss, svcPrice(s))
        : `<li><button type="button" class="svc" data-svc="${s.id}" aria-pressed="false"><span class="svc-name">${esc(ss.name)}</span><span class="svc-time">${esc(ss.time)}</span><span class="svc-price">${svcPrice(s)}</span></button></li>`;
    }).join('');
  }
  function renderChips() {
    const chips = $('#rpServices');
    if (!chips) return;
    const on = $$('input[name="svc"]:checked', chips).map(i => i.value);
    chips.innerHTML = SERVICES.map(s =>
      `<label class="chip"><input type="checkbox" name="svc" value="${s.id}" data-svc-id="${s.id}"${on.indexOf(s.id) !== -1 ? ' checked' : ''}><span>${esc(L(s.name))}</span></label>`).join('');
  }
  function renderServices() {
    renderServiceList();
    const form = $('#repairForm');
    if (form && !form.children.length) form.innerHTML = repairFormHTML(form.dataset.titleKey);
    renderChips();
    const date = $('#rpDate');
    if (date) { const d = new Date(); date.min = `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`; }
    syncServiceRows();
  }
  function syncServiceRows() {
    $$('[data-svc]').forEach(b => {
      const cb = $(`#rpServices input[data-svc-id="${cssEsc(b.dataset.svc)}"]`);
      const on = !!(cb && cb.checked);
      b.classList.toggle('is-picked', on);
      b.setAttribute('aria-pressed', on);
    });
  }
  function flashChip(cb) {
    const chip = cb.closest('.chip');
    chip.classList.remove('flash'); void chip.offsetWidth; chip.classList.add('flash');
  }
  function pickService(id) {
    const cb = $(`#rpServices input[data-svc-id="${cssEsc(id)}"]`);
    if (!cb) return;
    cb.checked = !cb.checked;
    const fld = cb.closest('.field');
    if (fld) clearFieldError(fld);
    syncServiceRows();
    if (cb.checked) {
      flashChip(cb);
      const s = SERVICES.find(x => x.id === id);
      toast(t('addedSvc', { name: s ? L(s.name) : '' }), false);
      const form = $('#repairForm');
      const r = form.getBoundingClientRect();
      if (r.top > window.innerHeight * 0.8 || r.bottom < 80) form.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' });
    }
  }
  // Кнопки вроде «Записаться на проверку зрения»: отмечают услугу и ведут к форме
  function selectService(id) {
    const cb = $(`#rpServices input[data-svc-id="${cssEsc(id)}"]`);
    if (!cb) return;
    cb.checked = true;
    const fld = cb.closest('.field');
    if (fld) clearFieldError(fld);
    syncServiceRows();
    flashChip(cb);
    const form = $('#repairForm');
    form.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' });
    setTimeout(() => { const n = form.elements.name; if (n && !n.value) n.focus({ preventScroll: true }); }, reduced() ? 0 : 700);
  }
  function submitRepair(e) {
    e.preventDefault();
    const f = e.currentTarget;
    clearErrors(f);
    const ids = $$('input[name="svc"]:checked', f).map(i => i.value);
    const errs = [];
    if (val(f, 'name').length < 2) errs.push([f.elements.name, 'e.name']);
    { const n = digitsCount(val(f, 'phone')); if (n < 9) errs.push([f.elements.phone, 'e.phone']); else if (n > 15) errs.push([f.elements.phone, 'e.phoneLong']); }
    if (!ids.length) errs.push([$('input[name="svc"]', f), 'e.svc']);
    const how = radioVal(f, 'handover');
    if (how === 'courier' && val(f, 'address').length < 5) errs.push([f.elements.address, 'e.pickupAddr']);
    if (errs.length) { errs.forEach(x => setError(x[0], x[1])); errs[0][0].focus(); return; }

    const ml = msgLang(), M = (k, v) => t(k, v, ml);
    const names = ids.map(id => { const s = SERVICES.find(x => x.id === id); return s ? L(s.name, ml) : id; });
    const id = makeId('R');
    const out = [M('m.helloRepair'), '', M('m.request', { id }), nowStr(), '', M('m.services', { v: names.join(', ') })];
    if (val(f, 'desc')) out.push(M('m.desc', { v: val(f, 'desc') }));
    out.push(M('m.handover', { v: radioMsg(f, 'handover', ml) }));
    if (how === 'courier') out.push(M('m.address', { v: val(f, 'address') }));
    const d = val(f, 'date');
    if (d) { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d); out.push(M('m.date', { v: m ? `${m[3]}.${m[2]}.${m[1]}` : d })); }
    out.push('', M('m.client'), M('m.name', { v: val(f, 'name') }), M('m.phone', { v: val(f, 'phone') }));

    const url = waUrl(out.join('\n'));
    sendToServer('repair', { number: id, name: val(f, 'name'), phone: val(f, 'phone'), text: out.join('\n'), details: { services: names, handover: how, address: how === 'courier' ? val(f, 'address') : '', date: val(f, 'date'), comment: val(f, 'desc') } });
    saveCustomer(f);
    prefill($('#checkoutForm'));
    openWA(url);
    $$('input[name="svc"]', f).forEach(i => { i.checked = false; });
    if (f.elements.desc) f.elements.desc.value = '';
    if (f.elements.date) f.elements.date.value = '';
    syncServiceRows();
    showSuccess('repair', id, url);
  }

  /* ---------- контакты из настроек ---------- */
  function fillConfig() {
    const map = {
      shopName: CONFIG.shopName, phone: CONFIG.phone, address: L(CONFIG.address),
      year: String(new Date().getFullYear()), instagram: CONFIG.instagram ? '@' + CONFIG.instagram : '',
      delivery: deliveryNote(), freeFrom: CONFIG.freeDeliveryFrom ? money(CONFIG.freeDeliveryFrom) : '',
      deliveryPrice: money(CONFIG.deliveryPrice || 0),
    };
    $$('[data-cfg]').forEach(el => {
      const k = el.dataset.cfg;
      if (k === 'hours') el.innerHTML = (L(CONFIG.hours) || []).map(esc).join('<br>');
      else if (map[k] != null) el.textContent = map[k];
    });
    $$('.js-delivery-note').forEach(el => { el.textContent = deliveryNote(); });
    const wa = waUrl(t('m.question', null, msgLang()));
    $$('[data-cfg-href]').forEach(el => {
      const k = el.dataset.cfgHref;
      if (k === 'wa') el.href = wa;
      else if (k === 'tel') el.href = 'tel:' + String(CONFIG.phone).replace(/[^\d+]/g, '');
      else if (k === 'map') el.href = 'https://maps.google.com/?q=' + encodeURIComponent(CONFIG.mapQuery || L(CONFIG.address));
      else if (k === 'ig') {
        if (CONFIG.instagram) el.href = 'https://instagram.com/' + encodeURIComponent(CONFIG.instagram);
        else (el.closest('[data-cfg-wrap]') || el).hidden = true;
      }
    });
    $$('iframe[data-cfg-map]').forEach(fr => {
      const src = 'https://maps.google.com/maps?q=' + encodeURIComponent(CONFIG.mapQuery || L(CONFIG.address)) + '&z=15&hl=' + lang + '&output=embed';
      if (!fr.dataset.src || fr.dataset.lang !== lang) { fr.src = src; fr.dataset.src = '1'; fr.dataset.lang = lang; }
    });
    if (!fillConfig.warned && /^9940+$/.test(String(CONFIG.whatsapp)) && (fillConfig.warned = true)) console.warn('Optika: укажите свой номер WhatsApp в CONFIG.whatsapp, чтобы заказы приходили вам.');
  }

  /* ---------- языки ---------- */
  function renderLangSwitch() {
    $$('[data-lang-switch]').forEach(box => {
      box.hidden = LANGS.length < 2;
      box.innerHTML = LANGS.map(l => `<button type="button" data-set-lang="${l}" lang="${l}" title="${LANG_NAMES[l] || l}" aria-pressed="${l === lang}" class="${l === lang ? 'is-active' : ''}">${l.toUpperCase()}</button>`).join('');
    });
  }
  function applyLang() {
    document.documentElement.lang = lang;
    $$('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    $$('[data-i18n-html]').forEach(el => { el.innerHTML = t(el.dataset.i18nHtml); });
    $$('[data-i18n-attr]').forEach(el => el.dataset.i18nAttr.split(';').forEach(pair => {
      const i = pair.indexOf(':');
      if (i > 0) el.setAttribute(pair.slice(0, i).trim(), t(pair.slice(i + 1).trim()));
    }));
    setMeta();
    $$('.field-error[data-err-key]').forEach(p => { p.textContent = t(p.dataset.errKey); });
    fillConfig();
    renderLangSwitch();
    renderCatalog();
    renderAudiences();
    renderServiceList();
    renderChips();
    syncServiceRows();
    renderCart();
    if (state.page) renderPP();
    if (state.view === 'checkout') renderCheckoutPage();
    if (state.view) { renderView(); setMeta(); }
    syncNav();
    if (isOpen('#successModal')) renderSuccess();
    if (TH.onLang) TH.onLang(lang);
  }
  function setLang(l) {
    if (LANGS.indexOf(l) === -1 || l === lang) return;
    lang = l;
    store.set(LANG_KEY, l);
    try { const u = new URL(window.location.href); u.searchParams.set('lang', l); window.history.replaceState(null, '', u.toString()); } catch (e) { /* ничего */ }
    applyLang();
  }

  /* ---------- шапка, меню и клавиатура ---------- */
  function closeMenu() {
    document.body.classList.remove('menu-open');
    $$('.js-menu-toggle').forEach(b => b.setAttribute('aria-expanded', 'false'));
  }
  function bindNav() {
    $$('.js-menu-toggle').forEach(tg => tg.addEventListener('click', () => {
      const on = !document.body.classList.contains('menu-open');
      document.body.classList.toggle('menu-open', on);
      tg.setAttribute('aria-expanded', on);
    }));
    const nav = $('#siteNav');
    if (nav) nav.addEventListener('click', e => { if (e.target.closest('a')) closeMenu(); });
    const header = $('.site-header');
    if (header) {
      const on = () => header.classList.toggle('is-scrolled', window.scrollY > 8);
      window.addEventListener('scroll', on, { passive: true });
      on();
    }
  }
  function onDocClick(e) {
    const tg = e.target;
    const a = tg.closest('a');
    if (a && e.button === 0 && !(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)) {
      // Ссылка на товар открывает его страницу без перезагрузки
      if (a.dataset.product && byId[a.dataset.product]) {
        e.preventDefault();
        const layer = a.closest('.layer');
        if (layer) closeLayer(layer, true);
        hideToast();
        navigate(a.dataset.product);
        return;
      }
      // Ссылка на страницу сайта («О нас», «Блог», «Контакты», статья) тоже открывается без перезагрузки
      if (a.dataset.view && VIEWS.indexOf(a.dataset.view) !== -1 && TH.view && $('#pageView')) {
        e.preventDefault();
        const layer = a.closest('.layer');
        if (layer) closeLayer(layer, true);
        hideToast();
        // Ссылка на раздел каталога сразу выбирает раздел, чтобы он попал в адрес
        if (a.dataset.goto) { state.cat = a.dataset.goto; state.aud = audById[a.dataset.aud] ? a.dataset.aud : ''; state.brands = []; }
        navigate({ view: a.dataset.view, post: a.dataset.post || '' }, { hash: a.dataset.hash || '' });
        if (!a.dataset.goto) return;
      }
      // Ссылки вида #раздел: блок может быть на главной, на странице каталога или на открытой странице
      const href = a.getAttribute('href') || '';
      if (href.charAt(0) === '#' && !a.dataset.view) {
        const target = href.length > 1 ? document.getElementById(href.slice(1)) : null;
        const part = target ? target.closest('[data-in-view]') : null, own = part && VIEWS.indexOf(part.dataset.inView) !== -1 ? part.dataset.inView : '';
        if (own) {
          // блок живёт на отдельной странице (каталог): открываем её, если она ещё не открыта
          if (state.view !== own) {
            e.preventDefault();
            const layer = a.closest('.layer');
            if (layer && !a.hasAttribute('data-close')) closeLayer(layer, true);
            if (a.dataset.goto) { state.cat = a.dataset.goto; state.aud = audById[a.dataset.aud] ? a.dataset.aud : ''; state.brands = []; }
            navigate({ view: own }, { hash: href });
          }
        } else if ((state.page || state.view) && (!target || !target.closest('#productPage, #pageView'))) {
          // со страницы товара и со страниц сайта ссылки на разделы главной сначала возвращают на главную
          e.preventDefault();
          navigate('', { hash: href.length > 1 ? href : '' });
        }
      }
    }
    const close = tg.closest('[data-close]');
    if (close) {
      const layer = close.closest('.layer');
      if (layer) {
        const href = close.getAttribute('href');
        if (!(href && href.charAt(0) === '#')) e.preventDefault();
        closeLayer(layer);
      }
      return;
    }
    const sl = tg.closest('[data-set-lang]');
    if (sl) { e.preventDefault(); setLang(sl.dataset.setLang); return; }
    if (tg.closest('[data-open-cart]')) { e.preventDefault(); hideToast(); openLayer($('#cartDrawer')); return; }
    if (tg.closest('[data-checkout]')) { e.preventDefault(); openCheckout(); return; }
    const ps = tg.closest('[data-pick-svc]');
    if (ps) { e.preventDefault(); selectService(ps.dataset.pickSvc); return; }
    const g = tg.closest('[data-goto]');
    if (g) {
      state.cat = g.dataset.goto;
      state.aud = audById[g.dataset.aud] ? g.dataset.aud : '';
      state.brands = [];
      state.q = '';
      const si = $('#searchInput');
      if (si) si.value = '';
      renderCatalog();
      closeMenu();
      return;
    }
    // Сортировка и бренды в каталоге
    const sb = tg.closest('[data-sort]');
    if (sb) { state.sort = sb.dataset.sort; renderProducts(); return; }
    const bb = tg.closest('[data-brand]');
    if (bb) {
      const id = bb.dataset.brand, i = state.brands.indexOf(id);
      if (i === -1) state.brands.push(id); else state.brands.splice(i, 1);
      renderCatalog();
      const again = $(`#brandList [data-brand="${cssEsc(id)}"]`);
      if (again) again.focus();
      return;
    }
    const au = tg.closest('[data-aud]');
    if (au) {
      const sw = au.closest('[data-aud-switch]'), key = au.dataset.key;
      state.aud = audById[au.dataset.aud] ? au.dataset.aud : '';
      renderCatalog();
      // Кнопки фильтра перерисовываются, поэтому возвращаем фокус на ту же кнопку
      if (sw) { const again = sw.querySelector(`[data-key="${cssEsc(key)}"]`); if (again) again.focus(); }
    }
  }
  function onKey(e) {
    if (!layers.length) {
      if (e.key === 'Escape' && document.body.classList.contains('menu-open')) closeMenu();
      return;
    }
    const top = layers[layers.length - 1].el;
    if (e.key === 'Escape') { e.preventDefault(); closeLayer(top); return; }
    if (e.key === 'Tab') {
      const f = focusables(top);
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (!top.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
      else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }
  function bindAll() {
    const tabs = $('#catTabs');
    if (tabs) tabs.addEventListener('click', e => { const b = e.target.closest('[data-cat]'); if (b) { state.cat = b.dataset.cat; renderBrands(); renderProducts(); } });
    const si = $('#searchInput');
    if (si) { let tm; si.addEventListener('input', () => { clearTimeout(tm); tm = setTimeout(() => { state.q = si.value.trim(); renderProducts(); }, 120); }); }
    const so = $('#sortSelect');
    if (so) so.addEventListener('change', () => { state.sort = so.value; renderProducts(); });
    $$('[data-reset-filter]').forEach(b => b.addEventListener('click', () => { state.cat = 'all'; state.aud = ''; state.brands = []; state.q = ''; if (si) si.value = ''; renderCatalog(); }));
    document.addEventListener('click', onGridClick);
    bindPP();
    bindCart();
    $('#okShare').addEventListener('click', sharePhotos);
    const cf = $('#checkoutForm');
    cf.addEventListener('submit', submitOrder);
    cf.addEventListener('change', e => {
      const n = e.target.name;
      if (n === 'delivery') { toggleField(cf, 'delivery', 'courier', '#coAddressField'); renderCheckoutSummary(); }
    });
    cf.addEventListener('input', e => { const fld = e.target.closest('.field'); if (fld && fld.classList.contains('is-invalid')) clearFieldError(fld); });
    const rf = $('#repairForm');
    if (rf) {
      rf.addEventListener('submit', submitRepair);
      rf.addEventListener('change', e => {
        if (e.target.name === 'handover') toggleField(rf, 'handover', 'courier', '#rpAddressField');
        if (e.target.name === 'svc') syncServiceRows();
        const fld = e.target.closest('.field');
        if (fld && fld.classList.contains('is-invalid')) clearFieldError(fld);
      });
      rf.addEventListener('input', e => { const fld = e.target.closest('.field'); if (fld && fld.classList.contains('is-invalid')) clearFieldError(fld); });
    }
    const sl = $('#servicesList');
    if (sl) sl.addEventListener('click', e => { const b = e.target.closest('[data-svc]'); if (b) pickService(b.dataset.svc); });
    $$('input[type="tel"]').forEach(bindPhone);
    document.addEventListener('click', onDocClick);
    document.addEventListener('keydown', onKey);
    bindNav();
    // Форма «Напишите нам» на странице контактов (страница перерисовывается, поэтому слушаем документ)
    document.addEventListener('submit', e => { if (e.target.id === 'contactForm') { e.preventDefault(); submitContact(e.target); } });
    document.addEventListener('input', e => {
      const fld = e.target.closest ? e.target.closest('#contactForm .field') : null;
      if (fld && fld.classList.contains('is-invalid')) clearFieldError(fld);
    });
    document.addEventListener('change', e => {
      const el = e.target;
      if (el.id === 'ct-photo' && el.files && el.files[0]) { setPhoto(ctState, el.files[0]); renderContactPhoto(); const again = $('#ct-photo'); if (again) again.focus(); }
      const fld = el.closest ? el.closest('#contactForm .field') : null;
      if (fld && fld.classList.contains('is-invalid')) clearFieldError(fld);
    });
    document.addEventListener('click', e => {
      if (e.target.closest('[data-ct-photo-remove]')) { ctState.photo = null; renderContactPhoto(); const again = $('#ct-photo'); if (again) again.focus(); }
    });
    // Кнопки «Назад» и «Вперёд» в браузере переключают главную, страницы товаров и страницы сайта
    window.addEventListener('popstate', e => {
      if (!state.page && !state.view && !pageFromURL() && !viewFromURL().view) return;
      showPage({ restore: true, hash: window.location.hash, y: e.state && typeof e.state.y === 'number' ? e.state.y : null });
    });
  }

  /* ---------- запуск ---------- */
  window.Shop = {
    CONFIG, state, byId, art, glasses, money, esc, swatches, swAttr, badges, needsOptions, priceLabel, catName,
    colorOf, hexA, icon: n => ICON[n] || '', toast, reduced, waUrl, t, L, setLang, href: hrefFor, hrefView, hrefCatalog, go: navigate, brandName,
    count: itemsCount, priceFrom,
    get lang() { return lang; },
    render: () => renderProducts(),
    setFilter(cat, q) {
      state.cat = cat || 'all';
      state.q = q || '';
      const si = $('#searchInput');
      if (si) si.value = q || '';
      renderProducts();
    },
  };
  function init() {
    injectDefs();
    const wrap = document.createElement('div');
    wrap.innerHTML = layersHTML();
    while (wrap.firstChild) document.body.appendChild(wrap.firstChild);
    const cpage = $('#checkoutPage'), mainEl = $('main');
    if (cpage && mainEl) mainEl.appendChild(cpage);
    renderServices();
    $$('[data-icon]').forEach(el => { el.innerHTML = ICON[el.dataset.icon] || ''; });
    loadCart();
    bindAll();
    applyLang();
    prefill($('#repairForm'));
    if (TH.onInit) TH.onInit();
    showPage({ init: true, hash: window.location.hash });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();

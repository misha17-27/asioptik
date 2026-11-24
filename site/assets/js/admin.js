/* Админ-панель: меню на телефоне, подтверждение удаления, цвет рядом с кодом цвета, язык полей, подготовка фото к загрузке */
(function () {
  'use strict';
  /* Надписи на языке админ-панели приходят вместе со страницей; без них остаются русские. */
  var T = {};
  try { T = JSON.parse(document.getElementById('ao-i18n').textContent) || {}; } catch (err) { /* русские надписи */ }
  function tx(key, ru, vars) {
    var s = typeof T[key] === 'string' && T[key] ? T[key] : ru, k;
    for (k in vars || {}) s = s.split('{' + k + '}').join(vars[k]);
    return s;
  }
  var side = document.querySelector('.side'), btn = document.querySelector('.menu-btn');
  if (side && btn) {
    btn.addEventListener('click', function () {
      var on = !side.classList.contains('is-open');
      side.classList.toggle('is-open', on);
      btn.setAttribute('aria-expanded', on);
    });
  }
  document.addEventListener('submit', function (e) {
    var form = e.target, msg = form.getAttribute && form.getAttribute('data-confirm');
    if (msg && !window.confirm(msg)) return e.preventDefault();
    // Если фото ещё готовится к загрузке, форма уйдёт сразу после этого, а не с исходным большим файлом
    var waiting = [].filter.call(form.querySelectorAll ? form.querySelectorAll('input[type=file]') : [], function (i) { return i._prep; }).map(function (i) { return i._prep; });
    if (!waiting.length) return;
    e.preventDefault();
    var by = e.submitter;
    Promise.all(waiting).then(function () {
      if (form.requestSubmit) form.requestSubmit(by && by.form === form ? by : undefined); else form.submit();
    });
  });
  document.addEventListener('input', function (e) {
    var el = e.target;
    if (!el.closest || !el.closest('.color-row') || el.name.slice(-3) !== '[c]') return;
    var sw = el.closest('.color-row').querySelector('.sw');
    if (sw) sw.style.background = /^#[0-9a-f]{3,8}$/i.test(el.value.trim()) ? el.value.trim() : 'transparent';
  });

  /* Языки в формах — для перевода: слева всегда основной язык сайта (AZ), справа второй язык.
     Кнопки в шапке формы выбирают, какой язык справа; выбор держится до закрытия вкладки.
     Сначала справа язык админ-панели, а если она на основном языке — первый из остальных (RU).
     Если форма вернулась с ошибкой в поле языка, который не открыт, справа открывается он. */
  var LGS = document.querySelector('.lgs'), LG = [].map.call(document.querySelectorAll('[data-lg-set]'), function (b) { return b.getAttribute('data-lg-set'); });
  var UI = LG.indexOf(document.documentElement.lang) < 0 ? LG[0] : document.documentElement.lang, KEEP = 'ao-lg2';
  function setLang(l) {
    if (LG.indexOf(l) < 0) l = UI;
    document.documentElement.setAttribute('data-lg', l);
    [].forEach.call(document.querySelectorAll('[data-lg-set]'), function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-lg-set') === l ? 'true' : 'false');
    });
    try { sessionStorage.setItem(KEEP, l); } catch (err) { /* без памяти вкладки просто не запоминаем */ }
  }
  if (LGS && LG.length && document.querySelector('.lang[data-lg]')) {
    var first = UI;
    try { first = sessionStorage.getItem(KEEP) || UI; } catch (err) { /* ничего */ }
    var bad = document.querySelector('.field.is-invalid .lang .err');
    bad = bad ? bad.closest('.lang') : null;
    if (!bad) {
      var wrong = document.querySelector('.field.is-invalid .langs');
      if (wrong) {
        bad = [].filter.call(wrong.querySelectorAll('.lang'), function (x) {
          var i = x.querySelector('input,textarea');
          return i && !i.value.trim();
        })[0] || null;
      }
    }
    bad = bad ? bad.getAttribute('data-lg') : '';
    setLang(LG.indexOf(bad) < 0 ? first : bad);
    document.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('[data-lg-set]') : null;
      if (b) setLang(b.getAttribute('data-lg-set'));
    });
  }

  /* Место филиала на карте: под полем с координатами стоит карта. Нажатие ставит метку и записывает координаты
     в поле, метку можно перетащить; координаты, вставленные в поле, двигают метку, пустое поле её убирает.
     Карта (библиотека Leaflet из assets/vendor, картинки OpenStreetMap) загружается, только когда такое поле есть. */
  var pick = document.querySelector('[data-map-pick]');
  if (pick) {
    var cin = document.getElementById(pick.getAttribute('data-map-pick')), lib = pick.getAttribute('data-map-lib');
    var coords = function (v) {
      var m = /^\s*(-?\d{1,2}(?:\.\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:\.\d+)?)\s*$/.exec(v || '');
      if (!m) return null;
      return Math.abs(+m[1]) <= 90 && Math.abs(+m[2]) <= 180 ? [+m[1], +m[2]] : null;
    };
    var mapOff = function () { pick.classList.add('is-off'); pick.textContent = pick.getAttribute('data-t-load'); };
    var css = document.createElement('link');
    css.rel = 'stylesheet'; css.href = lib + 'leaflet.css?v=1.9.4';
    document.head.appendChild(css);
    var js = document.createElement('script');
    js.src = lib + 'leaflet.js?v=1.9.4';
    js.onerror = mapOff;
    js.onload = function () {
      var L = window.L;
      if (!L || !cin) { mapOff(); return; }
      var at = coords(cin.value);
      var map = L.map(pick, { scrollWheelZoom: false, zoomControl: false }).setView(at || coords(pick.getAttribute('data-map-center')) || [40.3777, 49.892], at ? 16 : 12);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19, referrerPolicy: 'strict-origin-when-cross-origin',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'
      }).addTo(map);
      map.attributionControl.setPrefix(false);
      L.control.zoom({ zoomInTitle: pick.getAttribute('data-t-in'), zoomOutTitle: pick.getAttribute('data-t-out') }).addTo(map);
      var pin = L.divIcon({
        className: 'map-pin', iconSize: [28, 38], iconAnchor: [14, 37],
        html: '<svg viewBox="0 0 28 38" aria-hidden="true"><path d="M14 37S27 23.500 27 13.500a13 13 0 0 0-26 0C1 23.500 14 37 14 37z" fill="#C8431E" stroke="#fff" stroke-width="2"/><circle cx="14" cy="13.500" r="4.800" fill="#fff"/></svg>'
      });
      var mark = null;
      var put = function (ll, write) {
        if (!mark) {
          mark = L.marker(ll, { icon: pin, draggable: true, keyboard: false }).addTo(map);
          mark.on('dragend', function () { put(mark.getLatLng(), true); });
        } else mark.setLatLng(ll);
        if (write) {
          var q = mark.getLatLng();
          cin.value = q.lat.toFixed(6) + ', ' + q.lng.toFixed(6);
          pick.setAttribute('data-map-at', cin.value);
        }
      };
      if (at) put(at, false);
      map.on('click', function (e) { put(e.latlng, true); });
      map.once('click', function () { map.scrollWheelZoom.enable(); });   // колесо мыши двигает карту только после нажатия на неё, иначе мешает листать форму
      cin.addEventListener('input', function () {
        var ll = coords(cin.value);
        if (ll) { put(ll, false); map.setView(ll, Math.max(map.getZoom(), 16)); }
        else if (!cin.value.trim() && mark) { map.removeLayer(mark); mark = null; }
      });
      pick.setAttribute('data-map-ready', '1');
      window.__mapPick = map;   // для проверок: test/php_branches.py
    };
    document.head.appendChild(js);
  }

  /* Фото уменьшается прямо в браузере до 2000 точек по длинной стороне:
     большой снимок с телефона проходит любой хостинг и загружается за секунды. Сервер всё равно проверяет и пересохраняет файл. */
  var MAX_SIDE = 2000, KEEP_UNDER = 1500000;
  function size(n) {
    return n >= 1048576 ? (n / 1048576).toFixed(1).replace('.', ',') + ' ' + tx('mb', 'МБ') : Math.max(1, Math.round(n / 1024)) + ' ' + tx('kb', 'КБ');
  }
  function note(input, text, bad) {
    var p = input.parentNode.querySelector('.file-note');
    if (!p) return;
    p.hidden = !text;
    p.textContent = text;
    p.classList.toggle('is-bad', !!bad);
  }
  function preview(input, file) {
    var box = input.closest('.imgf'), img = box && box.querySelector('.thumb');
    if (!box || !window.URL || !URL.createObjectURL) return;
    if (!img) {
      img = document.createElement('img');
      img.className = 'thumb';
      img.alt = '';
      box.insertBefore(img, box.firstChild);
    }
    if (img.dataset.blob) URL.revokeObjectURL(img.dataset.blob);
    img.dataset.blob = img.src = URL.createObjectURL(file);
  }
  function shrink(file) {
    if (!window.createImageBitmap || !window.DataTransfer || !window.File || !HTMLCanvasElement.prototype.toBlob) return Promise.resolve(file);
    return createImageBitmap(file, { imageOrientation: 'from-image' }).then(function (bmp) {
      var k = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
      if (k === 1 && file.size <= KEEP_UNDER) return file;
      var c = document.createElement('canvas'), png = file.type === 'image/png';
      c.width = Math.max(1, Math.round(bmp.width * k));
      c.height = Math.max(1, Math.round(bmp.height * k));
      var ctx = c.getContext('2d');
      if (!png) {   // у PNG сохраняем прозрачный фон, остальным подкладываем белый
        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, c.width, c.height);
      }
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(bmp, 0, 0, c.width, c.height);
      if (bmp.close) bmp.close();
      return new Promise(function (resolve) {
        c.toBlob(function (blob) {
          if (!blob || blob.size >= file.size) return resolve(file);
          var ext = blob.type === 'image/webp' ? 'webp' : (blob.type === 'image/png' ? 'png' : 'jpg');
          resolve(new File([blob], file.name.replace(/\.[^.]*$/, '') + '.' + ext, { type: blob.type }));
        }, png ? 'image/webp' : 'image/jpeg', png ? 0.9 : 0.86);
      });
    }).catch(function () { return file; });
  }
  /* Несколько фото сразу (раздел «Изображения»): каждое готовится так же, затем сверяются число и общий размер */
  function prepMany(input) {
    var files = [].slice.call(input.files || []);
    var max = parseInt(input.getAttribute('data-max'), 10) || 0, total = parseInt(input.getAttribute('data-max-total'), 10) || 0, many = parseInt(input.getAttribute('data-max-files'), 10) || 20;
    if (!files.length) return note(input, '');
    var odd = files.filter(function (f) { return !/^image\/(jpeg|png|webp)$/.test(f.type); })[0];
    if (odd) {
      input.value = '';
      return note(input, tx('fileBad', 'Файл «{name}» не подходит: нужна картинка JPG, PNG или WebP.', { name: odd.name }), true);
    }
    if (files.length > many) {
      input.value = '';
      return note(input, tx('filesMany', 'За один раз можно загрузить не больше {n} фото. Выберите меньше.', { n: many }), true);
    }
    note(input, tx('filePrep', 'Готовлю фото…'));
    input._prep = Promise.all(files.map(shrink)).then(function (out) {
      input._prep = null;
      try {
        var dt = new DataTransfer();
        out.forEach(function (f) { dt.items.add(f); });
        input.dataset.busy = '1';
        input.files = dt.files;
        delete input.dataset.busy;
      } catch (err) { out = files; }
      var sum = out.reduce(function (a, f) { return a + f.size; }, 0);
      var big = out.filter(function (f) { return max && f.size > max; })[0];
      if (big) return note(input, tx('fileBig', 'Файл {size} — больше, чем принимает хостинг ({max}). Уменьшите фото и выберите его снова.', { size: size(big.size), max: size(max) }), true);
      if (total && sum > total) return note(input, tx('filesBig', 'Выбрано {size} — больше, чем хостинг принимает за один раз ({max}). Выберите меньше фото.', { size: size(sum), max: size(total) }), true);
      note(input, tx('filesOk', 'Выбрано фото: {n}, всего {size}. Нажмите «Загрузить».', { n: out.length, size: size(sum) }));
    });
  }
  document.addEventListener('change', function (e) {
    var input = e.target;
    if (!input.matches || !input.matches('input[type=file][data-max]') || input.dataset.busy) return;
    if (input.multiple) return prepMany(input);
    var file = input.files && input.files[0];
    if (!file) return note(input, '');
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) {
      input.value = '';
      return note(input, tx('fileBad', 'Файл «{name}» не подходит: нужна картинка JPG, PNG или WebP.', { name: file.name }), true);
    }
    var max = parseInt(input.getAttribute('data-max'), 10) || 0;
    note(input, tx('filePrep', 'Готовлю фото…'));
    input._prep = shrink(file).then(function (out) {
      input._prep = null;
      if (out !== file) {
        try {
          var dt = new DataTransfer();
          dt.items.add(out);
          input.dataset.busy = '1';
          input.files = dt.files;
          delete input.dataset.busy;
        } catch (err) { out = file; }
      }
      preview(input, out);
      if (max && out.size > max) return note(input, tx('fileBig', 'Файл {size} — больше, чем принимает хостинг ({max}). Уменьшите фото и выберите его снова.', { size: size(out.size), max: size(max) }), true);
      note(input, out !== file ? tx('fileSmall', 'Фото уменьшено: {from} → {to}. Нажмите «Сохранить».', { from: size(file.size), to: size(out.size) })
        : tx('fileOk', 'Фото выбрано: {size}. Нажмите «Сохранить».', { size: size(out.size) }));
    });
  });

  /* Счётчик знаков у SEO-полей: что длиннее нормы, поисковик обрежет. Пустое поле считает текст, который сайт поставит сам. */
  [].forEach.call(document.querySelectorAll('[data-count]'), function (el) {
    var max = parseInt(el.getAttribute('data-count'), 10) || 0;
    var out = document.createElement('span');
    out.className = 'count';
    el.parentNode.appendChild(out);
    function update() {
      var own = el.value.replace(/^\s+|\s+$/g, '').length;
      var n = own || (el.getAttribute('placeholder') || '').length;
      out.textContent = own || !n ? tx('count', '{n} из {max} знаков', { n: n, max: max }) : tx('countAuto', '{n} из {max} знаков — текст сайта', { n: n, max: max });
      out.className = 'count' + (n > max ? ' is-long' : '');
    }
    el.addEventListener('input', update);
    update();
  });

  /* Меню листается отдельно от страницы: открытый раздел должен быть на виду, а не под краем экрана */
  var cur = document.querySelector('#adm-nav a[aria-current]');
  if (cur && cur.scrollIntoView) { try { cur.scrollIntoView({ block: 'nearest' }); } catch (err) { /* старый браузер */ } }

  /* Копирование по нажатию: путь к фото в разделе «Изображения». Кнопка на секунду показывает «Скопировано». */
  function copyText(text, done) {
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
      document.body.removeChild(ta);
      done(ok);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { done(true); }, fallback);
    else fallback();
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('[data-copy]') : null;
    if (!b) return;
    e.preventDefault();
    copyText(b.getAttribute('data-copy'), function (ok) {
      var label = b.querySelector('[data-copy-label]') || b, was = b.getAttribute('data-was') || label.textContent;
      b.setAttribute('data-was', was);
      label.textContent = ok ? tx('copied', 'Скопировано') : tx('copyFail', 'Не скопировалось — выделите и скопируйте вручную');
      b.classList.toggle('is-copied', ok);
      clearTimeout(b._t);
      b._t = setTimeout(function () { label.textContent = was; b.classList.remove('is-copied'); }, 1600);
    });
  });
})();
